# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from urllib import unquote
import icalendar
import posixpath
import os

from util import DEBUG
import config
import backends
import xmlutils
import ical

class Application(object):
    """ Main application interface """

    def __init__(self, confpath):
        config.load(confpath)
        backends.load()

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

        request_body = self.wsgi_get_content(environ)
        DEBUG('Request Body:\n{0}'.format(request_body))

        path = self.wsgi_sanitize_path(environ['PATH_INFO'])
        DEBUG('Sanitized path: {0}'.format(path))

        try:
            function = getattr(self, request)
        except AttributeError:
            raise NotImplementedError

        collections = ical.Calendar.from_path(path)

        response = function(path, collections, request_body, environ)
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

    def wsgi_name_from_path(self, path, collection):
        """ Get item name from path """

        collection_parts = collection.path.strip('/').split('/')
        path_parts = path.strip('/').split('/')

        if (len(path_parts) - len(collection_parts)):
            name = os.path.splitext(path_parts[-1])[0]

            DEBUG('name from path: {0}'.format(name))

            return name

    ## Request handlers

    def options(self, path, collections, request_body, environ):
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

    def propfind(self, path, collections, request_body, environ):
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

        headers = {
            'DAV': '1, 2, access-control, calendar-access',
            'Content-Type': 'text/xml',
        }

        # Read request

        dom = ET.fromstring(request_body)

        dprop = dom.find(xmlutils.tag('D', 'prop'))
        props = [prop.tag for prop in dprop]

        # Write answer

        multistatus = ET.Element(xmlutils.tag('D', 'multistatus'))

        for collection in collections:
            response = xmlutils.propfind_response(path, collection, props)
            multistatus.append(response)

        return 207, headers, [xmlutils.render(multistatus)]

    def head(self, path, collections, request_body, environ):
        """
            Manage HEAD request.

            According to [RFC 2518], a HEAD request is like a GET
            request, but without response body.
        """

        status, headers, body = self.get(path, collections, request_body, environ)
        return status, headers, []

    def get(self, path, collections, request_body, environ):
        """
            Manage GET request.

            It should return the Etag and the resource content.
        """

        headers = {}

        collection = collections[0]
        item_name = self.wsgi_name_from_path(path, collection)

        if item_name:
            # Retrieve collection item
            item = collection.get_item(item_name)

            if item:
                items = collection.timezones
                items.append(item)
                body = items.to_ical()
                etag = item.etag
            else:
                return 410, headers, []
        else:
            # Get whole collection
            body = collection.text
            etag = collection.etag

        headers['Content-Type'] = collection.mimetype
        headers['Last-Modified'] = collection.last_modified
        headers['ETag'] = etag

        return 200, headers, [body]

    def report(self, path, collections, request_body, environ):
        """
            Manage REPORT request.

            According to [RFC 3253], it should return 207 Multi-Status.
            The request body contains :

                <C:calendar-query>
                    <D:prop>
                        ...
                    </D:prop>
                </C:calendar-query
        """

        headers = {
            'Content-Type': 'text/xml',
        }

        return 207, headers, []


    def put(self, path, collections, request_body, environ):
        """
            Manage PUT request.

            It should return the etag of the element after setting it.
        """

        headers = {}

        ical = icalendar.Calendar.from_ical(request_body)

        collection = collections[0]
        item_name = self.wsgi_name_from_path(path, collection)

        item = collection.get_item(item_name)

        if (not item and not environ.get('HTTP_IF_MATCH')) or (item and environ.get('HTTP_IF_MATCH', item.etag) == item.etag):

            if item_name in (item.name for item in collection.items):
                # Replace item
                collection.replace(item_name, ical)
            else:
                collection.append(item_name, ical)

            headers['ETag'] = collection.get_item(item_name).etag
            status = 201
        else:
            status = 412

        return status, headers, []
