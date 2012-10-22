# -*- coding: utf-8 -*-

from requests import requests

class Application(object):
    def __init__(self):
        super(Application, self).__init__()

    def __call__(self, environ, start_response):
        """ WSGI request handler. """

        status, headers, content = self.handle_request(environ)

        headers['Content-Length'] = sum([len(c) for c in content])

        start_response(status, list(headers.items()))

        return content

    def handle_request(self, environ):
        request = environ['REQUEST_METHOD'].upper()

        content = self.get_content(environ)

        if request in requests:
            status, headers, content = requests[request](environ, content)
        else:
            status = 500
            headers = {}
            content = ['Request {0} not implemented\n'.format(request)]

        return status, headers, content

    def get_content(self, environ):
        """ Get WSGI input content. """

        charsets = []

        # Retrieve content
        content_length = int(environ['CONTENT_LENGTH'])
        content = environ['wsgi.input'].read(content_length)

        # Retrieve encoding defined in request
        content_type = environ['CONTENT_TYPE']

        if content_type and 'charset=' in content_type:
            charsets.append(content_type.split('charset=')[1].strip())

        # Append default encoding
        charsets.append('utf-8')
        charsets.append('iso8859-1')

        # Try to decode content
        for charset in charsets:
            try:
                return content.decode(charset)
            except UnicodeDecodeError:
                pass

        # No charset worked, raise an error
        raise UnicodeDecodeError

