import requests
import logging
import urllib
import datetime

from nose.tools import assert_equal
from nose.plugins.skip import SkipTest
from ckan import model
from ckan.logic import get_action
from ckan import plugins as p
import ckan.lib.helpers as ckan_helpers
try:
    from ckan.tests.helpers import reset_db
    from ckan.tests import factories as ckan_factories
    from ckan.tests.legacy import BaseCase
except ImportError:
    from ckan.new_tests.helpers import reset_db
    from ckan.new_tests import factories as ckan_factories
    from ckan.tests import BaseCase

import ckanext.qa.tasks
from ckanext.qa.tasks import resource_score, extension_variants
import ckanext.archiver
import ckanext.archiver.tasks
from ckanext.qa import model as qa_model
from ckanext.archiver import model as archiver_model
from ckanext.archiver.model import Archival, Status

log = logging.getLogger(__name__)

# Monkey patch get_cached_resource_filepath so that it doesn't barf when
# it can't find the file


def mock_get_cached_resource_filepath(cache_url):
    if not cache_url:
        return None
    return cache_url.replace('http://remotesite.com/', '/resources')


ckanext.qa.tasks.get_cached_resource_filepath = mock_get_cached_resource_filepath

# Monkey patch sniff_file_format. This isolates the testing of tasks from
# actual sniffing
sniffed_format = None


def mock_sniff_file_format(filepath):
    return sniffed_format


ckanext.qa.tasks.sniff_file_format = mock_sniff_file_format


def set_sniffed_format(format_name):
    global sniffed_format
    if format_name:
        format_tuple = ckan_helpers.resource_formats().get(format_name.lower())
        sniffed_format = {'format': format_tuple[1]}
    else:
        sniffed_format = None


TODAY = datetime.datetime(year=2008, month=10, day=10)
TODAY_STR = TODAY.isoformat()


class TestTask(BaseCase):

    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)
        qa_model.init_tables(model.meta.engine)

    def test_trigger_on_archival(cls):
        # create package
        context = {'model': model, 'ignore_auth': True, 'session': model.Session, 'user': 'test'}
        pkg = {'name': 'testpkg', 'license_id': 'uk-ogl', 'resources': [
            {'url': 'http://test.com/', 'format': 'CSV', 'description': 'Test'}
        ]}
        pkg = get_action('package_create')(context, pkg)
        resource_dict = pkg['resources'][0]
        res_id = resource_dict['id']
        # create record of archival
        archival = Archival.create(res_id)
        cache_filepath = __file__  # just needs to exist
        archival.cache_filepath = cache_filepath
        archival.updated = TODAY
        model.Session.add(archival)
        model.Session.commit()
        # TODO show that QA hasn't run yet

        # create a send_data from ckanext-archiver, that gets picked up by
        # ckanext-qa to put a task on the queue
        ckanext.archiver.tasks.notify_package(pkg, 'priority')
        # this is useful on its own (without any asserts) because it checks
        # there are no exceptions when running it

        # TODO run celery and check it actually ran...


