from slackclient import SlackClient
from swimlane import Swimlane
from swimlane.core.search import EQ
import time

slApiUser = sw_context.inputs['apiUser']
slApiKey = sw_context.inputs['apiKey']
slApiHost = sw_context.inputs['apiHost']
seAppId = sw_context.inputs['seAppId']
trAppId = sw_context.inputs['trAppId']
recordId = sw_context.inputs['recordId']
os.environ['HTTPS_PROXY'] = sw_context.inputs['proxyUrl']
sc = SlackClient(sw_context.inputs['slackToken'])

class updateOrCreateTicket:
    """Update or create Swimlane ticket class.

    """

    def __init__(self, slApiHost, slApiUser, slApiKey):
        """Sets arguments within the class.

        Args:
            slApiHost (String): Swimlane Host Address i.e. https:/127.0.0.1/
            slApiUser (String): Swimlane API User
            slApiKey (String): Swimlane API Password
        """
        self.swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)
        self.app1Id = None
        self.app2Id = None
        # self.app1 = self.swimlane.apps.get(id=self.app1Id)
        # self.app2 = self.swimlane.apps.get(id=self.app2Id)
        self.fieldsToIncludes = []
        self.fieldsToRemove = []

    def swimlaneUbersmithPriorityMapping(self, priority):
        if priority == 'P1 - Critical':
            return 3
        elif priority == 'P2 - High':
            return 2
        elif priority == 'P3 - Medium':
            return 1
        elif priority == 'P4 - Low':
            return 0
        elif priority == 3:
            return 'P1 - Critical'
        elif priority == 2:
            return 'P2 - High'
        elif priority == 1:
            return 'P3 - Medium'
        elif priority == 0:
            return 'P4 - Low'
        elif priority == '911':
            return 'P1 - Critical'
        elif priority == 'High':
            return 'P2 - High'
        elif priority == 'Normal':
            return 'P3 - Medium'
        elif priority == 'Low':
            return 'P4 - Low'
        else:
            print 'Wrong Priority'

    def swimlaneUbersmithStatusMapping(self, status):
        if status == 'New Case':
            return 1
        elif status == 'Assigned':
            return 1
        elif status == 'In Progress':
            return 1
        elif status == 'Pending Customer Response':
            return 2
        elif status == 'Escalation Required':
            return 1
        elif status == 'Closed':
            return 3
        elif status == 1:
            return 'In Progress'
        elif status == 2:
            return 'Pending Customer Response'
        elif status == 3:
            return 'Closed'
        elif status == 'Open':
            return 'New Case'
        elif status == 'On Hold':
            return 'Pending Customer Response'
        elif status == 'Closed':
            return 'Closed'
        else:
            print 'Wrong Status'

    def setFieldsToIncludes(self, fieldDict):
        """Set that fields that need to be included in ticket creations.

        Args:
            fieldDict (List): List of dict with the except format:
            [{"app2FieldName": <app2fieldName>, "app1FieldName": <app1FieldName>, ...}]
        Return:

        """
        if fieldDict is None:
            self.fieldsToIncludes = None
        else:
            self.fieldsToIncludes = fieldDict

    def setFieldsToRemove(self, fieldList):
        """Set the list of fields that needs to be removed.

        Args:
            fieldList (List): A list of fields that need to be removed.
        Return:
             Nothing
        """
        if fieldList is None:
            self.fieldsToRemove = None
        else:
            self.fieldsToRemove = fieldList

    def getFieldIds(self, app):
        """Builds dictionary of field names and ids base on the given app.

        Args:
            app (object): app object from Swimlane class
        Return:
            The return value is the dictionary.
        """
        fieldIds = {}
        for e in app._raw['fields']:
            fieldIds[e['name']] = e['id']
        return fieldIds

    def buildComparedList(self, app1, app2):
        """Builds a list of common fields between two Swimlane app.
        If fieldToRemove is set, then thus fields will be removed.

        Args:
            app1 (object): The First app
            app2 (object): The Second app
        Return:
            The return value is a list of fields in common to each Swimlane app.
        """
        comparedList = list(set(self.getFieldIds(app1).keys()) & set(self.getFieldIds(app2).keys()))
        if self.fieldsToRemove is not None:
            for e in self.fieldsToRemove:
                while True:
                    try:
                        comparedList.remove(e)
                    except:
                        break
        return comparedList

    def creatNewTicket(self, app1, app2, recordId):
        """ Creates a new ticket within app2 based on record id in app1.
        If fieldsToIncludes is set, then thous fields will be added.

        Args:
            app1 (Object): The First app
            app2 (Object): The Second app
            app1RecordId (String): app1 record id
        Return:
            Returns nothing.
        """
        record1 = app1.records.get(id=recordId)
        fieldDict = {}
        for field in self.buildComparedList(app1, app2):
            fieldDict[field] = record1[field]
        if self.fieldsToIncludes is not None:
            for e in self.fieldsToIncludes:
                if e["app1FieldName"] == 'UBS Prority':
                    fieldDict[e["app2FieldName"]] = self.swimlaneUbersmithPriorityMapping(record1[e["app1FieldName"]])
                elif e["app1FieldName"] == 'UBS Ticket Status':
                    fieldDict[e["app2FieldName"]] = self.swimlaneUbersmithStatusMapping(record1[e["app1FieldName"]])
                else:
                    fieldDict[e["app2FieldName"]] = record1[e["app1FieldName"]]
        fieldDict['Ticket Type'] = 'Security Event'
        new_record = app2.records.create(**fieldDict)
        time.sleep(2)
        app2record = app2.records.get(tracking_id=new_record)
        record1 = app1.records.get(id=recordId)
        record1['TR: Tracking ID'] = app2record['AV: Tracking ID']
        record1['TR: Application ID'] = app2record['AV: Application ID']
        record1['TR: Record ID'] = app2record['AV: Record ID']
        reference = record1['TR: Ticket Routing App']
        reference.add(new_record)
        record1.save()

    def updateTicket(self, app1, app2, recordId):
        """Updates a ticket within app2 base on record id in app1.

        Args:
            app1 (Object):
            app2 (Object):
            recordId (String):
        Return:

        """
        record1 = app1.records.get(id=recordId)
        record2 = app2.records.get(id=record1['TR: Record ID'])
        needToSave = 'no'
        for field in self.buildComparedList(app1, app2):
            if record1[field] != record2[field]:
                record2[field] = record1[field]
                needToSave = 'yes'
        if needToSave == 'yes':
            if self.fieldsToIncludes is not None:
                for e in self.fieldsToIncludes:
                    if e["app1FieldName"] == 'UBS Prority':
                        record2[e["app2FieldName"]] = self.swimlaneUbersmithPriorityMapping(record1[e["app1FieldName"]])
                    elif e["app1FieldName"] == 'UBS Ticket Status':
                        record2[e["app2FieldName"]] = self.swimlaneUbersmithStatusMapping(record1[e["app1FieldName"]])
                    else:
                        record2[e['app2FieldName']] = record1[e['app1FieldName']]
            record2.save()
        record1 = app1.records.get(id=recordId)
        record2 = app2.records.get(id=record1['TR: Record ID'])
        newComments = self.checkAndBuildCommentList(record1, record2)
        if len(newComments) > 0:
            self.postCommentsToApp(app2, record2, record1['TR: Record ID'], newComments)

    def updateOrCreateOnSave(self, app1, app2, recordId):
        """This function checks if it is needed to update or create a ticket

        Args:
            app1 (Object):
            app2 (Object):
            recordId (String):
        Return:

        """
        app1 = self.swimlane.apps.get(id=app1)
        app2 = self.swimlane.apps.get(id=app2)
        record1 = app1.records.get(id=recordId)
        if record1['LG: Record Exists'] == 'yes':
            reports2 = app2.reports.build('Get-All-Reports')
            reports2.filter('Security Event', EQ, record1['AV:  Record ID'])
            if len(reports2) > 1:
                print "Ya That shouldn't be the case."
            elif len(reports2) == 1:
                self.updateTicket(app1, app2, recordId)
            elif len(reports2) == 0:
                self.creatNewTicket(app1, app2, recordId)

    def checkAndBuildCommentList(self, record1, record2):
        ticketHistory1 = record1['Ticket History']
        comments1 = []
        for th1 in ticketHistory1:
            comments1.append({'message': th1.message, 'id': th1.user.id, 'username': th1.user.name,
                              'createdDate': th1.created_date.to_rfc3339_string()})
        ticketHistory2 = record2['Ticket History']
        comments2 = []
        for th2 in ticketHistory2:
            comments2.append({'message': th2.message, 'id': th2.user.id, 'username': th2.user.name,
                              'createdDate': th2.created_date.to_rfc3339_string()})
        newComments = [i for i in comments1 if i not in comments2]
        return newComments

    def postCommentsToApp(self, app2, record2, record2Id, newComments):
        fieldIds2 = self.getFieldIds(app2)
        for k, v in record2._raw['values'].items():
            if v is None:
                record2._raw['values'].pop(k, None)
        record2._raw.pop('modifiedDate', None)
        record2._raw.pop('modifiedByUser', None)
        for comment in newComments:
            if fieldIds2['Ticket History'] not in record2._raw['comments']:
                record2._raw['comments'] = {fieldIds2['Ticket History']: [
                    {u'$type': u'Core.Models.Record.Comments, Core', u'message': comment['message'],
                     u'createdDate': comment['createdDate'],
                     u'createdByUser': {u'$type': u'Core.Models.Utilities.UserGroupSelection, Core',
                                        u'id': comment['id'],
                                        u'name': comment['username']}}]}
            else:
                record2._raw['comments'][fieldIds2['Ticket History']].append(
                    {u'$type': u'Core.Models.Record.Comments, Core', u'message': comment['message'],
                     u'createdDate': comment['createdDate'],
                     u'createdByUser': {u'$type': u'Core.Models.Utilities.UserGroupSelection, Core',
                                        u'id': comment['id'],
                                        u'name': comment['username']}})
        apiRequest = self.swimlane.request('put', '/app/{}/record/{}'.format(seAppId, record2Id), json=record2._raw)
        print apiRequest


