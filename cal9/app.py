# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
from urllib import unquote
import icalendar
import posixpath
import os

from util import DEBUG
import util
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
            raise NotImplementedError, '{0} {1}'.format(request.upper(), path)

        collections = ical.Collection.from_path(path, depth=environ.get('HTTP_DEPTH', '0'))

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

                <C:calendar-multiget / calendar-query>
                    <D:href>...</D:href>
                    <D:prop>
                        ...
                    </D:prop>
                </C:calendar-multiget / calendar-query>

            It should returns the following content :

                <D:multistatus>
                    <D:response>
                        <D:href>
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
            'Content-Type': 'text/xml',
        }

        collection = collections[0]

        # Parse request body
        dom = ET.fromstring(request_body)

        dprop = dom.find(xmlutils.tag('D', 'prop'))
        properties = [prop.tag for prop in dprop]

        if collection:
            if dom.tag == xmlutils.tag('C', 'calendar-multiget'):
                hrefs = set(href.text for href in dom.findall(xmlutils.tag('D', 'href')))

            else:
                hrefs = (path,)
        else:
            hrefs = ()

        # Write response body
        multistatus = ET.Element(xmlutils.tag('D', 'multistatus'))

        for href in hrefs:
            name = self.wsgi_name_from_path(href, collection)

            if name:
                # The reference is an item

                path = '/'.join(href.split('/')[:-1]) + '/'
                items = (item for item in collection.items if item.name == name)

            else:
                # The reference is a collection
                path = href
                items = collection.components

            # Create a response element for all items
            for item in items:
                response = ET.Element(xmlutils.tag('D', 'response'))
                multistatus.append(response)

                xmlhref = ET.Element(xmlutils.tag('D', 'href'))
                xmlhref.text = '/'.join([path.rstrip('/'), item.name]) + '.ics'
                response.append(xmlhref)

                propstat = ET.Element(xmlutils.tag('D', 'propstat'))
                response.append(propstat)

                prop = ET.Element(xmlutils.tag('D', 'prop'))
                propstat.append(prop)

                for tag in properties:
                    element = ET.Element(tag)

                    if tag == xmlutils.tag('D', 'getetag'):
                        element.text = item.etag

                    elif tag == xmlutils.tag('C', 'calendar-data'):
                        if isinstance(item, ical.Component):
                            element.text = item.to_ical()

                    prop.append(element)

                status = ET.Element(xmlutils.tag('D', 'status'))
                status.text = util.http_response(200)
                propstat.append(status)

        return 207, headers, [xmlutils.render(multistatus)]


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

    def delete(self, path, collections, request_body, environ):
        """
            Manage DELETE request.

            The URL contains the element to delete :

                /path/to/calendar/element-uid.ics : delete an item
                /path/to/calendar/ : delete the whole calendar
        """

        collection = collections[0]

        if collection.path == path.strip('/'):
            # Path match the collection, delete the whole collection
            item = collection

        else:
            # Path match an item, delete the item
            item = collection.get_item(self.wsgi_name_from_path(path, collection))

        if item and environ.get('HTTP_IF_MATCH', item.etag) == item.etag:
            # No ETag precondition, or precondition verified

            if item is collection:
                collection.delete()

            else:
                collection.remove(item.name)

            # Write response body

            multistatus = ET.Element(xmlutils.tag('D', 'multistatus'))
            response = ET.Element(xmlutils.tag('D', 'response'))
            multistatus.append(response)

            href = ET.Element(xmlutils.tag('D', 'href'))
            href.text = path
            response.append(href)

            status = ET.Element(xmlutils.tag('D', 'status'))
            status.text = util.http_response(200)
            response.append(status)

            return 204, {}, [xmlutils.render(multistatus)]

        # No item or ETag precondition not verified
        return 412, {}, []

    def copy(self, path, collections, request_body, environ):
        """
            Manage COPY request.

            Copy an item from one calendar to another.

            The [RFC 2518] allows to copy the item on a distant calendar.
            If the remote server refuse the resource, we should return a 502 Bad Gateway.
            But for security reason, we don't allow this.
        """

        from_collection = collections[0]
        from_name = self.wsgi_name_from_path(path, from_collection)

        if from_name:
            item = from_collection.get_item(from_name)

            if item:
                url_parts = urlparse(environ['HTTP_DESTINATION'])

                # Check if we are on the same host
                if url_parts.netlock == environ['HTTP_HOST']:

                    # Copy the item
                    to_path, to_name = url_parts.path.rstrip('/').rsplit('/', 1)

                    to_collection = ical.Collection.from_path(to_path, depth="0")[0]
                    to_collection.append(to_name, item.ical)

                    return 201, {}, []

                else:
                    # Remote destination server is forbidden
                    return 502, {}, []

            else:
                # The item wasn't found
                return 410, {}, []
        else:
            # Moving entire collection is Forbidden
            return 403, {}, []

    def move(self, path, collections, request_body, environ):
        """
            Manage MOVE request.

            It's like a COPY request, but delete the item after copy.
        """

         # Copy the item
        status, headers, content = self.copy(path, collections, request_body, environ)

        # If the copy was successful
        if status == 201:
            # Delete the source
            collection = collections[0]
            name = self.wsgi_name_from_path(path, collection)
            collection.remove(name)

        return status, headers, content
