# -*- coding: utf-8 -*-

from cal9 import config
from cal9 import ical
from cal9.util import DEBUG

from contextlib import contextmanager

import simplejson as json
import icalendar
import os

FOLDER = config.config.calendars.folder

class Calendar(ical.Calendar):
    @property
    def _path(self):
        """ Path on the computer """

        # Remove first / and last /
        path = self.path[1:-1]

        return os.path.join(FOLDER, path.replace('/', os.sep))

    @property
    def _props_path(self):
        """ Properties path on the computer """
        return '{0}.props'.format(self._path)

    def _makedirs(self):
        if not os.path.exists(os.path.dirname(self._path)):
            os.makedirs(os.path.dirname(self._path))

    @property
    def ical(self):
        ical = icalendar.Calendar()
        return ical

    @property
    @contextmanager
    def props(self):
        properties = {}

        # Read properties

        if os.path.exists(self._props_path):
            with open(self._props_path, 'r') as f:
                properties.update(json.load(f))

        yield properties

        # Save properties

        self._makedirs()
        with open(self._props_path, 'w') as f:
            json.dump(properties, f)

    def save(self, ical):
        self._makedirs()

        with open(self._path, 'w') as f:
            f.write(ical.to_ical())

    def delete(self):
        os.remove(self._path)

    @classmethod
    def is_calendar(cls, path):
        abs_path = os.path.join(FOLDER, path.replace('/', os.sep))
        return os.path.isdir(abs_path)

    @classmethod
    def is_item(cls, path):
        abs_path = os.path.join(FOLDER, path.replace('/', os.sep))
        return os.path.isfile(abs_path)

ical.Calendar = Calendar
