# Copyright 2013 Evan Vitero

# This file is part of chatlogsync.

# chatlogsync is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# chatlogsync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with chatlogsync.  If not, see <http://www.gnu.org/licenses/>.

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
from dateutil.tz import tzoffset
from os.path import join, dirname, isfile, realpath

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement

from chatlogsync import util
from chatlogsync.timezones import getoffset
from chatlogsync.errors import ArgumentError
from chatlogsync.formats._base import ChatlogFormat

def _validate_argument(arg, argname, cls):
    msg = "expected a '%s' for argument '%s' - '%s' is a '%s'"
    if not isinstance(arg, cls):
        raise TypeError(msg % (cls.__name__, argname,
                               arg, type(arg).__name__))

def _get_text(html):
    strings = []
    for x in html:
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
    return ''.join(strings)

class Conversation(object):
    """Object representing a conversation from a chatlog"""
    def __init__(self, parsedby, path, source, destination, service, time,
                 entries, images, resource='', isgroup=False, transforms={}):
        self._source = source
        self._resource = resource
        self._destination = destination
        self._service = service
        self._path = path
        self._parsedby = parsedby
        self._original_parser_name = None
        self._isgroup = True if isgroup else False

        for argname in ('source', 'destination', 'service', 'path'):
            _validate_argument(getattr(self, '_'+argname), argname, basestring)
        if not isfile(self._path):
            raise ArgumentError("path '%s' does not exist" % path)
        _validate_argument(parsedby, 'parsedby', ChatlogFormat)
        self.__validate_time(time)
        self.__validate_images(images)
        self.entries = entries

        for attr, function in iter(transforms.items()):
            cur_value = getattr(self, '_'+attr)
            new_value = function(cur_value, self)
            setattr(self, '_'+attr, new_value)

    @property
    def original_parser_name(self):
        return self._original_parser_name
    @original_parser_name.setter
    def original_parser_name(self, name):
        self._original_parser_name = name

    @property
    def resource(self):
        return self._resource
    @resource.setter
    def resource(self, resource):
        self._resource = resource

    @property
    def isgroup(self):
        return self._isgroup
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
    @images.setter
    def images(self, images):
        self.__validate_images(images)
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

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

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
        for k in ('destination', 'service', 'time', 'isgroup'):
            h = h^hash(getattr(self, k))
        for k in ('images', 'entries'):
            h = h^hash(tuple(getattr(self, k)))

        return h

    def __eq__(self, other):
        for k in ('source', 'destination', 'service', 'time', 'isgroup',
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
        self._delayed = False
        self._alternate = False
        self._html = []
        self._isuser = False

        for k, v in iter(kwargs.items()):
            setattr(self, '_'+k, v)

        self._system = True if kwargs.get('system', None) else False
        if self._text and not self._html:
            self._html = [NavigableString(self._text)]

        for argname in ('alias', 'sender', 'text'):
            _validate_argument(getattr(self, '_'+argname), argname, basestring)

        if self._system:
            self._alias = ''
            self._sender = ''
        elif not self._alias and not self._sender:
            raise ArgumentError('non-system Entry must have sender or alias')
        elif self._alias == self._sender:
            self._alias = ''
        _validate_argument(self._time, 'time', datetime.datetime)
        _validate_argument(self._html, 'html', list)
        for e in self._html:
            _validate_argument(e, 'html', PageElement)

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        equal = True
        for k, v in iter(vars(other.__class__).items()):
            if isinstance(v, property) and \
                    getattr(self, k) != getattr(other, k):
                equal = False
                break

        return equal

    def __ne__(self, other):
        return not self == other

    def dump(self):
        d = {}
        for k, v in iter(vars(self).items()):
            if k.startswith("_"):
                k = k[1:]
            if 'html' in k:
                v = [str(v) for v in v]
            d[k] = v
        return "%s %r" % (self.__class__.__name__, d)

    @classmethod
    def from_dump(cls, dump):
        """Return (constructor, kwargs)"""
        name, kwargs_str = dump.split(' ', 1)
        kwargs = eval(kwargs_str)
        for k, v in iter(kwargs.items()):
            if 'html' in k and v:
                html = []
                for h in v:
                    html.extend(list(BeautifulSoup(h).body.children))
                kwargs[k] = html

        return globals()[name], kwargs

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
    def delayed(self):
        return self._delayed
    @property
    def alternate(self):
        return self._alternate
    @property
    def isuser(self):
        return self._isuser

    @property
    def text(self):
        if not self._text and self.html:
            self._text = _get_text(self.html)
        return self._text

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)

    def __str__(self):
        t = self.time.strftime('%X') if self.time else ''
        if self.alias:
            sa = '%s (%s)' % (self.alias, self.sender)
        else:
            sa = str(self.sender)
        s = '%s [%s]: %s' % (sa, t, self.text)

        return s

