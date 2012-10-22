# -*- coding: utf-8 -*-

class Ressource(object):
    """ Define a WebDAV ressource. """

    def __init__(self, **kwargs):
        self.props = {}

        self.props.update(kwargs)

    def save(self):
        import sys
        print >>sys.stderr, self.props
