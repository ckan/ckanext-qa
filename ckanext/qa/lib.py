import os
import json
import re
import logging

import ckan
from ckan.common import config

from ckan import plugins as p
from ckanext.qa import tasks

log = logging.getLogger(__name__)

_RESOURCE_FORMAT_SCORES = None


def compat_enqueue(name, fn, queue, args=None):

    u'''
    Enqueue a background job using Celery or RQ.
    '''
    try:
        # Try to use RQ
        from ckan.plugins.toolkit import enqueue_job
        enqueue_job(fn, args=args, queue=queue)
    except ImportError:
        # Fallback to Celery
        import uuid
        from ckan.lib.celery_app import celery
        celery.send_task(name, args=args + [queue], task_id=str(uuid.uuid4()))


def resource_format_scores():
    ''' Returns the resource formats scores as a dict keyed by format shortname
    (usually extension)

    :param key:  format shortname (usually extension) as defined in ckan's
                 resource_format.json
    :param value:  string
    :returns: openness score (int) - assuming it is accessible and has an open
              licence

    Fuller description of the fields are described in
    `ckan/config/resource_formats.json`.
    '''
    global _RESOURCE_FORMAT_SCORES
    if not _RESOURCE_FORMAT_SCORES:
        _RESOURCE_FORMAT_SCORES = {}
        json_filepath = config.get('qa.resource_format_openness_scores_json')
        import ckanext.qa.plugin
        if not json_filepath:
            json_filepath = os.path.join(
                os.path.dirname(os.path.realpath(ckanext.qa.plugin.__file__)),
                'resource_format_openness_scores.json'
            )
        with open(json_filepath) as format_file:
            try:
                file_resource_formats = json.loads(format_file.read())
            except ValueError as e:
                # includes simplejson.decoder.JSONDecodeError
                raise ValueError('Invalid JSON syntax in %s: %s' %
                                 (json_filepath, e))

            for format_line in file_resource_formats:
                if format_line[0] == '_comment':
                    continue
                format_, score = format_line
                if not isinstance(score, int):
                    raise ValueError('Score must be integer in %s: %s: %r'
                                     % json_filepath, format_, score)
                if format_ in _RESOURCE_FORMAT_SCORES:
                    raise ValueError('Duplicate resource format '
                                     'identifier in %s: %s' %
                                     (json_filepath, format_))
                _RESOURCE_FORMAT_SCORES[format_] = score

    return _RESOURCE_FORMAT_SCORES


def munge_format_to_be_canonical(format_name):
    '''Tries some things to help try and get a resource format to match one of
    the canonical ones
    '''
    format_name = format_name.strip().lower()
    if format_name.startswith('.'):
        format_name = format_name[1:]
    return re.sub('[^a-z/+]', '', format_name)


def create_qa_update_package_task(package, queue):
    ckan_ini_filepath = os.path.abspath(ckan.config.__file__)

    compat_enqueue('qa.update_package', tasks.update_package, queue,  args=[ckan_ini_filepath, package.id])
    log.debug('QA of package put into celery queue %s: %s',
              queue, package.name)


def create_qa_update_task(resource, queue):
    if p.toolkit.check_ckan_version(max_version='2.2.99'):
        package = resource.resource_group.package
    else:
        package = resource.package
    ckan_ini_filepath = os.path.abspath(ckan.config.__file__)

    compat_enqueue('qa.update', tasks.update, queue, args=[ckan_ini_filepath, resource.id])

    log.debug('QA of resource put into celery queue %s: %s/%s url=%r',
              queue, package.name, resource.id, resource.url)
