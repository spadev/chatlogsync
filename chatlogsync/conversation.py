from __future__ import unicode_literals
from __future__ import absolute_import

import time as time_module

from bs4.element import NavigableString

from chatlogsync.timezones import getoffset
from chatlogsync import util

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
            strings = []
            for x in self.html:
                if isinstance(x, NavigableString):
                    strings.append(x.string)
                else:
                    # links should always contain the url
                    if x.name == 'a':
                        if x.text != x['href']:
                            s = '<%s %s>' % (x.text, x['href'])
                        else:
                            s = '<%s>' % (x['href'])
                    else:
                        s = x.text
                    strings.append(s)

            self._text = ''.join(strings)

        return self._text

    @text.setter
    def text(self, text):
        self._text = text

    def __str__(self):
        t = self.time.strftime('%X') if self.time else ''
        s = '%s (%s) [%s]: %s' % (self.sender, self.alias, t, self.text)

        return s

class Message(Entry):
    def __init__(self, **kwargs):
        super(Message, self).__init__(**kwargs)

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

    def __init__(self,  **kwargs):
        assert('type' in kwargs)
        super(Status, self).__init__(**kwargs)

class Event(Entry):
    WINDOWCLOSED = 1
    WINDOWOPENED = 2

    def __init__(self, **kwargs):
        assert('type' in kwargs)
        super(Event, self).__init__(**kwargs)
