from datetime import datetime, timedelta
from requests import Session
from slackclient import SlackClient
from swimlane import Swimlane
from swimlane.core.search import EQ, GTE
from zeep import Client, helpers
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
import collections
import re
import time
import urllib3
import os
import pendulum
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)


def prefix(key):
    if key == 'Impacted Location':
        return 'IL: '
    elif key == 'Impacted Network':
        return 'IN: '
    elif key == 'Origin Location':
        return 'OL: '
    elif key == 'Origin Network':
        return 'ON: '


def setLrApiClient(url, username, password):
    session = Session()
    session.verify = False
    transport = Transport(session=session, timeout=240)
    apiClient = Client(url, wsse=UsernameToken(username, password), transport=transport, strict=False)
    return apiClient


def GetAlarmsServiceCall(apiClient, status, nextPage=None):
    now = datetime.utcnow()
    yesterday = now - timedelta(minutes=60)
    allusers = 'true'
    maxresults = 100
    if nextPage is not None:
        alarms = apiClient.service.GetNextPageAlarms(nextPage)
    else:
        alarms = apiClient.service.GetFirstPageAlarmsByAlarmStatus(yesterday, now, status, allusers, maxresults)
    return helpers.serialize_object(alarms)


def getLrAlarms(apiClient, status):
    lrApiAlarms = GetAlarmsServiceCall(apiClient, status, nextPage=None)
    pages = []
    pages.append(lrApiAlarms)
    while lrApiAlarms['HasMoreResults'] == True:
        lrApiAlarms = GetAlarmsServiceCall(apiClient, status, lrApiAlarms['NextPageID'])
        pages.append(lrApiAlarms)
    return pages


def buildAlarmDict(alarmDicts):
    ad = {}
    adKeys = []
    for alarms in alarmDicts:
        add = {}
        for alarmKey, alarmValue in alarms.iteritems():
            add[alarmKey] = alarmValue
        ad[str(alarms['AlarmID'])] = add
        adKeys = ad.keys()
    ad = collections.OrderedDict(sorted(ad.items(), key=lambda x: x[0]))
    return ad, adKeys


def findNewAlarms(page, swimlane, seAppId):
    lrAlarms, lrAlarmIds = buildAlarmDict(page['Alarms']['AlarmSummaryDataModel'])
    seAlarmIds = getSeAlarms(swimlane, seAppId)
    newAlarms = list(set(lrAlarms) - set(seAlarmIds))
    numberOfAlarms = None
    if len(newAlarms) == 0:
        numberOfAlarms = 0
        lrAlarms = {}
    elif len(newAlarms) > 0:
        for key in lrAlarms.keys():
            if key not in set(newAlarms):
                del lrAlarms[key]
        numberOfAlarms = len(lrAlarms)
    return numberOfAlarms, lrAlarms


def getSeAlarms(swimlane, seAppId):
    seAlarmIds = []
    seApp = swimlane.apps.get(id=seAppId)
    seReport = seApp.reports.build('Get All SIEM Alerts', limit=0)
    seReport.filter('TL: Case Created', GTE, pendulum.yesterday())
    for seRecords in seReport:
        seAlarmIds.append(str(seRecords['Alarm ID']))
    return seAlarmIds


def getAndBuildClientIdToEntitiesId(swimlane, crmAppId):
    crmApp = swimlane.apps.get(id=crmAppId)
    crmReports = crmApp.reports.build('Get Client ID from CRM App')
    clientIDs = []
    for crmRecord in crmReports:
        for e in crmRecord['Entity ID']:
            clientIDs.append(int(e))
    return clientIDs


def getClientIdByEntityId(swimlane, crmAppId, entityId):
    crmApp = swimlane.apps.get(id=crmAppId)
    crmReports = crmApp.reports.build('Get Client ID from CRM App')
    for record in crmReports:
        for eid in record['Entity ID']:
            if eid in record['Entity ID']:
                clientId = record['Client Name']
                return clientId


def setCaseSource(alarmId, listOfEnabledSiemDiagnostics):
    if listOfEnabledSiemDiagnostics.count(alarmId) > 0:
        return 'SIEM Diagnostics'
    else:
        return 'SIEM Alert'


