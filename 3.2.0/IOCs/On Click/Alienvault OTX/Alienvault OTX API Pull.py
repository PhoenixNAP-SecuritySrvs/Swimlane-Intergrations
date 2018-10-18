import requests
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter


class otxAPI():
    def __init__(self):
        self.key = sw_context.inputs['otx_api_key']
        self.headers = {'X-OTX-API-KEY': self.key, 'User-Agent': 'OTX Swimlane Python SDK/1.0',
                        'Content-Type': 'application/json'}
        self.ioc = None
        self.iocType = None
        self.project = 'SDK'
        self.proxies = {'http': sw_context.inputs['proxy'], 'https': sw_context.inputs['proxy']}
        self.response = None
        self.request_session = requests.Session()
        self.request_session.mount('https://', HTTPAdapter(
            max_retries=Retry(total=5, status_forcelist=[429, 500, 502, 503], backoff_factor=5, )))
        self.section = None
        self.server = sw_context.inputs['otx_api_server']
        self.table = None
        self.uri = None

    def buildURL(self):
        if self.iocType == "IPv4" or self.iocType == "IPv6":
            if self.section is not None:
                self.uri = '{}/api/v1/indicators/IPv4/{}/{}'.format(self.server, self.ioc, self.section)
            else:
                self.uri = '{}/api/v1/indicators/IPv4/{}/'.format(self.server, self.ioc)
        return self.uri

    def formatTable(self, response):
        self.table = '<table>'
        for aKey in response.keys():
            if type(response[aKey]) is dict:
                for bKey in response[aKey].keys():
                    self.table += '<tr><td style="text-align: center;">{}</td><td style="text-align: center;">{}</td></tr>'.format(
                        bKey, response[aKey][bKey])
            else:
                self.table += '<tr><td style="text-align: center;">{}</td><td style="text-align: center;">{}</td></tr>'.format(
                    aKey, response[aKey])
        self.table += '</table>'
        self.response = self.table
        return self.response

    def generalFilter(self, general):
        if 'pulses' in general:
            del general['pulses']
        if 'pulse_info' in general:
            del general['pulse_info']
        if 'sections' in general:
            del general['sections']
        return general

    def makeAPICall(self):
        return self.request_session.get(self.buildURL(), headers=self.headers, proxies=self.proxies)

    def lookupIPv4IOC(self):
        self.setIOCType('IPv4')
        self.setSection('general')
        self.general = self.formatTable(self.generalFilter(self.makeAPICall().json()))
        self.setSection('geo')
        self.geo = self.formatTable(self.makeAPICall().json())
        self.setSection('reputation')
        self.reputation = self.formatTable(self.makeAPICall().json())
        self.setSection('url_list')
        self.url_list = self.formatTable(self.makeAPICall().json())
        self.setSection('passive_dns')
        self.passive_dns = self.formatTable(self.makeAPICall().json())
        self.setSection('malware')
        self.malware = self.formatTable(self.makeAPICall().json())
        self.setSection('nids_list')
        self.nids_list = self.formatTable(self.makeAPICall().json())
        self.setSection('http_scans')
        self.http_scans = self.formatTable(self.makeAPICall().json())

    def lookupIPv6IOC(self):
        self.setIOCType('IPv4')
        self.setSection('general')
        self.general = self.formatTable(self.generalFilter(self.makeAPICall().json()))
        self.setSection('geo')
        self.geo = self.formatTable(self.makeAPICall().json())
        self.setSection('reputation')
        self.reputation = self.formatTable(self.makeAPICall().json())
        self.setSection('url_list')
        self.url_list = self.formatTable(self.makeAPICall().json())
        self.setSection('passive_dns')
        self.passive_dns = self.formatTable(self.makeAPICall().json())
        self.setSection('malware')
        self.malware = self.formatTable(self.makeAPICall().json())
        self.setSection('http_scans')
        self.http_scans = self.formatTable(self.makeAPICall().json())

    def setSWOutput(self):
        if self.iocType == 'IPv4':
            self.swOutputs = [{'general': self.general, 'geo': self.geo, 'reputation': self.reputation, 'url_list': self.url_list, 'passive_dns': self.passive_dns, 'malware': self.malware, 'nids_list': self.nids_list, 'http_scans': self.http_scans}]
        elif self.iocType == 'IPv6':
            self.swOutputs = [{'general': self.general, 'geo': self.geo, 'reputation': self.reputation, 'url_list': self.url_list, 'passive_dns': self.passive_dns, 'malware': self.malware, 'nids_list': self.nids_list}]

    def setIOC(self, IOC):
        self.ioc = IOC

    def setIOCType(self, iocType):
        self.iocType = iocType

    def setSection(self, section):
        self.section = section


otx = otxAPI()
otx.setIOCType(sw_context.inputs['iocType'])
otx.setIOC(sw_context.inputs['ioc'])
if otx.iocType == 'IPv4':
    otx.lookupIPv4IOC()
elif otx.iocType == 'IPv6':
    otx.lookupIPv6IOC()
otx.setSWOutput()

sw_outputs = otx.swOutputs