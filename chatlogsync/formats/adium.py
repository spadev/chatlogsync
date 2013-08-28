from __future__ import unicode_literals
from __future__ import absolute_import

import os
import codecs
import shutil
from os.path import join, dirname, relpath, realpath

from dateutil.parser import parse
from bs4 import BeautifulSoup
from bs4.element import Tag

from chatlogsync.formats._base import ChatlogFormat
from chatlogsync import util
from chatlogsync.errors import ParseError
from chatlogsync.conversation import Conversation, Message, Status, Event
from chatlogsync.timezones import getoffset

class Adium(ChatlogFormat):
    type = 'adium'
    SERVICE_MAP = {'GTalk' : 'gtalk',
                   'AIM' : 'aim'
                   }

    STATUS_TYPEMAP = {'offline': Status.OFFLINE,
                      'online': Status.ONLINE,
                      'disconnected': Status.DISCONNECTED,
                      'connected': Status.CONNECTED,
                      'away': Status.AWAY,
                      'idle': Status.IDLE,
                      'purple': Status.PURPLE,
                      'available': Status.AVAILABLE,
                      'chat-error': Status.CHATERROR,
                      }

    EVENT_TYPEMAP = {'windowClosed': Event.WINDOWCLOSED,
                     'windowOpened': Event.WINDOWOPENED,
                     }

    FILE_PATTERN = ('Logs/<service>.<source>/'
                    '<destination>/'
                    '<destination> (<time>).chatlog/'
                    '<destination> (<time>).xml')
    IMAGE_DIRECTORY = '.'
    TIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S%z'
    TIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S%z'
    XMLNS = "http://purl.org/net/ulf/ns/0.4-02"

    def parse(self, path, messages=True):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        time = parse(info['time'].replace('.', ':'), tzinfos=getoffset)
        source = info['source']
        destination = info['destination']
        service = self.SERVICE_MAP[info['service']]

        dp = dirname(path)
        images = [relpath(join(dp, x), start=dp) for x in os.listdir(dp)
                  if not x.endswith('.xml')]

        conversation = Conversation(self, path, source, destination,
                                    service, time, images)
        if not messages:
            return [conversation]

        # parse xml
        with open(path) as f:
            soup = BeautifulSoup(f, ['lxml', 'xml'])
        chat = soup.find('chat')
        for e in chat.children:
            if not isinstance(e, Tag):
                continue

            alias = e.get('alias')
            sender = e.get('sender')
            timestr = e.get('time')
            if timestr:
                time = parse(timestr, default=conversation.time,
                             ignoretz=True)
            else:
                time = None
            html =  list(e.children)
            type_attr = e.get('type')

            if e.name == 'status':
                type = self.STATUS_TYPEMAP.get(type_attr, None)
                if not type:
                    raise ParseError("unknown type '%s' for status" % type_attr)
                entry = Status(alias, sender, time, type, html=html)
            elif e.name == 'event':
                type = self.EVENT_TYPEMAP.get(type_attr, None)
                if not type:
                    raise ParseError("unknown type '%s' for event" % type_attr)
                entry = Event(alias, sender, time, type, html=html)
            elif e.name == 'message':
                entry = Message(alias, sender, time, html=html)
            else:
                raise ParseError("unknown type '%s' for entry" % e.name)
            conversation.entries.append(entry)

        csource = chat.get('account')
        cservice = self.SERVICE_MAP[chat.get('service')]
        if source != csource or service != cservice:
            raise ParseError('mismatch between path and chatinfo for %s' % path)

        return [conversation]

    def write(self, path, conversations):
        if len(conversations) != 1:
            msg = '%s only supports one conversation per file:\n  %s has %i' % \
                  (self.type, path, len(conversations))
            raise ParseError(msg)

        conversation = conversations[0]
        soup = BeautifulSoup(features='xml')
        chat = soup.new_tag(name='chat')
        soup.append(chat)

        chat['xmlns'] = self.XMLNS
        chat['account'] = conversation.source
        chat['service'] = self.PAM_ECIVRES[conversation.service]
        chat.append('\n')

        for i, entry in enumerate(conversation.entries):
            if isinstance(entry, Message):
                name = 'message'
            elif isinstance(entry, Status):
                name = 'status'
            elif isinstance(entry, Event):
                name = 'event'
            elem = soup.new_tag(name=name)

            for k in ('alias', 'sender'):
                v = getattr(entry, k)
                if v:
                    elem[k] = v

            if entry.type:
                if isinstance(entry, Status):
                    t = self.PAMEPYT_SUTATS[entry.type]
                elif isinstance(entry, Event):
                    t = self.PAMEPYT_TNEVE[entry.type]
                elem['type'] = t

            if entry.time:
                f1 = self.TIME_FMT_CONVERSATION[:-2]
                f2 = self.TIME_FMT_CONVERSATION[-2:]
                v1 = entry.time.strftime(f1)
                v2 = entry.time.strftime(f2)
                v = v1+v2[:3]+':'+v2[3:]
                elem['time'] = v

            for html in entry.html:
                elem.append(html)

            if not entry.html:
                elem.append(entry.text)

            chat.append(elem)
            if i != len(conversation.entries)-1:
                chat.append('\n')

        # images
        for img_relpath in conversation.images:
            srcdir = dirname(conversation.path)
            dstdir = dirname(path)
            srcimg = join(srcdir, img_relpath)
            dstimg = join(dstdir, img_relpath)
            if realpath(srcimg) != realpath(dstimg):
                shutil.copy(srcimg, dstimg)

        # newline at end
        soup.append('\n')
        with codecs.open(path, 'wb', 'utf-8') as fh:
            fh.write(soup.decode())

formats = [Adium]