class Message(Entry):
    """Immutable object representing a message in a Conversation"""
    def __init__(self, **kwargs):
        self._auto = kwargs.get('auto', False)
        super(Message, self).__init__(**kwargs)

    @property
    def auto(self):
        return self._auto

    def __str__(self):
        s = super(Message, self).__str__()
        if self.auto:
            s = '*auto-reply* '+s

        return s

class Status(Entry):
    """Immutable object representing a status in a Conversation"""
    OFFLINE = 1
    ONLINE = 2
    AVAILABLE = 3
    AWAY = 4
    IDLE = 5
    DISCONNECTED = 6
    CONNECTED = 7
    ERROR = 8
    SYSTEM = 9
    MOBILE = 10

    SYSTEM_STATUSES = (SYSTEM,)
    OPPOSITES = { OFFLINE: ONLINE,
                  ONLINE: (OFFLINE, IDLE, MOBILE),
                  AVAILABLE: AWAY,
                  AWAY: AVAILABLE,
                  IDLE: ONLINE,
                  DISCONNECTED: CONNECTED,
                  CONNECTED: DISCONNECTED,
                  MOBILE: ONLINE }

    _MIN = 1
    _MAX = 10

    TYPE_MAP = {
        OFFLINE: _("Offline"),
        ONLINE: _("Online"),
        AVAILABLE: _("Available"),
        AWAY: _("Away"),
        IDLE: _("Idle"),
        DISCONNECTED: _("Disconnected"),
        CONNECTED: _("Connected"),
        ERROR: _("Error"),
        SYSTEM: _("System Message"),
        MOBILE: _("Mobile"),
        }

    PAM_EPYT = dict({v: k for k, v in iter(TYPE_MAP.items())},
                    **{v.lower(): k for k, v in iter(TYPE_MAP.items())})

    USER_TYPES = (OFFLINE, ONLINE, AVAILABLE, AWAY, IDLE, MOBILE)
    CHANGED_STATUS_TO = _("changed status to")
    STATUS_STRING_FMT = "%s "+CHANGED_STATUS_TO+" %s%s"

    def __init__(self,  **kwargs):
        self._msg_text = ''
        self._msg_html = []
        atype = kwargs.get('type', None)
        if atype < self._MIN or atype > self._MAX:
            raise TypeError("unknown type %r for status" % atype)
        self._type = atype
        if self._msg_text and not self._msg_html:
            self._msg_html = [NavigableString(self._msg_text)]

        if self._type in self.SYSTEM_STATUSES:
            kwargs['system'] = True

        super(Status, self).__init__(**kwargs)
        self._has_other_html = True if self._html else False

    @property
    def typestr(self):
        return self.TYPE_MAP[self.type]

    @property
    def msg_text(self):
        if not self._msg_text and self.msg_html:
            self._msg_text = _get_text(self.msg_html)
        return self._msg_text

    @property
    def msg_html(self):
        return self._msg_html

    @property
    def has_other_html(self):
        return self._has_other_html

    @property
    def html(self):
        if not self._html:
            self._html = []
            if self.type in self.USER_TYPES:
                s = self.STATUS_STRING_FMT % \
                    (self.alias if self.alias else self.sender, self.typestr,
                     ': ' if self.msg_html else '')
                self._html.append(NavigableString(s))
                self._html.extend(self.msg_html)
            else:
                self._html.append(self.typestr)
        return self._html

    @property
    def type(self):
        return self._type

    def __str__(self):
        s = super(Status, self).__str__()
        return '*%s* %s' % (self.typestr, s)

class Event(Entry):
    """Immutable object representing an event in a Conversation"""
    WINDOWCLOSED = 1
    WINDOWOPENED = 2

    _MIN = 1
    _MAX = 2

    TYPE_MAP = {
        WINDOWCLOSED: _("Window Closed"),
        WINDOWOPENED: _("Window Opened"),
        }

    def __init__(self, **kwargs):
        atype = kwargs.get('type', None)
        if atype < self._MIN or atype > self._MAX:
            raise TypeError("unknown type '%s' for event" % atype)
        self._type = atype

        super(Event, self).__init__(**kwargs)

    @property
    def type(self):
        return self._type

    @property
    def typestr(self):
        return self.TYPE_MAP[self.type]

    def __str__(self):
        s = super(Event, self).__str__()
        return '*%s* %s' % (self.typestr, s)
