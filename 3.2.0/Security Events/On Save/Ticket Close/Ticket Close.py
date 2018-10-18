from requests import Session
from slackclient import SlackClient
from swimlane import Swimlane
from zeep import Client, helpers
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
import json
import os
import time
import urllib3


lrApiUsername = sw_context.inputs['lrApiUsername']
lrApiPassword = sw_context.inputs['lrApiKey']
lrApiUrl = sw_context.inputs['lrApiHost']
os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
slApiUser = sw_context.inputs['swimlaneApiUser']
slApiKey = sw_context.inputs['swimlaneApiKey']
slApiHost = sw_context.inputs['swimlaneApiHost']
seAppId = sw_context.config["ApplicationId"]
seRecordId = sw_context.config["RecordId"]
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
seApp = swimlane.apps.get(id=seAppId)
seRecord = seApp.records.get(id=seRecordId)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def swimlaneToLRStatusMapping(swimlaneStatus, swimlaneClosureReason):
    if swimlaneStatus == 'New Case':
        return 'New'
    elif swimlaneStatus == 'Assigned':
        return 'Opened'
    elif swimlaneStatus == 'In Progress':
        return 'Working'
    elif swimlaneStatus == 'Pending Customer Response':
        return 'Escalated'
    elif swimlaneStatus == 'Escalation Required':
        return 'Escalated'
    elif swimlaneStatus == 'Closed':
        if swimlaneClosureReason == 'Customer Notified':
            return 'Closed_Reported'
        elif swimlaneClosureReason == 'Duplicate Case':
            return 'Closed'
        elif swimlaneClosureReason == 'Escalated to Engineering':
            return 'Closed_Unresolved'
        elif swimlaneClosureReason == 'False Positive':
            return 'Closed_FalseAlarm'
        elif swimlaneClosureReason == 'SOC Resolved':
            return 'Closed_Resolved'


def buildLrComment(seRecord, seAppId, seRecordId):
    users = None
    if len(seRecord['AP: Assigned To User(s)']) + len(seRecord['AP: Support User(s)']) > 1:
        userList = []
        for user in seRecord['AP: Assigned To User(s)']:
            userList.append(user.name)
        for user in seRecord['AP: Support User(s)']:
            userList.append(user.name)
        users = ", ".join(userList)
    else:
        for user in seRecord['AP: Assigned To User(s)']:
            users = user.name
    return 'Security Event Closed at {} by {} for reason {}. {}/record/{}/{}'.format(
        seRecord['TL: Case Closed'].to_datetime_string(), users, seRecord['Closure Reason'], sw_context.inputs['swimlaneWebUrl'], seAppId, seRecordId)



session = Session()
session.verify = False
transport = Transport(session=session)
apiClient = Client(lrApiUrl, wsse=UsernameToken(lrApiUsername, lrApiPassword), transport=transport)
update = apiClient.service.UpdateAlarmStatus(seRecord['Alarm ID'], swimlaneToLRStatusMapping(seRecord['CS: Case Status'], seRecord['Closure Reason']), buildLrComment(seRecord, seAppId, seRecordId))
