# -*- coding: utf-8 -*-

from app import Application
import os

confpath = os.environ['CAL9_CONFIG']

application = Application(confpath)