class TestResourceScore(BaseCase):

    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)
        qa_model.init_tables(model.meta.engine)
        cls.fake_resource = {
            'id': u'fake_resource_id',
            'url': 'http://remotesite.com/filename.csv',
            'cache_url': 'http://remotesite.com/resources/filename.csv',
            'cache_filepath': __file__,  # must exist
            'package': u'fake_package_id',
            'is_open': True,
            'position': 2,
        }

    def _test_resource(self, url='anything', format='TXT', archived=True, cached=True, license_id='uk-ogl'):
        pkg = {'license_id': license_id,
               'resources': [
                   {'url': url, 'format': format, 'description': 'Test'}
               ]}
        pkg = ckan_factories.Dataset(**pkg)
        res_id = pkg['resources'][0]['id']
        if archived:
            archival = Archival.create(res_id)
            archival.cache_filepath = __file__ if cached else None  # just needs to exist
            archival.updated = TODAY
            model.Session.add(archival)
            model.Session.commit()
        return model.Resource.get(res_id)

    @classmethod
    def _set_task_status(cls, task_type, task_status_str):
        url = '%s/set_task_status/%s/%s' % (cls.fake_ckan_url,
                                            task_type,
                                            urllib.quote(task_status_str))
        res = requests.get(url)
        assert res.status_code == 200

    def test_by_sniff_csv(self):
        set_sniffed_format('CSV')
        result = resource_score(self._test_resource())
        assert result['openness_score'] == 3, result
        assert 'Content of file appeared to be format "CSV"' in result['openness_score_reason'], result
        assert result['format'] == 'CSV', result
        assert result['archival_timestamp'] == TODAY_STR, result

    def test_not_archived(self):
        result = resource_score(self._test_resource(archived=False, cached=False, format=None))
        # falls back on previous QA data detailing failed attempts
        assert result['openness_score'] == 1, result
        assert result['format'] is None, result
        assert result['archival_timestamp'] is None, result
        assert 'This file had not been downloaded at the time of scoring it.' in result['openness_score_reason'], result
        assert 'Could not determine a file extension in the URL.' in result['openness_score_reason'], result
        assert 'Format field is blank.' in result['openness_score_reason'], result
        assert 'Could not understand the file format, therefore score is 1.' in result['openness_score_reason'], result

    def test_archiver_ran_but_not_cached(self):
        result = resource_score(self._test_resource(cached=False, format=None))
        # falls back on previous QA data detailing failed attempts
        assert result['openness_score'] == 1, result
        assert result['format'] is None, result
        assert result['archival_timestamp'] == TODAY_STR, result
        assert 'This file had not been downloaded at the time of scoring it.' in result['openness_score_reason'], result
        assert 'Could not determine a file extension in the URL.' in result['openness_score_reason'], result
        assert 'Format field is blank.' in result['openness_score_reason'], result
        assert 'Could not understand the file format, therefore score is 1.' in result['openness_score_reason'], result

    def test_by_extension(self):
        set_sniffed_format(None)
        result = resource_score(self._test_resource('http://site.com/filename.xls'))
        assert result['openness_score'] == 2, result
        assert result['archival_timestamp'] == TODAY_STR, result
        assert_equal(result['format'], 'XLS')
        assert 'not recognized from its contents' in result['openness_score_reason'], result
        assert 'extension "xls" relates to format "XLS"' in result['openness_score_reason'], result

    def test_extension_not_recognized(self):
        set_sniffed_format(None)
        result = resource_score(self._test_resource('http://site.com/filename.zar'))
        assert result['openness_score'] == 1, result
        assert 'not recognized from its contents' in result['openness_score_reason'], result
        assert 'URL extension "zar" is an unknown format' in result['openness_score_reason'], result

    def test_by_format_field(self):
        set_sniffed_format(None)
        result = resource_score(self._test_resource(format='XLS'))
        assert result['openness_score'] == 2, result
        assert_equal(result['format'], 'XLS')
        assert 'not recognized from its contents' in result['openness_score_reason'], result
        assert 'Could not determine a file extension in the URL' in result['openness_score_reason'], result
        assert 'Format field "XLS"' in result['openness_score_reason'], result

    def test_by_format_field_excel(self):
        set_sniffed_format(None)
        if p.toolkit.check_ckan_version(max_version='2.4.99'):
            raise SkipTest
        result = resource_score(self._test_resource(format='Excel'))
        assert_equal(result['format'], 'XLS')

    def test_format_field_not_recognized(self):
        set_sniffed_format(None)
        result = resource_score(self._test_resource(format='ZAR'))
        assert result['openness_score'] == 1, result
        assert 'not recognized from its contents' in result['openness_score_reason'], result
        assert 'Could not determine a file extension in the URL' in result['openness_score_reason'], result
        assert 'Format field "ZAR" does not correspond to a known format' in result['openness_score_reason'], result

    def test_no_format_clues(self):
        set_sniffed_format(None)
        result = resource_score(self._test_resource(format=None))
        assert result['openness_score'] == 1, result
        assert 'not recognized from its contents' in result['openness_score_reason'], result
        assert 'Could not determine a file extension in the URL' in result['openness_score_reason'], result
        assert 'Format field is blank' in result['openness_score_reason'], result

    def test_available_but_not_open(self):
        set_sniffed_format('CSV')
        result = resource_score(self._test_resource(license_id=None))
        assert result['openness_score'] == 0, result
        assert_equal(result['format'], 'CSV')
        assert 'License not open' in result['openness_score_reason'], result

    def test_not_available_and_not_open(self):
        res = self._test_resource(license_id=None, format=None, cached=False)
        archival = Archival.get_for_resource(res.id)
        archival.status_id = Status.by_text('Download error')
        archival.reason = 'Server returned 500 error'
        archival.last_success = None
        archival.first_failure = datetime.datetime(year=2008, month=10, day=1, hour=6, minute=30)
        archival.failure_count = 16
        archival.is_broken = True
        model.Session.commit()
        result = resource_score(res)
        assert result['openness_score'] == 0, result
        assert_equal(result['format'], None)
        # in preference it should report that it is not available
        assert_equal(result['openness_score_reason'], u'File could not be downloaded. '
                                                      u'Reason: Download error. Error details: Server returned 500 error.'
                                                      u' Attempted on 10/10/2008. Tried 16 times since 01/10/2008.'
                                                      u' This URL has not worked in the history of this tool.')

    def test_not_available_any_more(self):
        # A cache of the data still exists from the previous run, but this
        # time, the archiver found the file gave a 404.
        # The record of the previous (successful) run of QA.
        res = self._test_resource(license_id=None, format=None)
        qa = qa_model.QA.create(res.id)
        qa.format = 'CSV'
        model.Session.add(qa)
        model.Session.commit()
        # cache still exists from the previous run, but this time, the archiver
        # found the file gave a 404.
        archival = Archival.get_for_resource(res.id)
        archival.cache_filepath = __file__
        archival.status_id = Status.by_text('Download error')
        archival.reason = 'Server returned 404 error'
        archival.last_success = datetime.datetime(year=2008, month=10, day=1)
        archival.first_failure = datetime.datetime(year=2008, month=10, day=2)
        archival.failure_count = 1
        archival.is_broken = True
        result = resource_score(res)
        assert result['openness_score'] == 0, result
        assert_equal(result['format'], 'CSV')
        # in preference it should report that it is not available
        assert_equal(result['openness_score_reason'], 'File could not be downloaded. '
                                                      'Reason: Download error. Error details: Server returned 404 error.'
                                                      ' Attempted on 10/10/2008. This URL last worked on: 01/10/2008.')


