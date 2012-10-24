# -*- coding: utf-8 -*-

import httplib

def http_response(code):
    return 'HTTP/1.1 {0} {1}'.format(code, httplib.responses[code])

def DEBUG(msg):
    import config
    import sys

    if config.config.debug:
        print >>sys.stderr, "DEBUG:", msg


class Dict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]

    def __setattr__(self, key, val):
        self[key] = val

    def update(self, *args, **kwargs):
        for k,v in dict(*args, **kwargs).iteritems():
            if isinstance(v, dict):
                self[k] = Dict()
                self[k].update(v)
            else:
                self[k] = v