def createSeRecord(clientIdToEntitiesId, alarmValue, swimlane, seAppId, listOfEnabledSiemDiagnostics):
    if alarmValue['EntityID'] in clientIdToEntitiesId:
        recordData = {'CS: Client Name': getClientIdByEntityId(swimlane, crmAppId, alarmValue['EntityID']),
                      'CS: TLP': 'Amber', 'CS: Priority': 'P3 - Medium',
                      'CS: Case Source': setCaseSource(alarmValue['AlarmRuleID'], listOfEnabledSiemDiagnostics),
                      'CS: Case Status': 'New Case', 'CS: Case Stage': 'Triage and Verification',
                      'CS: Event Occurred': alarmValue['EventDateFirst'],
                      'CD: Case Title': 'Security Event Detected: {}'.format(alarmValue['AlarmRuleName']),
                      'CS: Alarm Rule ID': alarmValue['AlarmID'],
                      'CS: Alarm Rule Name': alarmValue['AlarmRuleName'],
                      'Alarm Date': alarmValue['AlarmDate'], 'Date Inserted': alarmValue['DateInserted'],
                      'Alarm Status': alarmValue['AlarmStatus'], 'Event Count': alarmValue['EventCount'],
                      'Event Date First': alarmValue['EventDateFirst'],
                      'Alarm Rule ID': alarmValue['AlarmRuleID'],
                      'Entity Name': alarmValue['EntityName'],
                      'Last Updated Name': alarmValue['LastUpdatedName'],
                      'Alarm ID': alarmValue['AlarmID'], 'RBP Max': alarmValue['RBPMax'],
                      'Entity ID': alarmValue['EntityID'],
                      'Event Date Last': alarmValue['EventDateLast'], 'Date Updated': alarmValue['DateUpdated'],
                      'Last Updated ID': alarmValue['LastUpdatedID'],
                      'Alarm Rule Name': alarmValue['AlarmRuleName'],
                      'AP: Assigned to Group(s)': [swimlane.groups.get(name='PHX_Security_Operations_L1_Analysts')],
                      'RBP Avg': alarmValue['RBPAvg'], 'LG: SIEM Created': 'yes'}
        seApp = swimlane.apps.get(id=seAppId)
        newRecord = seApp.records.create(**recordData)
        print newRecord
        return newRecord


def addLrComment(apiClient, alarmId, comment):
    lrComment = apiClient.service.AddAlarmComments(alarmId, comment)


def updateLrStatus(apiClient, alarmId, status, comment):
    update = apiClient.service.UpdateAlarmStatus(alarmId, status, comment)


def getNewRecordData(swimlane, appId, trackingId):
    app = swimlane.apps.get(id=appId)
    record = app.records.get(tracking_id=trackingId)
    return record


def postCommentToLrSwimlaneRecordId(apiClient, new_record, swimlane, seAppId, alarmId):
    seRecord = getNewRecordData(swimlane, seAppId, new_record['Tracking Id'])
    comment = "Swimlane Security Event Created: {} {} {}/record/{}/{}".format(
        seRecord['AV: Tracking ID'], seRecord['AV:  Record ID'], sw_context.inputs['swimlaneWebUrl'], seRecord['AV: Application ID'],
        seRecord['AV:  Record ID'])
    updateLrStatus(apiClient, alarmId, "New", comment)


def pollLrAlarms(clientIdToEntitiesId, url, username, password, swimlane, seAppId, listOfEnabledSiemDiagnostics,
                 entityIdExclude, status):
    apiClient = setLrApiClient(url, username, password)
    lrAlarms = getLrAlarms(apiClient, status)
    for page in lrAlarms:
        if page['Alarms'] is not None:
            numberOfAlarms, lrAlarms = findNewAlarms(page, swimlane, seAppId)
            if numberOfAlarms > 0:
                for alarmKey, alarmValue in lrAlarms.iteritems():
                    if alarmValue['EntityID'] not in entityIdExclude:
                        newRecord = createSeRecord(clientIdToEntitiesId, alarmValue, swimlane, seAppId,
                                                   listOfEnabledSiemDiagnostics)
                        print 'New Alarm'
            else:
                print 'No New Alarms'
        else:
            print 'No Alarms'


slApiUser = sw_context.inputs['apiUser']
slApiKey = sw_context.inputs['apiKey']
slApiHost = sw_context.inputs['apiHost']
seAppId = sw_context.inputs['seAppId']
crmAppId = sw_context.inputs['crmAppId']
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
username = sw_context.inputs['lrUsername']
password = sw_context.inputs['lrKey']
url = sw_context.inputs['lrAlarmEndpoint']
os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
sc = SlackClient(sw_context.inputs['slackToken'])
try:
    listOfEnabledSiemDiagnostics = [96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 194, 210, 212, 230, 231,
                                    232,
                                    233, 408, 676, 677, 947, 948, 949, 1002, 1003, 1084, 1093, 1094, 1095, 1096, 1097,
                                    1098,
                                    1099, 1100, 1102, 1139, 1140, 1141, 1424, 1425, 1426, 1427, 1428]
    entityIdExclude = [1, 2, -100]
    clientIdToEntitiesId = getAndBuildClientIdToEntitiesId(swimlane, crmAppId)
    pollLrAlarms(clientIdToEntitiesId, url, username, password, swimlane, seAppId, listOfEnabledSiemDiagnostics,
                 entityIdExclude, "New")
except Exception as e:
    scText = 'Error running integration SE: Poll LogRythem for alarms.  Error: {}'.format(e)
    scApiCall = sc.api_call("chat.postMessage", channel="GCWRQ3802", text=scText)
