from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import time as time_module

from chatlogconv.timezones import getoffset
from chatlogconv import util

class Conversation(object):
    def __init__(self, parsedby, path, source, destination,
                 service, time, images=[]):
        self.source = source
        self.destination = destination
        self.service = service
        self.time = time
        self.path = path
        self.parsedby = parsedby
        self.images = images # always relative paths
        self.entries = []

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        if not time.tzinfo:
            abbrev = time_module.tzname[time_module.daylight]
            if time_module.daylight:
                offset = -time_module.altzone
            else:
                offset = -time_module.timezone
            time = time.replace(tzinfo=getoffset(abbrev, offset))
        elif not time.tzname():
            offset = time.strftime('%z')
            time = time.replace(tzinfo=getoffset(None, offset))

        self._time = time

    def __str__(self):
        s = 'source: %s, destination: %s, service: %s, time: %s' % \
            (self.source, self.destination, self.service, self.time)
        if self.images:
            s += ' images: %s' % ', '.join(self.images)
        e = ['  '+str(x) for x in self.entries]
        if e:
            s += '\n'+'\n'.join(e)

        return s

    def __hash__(self):
        h = hash(self.source)
        for k in ('destination', 'service', 'time'):
            h = h^hash(getattr(self, k))
        for k in ('images', 'entries'):
            h = h^hash(tuple(getattr(self, k)))

        return h

    def __eq__(self, other):
        for k in ('source', 'destination', 'service', 'time',
                  'images', 'entries'):
            if getattr(self, k) != getattr(other, k):
                return False
        return True

class Entry(object):
    def __init__(self, **kwargs):
        self.alias = ''
        self.sender = ''
        self.text = ''
        self.time = None
        self.type = None
        self.html = []

        for k, v in iter(kwargs.items()):
            setattr(self, k, v)

    @property
    def text(self):
        if not self._text and self.html:
            self._text = ''.join([x.text for x in self.html])

        return self._text

    @text.setter
    def text(self, text):
        self._text = text

    def __str__(self):
        s = '%s (%s) [%s]: %s' % (self.sender, self.alias,
                                  self.time.strftime('%X'), self.text)

        return s

class Message(Entry):
    def __init__(self, alias, sender, time, text='', html=[]):
        super(Message, self).__init__(alias=alias, sender=sender, time=time,
                                      text=text, html=html)

class Status(Entry):
    OFFLINE = 1
    ONLINE = 2
    DISCONNECTED = 3
    CONNECTED = 4
    AVAILABLE = 5
    AWAY = 6
    IDLE = 7
    CHATERROR = 10
    PURPLE = 11

    def __init__(self, alias, sender, time, type, text='', html=[]):
        super(Status, self).__init__(alias=alias, sender=sender, type=type,
                                     time=time, text=text, html=html)

class Event(Entry):
    WINDOWCLOSED = 1
    WINDOWOPENED = 2

    def __init__(self, alias, sender, time, type, text='', html=[]):
        super(Event, self).__init__(alias=alias, sender=sender, type=type,
                                    time=time, text=text, html=html)
