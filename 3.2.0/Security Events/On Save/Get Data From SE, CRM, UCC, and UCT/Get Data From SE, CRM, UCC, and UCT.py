from slackclient import SlackClient
from swimlane import Swimlane
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

slApiUser = sw_context.inputs['apiUser']
slApiKey = sw_context.inputs['apiKey']
slApiHost = sw_context.inputs['apiHost']
seAppId = sw_context.config["ApplicationId"]
seRecordId = sw_context.config["RecordId"]
seAlarmRuleName = sw_context.inputs["AlarmRuleName"]
seCaseSource = sw_context.inputs["caseSource"]
crmAppId = sw_context.inputs['crmAppId']
uccAppId = sw_context.inputs['socUccAppId']
uctAppId = sw_context.inputs['socUctAppId']
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
seApp = swimlane.apps.get(id=seAppId)
crmApp = swimlane.apps.get(id=crmAppId)
uccApp = swimlane.apps.get(id=uccAppId)
uctApp = swimlane.apps.get(id=uctAppId)
seRecord = seApp.records.get(id=seRecordId)
tracking_id = seRecord['Tracking Id']
clientName = seRecord['CS: Client Name']
sc = SlackClient(sw_context.inputs['slackToken'])

os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']

def merge_two_dicts(x, y):
    z = x.copy()  # start with x's keys and values
    z.update(y)  # modifies z with y's keys and values & returns None
    return z


