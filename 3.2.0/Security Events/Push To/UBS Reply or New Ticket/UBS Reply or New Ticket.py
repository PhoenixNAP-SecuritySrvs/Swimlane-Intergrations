from slackclient import SlackClient
from swimlane import Swimlane
import ubersmith_client

os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
sc = SlackClient(sw_context.inputs['slackToken'])

slApiUser = sw_context.inputs['apiUser']
slApiKey = sw_context.inputs['apiKey']
slApiHost = sw_context.inputs['apiHost']
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
seAppId = sw_context.inputs['seAppId']
seRecordId = sw_context.config["RecordId"]
seApp = swimlane.apps.get(id=seAppId)
seRecord = seApp.records.get(id=seRecordId)
ubsHost = sw_context.inputs['ubsHost']
ubsApiUser = sw_context.inputs['ubsApiUser']
ubsApiKey = sw_context.inputs['ubsApiKey']
ubsApi = ubersmith_client.api.init(ubsHost, ubsApiUser, ubsApiKey)

try:
    if seRecord['LG: Record Exists'] == 'yes':
        ubsOutput = None
        ubsTicketNumber = None
        if seRecord['UBS Action'] == 'Reply To Client':
            params = {'ticket_id': seRecord['UBS Ticket Number'], 'subject': seRecord['Message Subject'],
                      'body': seRecord['Message Body'], 'comment': 0, 'recipient': seRecord['To'],
                      'author': 'soc@phoenixnap.com', 'cc': seRecord['CC'], 'bcc': seRecord['BCC'],
                      'meta_security_event_source': seRecord['QV: Case Source'],
          			  'meta_security_case_stage': seRecord['QV Case Stage'],
          			  'meta_swimlane_case_number': seRecord['QV: Case Number'],
          			  'meta_security_case_type': 'Security Event',
          			  'meta_date_security_event_occurred': seRecord['TL: Event Occurred'],}
            ubsOutput = ubsApi.support.ticket_post_staff_response(**params)
            print ubsOutput
        elif seRecord['UBS Action'] == 'Create New Ticket':
            params = {'internal_ticket': 1, 'body': seRecord['Message Body'], 'subject': seRecord['Message Subject'],
                      'author': 'soc@phoenixnap.com', 'name': 'SOC api user', 'cc': seRecord['CC'],
                      'bcc': seRecord['BCC'], 'priority': seRecord['UBS Prority'], 'queue': 139,
                      'client_id': seRecord['UBS: Client ID'],
                      'meta_security_event_source': seRecord['QV: Case Source'],
          			  'meta_security_case_stage': seRecord['QV Case Stage'],
          			  'meta_swimlane_case_number': seRecord['QV: Case Number'],
          			  'meta_security_case_type': 'Security Event',
          			  'meta_date_security_event_occurred': seRecord['TL: Event Occurred'],}
            ubsTicketNumber = ubsApi.support.ticket_submit(**params)
            ubsOutput = ubsApi.support.ticket_update(ticket_id=ubsTicketNumber, assignment=996)
            print ubsTicketNumber, ubsOutput
        elif seRecord['UBS Action'] == 'Create New Outgoing Ticket':
            params = {'internal_ticket': 1, 'body': seRecord['Message Body'], 'subject': seRecord['Message Subject'],
                      'user_id': 996,
                      'recipient': seRecord['To'], 'author': 'soc@phoenixnap.com', 'cc': seRecord['CC'],
                      'bcc': seRecord['BCC'],
                      'priority': seRecord['UBS Prority'], 'queue': 139, 'client_id': seRecord['UBS: Client ID'],
                      'meta_security_event_source': seRecord['QV: Case Source'],
          			  'meta_security_case_stage': seRecord['QV Case Stage'],
          			  'meta_swimlane_case_number': seRecord['QV: Case Number'],
          			  'meta_security_case_type': 'Security Event',
          			  'meta_date_security_event_occurred': seRecord['TL: Event Occurred'], }
            ubsTicketNumber = ubsApi.support.ticket_submit_outgoing(**params)
        elif seRecord['UBS Action'] == 'Post Comment':
            pass
        if ubsTicketNumber is not None:
            sw_outputs = [{'UbsTicketNumber': ubsTicketNumber, 'RemoveLastMessage': ''}]
except Exception as e:
    scText = 'Error running integration SE: Push To TR on Record {}. Error: {}'.format(seRecord, e)
    scApiCall = sc.api_call("chat.postMessage", channel="GCWRQ3802", text=scText)
