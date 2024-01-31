import logging
from pathlib import Path

import ckan.model as model
import ckan.plugins as p
from ckan.plugins import toolkit

from ckanext.archiver.interfaces import IPipe
from ckanext.qa.logic import action, auth
from ckanext.qa.model import QA, aggregate_qa_for_a_dataset
from ckanext.qa.helpers import qa_openness_stars_resource_html, qa_openness_stars_dataset_html
from ckanext.qa.lib import create_qa_update_package_task
from ckanext.report.interfaces import IReport


log = logging.getLogger(__name__)


if toolkit.check_ckan_version(min_version='2.9.0'):
    from ckanext.qa.plugin.flask_plugin import MixinPlugin
else:
    from ckanext.qa.plugin.pylons_plugin import MixinPlugin


class QAPlugin(MixinPlugin, p.SingletonPlugin, toolkit.DefaultDatasetForm):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(IPipe, inherit=True)
    p.implements(IReport)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IPackageController, inherit=True)

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, '../templates')

        # check for qsv config
        qsv_bin = config.get('ckanext.qa.qsv_bin')
        if qsv_bin:
            qsv_path = Path(qsv_bin)
            if not qsv_path.is_file():
                log.error('ckanext.qa.qsv_bin file not found: %s', qsv_path)
        else:
            log.error('ckanext.qa.qsv_bin not set')

    # IPipe

    def receive_data(self, operation, queue, **params):
        '''Receive notification from ckan-archiver that a dataset has been
        archived.'''
        if not operation == 'package-archived':
            return
        dataset_id = params['package_id']

        dataset = model.Package.get(dataset_id)
        assert dataset

        create_qa_update_package_task(dataset, queue=queue)

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
            qa_openness_stars_resource_html,
            'qa_openness_stars_dataset_html':
            qa_openness_stars_dataset_html,
            }

    # IPackageController

    def after_show(self, context, pkg_dict):
        """ Old CKAN function name """
        return self.after_dataset_show(context, pkg_dict)

    def after_dataset_show(self, context, pkg_dict):
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

    def before_dataset_index(self, pkg_dict):
        '''
        remove `qa` from index
        '''
        pkg_dict.pop('qa', None)
        return pkg_dict
