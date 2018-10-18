from swimlane import Swimlane
from swimlane.core.search import EQ, NOT_EQ, LTE
from slackclient import SlackClient
import pendulum
import json
import requests
import urllib3
import time
import os

os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
os.environ['NO_PROXY'] = 'phoenixnap-internal.com'
time.sleep(30)
slApiUser = sw_context.inputs['apiUser']
slApiKey = sw_context.inputs['apiKey']
slApiHost = sw_context.inputs['apiHost']
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
lrRestApiDrilldown = sw_context.inputs['lrRestApiDrilldown']
lrRestApiKey = sw_context.inputs['lrRestApiKey']
sc = SlackClient(sw_context.inputs['slackToken'])
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


app = swimlane.apps.get(id='aP0pSxO_qFQhNWteI')
seReport = app.reports.build('Get All Open Tickets', limit=0)
seReport.filter('CS: Case Status', NOT_EQ, 'Closed')
seReport.filter('Log Rhythm Log Message', EQ, None)
seReport.filter('TL: Case Created', LTE, pendulum.now().subtract(minutes=1))
try:
    for seRecord in seReport:
        outputs = {}
        apiCall = requests.get("{}{}".format(lrRestApiDrilldown, seRecord['Alarm ID']), headers={"Authorization": "Bearer {}".format(lrRestApiKey)}, verify=False)
        apiResult = apiCall.content
        if len(apiResult) == 0:
            outputs = 'Empty Request due to no content'
        else:
            print
            jsonData = json.loads(apiResult)
            outputs = {}
            if jsonData['Data']['DrillDownResults'] is not None:
                for block in jsonData['Data']['DrillDownResults']['RuleBlocks']:
                    try:
                        logMessage = str()
                        for data in json.loads(block['DrillDownLogs'].encode("utf-8")):
                            outputs = json.loads(json.dumps(data))
                            logMessage += "{}\r".format(outputs['logMessage'])
                        outputs = logMessage
                    except Exception as e:
                        pass
            else:
                if seRecord['CS: Case Source'] == 'SIEM Diagnostics':
                    outputs = 'No Cache Data due to Non AIE Alarm'
                else:
                    outputs = 'No Cache Data due to error'
        seRecord['Log Rhythm Log Message'] = outputs
        seRecord.save()
        if seRecord['ts']:
            scText = 'Pulled Drilldown Cache: {}/record/{}/{}'.format(
                sw_context.inputs['swimlaneWebUrl'], seRecord['AV: Application ID'], seRecord['AV:  Record ID'])
            scApiCall = sc.api_call("chat.postMessage", channel=sw_context.inputs['slackAlarmChannel'], text=scText, thread_ts=seRecord['ts'])
        else:
            scText = 'Pulled Drilldown Cache: {}/record/{}/{}'.format(sw_context.inputs['swimlaneWebUrl'],
                                                                      seRecord['AV: Application ID'], seRecord['AV:  Record ID'])
            scApiCall = sc.api_call("chat.postMessage", channel=sw_context.inputs['slackAlarmChannel'], text=scText)
except Exception as e:
    scText = 'Error running integration SE: Poll LogRythem REST Drill Down Cache.  Error: {}'.format(e)
    scApiCall = sc.api_call("chat.postMessage", channel=sw_context.inputs['slackErrorChannel'], text=scText)
    scData = {'ts': scApiCall['ts'], 'channel': scApiCall['channel']}