try:
    uct = updateOrCreateTicket(slApiHost, slApiUser, slApiKey)
	uct.setFieldsToRemove(['AV: Application ID', 'AV: Record ID', 'AV: Tracking ID', 'DateTimeNow', 'Ticket History',
                       'UBS Comment Replies', 'Tracking Id', 'To', 'CC', 'BCC'])
	uct.setFieldsToIncludes([{"app2FieldName": "Security Event Tracking ID", "app1FieldName": "AV: Tracking ID"},
                         {"app2FieldName": "Security Event", "app1FieldName": "AV:  Record ID"},
                         {"app2FieldName": "Security Event Priority", "app1FieldName": "QV: Priority"},
                         {"app2FieldName": "Security Event Case Title", "app1FieldName": "QV: Case Title"},
                         {"app2FieldName": "Client Name", "app1FieldName": "CS: Client Name"},
                         {"app2FieldName": "Security Event Occurred", "app1FieldName": "CS: Event Occurred"}, ])
	uct.updateOrCreateOnSave(seAppId, trAppId, recordId)
except Exception as e:
    scText = 'Error running integration SE: Push To TR on Record {}. Error: {}'.format(recordId, e)
    scApiCall = sc.api_call("chat.postMessage", channel="GCWRQ3802", text=scText)