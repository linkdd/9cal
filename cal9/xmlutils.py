# -*- coding: utf-8 -*-

from util import http_response
import ical

import xml.etree.ElementTree as ET
import re
import os

NAMESPACES = {
    'C': 'urn:ietf:params:xml:ns:caldav',
    'CR': 'urn:ietf:params:xml:ns:carddav',
    'D': 'DAV:',
    'CS': 'http://calendarserver.org/ns/',
    'ICAL': 'http://apple.com/ns/ical/',
    'ME': 'http://me.com/_namespace/',
}

# Generate reverse dict

NAMESPACES_REV = {}

for ns, url in NAMESPACES.items():
    NAMESPACES_REV[url] = ns

    # Register namespace
    if hasattr(ET, 'register_namespace'):
        ET.register_namespace('' if ns == 'D' else ns, url)
    else:
        ET._namespace_map[url] = ns


CLARK_TAG_REGEX = re.compile(r'{(?P<namespace>[^}]*)}(?P<tag>.*)')

def tag(ns, name):
    return '{{{0}}}{1}'.format(NAMESPACES[ns], name)

def tag_clark(tagname):
    match = CLARK_TAG_REGEX.match(tagname)

    if match and match.group('namespace') in NAMESPACES_REV:
        return '{0}:{1}'.format(
                NAMESPACES_REV[match.group('namespace')],
                match.group('tag')
        )

    return tagname

def render(xml):
    """ Render XML tree to string """

    return u'<?xml version="1.0" encoding="utf-8" ?>{0}'.format(ET.tostring(xml))


def propfind_response(path, item, props):
    """ Perform a PROPFIND on ``item`` """

    is_collection = isinstance(item, ical.Calendar)

    if is_collection:
        with item.props as properties:
            collection_props = properties

    response = ET.Element(tag('D', 'response'))

    href = ET.Element(tag('D', 'href'))
    href.text = item.name
    response.append(href)

    propstat404 = ET.Element(tag('D', 'propstat'))
    propstat200 = ET.Element(tag('D', 'propstat'))
    response.append(propstat200)

    prop404 = ET.Element(tag('D', 'prop'))
    propstat404.append(prop404)

    prop200 = ET.Element(tag('D', 'prop'))
    propstat200.append(prop200)

    for xmltag in props:
        element = ET.Element(xmltag)
        tag_not_found = False

        if xmltag == tag('D', 'getetag'):
            element.text = item.etag

        elif xmltag == tag('D', 'principal-URL'):
            xmltag = ET.Element(tag('D', 'href'))
            xmltag.text = path
            element.append(xmltag)

        elif xmltag in (
                tag('D', 'principal-collection-set'),
                tag('C', 'calendar-user-address-set'),
                tag('C', 'calendar-home-set')
                ):
            xmltag = ET.Element(tag('D', 'href'))
            xmltag.text = path
            element.append(xmltag)

        elif xmltag == tag('C', 'supported-calendar-component-set'):
            for component in ("VTODO", "VEVENT", "VJOURNAL"):
                comp = ET.Element(tag('C', 'comp'))
                comp.set('name', component)
                element.append(comp)

        elif xmltag == tag('D', 'current-user-principal'):
            xmltag = ET.Element(tag('D', 'href'))
            xmltag.text = path
            element.append(xmltag)

        elif xmltag == tag('D', 'current-user-privilege-set'):
            privilege = ET.Element(tag('D', 'privilege'))
            privilege.append(ET.Element(tag('D', 'all')))
            element.append(privilege)

        elif xmltag == tag('D', 'supported-report-set'):
            for report_name in (
                    'principal-property-search',
                    'sync-collection',
                    'expand-property',
                    'principal-search-property-set'
                    ):
                supported = ET.Element(tag('D', 'supported-report'))
                report_tag = ET.Element(tag('D', 'report'))
                report_tag.text = report_name
                supported.append(report_tag)
                element.append(supported)

        elif is_collection:
            # Only for collections
            if xmltag == tag('D', 'getcontenttype'):
                element.text = item.mimetype

            elif xmltag == tag('D', 'resourcetype'):
                xmltag = ET.Element(tag('C', item.resource_type))
                element.append(xmltag)

                xmltag = ET.Element(tag('D', 'collection'))
                element.append(xmltag)

            elif xmltag == tag('D', 'owner'):
                element.text = os.path.dirname(path)

            elif xmltag == tag('CS', 'getctag'):
                element.text = item.etag

            elif xmltag == tag('C', 'calendar-timezone'):
                element.text = item.timezones.to_ical()

            else:
                tagname = tag_clark(xmltag)

                if tagname in collection_props:
                    element.text = collection_props[tagname]
                else:
                    tag_not_found = True

        # Not for collections
        elif xmltag == tag('D', 'getcontenttype'):
            element.text = '{0}; component={1}'.format(item.mimetype, item.tag.lower())

        elif xmltag == tag('D', 'resourcetype'):
            # Must be empty for non-collection element
            pass

        else:
            tag_not_found = True

        if tag_not_found:
            prop404.append(element)
        else:
            prop200.append(element)

    status200 = ET.Element(tag('D', 'status'))
    status200.text = http_response(200)
    propstat200.append(status200)

    status404 = ET.Element(tag('D', 'status'))
    status404.text = http_response(404)
    propstat404.append(status404)

    if len(prop404):
        response.append(propstat404)

    return response