class TestExtensionVariants:
    def test_0_normal(self):
        assert_equal(extension_variants('http://dept.gov.uk/coins-data-1996.csv'),
                     ['csv'])

    def test_1_multiple(self):
        assert_equal(extension_variants('http://dept.gov.uk/coins.data.1996.csv.zip'),
                     ['csv.zip', 'zip'])

    def test_2_parameter(self):
        assert_equal(extension_variants('http://dept.gov.uk/coins-data-1996.csv?callback=1'),
                     ['csv'])

    def test_3_none(self):
        assert_equal(extension_variants('http://dept.gov.uk/coins-data-1996'),
                     [])


class TestSaveQaResult(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)
        qa_model.init_tables(model.meta.engine)

    @classmethod
    def get_qa_result(cls, **kwargs):
        qa_result = {
            'openness_score': 3,
            'openness_score_reason': 'Detected as CSV which scores 3',
            'format': 'CSV',
            'archival_timestamp': datetime.datetime(2015, 12, 16),
        }
        qa_result.update(kwargs)
        return qa_result

    def test_simple(self):
        resource_dict = ckan_factories.Resource()
        resource = model.Resource.get(resource_dict['id'])
        qa_result = self.get_qa_result()

        qa = ckanext.qa.tasks.save_qa_result(resource, qa_result)

        assert_equal(qa.openness_score, qa_result['openness_score'])
        assert_equal(qa.openness_score_reason,
                     qa_result['openness_score_reason'])
        assert_equal(qa.format, qa_result['format'])
        assert_equal(qa.archival_timestamp, qa_result['archival_timestamp'])
        assert qa.updated, qa.updated


class TestUpdatePackage(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)
        qa_model.init_tables(model.meta.engine)

    def test_simple(self):
        resource = {
            'url': 'http://example.com/file.csv',
            'title': 'Some data',
            'format': '',
        }
        dataset = ckan_factories.Dataset(resources=[resource])
        resource = model.Resource.get(dataset['resources'][0]['id'])

        ckanext.qa.tasks.update_package_(dataset['id'])

        qa = qa_model.QA.get_for_resource(dataset['resources'][0]['id'])
        assert qa
        assert_equal(qa.openness_score, 0)
        assert_equal(qa.openness_score_reason, 'License not open')


class TestUpdateResource(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)
        qa_model.init_tables(model.meta.engine)

    def test_simple(self):
        resource = {
            'url': 'http://example.com/file.csv',
            'title': 'Some data',
            'format': '',
        }
        dataset = ckan_factories.Dataset(resources=[resource])
        resource = model.Resource.get(dataset['resources'][0]['id'])

        ckanext.qa.tasks.update_resource_(dataset['resources'][0]['id'])

        qa = qa_model.QA.get_for_resource(dataset['resources'][0]['id'])
        assert qa
        assert_equal(qa.openness_score, 0)
        assert_equal(qa.openness_score_reason, 'License not open')
