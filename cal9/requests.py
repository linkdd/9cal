# -*- coding: utf-8 -*-

import icalendar

from backend import Backend
from . import xmlutils

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
    """
        Body:

        <C:mkcalendar>
            <D:set>
                <D:prop>
                    <D:displayname>display name</D:displayname>
                    <C:calendar-description>description</C:calendar-description>
                    <C:supported-calendar-component-set>
                        <C:comp name="COMPONENT TYPE" />
                        ...
                    </C:supported-calendar-component-set>
                    <C:calendar-timezone>
                        iCal object: timezone
                    </C:calendar-timezone>
                </D:prop>
            </D:set>
        </C:mkcalendar>
    """

    headers = {
        'Cache-Control': 'no-cache',
    }

    dom = xmlutils.parseString(content)

    # Retrieve calendar properties

    displayname = dom.findall('./{0}/{1}/{2}'.format(
                        xmlutils.tag('D', 'set'),
                        xmlutils.tag('D', 'prop'),
                        xmlutils.tag('D', 'displayname')
    ))

    description = dom.findall('./{0}/{1}/{2}'.format(
                        xmlutils.tag('D', 'set'),
                        xmlutils.tag('D', 'prop'),
                        xmlutils.tag('C', 'calendar-description')
    ))

    comps = dom.findall('./{0}/{1}/{2}'.format(
                        xmlutils.tag('D', 'set'),
                        xmlutils.tag('D', 'prop'),
                        xmlutils.tag('C', 'supported-calendar-component-set')
    ))

    components = []

    for comp in comps[0]:
        if comp.tag == xmlutils.tag('C', 'comp'):
            components.append(comp.attrib['name'])

    timezone = dom.findall('./{0}/{1}/{2}'.format(
                        xmlutils.tag('D', 'set'),
                        xmlutils.tag('D', 'prop'),
                        xmlutils.tag('C', 'calendar-timezone')
    ))

    # here, we got lists, if the element wasn't found, then the list is empty
    if not displayname or not description or not components or not timezone:
        return 500, headers, ['Invalid XML body.\n']

    try:
        status, msg = Backend.mkcalendar(environ['PATH_INFO'],
                                         displayname[0].text,
                                         description[0].text,
                                         icalendar.Calendar.from_ical(timezone[0].text)
        )
    except NotImplementedError:
        return 500, headers, ['Not yet implemented.\n']

    return status, headers, msg

requests = {
    'OPTIONS': options,
    'MKCALENDAR': mkcalendar
}
