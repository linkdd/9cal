# -*- coding: utf-8 -*-

import httplib

def http_response(code):
    return 'HTTP/1.1 {0} {1}'.format(code, httplib.responses[code])

