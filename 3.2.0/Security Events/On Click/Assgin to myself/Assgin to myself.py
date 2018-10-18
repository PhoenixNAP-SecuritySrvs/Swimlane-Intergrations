#imports
from swimlane import Swimlane

#variable definitions
recordId = sw_context.config["RecordId"]
applicationId = sw_context.config["ApplicationId"]
host = sw_context.inputs['host']
apiUser = sw_context.inputs['apiUser']
apiKey = sw_context.inputs['apiKey']

#connection string
swimlane = Swimlane(host, apiUser, apiKey, verify_ssl=False)

#get applicationID
app = swimlane.apps.get(id=applicationId)

#get recordID
record = app.records.get(id=recordId)

#assigns record to logged in user
user = swimlane.users.get(display_name=sw_context.user['display_name'])
record['AP: Assigned To User(s)'] = [user]

#save the record
record.save()
sw_outputs = [{"LGAssignedToMySelf": 'yes'}]