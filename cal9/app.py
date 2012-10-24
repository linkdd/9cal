# -*- coding: utf-8 -*-

import posixpath
import sys

import xml.etree.ElementTree as ET
from urllib import unquote

import xmlutils
import ical

def DEBUG(msg):
    print >>sys.stderr, "DEBUG: ", msg

class Application(object):
    """ Main application interface """

    def __call__(self, environ, start_response):
        """ WSGI caller """

        DEBUG('{0} {1}\n{2}'.format(environ['REQUEST_METHOD'], environ['PATH_INFO'], environ))

        status, headers, content = self.manage(environ)

        headers['Content-Length'] = sum([len(c) for c in content])

        start_response(status, list(headers.items()))

        return content

    def manage(self, environ):
        """ Handle a request """

        request = environ['REQUEST_METHOD'].lower()

        try:
            function = getattr(self, request)
        except AttributeError:
            raise NotImplementedError

        request_body = self.wsgi_get_content(environ)
        DEBUG('Request Body:\n{0}'.format(request_body))

        path = self.wsgi_sanitize_path(environ['PATH_INFO'])
        DEBUG('Sanitized path: {0}'.format(path))

        collections = ical.Calendar.from_path(path)

        response = function(path, collections, request_body)
        DEBUG('Response body:\n{0}'.format(response))

        return response

    def wsgi_get_content(self, environ):
        """ Get WSGI input content """

        charsets = []

        # Retrieve content
        content_length = int(environ['CONTENT_LENGTH'] or 0)
        content = environ['wsgi.input'].read(content_length)

        # Retrieve encoding
        content_type = environ['CONTENT_TYPE']

        if content_type and 'charset=' in content_type:
            charsets.append(content_type.split('charset=')[1].strip())

        # Append default encoding
        charsets.append('utf-8')
        charsets.append('iso8859-1')

        # Try to decode content
        for c in charsets:
            try:
                return content.decode(c)
            except UnicodeDecodeError:
                pass

        # No charset worked, raise an error
        raise UnicodeDecodeError

    def wsgi_sanitize_path(self, path):
        """ Unquote and remove possible /../ """

        uri = unquote(path)
        trailing_slash = '/' if uri.endswith('/') else ''
        uri = posixpath.normpath(uri)
        trailing_slash = '' if uri == '/' else trailing_slash

        return '{0}{1}'.format(uri, trailing_slash)

    ## Request handlers

    def options(self, path, collections, request_body):
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
            'DAV': '1, 2, access-control, calendar-access'
        }

        return 200, headers, []

    def propfind(self, path, collections, request_body):
        """
            Manage PROPFIND request.

            According to [RFC 4918], it should have the following request body :

                <D:propfind>
                    <D:prop>
                        ...
                    </D:prop>
                </D:propfind>

            It should return the following content :

                207 Multi-Status

                <D:multistatus>
                    <D:response>
                        <D:href>calendar uri</D:href>
                        <D:propstat>
                            <D:prop>
                                ...
                            </D:prop>
                            <D:status>...</D:status>
                        </D:propstat>
                    </D:response>
                    ...
                </D:multistatus>
        """

        # Read request

        dom = ET.fromstring(request_body)

        dprop = dom.find(xmlutils.tag('D', 'prop'))
        props = [prop.tag for prop in dprop]

        # Write answer

        multistatus = ET.Element(xmlutils.tag('D', 'multistatus'))

        for collection in collections:
            response = xmlutils.propfind_response(path, collection, props)
            multistatus.append(response)

        return xmlutils.render(multistatus)
