# -*- coding: utf-8 -*-

from util import Dict
import simplejson as json

import sys

class Config(Dict):
    def __init__(self, path):
        with open(path) as f:
            self.update(json.load(f))

config = None

def load(path):
    global config
    config = Config(path)
