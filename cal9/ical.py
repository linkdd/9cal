# -*- coding: utf-8 -*-

from contextlib import contextmanager
import icalendar

PRODID = "-//9cal//9h37 CalDAV server//"
VERSION = "2.0"

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
                    self._name = str(c.get('UID'))
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

    def to_ical(self):
        return self.ical.to_ical()

class Component(Item):
    pass

class Event(Component):
    tag = 'VEVENT'
    mimetype = 'text/calendar'

class Todo(Component):
    tag = 'VTODO'
    mimetype = 'text/calendar'

class Journal(Component):
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
        ical.set('prodid', PRODID)
        ical.set('version', VERSION)

        for item in self:
            for component in item.ical.subcomponents:
                ical.add_component(component)

        return ical.to_ical()

class Calendar(object):
    """ Abstract class which define access API to calendars """

    def __init__(self, path):
        self.path = path
        self._ical = None

    ## Calendar properties

    @property
    def ical(self):
        """ Wrapper to internal iCalendar object """

        if self._ical is None:
            self._ical = self.get()

        return self._ical

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
        """ Return calendar's name """

        with self.props as props:
            return props.get('D:displayname', self.path.split('/')[-1])

    @property
    def text(self):
        """ The collection as plain text """
        self.ical.set('prodid', PRODID)
        self.ical.set('version', VERSION)
        return self.ical.to_ical()

    @property
    def last_modified(self):
        """ Last modification on calendar """
        raise NotImplementedError

    @property
    @contextmanager
    def props(self):
        """ Return collection properties """
        raise NotImplementedError

    ## Calendar method

    def get(self):
        """ Get calendar from the storage backend """
        raise NotImplementedError

    def save(self):
        """ Save changes to the collection and update the internal calendar """

        self.write()
        self._ical = self.get()


    def write(self):
        """ Write changes to the collection """
        raise NotImplementedError

    def delete(self):
        """ Remove collection """

        raise NotImplementedError

    def append(self, name, ical):
        """ Append item to the collection """

        for component in ical.subcomponents:
            self.ical.add_component(component)

        self.save()

    def remove(self, name):
        """ Remove item from collection """

        for component in self.ical.walk():
            item = Item(component.to_ical())

            if item.name == name:
                del component

        self.save()

    def replace(self, name, ical):
        """ Replace item in collection """

        self.remove(name)
        self.append(name, ical)

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
        if not (cls.is_item(path) or path.endswith('/')):
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

                component_found = False

                # Get the correct item type, by checking the tag defined for each
                # subclass of Item.
                for t in Item.__subclasses__():

                    # If the subclass is Component, check for its subclasses
                    if t is Component:

                        for ct in Component.__subclasses__():

                            # If the component's type match
                            if component.name == ct.tag:
                                # Append object to the list
                                items.append(ct(ical.to_ical()))

                                component_found = True
                                break

                    # If the component was found in subclass of Component
                    if component_found:
                        # the item was added
                        break

                    # If the component's type match
                    if component.name == t.tag:
                        # Append object to the list
                        items.append(t(ical.to_ical()))
                        break

                else:
                    # We didn't find the component's type
                    # Fallback on Item
                    items.append(Item(ical.to_ical()))

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

    def get_item(self, name):
        """ Get item named ``name`` """

        for item in self.items:
            if item.name == name:
                return item
