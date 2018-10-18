from slackclient import SlackClient
from swimlane import Swimlane
from swimlane.core.search import EQ, NOT_EQ, LTE
from requests import Session
from zeep import Client, helpers
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
import collections
import re
import os
import urllib3
import pendulum
import time

os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def convert(name):
    """Formats keys

        Args:
            name: string
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)


def prefix(key):
    """add correct prfix to fields based on key

        Args:
            key: string
    """
    if key == 'Impacted Location':
        return 'IL: '
    elif key == 'Impacted Network':
        return 'IN: '
    elif key == 'Origin Location':
        return 'OL: '
    elif key == 'Origin Network':
        return 'ON: '


def setLrApiClient(url, username, password):
    """Creates and set LogRythem API Client

    Args:
        url: string LogRythem API server url
        username: string LogRythem API username
        password: string LogRythem API password

    Return:
        apiClient: object
    """
    session = Session()
    session.verify = False
    transport = Transport(session=session, timeout=120)
    apiClient = Client(url, wsse=UsernameToken(username, password), transport=transport, strict=False)
    return apiClient


def getEventForAlarm(apiClient, swimlane, lredAppId, alarmValue):
    """Gets the evant date from Log Rythem based on alarmId

   Args:
       apiClient: object from setLrApiClient function
       swimlane: object, swimlane class object
       lredAppId: string swimlane LRED app id
       alarmValue: staring alramId

   Return:
       setLrApiClient: object, swimlane new record object
   """
    lrPullStart = time.time()
    response = apiClient.service.GetAlarmEventsByID(alarmValue['Alarm ID'], True)
    lrPullEnd = time.time()
    print "lrPull", lrPullStart, lrPullEnd, lrPullEnd - lrPullStart
    eventList = []
    for event in response['Events']['LogDataModel']:
        eventDict = {}
        input_dict = helpers.serialize_object(event)
        for key, value in input_dict.iteritems():
            if isinstance(value, collections.OrderedDict):
                for key2, value2 in value.iteritems():
                    eventDict[prefix(convert(key)) + convert(key2)] = value2
            else:
                if str(value) == 'nan':
                    eventDict[convert(key)] = None
                else:
                    eventDict[convert(key)] = value
            eventDict['Alarm ID'] = alarmValue['Alarm ID']
            eventDict['Alarm Rule ID'] = alarmValue['Alarm Rule ID']
            eventDict['Alarm Rule Name'] = alarmValue['Alarm Rule Name']
            eventDict['SE: Tracking ID'] = alarmValue['AV: Tracking ID']
            eventDict['SE: Application ID'] = alarmValue['AV: Application ID']
            eventDict['SE: Record ID'] = alarmValue['AV:  Record ID']
            eventDict['SE: Security Events Ref'] = alarmValue
            eventDict['ts'] = alarmValue['ts']
            eventDict['channel'] = alarmValue['channel']
        lredApp = swimlane.apps.get(id=lredAppId)
        newLredAppRecord = lredApp.records.create(**eventDict)
        eventList.append(collections.OrderedDict(sorted(eventDict.items(), key=lambda x: x[0])))
        return newLredAppRecord


def addLrComment(apiClient, alarmId, comment):
    """ Adds comment to LogRythem

        Args:
            apiClient: object from setLrApiClient function
            alarmId: string
            comment: string
    """
    lrComment = apiClient.service.AddAlarmComments(alarmId, comment)


time.sleep(15)
os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
sc = SlackClient(sw_context.inputs['slackToken'])
try:
    slApiUser = sw_context.inputs['apiUser']
    slApiKey = sw_context.inputs['apiKey']
    slApiHost = sw_context.inputs['apiHost']
    lredAppId = sw_context.inputs['lredAppId']
    seAppId = sw_context.inputs['seAppId']
    crmAppId = sw_context.inputs['crmAppId']
    swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
    username = sw_context.inputs['lrUsername']
    password = sw_context.inputs['lrKey']
    url = sw_context.inputs['lrAlarmEndpoint']

    apiClient = setLrApiClient(url, username, password)
    seApp = swimlane.apps.get(id=seAppId)
    seReport = seApp.reports.build("Get SE Records", limit=0)
    seReport.filter('TL: Case Created', LTE, pendulum.now().subtract(minutes=1))
    seReport.filter("CS: Case Status", NOT_EQ, "Closed")
    seReport.filter("LG: LRED Pulled", NOT_EQ, "yes")
    seReport.filter("LG: Record Exists", EQ, "yes")
    if len(seReport) > 0:
        for seRecord in seReport:
            newLredAppRecord = getEventForAlarm(apiClient, swimlane, lredAppId, seRecord)
            comment = "Pulled Events for LR Alarm {} into swimlane.".format(seRecord['Alarm ID'])
            addLrComment(apiClient, seRecord['Alarm ID'], comment)
            seRecord['LG: LRED Pulled'] = 'yes'
            seRecord['LR: Event(s)'].add(newLredAppRecord)
            seRecord.save()
    else:
        pass
except Exception as e:
    scText = 'Error running integration SE: Poll LogRythem Event Data for alarms.  Error: {}'.format(e)
    scApiCall = sc.api_call("chat.postMessage", channel="GCWRQ3802", text=scText)