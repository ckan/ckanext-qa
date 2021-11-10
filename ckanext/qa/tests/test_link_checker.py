import pytest

import logging
import json
from urllib import urlencode
from ckanext.archiver.tasks import update_package


# enable celery logging for when you run nosetests -s
log = logging.getLogger('ckanext.archiver.tasks')


def get_logger():
    return log


update_package.get_logger = get_logger


class TestLinkChecker:
    """
    Tests for link checker task
    """

    @pytest.fixture(autouse=True)
    @pytest.mark.usefixtures(u"clean_db")
    @pytest.mark.ckan_config("ckan.plugins", "archiver qa")
    def initial_data(self, clean_db):
        return {}

    def check_link(self, url):
        result = self.app.get('/qa/link_checker?%s' % urlencode({'url': url}))
        return json.loads(result.body)[0]

    def test_url_working_but_formatless(self, client):
        url = client + '/?status=200'
        result = self.check_link(url)
        assert result['format'] is None

    def test_format_by_url_extension(self, client):
        url = client + '/file.csv'
        result = self.check_link(url)
        assert result['format'] == 'CSV'

    def test_format_by_url_extension_zipped(self, client):
        url = client + '/file.csv.zip'
        result = self.check_link(url)
        assert result['format'] == 'CSV / ZIP'

    def test_format_by_url_extension_unknown(self, client):
        url = client + '/file.f1.f2'
        result = self.check_link(url)
        assert result['format'] == 'F1 / F2'

    def test_encoded_url(self):
        # This is not actually a URL, and the encoded letters get
        # interpreted as being in the hostname. But should not cause
        # an exception.
        url = 'Over+\xc2\xa325,000+expenditure+report+April-13'
        result = self.check_link(url)
        assert result['format'] == ''

    def test_format_by_mimetype_txt(self, client):
        url = client + '/?status=200;content-type=text/plain'
        result = self.check_link(url)
        assert result['format'] == 'TXT'

    def test_format_by_mimetype_csv(self, client):
        url = client + '/?status=200;content-type=text/csv'
        result = self.check_link(url)
        assert result['format'] == 'CSV'

    def test_file_url(self):
        url = u'file:///home/root/test.txt'
        result = self.check_link(url)
        assert u'Invalid url scheme. Please use one of: ftp http https' in result['url_errors']
        # assert_raises(LinkCheckerError, link_checker, context, data)

    def test_empty_url(self):
        url = u''
        result = self.check_link(url)
        assert "URL parsing failure - did not find a host name" in result['url_errors']

    def test_url_with_503(self, client):
        url = client + '/?status=503'
        result = self.check_link(url)
        assert 'Server returned HTTP error status: 503 Service Unavailable' in result['url_errors']

    def test_url_with_404(self, client):
        url = client + '/?status=404'
        result = self.check_link(url)
        assert 'Server returned HTTP error status: 404 Not Found' in result['url_errors']

    # Disabled as doesn't work
    # @with_mock_url('')
    # def test_url_with_30x_follows_redirect(self, url):
    #    redirect_url = url + u'?status=200&content=test&content-type=text/csv'
    #    url += u'?status=301&location=%s' % quote_plus(redirect_url)
    #    result = self.check_link(url)
    #    # The redirect works and the CSV is picked up
    #    assert_equal(result['format'], 'CSV')

    # e.g. "http://www.dasa.mod.uk/applications/newWeb/www/index.php?page=48
    # &thiscontent=180&date=2011-05-26&pubType=1&PublishTime=09:30:00&from=home&tabOption=1"
    def test_colon_in_query_string(self, client):
        url = client + '/?time=09:30&status=200'
        # accept, because browsers accept this
        # see discussion: http://trac.ckan.org/ticket/318
        result = self.check_link(url)
        print(result)
        assert result['url_errors'] == []

    def test_trailing_whitespace(self, client):
        url = client + '/?status=200 '
        # accept, because browsers accept this
        result = self.check_link(url)
        print(result)
        assert result['url_errors'] == []
