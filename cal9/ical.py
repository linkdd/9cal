# -*- coding: utf-8 -*-

from contextlib import contextmanager
import icalendar

class Item(object):
    """ Abstract class which define an iCal object """

    tag = None
    mimetype = None

    def __init__(self, text, name=None):
        self.ical = icalendar.Calendar.from_ical(text)
        self._name = name

        if not self._name:
            # Try to find the element's name

            for c in self.ical.walk():
                if c.get('X-CAL9-NAME'):
                    self._name = str(c.get('X-CAL9-NAME'))
                    break

                elif c.get('TZID'):
                    self._name = str(c.get('TZID'))
                    break

                elif c.get('UID'):
                    self.name = str(c.get('UID'))
                    # Do not break, X-CAL9-NAME can still appear

        if not self._name:
            # The name is still not found, define one
            import uuid

            self._name = str(uuid.uuid4())

        # Now redefine the X-CAL9-NAME property

        for c in self.ical.walk():
            if c.get('X-CAL9-NAME'):
                c['X-CAL9-NAME'] = icalendar.vText(self._name)
                break
        else:
            self.ical['X-CAL9-NAME'] = icalendar.vText(self._name)

    @property
    def etag(self):
        return '"{0}"'.format(hash(self.ical.to_ical()))

    @property
    def name(self):
        return self._name

class Event(Item):
    tag = 'VEVENT'
    mimetype = 'text/calendar'

class Todo(Item):
    tag = 'VTODO'
    mimetype = 'text/calendar'

class Journal(Item):
    tag = 'VJOURNAL'
    mimetype = 'text/calendar'

class Timezone(Item):
    tag = 'VTIMEZONE'


class ItemList(list):
    """ Define a list of Item """

    def to_ical(self):
        """
            Put all components from each items in the list into an
            iCalendar object and return it as a string.
        """

        ical = icalendar.Calendar()

        for item in self:
            for component in item.ical.subcomponents:
                ical.add_component(component)

        return ical.to_ical()

class Calendar(object):
    """ Abstract class which define access API to calendars """

    def __init__(self, path):
        self.path = path

    ## Calendar properties

    @property
    def ical(self):
        """ MUST return a iCalendar object """
        raise NotImplementedError

    @property
    def mimetype(self):
        return "text/calendar"

    @property
    def resource_type(self):
        return "calendar"

    @property
    def etag(self):
        return '"{0}"'.format(hash(self.ical.to_ical()))

    @property
    def name(self):
        raise NotImplementedError

    @property
    def text(self):
        """ The collection as plain text """
        raise NotImplementedError

    @property
    @contextmanager
    def props(self):
        """ Return collection properties """
        raise NotImplementedError

    ## Calendar method

    def save(self):
        """ Save changes to the collection """
        raise NotImplementedError

    def delete(self):
        """ Remove collection """

        raise NotImplementedError

    @classmethod
    def is_calendar(cls, path):
        """ Check if ``path`` designate a calendar """

        raise NotImplementedError

    @classmethod
    def is_item(cls, path):
        """ Check if ``path`` designate an item """

        raise NotImplementedError

    @classmethod
    def from_path(cls, path):
        """ Return a calendar and its components associated to ``path`` """

        parts = path.split("/")

        # If ``path`` is an item
        if cls.is_item(path):
            # Get the path associated to the calendar
            parts.pop()

        path = "/".join(parts)

        # Create the object
        result = []

        cal = cls(path)
        result.append(cal)
        result.extend(cal.components)

        return result

    ## Filtering components

    def filter(self, item_type):
        """ Filter items, ``item_type`` is a class derivated from Item """
        items = ItemList()

        for component in self.ical.walk():
            # If tag is not None, filter
            if item_type.tag:
                # Check component's type
                if component.name == item_type.tag:
                    # Encapsulate the component in a calendar
                    ical = icalendar.Calendar()
                    ical.add_component(component)

                    # Generate an object from it, and append it to the list
                    items.append(item_type(ical.to_ical()))
            else:
                # Encapsulate the component in a calendar
                ical = icalendar.Calendar()
                ical.add_component(component)

                # Generate an object from it, and append it to the list
                items.append(item_type(ical.to_ical()))

        return items

    @property
    def items(self):
        """ Return the list of all items """

        return self.filter(Item)

    @property
    def events(self):
        """ Return a list of Event """

        return self.filter(Event)

    @property
    def todos(self):
        """ Return a list of Todo """

        return self.filter(Todo)

    @property
    def journals(self):
        """ Return a list of Journal """

        return self.filter(Journal)

    @property
    def components(self):
        """ Return a list of components """

        return self.events + self.todos + self.journals

    @property
    def timezones(self):
        """ Return a list of Timezone """

        return self.filter(Timezone)