try:
    needsToBeSaved = False
    crmReports = crmApp.reports.build('Get All CRM Records')
    clientIDs = []
    for crmRecord in crmReports:
        for e in crmRecord['Entity ID']:
            clientIDs.append(int(e))
    crmReport = crmApp.reports.build('Get All CRM Records')
    crmReport.filter('Client Name', 'equals', clientName)
    recordCount = len(crmReport)
    data = {}
    if clientName == 'Unknown' or recordCount == 0:
        data = {"tracking_id": tracking_id, "allication_id": seAppId, "record_id": seRecordId, "record_exists": "yes",
                "LgPollSEV2Completed": "yes", 'LGPollCRMCompleted': "yes", "LGPollUCTandUCCCompleted": "yes", }
    elif recordCount > 0:
        clientId = None
        crmReport = crmApp.reports.build('Get All CRM Records')
        crmReport.filter('Client Name', 'equals', clientName)
        for crmRecord in crmReport:
            data = {"tracking_id": tracking_id,
                    "allication_id": seAppId,
                    "record_id": seRecordId,
                    "record_exists": "yes",
                    "LgPollSEV2Completed": "yes",
                    'industry': crmRecord['Client Industry'],
                    'employees': crmRecord['Client Number of Employees'],
                    'operation': crmRecord['Client Country of Operation'],
                    'notes': crmRecord['Additional notes'],
                    'ubscid': crmRecord['UBS: Client ID'],
                    'ubscname': crmRecord['UBS: Client Name'],
                    'LGPollCRMCompleted': "yes",
                    "UbsClientId": crmRecord['UBS: Client ID'],
                    "UbsClientName": crmRecord['UBS: Client Name'],
                    "ClientId": clientId}
            contactToList = []
            CcContactToList = []
            for r in crmRecord['Primary Alert Contact Information']:
                seRecord['Primary Alert Contact Information'].add(r)
                contactToList.append(r['E-Mail'])
                needsToBeSaved = True
            for r in crmRecord['Secondary Alert Contact Information']:
                seRecord['Secondary Alert Contact Information'].add(r)
                CcContactToList.append(r['E-Mail'])
                needsToBeSaved = True
            for r in crmRecord['Tertiary Alert Contact Information']:
                seRecord['Tertiary Alert Contact Information'].add(r)
                CcContactToList.append(r['E-Mail'])
                needsToBeSaved = True
            for r in crmRecord['Quaternary Alert Contact Information']:
                seRecord['Quaternary Alert Contact Information'].add(r)
                CcContactToList.append(r['E-Mail'])
                needsToBeSaved = True
            for r in crmRecord['On-Call Alert Contact Information']:
                seRecord['On-Call Alert Contact Information'].add(r)
                CcContactToList.append(r['E-Mail'])
                needsToBeSaved = True
            if needsToBeSaved:
                seRecord['LG: No Second Pass'] = 'no'
                seRecord.save()
            contactToList = list(set(contactToList))
            CcContactToList = list(set(CcContactToList))
            data["to"] = contactToList
            data['cc'] = CcContactToList
    if seCaseSource == 'SIEM Alert' or seCaseSource == 'SIEM Diagnostics':
        uccReport = uccApp.reports.build('Get UCC App Records')
        uccReport.filter('SIEM Rule Name', 'equals', seAlarmRuleName)
        uccReport.filter('Client Name', 'equals', clientName)
        recordCount = len(uccReport)
        if recordCount > 0:
            for uccRecord in uccReport:
                fields = {"LGPollUCTandUCCCompleted": "yes",
                          "priority": uccRecord['SIEM Priority'],
                          "ruleId": uccRecord['SIEM Rule Number'],
                          "rpn": uccRecord['Response Procedure Name'],
                          "LG: UCT Exists": "yes",
                          "VERISSecurityIncident": uccRecord['VERIS: Security Incident'],
                          "VERISConfidence": uccRecord['VERIS: Confidence?'],
                          "VERISCustomerInternal": uccRecord['VERIS: Customer (Internal)'],
                          "VERISPrimaryThreatActor": uccRecord['VERIS: Primary Threat Actor'],
                          "VERISVarietiesofinternalactors": uccRecord['VERIS: Varieties of internal actors'],
                          "VERISMotivesofinternalactors": uccRecord['VERIS: Motives of internal actors'],
                          "VERISErrorActions": uccRecord['VERIS: Error Action(s)'],
                          "VERISPrimaryThreatAction": uccRecord['VERIS: Primary Threat Action'],
                          "VERISVarietiesoferrors": uccRecord['VERIS: Varieties of errors'],
                          "VERISWhyerrorsoccurred": uccRecord['VERIS: Why errors occurred'],
                          "VERISIfvarietyLosswherelost": uccRecord['VERIS: If variety = \'Loss\', where lost?'],
                          "VERISWhoHOSTSorstorestheseassets": uccRecord['VERIS: Who HOSTS (or stores) these asset(s)?'],
                          "VERISWhoMANAGEStheseassets": uccRecord['VERIS: Who MANAGES these asset(s)?'],
                          "VERISAvailabilityUtility": uccRecord['VERIS: Availability/Utility'],
                          "VERISInterruption": uccRecord['VERIS: Interruption'],
                          "CyberKillChainPhase": uccRecord['Cyber Kill Chain Phase'],
                          "RecommendedActionbyClient": uccRecord['Recommended Action by Client'],
                          "RecommendedActionbyAnalyst": uccRecord['Recommended Action by Analyst'],
                          "Introduction": uccRecord['Introduction'],
                          "Logic": uccRecord['Logic'],
                          }
                data = merge_two_dicts(data, fields)
        elif recordCount == 0:
            data = merge_two_dicts(data, {"record_exists": "yes",
                                          "LgPollSEV2Completed": "yes",
                                          "LGPollUCTandUCCCompleted": "yes",
                                          "LGPollCRMCompleted": "yes", })

    else:
        data = merge_two_dicts(data, {"tracking_id": tracking_id,
                                      "allication_id": seAppId,
                                      "record_id": seRecordId,
                                      "record_exists": "yes",
                                      "LgPollSEV2Completed": "yes",
                                      "LGPollUCTandUCCCompleted": "yes",
                                      "LGPollCRMCompleted": "yes",})
    seRecord = seApp.records.get(id=seRecordId)
    scData = {}
    if seRecord['LG: No Second Pass'] != 'no':
        if seRecord['ts']:
            scText = 'Updated Ticket Details: {}/record/{}/{}'.format(sw_context.inputs['swimlaneWebUrl'], seAppId,
                                                                      seRecordId)
            scApiCall = sc.api_call("chat.postMessage", channel="GBNQZ0F27", text=scText, thread_ts=seRecord['ts'])
            scData = {'ts': scApiCall['ts'], 'channel': scApiCall['channel']}
        else:
            scText = 'New Security Event Created: {}/record/{}/{}'.format(sw_context.inputs['swimlaneWebUrl'], seAppId,
                                                                          seRecordId)
            scApiCall = sc.api_call("chat.postMessage", channel=sw_context.inputs['slackAlarmChannel'], text=scText)
            scData = {'ts': scApiCall['ts'], 'channel': scApiCall['channel']}
    combineData = merge_two_dicts(data, scData)
    sw_outputs = [combineData]
except Exception as e:
    scText = 'Error running integration SE: Poll data from SE, CRM, UCC, and UCT on Record {}. Error: {}'.format(seRecordId, e)
    scApiCall = sc.api_call("chat.postMessage", channel=sw_context.inputs['slackErrorChannel'], text=scText)