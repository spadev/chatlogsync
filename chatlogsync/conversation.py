from __future__ import unicode_literals
from __future__ import absolute_import

try:
    unicode = unicode
except NameError:
    # 'unicode' is undefined, must be Python 3
    str = str
    unicode = str
    bytes = bytes
    basestring = (str,bytes)
else:
    # 'unicode' exists, must be Python 2
    str = str
    unicode = unicode
    bytes = str
    basestring = basestring

import time
import datetime
from os.path import join, dirname, isfile, realpath

from bs4.element import NavigableString, PageElement

from chatlogsync import util
from chatlogsync.timezones import getoffset
from chatlogsync.errors import ArgumentError
from chatlogsync.formats._base import ChatlogFormat

def _validate_argument(arg, argname, cls):
    msg = "Incorrect argument type for %s:\n  %s is a %s, but expected a %s"
    if not isinstance(arg, cls):
        raise ArgumentError(msg % (argname, arg, type(arg), cls))

class Conversation(object):
    """Object representing a converation from a chatlog"""
    def __init__(self, parsedby, path, source, destination,
                 service, time, entries=[], images=[]):
        self._source = source
        self._destination = destination
        self._service = service
        self._path = path
        self._parsedby = parsedby

        for argname in ('source', 'destination', 'service', 'path'):
            _validate_argument(getattr(self, '_'+argname), argname, basestring)
        if not isfile(self._path):
            raise ArgumentError('Path %s does not exist' % path)
        _validate_argument(parsedby, 'parsedby', ChatlogFormat)
        self.__validate_time(time)
        self.__validate_images(images)
        self.entries = entries

    @property
    def source(self):
        return self._source
    @property
    def destination(self):
        return self._destination
    @property
    def service(self):
        return self._service
    @property
    def time(self):
        return self._time
    @property
    def path(self):
        return self._path
    @property
    def parsedby(self):
        return self._parsedby
    @property
    def images(self):
        """List of relative paths of images in in conversation"""
        return self._images
    @property
    def images_full(self):
        """List of (relative path, full path) of images in in conversation"""
        return self._images_full
    @property
    def entries(self):
        return self._entries
    @entries.setter
    def entries(self, entries):
        _validate_argument(entries, 'entries', list)
        for e in entries:
            _validate_argument(e, 'entries', Entry)
        self._entries = entries

    def __validate_images(self, images):
        self._images_full = []
        self._images = []
        _validate_argument(images, 'images', list)

        dirpath = dirname(self._path)
        for img_relpath in images:
            _validate_argument(img_relpath, 'images', basestring)
            img_fullpath = realpath(join(dirpath, img_relpath))
            if not isfile(img_fullpath):
                print_e('Skipping nonexistent image at %s' % img_fullpath)
            else:
                self._images.append(img_relpath)
                self._images_full.append((img_relpath, img_fullpath))

    def __validate_time(self, t):
        _validate_argument(t, 'time', datetime.datetime)
        if not t.tzinfo:
            abbrev = time.tzname[time.daylight]
            if time.daylight:
                offset = -time.altzone
            else:
                offset = -time.timezone
            t = t.replace(tzinfo=getoffset(abbrev, offset))
        elif not t.tzname():
            offset = t.strft('%z')
            t = t.replace(tzinfo=getoffset(None, offset))

        self._time = t

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
    """Immutable object representing an entry in a Conversation"""
    def __init__(self, **kwargs):
        self._alias = ''
        self._sender = ''
        self._text = ''
        self._time = ''
        self._html = []

        for k, v in iter(kwargs.items()):
            setattr(self, '_'+k, v)

        self._system = True if kwargs.get('system', None) else False

        for argname in ('alias', 'sender', 'text'):
            _validate_argument(getattr(self, '_'+argname), argname, basestring)

        if not self._alias and not self._sender and not self._system:
            raise ArgumentError('Non-system Entry must have sender or alias')
        elif self._alias == self._sender:
            self._alias = ''
        _validate_argument(self._time, 'time', datetime.datetime)
        _validate_argument(self._html, 'html', list)
        for e in self._html:
            _validate_argument(e, 'html', PageElement)

    @property
    def alias(self):
        return self._alias
    @property
    def sender(self):
        return self._sender
    @property
    def time(self):
        return self._time
    @property
    def html(self):
        return self._html
    @property
    def system(self):
        return self._system

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

    def __str__(self):
        t = self.time.strftime('%X') if self.time else ''
        s = '%s (%s) [%s]: %s' % (self.sender, self.alias, t, self.text)

        return s

class Message(Entry):
    """Immutable object representing a message in a Conversation"""
    def __init__(self, **kwargs):
        self._auto = kwargs.get('auto', False)
        super(Message, self).__init__(**kwargs)

    @property
    def auto(self):
        return self._auto

class Status(Entry):
    """Immutable object representing a status in a Conversation"""
    OFFLINE = 1
    ONLINE = 2
    DISCONNECTED = 3
    CONNECTED = 4
    AVAILABLE = 5
    AWAY = 6
    IDLE = 7
    CHATERROR = 8
    PURPLE = 9

    _MIN = 1
    _MAX = 9

    def __init__(self,  **kwargs):
        atype = kwargs.get('type', None)
        if atype < self._MIN or atype > self._MAX:
            raise ArgumentError("unknown type '%s' for status" % atype)
        self._type = atype

        super(Status, self).__init__(**kwargs)

    @property
    def type(self):
        return self._type

class Event(Entry):
    """Immutable object representing an event in a Conversation"""
    WINDOWCLOSED = 1
    WINDOWOPENED = 2

    _MIN = 1
    _MAX = 2

    def __init__(self, **kwargs):
        atype = kwargs.get('type', None)
        if atype < self._MIN or atype > self._MAX:
            raise ArgumentError("unknown type '%s' for event" % atype)
        self._type = atype

        super(Event, self).__init__(**kwargs)

    @property
    def type(self):
        return self._type
