# -*- coding: utf-8 -*-

from cal9 import config
from cal9 import ical

from contextlib import contextmanager

import icalendar
import os

FOLDER = config.config.calendars.folder

class Calendar(ical.Calendar):
    @property
    def _path(self):
        """ Path on the computer """
        return os.path.join(FOLDER, self.path.replace('/', os.sep))

    def _makedirs(self):
        if not os.path.exists(os.path.dirname(self._path)):
            os.makedirs(os.path.dirname(self._path))

    @property
    def ical(self):
        ical = icalendar.Calendar()
        return ical

    def save(self, ical):
        self._makedirs()
        f = open(self._path, 'w')
        f.write(ical.to_ical())
        f.close()

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
