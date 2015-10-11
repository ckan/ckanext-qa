'''
Score datasets on Sir Tim Berners-Lee\'s five stars of openness
based on mime-type.
'''
import datetime
import mimetypes
import json
import requests
import urlparse
import ckan.lib.celery_app as celery_app

from ckanext.archiver.tasks import link_checker, LinkCheckerError

import urllib2
from urllib2 import Request, urlopen, URLError, HTTPError
import logging
log = logging.getLogger('ckanext.qa')

class QAError(Exception):
    pass


class CkanError(Exception):
    pass


OPENNESS_SCORE_REASON = {
    -1: 'unrecognised content type',
    0: 'not obtainable',
    1: 'obtainable via web page',
    2: 'machine readable format',
    3: 'open and standardized format',
    4: 'ontologically represented',
    5: 'fully Linked Open Data as appropriate',
}

MIME_TYPE_SCORE = {
    'text/plain': 1,
    'text': 1,
    'txt': 1,
    'application/vnd.ms-excel': 2,
    'application/vnd.ms-excel.sheet.binary.macroenabled.12': 2,
    'application/vnd.ms-excel.sheet.macroenabled.12': 2,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 2,
    'xls': 2,
    'text/csv': 3,
    'application/json': 3,
    'application/xml': 3,
    'text/xml': 3,
    'csv': 3,
    'xml': 3,
    'json': 3,
    'application/rdf+xml': 4,
    'rdf': 4
}


def _update_task_status(context, data):
    """
    Use CKAN API to update the task status. The data parameter
    should be a dict representing one row in the task_status table.

    Returns the content of the response.
    """
    api_url = urlparse.urljoin(context['site_url'], 'api/action')
    '''res = requests.post(
        api_url + '/task_status_update', json.dumps(data),
        headers={'Authorization': context['apikey'],
                 'Content-Type': 'application/json'}
    )'''

    url = api_url + '/task_status_update'
    params = '%s=1' % json.dumps({'data': data})
    headers = { "Accept" : "application/json",
                "Conthent-Type": "application/json",
                'Authorization': context['apikey']
              }
                 
    req = urllib2.Request(url, params, headers)
    try:
        response = urllib2.urlopen(req)
    except HTTPError as e:            
      #raise CkanError('The server couldn\'t fulfill the request. Error code: %s'
      #                      % (e.code))
      log.error('The server couldn\'t fulfill the request. Error code: %s'
                            % (e.code))
    except URLError as e:      
      #raise CkanError('We failed to reach a server. Reason: %s'
      #                      % (e.reason))      
      log.error('We failed to reach a server. Reason: %s'
                            % (e.reason))
    except:      
      pass     
    else:
        f = response.read()
        content = json.loads(f)
        
        if content.getcode() == 200:
            return json.dumps(content.get('result').get('results'))
        else:
            #raise CkanError('ckan failed to update task_status, status_code (%s), error %s'
            #                % (res.status_code, res.content))
            log.error('ckan failed to update task_status, status_code (%s), error %s'
                            % (res.status_code, res.content))

def _task_status_data(id, result):
    return [
        {
            'entity_id': id,
            'entity_type': u'resource',
            'task_type': 'qa',
            'key': u'openness_score',
            'value': result['openness_score'],
            'last_updated': datetime.datetime.now().isoformat()
        },
        {
            'entity_id': id,
            'entity_type': u'resource',
            'task_type': 'qa',
            'key': u'openness_score_reason',
            'value': result['openness_score_reason'],
            'last_updated': datetime.datetime.now().isoformat()
        },
        {
            'entity_id': id,
            'entity_type': u'resource',
            'task_type': 'qa',
            'key': u'openness_score_failure_count',
            'value': result['openness_score_failure_count'],
            'last_updated': datetime.datetime.now().isoformat()
        },
    ]


