# -*- coding: utf-8 -*-

from cal9 import config
from cal9 import ical
from cal9.util import DEBUG

from contextlib import contextmanager

import simplejson as json
import icalendar
import time
import os

FOLDER = config.config.calendars.folder

class Calendar(ical.Calendar):
    @property
    def _path(self):
        """ Path on the computer """

        # Remove first / and last /
        path = self.path.strip('/')

        return os.path.join(FOLDER, path.replace('/', os.sep))

    @property
    def _props_path(self):
        """ Properties path on the computer """
        return '{0}.props'.format(self._path)

    def _makedirs(self):
        if not os.path.exists(os.path.dirname(self._path)):
            os.makedirs(os.path.dirname(self._path))

    @property
    def last_modified(self):
        # Create calendar if needed
        if not os.path.exists(self._path):
            self.save()

        modification_time = time.gmtime(os.path.getmtime(self._path))
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", modification_time)

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

    def get(self):
        ical = None

        # If path exists
        if os.path.exists(self._path):
            # Parse iCalendar object
            with open(self._path) as f:
                ical = icalendar.Calendar.from_ical(f.read())

        if not ical:
            ical = icalendar.Calendar()

        return ical


    def save(self):
        self._makedirs()

        content = self.text

        with open(self._path, 'w') as f:
            f.write(content)

        self.ical = self.get()

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
