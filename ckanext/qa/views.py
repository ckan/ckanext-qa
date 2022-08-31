from flask import Blueprint
import json
import mimetypes
import posixpath
import sys
from ckan.plugins.toolkit import request
from ckanext.archiver.tasks import link_checker, LinkCheckerError
from ckan.lib import helpers as ckan_helpers
from ckan.lib.helpers import parse_rfc_2822_date

if sys.version_info[0] >= 3:
    from urllib.parse import urlparse
else:
    from urlparse import urlparse


def qa_resource_checklink():
    urls = request.args.getlist('url')
    result = [_check_link(url) for url in urls]
    return json.dumps(result)


def _check_link(url):
    """
    Synchronously check the given link, and return dict representing results.
    Does not handle 30x redirects.
    """

    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    path = parsed_url.path

    # If a user enters "www.example.com" then we assume they meant "http://www.example.com"
    if not scheme:
        url = 'http://' + path

    context = {}
    data = {
        'url_timeout': 10,
        'url': url
    }
    result = {
        'errors': [],
        'url_errors': [],
        'format': '',
        'mimetype': '',
        'size': '',
        'last_modified': '',
    }

    try:
        headers = json.loads(link_checker(json.dumps(context), json.dumps(data)))
        result['format'] = _extract_file_format(url, headers)
        result['mimetype'] = _extract_mimetype(headers)
        result['size'] = headers.get('content-length', '')
        result['last_modified'] = _parse_and_format_date(headers.get('last-modified', ''))
    except LinkCheckerError as e:
        result['url_errors'].append(str(e))
    return result


def _extract_file_format(url, headers):
    """
    Makes a best guess at the file format.

    /path/to/a_file.csv has format "CSV"
    /path/to/a_file.csv.zip has format "CSV / Zip"

    First this function tries to extract the file-extensions from the url,
    and deduce the format from there.  If no file-extension is found, then
    the mimetype from the headers is passed to `mimetypes.guess_extension()`.
    """
    formats = []
    parsed_url = urlparse(url)
    path = parsed_url.path
    base, extension = posixpath.splitext(path)
    while extension:
        formats.append(extension[1:].upper())  # strip leading '.' from extension
        base, extension = posixpath.splitext(base)
    if formats:
        extension = '.'.join(formats[::-1]).lower()
        format_tuple = ckan_helpers.resource_formats().get(extension)
        if format_tuple:
            return format_tuple[1]
        return ' / '.join(formats[::-1])

    # No file extension found, attempt to extract format using the mimetype
    stripped_mimetype = _extract_mimetype(headers)  # stripped of charset
    format_tuple = ckan_helpers.resource_formats().get(stripped_mimetype)
    if format_tuple:
        return format_tuple[1]

    extension = mimetypes.guess_extension(stripped_mimetype)
    if extension:
        return extension[1:].upper()


def _extract_mimetype(headers):
    """
    The Content-Type in headers, stripped of character encoding parameters.
    """
    return headers.get('content-type', '').split(';')[0].strip()


def _parse_and_format_date(date_string):
    """
    Parse date string in form specified in RFC 2822, and reformat to iso format.

    Returns the empty string if the date_string cannot be parsed
    """
    dt = parse_rfc_2822_date(date_string)

    # Remove timezone information, adjusting as necessary.
    if dt and dt.tzinfo:
        dt = (dt - dt.utcoffset()).replace(tzinfo=None)
    return dt.isoformat() if dt else ''


qa_blueprints = Blueprint('qa_blueprint', __name__)
qa_blueprints.add_url_rule('/qa/link_checker', view_func=qa_resource_checklink)


def get_blueprints():
    return [qa_blueprints]
