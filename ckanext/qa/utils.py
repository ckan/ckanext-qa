"""
Utils for new and old cli
"""
import logging
from sqlalchemy import or_
import sys


log = logging.getLogger(__name__)


def init_db():
    import ckan.model as model
    from ckanext.qa.model import init_tables
    init_tables(model.meta.engine)


def update(*args, **kwargs):
    from ckan import model
    from ckanext.qa import lib
    queue = kwargs.pop('queue')
    if kwargs:
        raise TypeError('"update" got an unexpected keyword argument {}'.format(kwargs))
    
    packages = []
    resources = []
    if len(args) > 0:
        for arg in args:
            # try arg as a group id/name
            group = model.Group.get(arg)
            if group and group.is_organization:
                # group.packages() is unreliable for an organization -
                # member objects are not definitive whereas owner_org, so
                # get packages using owner_org
                query = model.Session.query(model.Package)\
                    .filter(
                        or_(model.Package.state == 'active',
                            model.Package.state == 'pending'))\
                    .filter_by(owner_org=group.id)
                packages.extend(query.all())
                if not queue:
                    queue = 'bulk'
                continue
            elif group:
                packages.extend(group.packages())
                if not queue:
                    queue = 'bulk'
                continue
            # try arg as a package id/name
            pkg = model.Package.get(arg)
            if pkg:
                packages.append(pkg)
                if not queue:
                    queue = 'priority'
                continue
            # try arg as a resource id
            res = model.Resource.get(arg)
            if res:
                resources.append(res)
                if not queue:
                    queue = 'priority'
                continue
            else:
                log.error('Could not recognize as a group, package '
                                'or resource: %r', arg)
                sys.exit(1)
    else:
        # all packages
        pkgs = model.Session.query(model.Package)\
                    .filter_by(state='active')\
                    .order_by('name').all()
        packages.extend(pkgs)
        if not queue:
            queue = 'bulk'

    if packages:
        log.info('Datasets to QA: %d', len(packages))
    if resources:
        log.info('Resources to QA: %d', len(resources))
    if not (packages or resources):
        log.error('No datasets or resources to process')
        sys.exit(1)

    log.info('Queue: %s', queue)
    for package in packages:
        lib.create_qa_update_package_task(package, queue)
        log.info('Queuing dataset %s (%s resources)',
                        package.name, len(package.resources))

    for resource in resources:
        package = resource.resource_group.package
        log.info('Queuing resource %s/%s', package.name, resource.id)
        lib.create_qa_update_task(resource, queue)

    log.info('Completed queueing')
