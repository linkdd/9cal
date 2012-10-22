# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET

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

