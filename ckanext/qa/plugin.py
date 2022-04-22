import logging

import ckan.model as model
import ckan.plugins as p

from ckanext.archiver.interfaces import IPipe
from ckanext.qa.logic import action, auth
from ckanext.qa.model import QA, aggregate_qa_for_a_dataset
from ckanext.qa import helpers
from ckanext.report.interfaces import IReport


log = logging.getLogger(__name__)


class QAPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(IPipe, inherit=True)
    p.implements(IReport)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IPackageController, inherit=True)

    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')

    if p.toolkit.check_ckan_version(max_version='2.9.5'):
        p.implements(p.IRoutes, inherit=True)
        # TODO IRoutes was deprecated and we need to figure out
        # if this is important and how to implement
        # https://github.com/ckan/ckan/commit/f2a5bffed60bb71db8f728091eb33a784c7a2052

        # IRoutes
        def before_map(self, map):
            # Link checker - deprecated
            res = 'ckanext.qa.controllers:LinkCheckerController'
            map.connect('qa_resource_checklink', '/qa/link_checker',
                        conditions=dict(method=['GET']),
                        controller=res,
                        action='check_link')
            return map

    if p.toolkit.check_ckan_version(min_version='2.9'):
        p.implements(p.IClick, inherit=True)
        # IClick
        def get_commands(self):
            from ckanext.qa import cli
            return cli.get_commands()

    # IPipe

    def receive_data(self, operation, queue, **params):
        '''Receive notification from ckan-archiver that a dataset has been
        archived.'''
        from ckanext.qa import lib
        if not operation == 'package-archived':
            return
        dataset_id = params['package_id']

        dataset = model.Package.get(dataset_id)
        assert dataset

        lib.create_qa_update_package_task(dataset, queue=queue)

    # IReport

    def register_reports(self):
        """Register details of an extension's reports"""
        from ckanext.qa import reports
        return [reports.openness_report_info]

    # IActions

    def get_actions(self):
        return {
            'qa_resource_show': action.qa_resource_show,
            'qa_package_openness_show': action.qa_package_openness_show,
            }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'qa_resource_show': auth.qa_resource_show,
            'qa_package_openness_show': auth.qa_package_openness_show,
            }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'qa_openness_stars_resource_html':
            helpers.qa_openness_stars_resource_html,
            'qa_openness_stars_dataset_html':
            helpers.qa_openness_stars_dataset_html,
            }

    # IPackageController

    def after_show(self, context, pkg_dict):
        # Insert the qa info into the package_dict so that it is
        # available on the API.
        # When you edit the dataset, these values will not show in the form,
        # it they will be saved in the resources (not the dataset). I can't see
        # and easy way to stop this, but I think it is harmless. It will get
        # overwritten here when output again.
        qa_objs = QA.get_for_package(pkg_dict['id'])
        if not qa_objs:
            return
        # dataset
        dataset_qa = aggregate_qa_for_a_dataset(qa_objs)
        pkg_dict['qa'] = dataset_qa
        # resources
        qa_by_res_id = dict((a.resource_id, a) for a in qa_objs)
        for res in pkg_dict['resources']:
            qa = qa_by_res_id.get(res['id'])
            if qa:
                qa_dict = qa.as_dict()
                del qa_dict['id']
                del qa_dict['package_id']
                del qa_dict['resource_id']
                res['qa'] = qa_dict
