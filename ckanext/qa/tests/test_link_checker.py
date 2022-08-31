import pytest
import logging
import json
from nose.tools import assert_in

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from ckanext.archiver.tasks import update_package

# enable celery logging for when you run nosetests -s
log = logging.getLogger('ckanext.archiver.tasks')


def get_logger():
    return log


update_package.get_logger = get_logger


@pytest.mark.usefixtures('with_plugins')
@pytest.mark.ckan_config('ckan.plugins', 'archiver qa')
class TestLinkChecker(object):
    """
    Tests for link checker task
    """

    def check_link(self, url, base_url, app):
        base_url = base_url + '/' if base_url is not None else ''
        result = app.get('/qa/link_checker?%s' % urlencode({'url': base_url + url}))
        return json.loads(result.body)[0]

    def test_url_working_but_formatless(self, client, app):
        url = '?status=200'
        result = self.check_link(url, client, app)
        assert result['format'] is None

    def test_format_by_url_extension(self, client, app):
        url = 'file.csv'
        result = self.check_link(url, client, app)
        assert result['format'] == 'CSV'

    def test_format_by_url_extension_zipped(self, client, app):
        url = 'file.csv.zip'
        result = self.check_link(url, client, app)
        assert result['format'] == 'CSV / ZIP'

    def test_format_by_url_extension_unknown(self, client, app):
        url = 'file.f1.f2'
        result = self.check_link(url, client, app)
        assert result['format'] == 'F1 / F2'

    def test_encoded_url(self, client, app):
        # This is not actually a URL, and the encoded letters get
        # interpreted as being in the hostname. But should not cause
        # an exception.
        url = 'Over+\xc2\xa325,000+expenditure+report+April-13'
        result = self.check_link(url, client, app)
        assert result['format'] is None

    def test_format_by_mimetype_txt(self, client, app):
        url = '?status=200&content-type=text/plain'
        result = self.check_link(url, client, app)
        assert result['format'] == 'TXT'

    def test_format_by_mimetype_csv(self, client, app):
        url = '?status=200&content-type=text/csv'
        result = self.check_link(url, client, app)
        assert result['format'] == 'CSV'

    def test_file_url(self, client, app):
        url = u'file:///home/root/test.txt'
        result = self.check_link(url, None, app)

        format_in_use = None
        # htt/https/ftp comes in random order in url_errors so check if any possible format is used in url_error
        schemes = [u'http ftp https', u'http https ftp', u'https ftp http', u'https http ftp', u'ftp https http',
                   u'ftp http https']
        for scheme in schemes:
            if u'Invalid url scheme. Please use one of: %s' % scheme in result['url_errors']:
                format_in_use = u'Invalid url scheme. Please use one of: %s' % scheme
                break

        if format_in_use:
            assert_in(format_in_use, result['url_errors'])
        else:
            pytest.fail("Link check failed {}".format(result['url_errors']))

    def test_empty_url(self, client, app):
        url = u''
        result = self.check_link(url, None, app)
        assert_in("URL parsing failure - did not find a host name", result['url_errors'])

    def test_url_with_503(self, client, app):
        url = '?status=503'
        result = self.check_link(url, client, app)
        assert_in('Server returned HTTP error status: 503 SERVICE UNAVAILABLE', result['url_errors'])

    def test_url_with_404(self, client, app):
        url = '?status=404'
        result = self.check_link(url, client, app)
        assert_in('Server returned HTTP error status: 404 NOT FOUND', result['url_errors'])

    # Disabled as doesn't work
    # @with_mock_url('')
    # def test_url_with_30x_follows_redirect(self, url):
    #    redirect_url = url + u'?status=200&content=test&content-type=text/csv'
    #    url += u'?status=301&location=%s' % quote_plus(redirect_url)
    #    result = self.check_link(url)
    #    # The redirect works and the CSV is picked up
    #    assert(result['format'], 'CSV')

    # e.g. "http://www.dasa.mod.uk/applications/newWeb/www/index.php?page=48
    # &thiscontent=180&date=2011-05-26&pubType=1&PublishTime=09:30:00&from=home&tabOption=1"
    def test_colon_in_query_string(self, client, app):
        url = '?time=09:30&status=200'
        # accept, because browsers accept this
        # see discussion: http://trac.ckan.org/ticket/318
        result = self.check_link(url, client, app)
        print(result)
        assert result['url_errors'] == []

    def test_trailing_whitespace(self, client, app):
        url = '?status=200 '
        # accept, because browsers accept this
        result = self.check_link(url, client, app)
        print(result)
        assert result['url_errors'] == []
