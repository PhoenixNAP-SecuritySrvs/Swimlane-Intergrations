from collections import OrderedDict
from slackclient import SlackClient
from swimlane import Swimlane
from swimlane.core.search import NOT_EQ
import datetime, json, os, pendulum, re, socket, sys, time, ubersmith_client
from collections import OrderedDict

os.environ['HTTPS_PROXY'] = sw_context.inputs['proxy']

slApiUser = sw_context.inputs['slApiUser']
slApiKey = sw_context.inputs['slApiKey']
slApiHost = sw_context.inputs['slApiHost']
swimlane = Swimlane(slApiHost, slApiUser, slApiKey, verify_ssl=False)

ubsHost = sw_context.inputs['ubsHost']
ubsApiUser = sw_context.inputs['ubsUser']
ubsApiKey = sw_context.inputs['ubsKey']
ubsApi = ubersmith_client.api.init(ubsHost, ubsApiUser, ubsApiKey)

ubsApiTicketList = ubsApi.support.ticket_list(queue=139, type=1)
for ubsApiTicketNumber, ubsApiTicketData in ubsApiTicketList.iteritems():
    for ubsApiTicketDetailField, ubsApiTicketDetailValue in ubsApi.support.ticket_get(ticket_id=ubsApiTicketNumber).iteritems():
        if ubsApiTicketDetailField not in ubsApiTicketData.keys():
            ubsApiTicketList[ubsApiTicketNumber][ubsApiTicketDetailField] = ubsApiTicketDetailValue
ubsOutputs = []
for ticket in ubsApiTicketList.values():
    ubsApiTicket = {}
    for k, v in ticket.iteritems():
        ubsApiTicket[k.replace("_", " ").title()] = v
        ubsOutputs.append(ubsApiTicket)
sw_outputs = ubsOutputs
print sw_outputs