@celery_app.celery.task(name="qa.update")
def update(context, data):
    """
    Score resources on Sir Tim Berners-Lee\'s five stars of openness
    based on mime-type.
    
    Returns a JSON dict with keys:

        'openness_score': score (int)
        'openness_score_reason': the reason for the score (string)
        'openness_score_failure_count': the number of consecutive times that
                                        this resource has returned a score of 0
    """
    #log = update.get_logger()
    try:
        data = json.loads(data)
        context = json.loads(context)

        result = resource_score(context, data)
        log.info('Openness score for dataset %s (res#%s): %r (%s)',
                 data['package'], data['position'],
                 result['openness_score'], result['openness_score_reason'])
        
        task_status_data = _task_status_data(data['id'], result)

        api_url = urlparse.urljoin(context['site_url'], 'api/action')
        '''response = requests.post(
            api_url + '/task_status_update_many',
            json.dumps({'data': task_status_data}),
            headers={'Authorization': context['apikey'],
                     'Content-Type': 'application/json'}
        )'''
        
        url = api_url + '/task_status_update_many'
        params = '%s=1' % json.dumps({'data': task_status_data})
        headers = { "Accept" : "application/json",
                    "Conthent-Type": "application/json",
                    'Authorization': context['apikey']
                  }
                 
        req = urllib2.Request(url, params, headers)
        response = urllib2.urlopen(req)
        f = response.read()
        content = json.loads(f)
                         
        if not content.get('success'):
            err = 'ckan failed to update task_status, error %s' \
                  % content['error']
            log.error(err)
            #raise CkanError(err)
        elif response.getcode() != 200:
            err = 'ckan failed to update task_status, status_code (%s), error %s' \
                  % (response.getcode(), content.get('result').get('results'))
            log.error(err)
            #raise CkanError(err)

        #return json.dumps(result)
        return json.dumps(content.get('result').get('results'))
    except Exception, e:
        log.error('Exception occurred during QA update: %s: %s', e.__class__.__name__,  unicode(e))
        _update_task_status(context, {
            'entity_id': data['id'],
            'entity_type': u'resource',
            'task_type': 'qa',
            'key': u'celery_task_id',
            'value': unicode(update.request.id),
            'error': '%s: %s' % (e.__class__.__name__,  unicode(e)),
            'last_updated': datetime.datetime.now().isoformat()
        })
        #raise


def resource_score(context, data):
    """
    Score resources on Sir Tim Berners-Lee\'s five stars of openness
    based on mime-type.

    returns a dict with keys:

        'openness_score': score (int)
        'openness_score_reason': the reason for the score (string)
        'openness_score_failure_count': the number of consecutive times that
                                        this resource has returned a score of 0
    """
    #log = update.get_logger()

    score = 0
    score_reason = ''
    score_failure_count = 0

    # get openness score failure count for task status table if exists
    api_url = urlparse.urljoin(context['site_url'], 'api/action')
    '''response = requests.post(
        api_url + '/task_status_show',
        json.dumps({'entity_id': data['id'], 'task_type': 'qa',
                    'key': 'openness_score_failure_count'}),
        headers={'Authorization': context['apikey'],
                 'Content-Type': 'application/json'}
    )'''
  
    args = {'entity_id': data['id'], 'task_type': 'qa',
            'key': 'openness_score_failure_count'}
            
    response = requests.get(api_url + '/task_status_show', params=args).text
    
    
    if json.loads(response)['success']:
        score_failure_count = int(json.loads(response)['result'].get('value', '0'))

    # no score for resources that don't have an open license
    if not data.get('is_open'):
        score_reason = 'License not open'
    else:
        try:
            headers = json.loads(link_checker("{}", json.dumps(data)))
            ct = headers.get('content-type')

            # ignore charset if exists (just take everything before the ';')
            if ct and ';' in ct:
                ct = ct.split(';')[0]

            # also get format from resource and by guessing from file extension
            format = data.get('format', '').lower()
            file_type = mimetypes.guess_type(data['url'])[0]

            # file type takes priority for scoring
            if file_type:
                score = MIME_TYPE_SCORE.get(file_type, -1)
            elif ct:
                score = MIME_TYPE_SCORE.get(ct, -1)
            elif format:
                score = MIME_TYPE_SCORE.get(format, -1)

            score_reason = OPENNESS_SCORE_REASON[score]

            # negative scores are only useful for getting the reason message,
            # set it back to 0 if it's still <0 at this point
            if score < 0:
                score = 0

            # check for mismatches between content-type, file_type and format
            # ideally they should all agree
            if not ct:
                # TODO: use the todo extension to flag this issue
                pass

        except LinkCheckerError, e:
            score_reason = str(e)
        except Exception, e:
            log.error('Unexpected error while calculating openness score %s: %s', e.__class__.__name__,  unicode(e))
            score_reason = "Unknown error: %s" % str(e)

    if score == 0:
        score_failure_count += 1
    else:
        score_failure_count = 0

    return {
        'openness_score': score,
        'openness_score_reason': score_reason,
        'openness_score_failure_count': score_failure_count,
    }
