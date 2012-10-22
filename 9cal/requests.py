# -*- coding: utf-8 -*-

import icalendar

from . import xmlutils
from . import dav

def options(environ, content):
    """
        Manage OPTIONS request.

        According to [RFC 4791], it should return following headers :

            HTTP/1.1 200 OK
            Allow: OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE
            Allow: PROPFIND, PROPPATCH, LOCK, UNLOCK, REPORT, ACL
            DAV: 1, 2, access-control, calendar-access
            Content-Length: 0
    """

    headers = {
        'Allow': 'OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, COPY, MOVE, PROPFIND, PROPPATCH, LOCK, UNLOCK, REPORT, ACL',
        'DAV': '1, 2, access-control, calendar-access',
    }

    return 200, headers, []

def mkcalendar(environ, content):
    headers = {
        'Cache-Control': 'no-cache',
    }

    dom = xmlutils.parseString(content)

    # Retrieve calendar properties

    Dset = dom.find(xmlutils.tag('D', 'set'))

    if Dset is None:
        return 500, headers, ['Can\'t find <D:set> tag in XML data\n']

    Dprops = Dset.find(xmlutils.tag('D', 'prop'))

    if Dprops is None:
        return 500, headers, ['Can\'nt find <D:set> / <D:prop> tag in XML data\n']

    props = {
        'type': 'C:mkcalendar',
    }

    for child in Dprops:
        if child.tag == xmlutils.tag('D', 'displayname'):
            props['D:displayname'] = child.text

        elif child.tag == xmlutils.tag('C', 'calendar-description'):
            props['C:calendar-description'] = child.text

        elif child.tag == xmlutils.tag('C', 'supported-calendar-component-set'):
            props['C:supported-calendar-component-set'] = []

            for comp in child:
                if comp.tag == xmlutils.tag('C', 'comp'):
                    props['C:supported-calendar-component-set'].append(comp.attrib['name'])

        elif child.tag == xmlutils.tag('C', 'calendar-timezone'):
            props['C:calendar-timezone'] = icalendar.Calendar.from_ical(child.text)

    # Create ressource
    rsrc = dav.Ressource(**props)
    rsrc.save()

    return 201, headers, []

requests = {
    'OPTIONS': options,
    'MKCALENDAR': mkcalendar
}
