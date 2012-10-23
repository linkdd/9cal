# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import httplib

NAMESPACES = {
    'C': 'urn:ietf:params:xml:ns:caldav',
    'CR': 'urn:ietf:params:xml:ns:carddav',
    'D': 'DAV:',
    'CS': 'http://calendarserver.org/ns/',
    'ICAL': 'http://apple.com/ns/ical/',
    'ME': 'http://me.com/_namespace/',
}

def tag(ns, name):
    return '{{{0}}}{1}'.format(NAMESPACES[ns], name)

def parseString(xml):
    return ET.fromstring(xml)

class XMLMultiStatus(object):
    """
        Build XML for Multi-Status body.

        <D:multistatus>
            <D:response>
                <D:propstat>
                    <D:prop>
                        <D:href>Complete URL to calendar</D:href>
                        <D:getetag>iCalendar hash</D:getetag>
                        <C:calendar-data>iCalendar</C:calendar-data>
                    </D:prop>
                    <D:status>HTTP/1.1 statuscode statusmsg</D:status>
                </D:propstat>
            </D:response>
            ...
        </D:multistatus>
    """

    def __init__(self):
        self.dom = ET.Element('D:multistatus')
        self.dom.attrib['xmlns:D'] = NAMESPACES['D']
        self.dom.attrib['xmlns:C'] = NAMESPACES['C']

    def __str__(self):
        return ET.dump(self.dom) or ''

    def add_response(self, code, href, ical):
        response = ET.SubElement(self.dom, 'D:response')

        Dhref = ET.SubElement(response, 'D:href')
        Dhref.text = href

        propstat = ET.SubElement(response, 'D:propstat')
        prop = ET.SubElement(propstat, 'D:prop')

        calendar_data = ET.SubElement(prop, 'C:calendar-data')
        calendar_data.text = ical.to_ical()

        getetag = ET.SubElement(prop, 'D:getetag')
        getetag.text = hash(calendar_data.text)

        status = ET.SubElement(propstat, 'D:status')
        status.text = 'HTTP/1.1 {0} {1}'.format(code, httplib.responses[code])


