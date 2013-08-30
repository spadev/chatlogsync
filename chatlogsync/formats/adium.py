from __future__ import unicode_literals
from __future__ import absolute_import

import os
import codecs
import shutil
import datetime
from os.path import join, dirname, relpath, realpath

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
                   'AIM' : 'aim',
                   'Facebook' : 'facebook',
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
    STRPTIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S'
    TIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S%z'
    STRPTIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S'
    XMLNS = "http://purl.org/net/ulf/ns/0.4-02"

    def _parse_ftime(self, timestr):
        ts1, ts2 = timestr[:-5], timestr[-5:]
        t = datetime.datetime.strptime(ts1, self.STRPTIME_FMT_FILE)
        return t.replace(tzinfo=getoffset(None, ts2))

    def _parse_ctime(self, timestr):
        ts1, ts2 = timestr[:-6], timestr[-6:].replace(':', '')
        t = datetime.datetime.strptime(ts1, self.STRPTIME_FMT_CONVERSATION)
        return t.replace(tzinfo = getoffset(None, ts2))

    def parse_path(self, path):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        # time = parse(info['time'].replace('.', ':'), tzinfos=getoffset)
        time = self._parse_ftime(info['time'])
        source = info['source']
        destination = info['destination']
        service = self.SERVICE_MAP[info['service']]

        dp = dirname(path)
        images = [relpath(join(dp, x), start=dp) for x in os.listdir(dp)
                  if not x.endswith('.xml')]

        conversation = Conversation(self, path, source, destination,
                                    service, time, entries=[], images=images)

        return [conversation]

    def parse_conversation(self, conversation):
        # parse xml
        with codecs.open(conversation.path, encoding='utf-8') as f:
            soup = BeautifulSoup(f, ['lxml', 'xml'])
        chat = soup.find('chat')

        for e in chat.children:
            if not isinstance(e, Tag):
                continue

            attrs = {}
            for a in ('alias', 'sender', 'auto', 'time'):
                attrs[a] = e.get(a, '')
            attrs['auto'] = True if attrs['auto'] else False
            if attrs['time']:
                attrs['time'] = self._parse_ctime(attrs['time'])
                # attrs['time'] = parse(attrs[2'time'], default=conversation.time,
                #                       ignoretz=True)
            attrs['html'] =  list(e.children)

            if e.name == 'status':
                cons = Status
                attrs['type'] = self.STATUS_TYPEMAP.get(e.get('type'), None)
            elif e.name == 'event':
                cons = Event
                attrs['type'] = self.EVENT_TYPEMAP.get(e.get('type'), None)
            elif e.name == 'message':
                cons = Message
            else:
                raise TypeError("unknown type '%s' for entry" % e.name)

            if not attrs['sender'] and not attrs['alias']:
                print_d("%s is a system entry" % e)
                attrs['system'] = True
            try:
                conversation.entries.append(cons(**attrs))
            except StandardError as err:
                print_e("Problem with element %s" % e)
                raise err

        source = chat.get('account')
        service = self.SERVICE_MAP[chat.get('service')]
        if source != conversation.source or service != conversation.service:
            raise ParseError("mismatch between path and chatinfo for '%s" %
                             conversation.path)

        return conversation

    def write(self, path, conversations):
        if len(conversations) != 1:
            raise ParseError(
                ("'%s' only supports one conversation per file:"
                 "\n  %s has %i") % (self.type, path, len(conversations))
                )

        conversation = conversations[0]
        soup = BeautifulSoup(features='xml')
        chat = soup.new_tag(name='chat')
        soup.append(chat)

        chat['xmlns'] = self.XMLNS
        chat['account'] = conversation.source
        chat['service'] = self.PAM_ECIVRES[conversation.service]
        chat.append('\n')

        for i, entry in enumerate(conversation.entries):
            attrs = dict(alias=entry.alias, sender=entry.sender)
            if isinstance(entry, Message):
                name = 'message'
                if entry.auto:
                    attrs['auto'] = "true"
            elif isinstance(entry, Status):
                name = 'status'
                attrs['type'] = self.PAMEPYT_SUTATS[entry.type]
            elif isinstance(entry, Event):
                name = 'event'
                attrs['type'] = self.PAMEPYT_TNEVE[entry.type]
            if entry.system: # no alias or sender for these
                del attrs['alias']
                del attrs['sender']
            elem = soup.new_tag(name=name, **attrs)

            f1 = self.TIME_FMT_CONVERSATION[:-2]
            f2 = self.TIME_FMT_CONVERSATION[-2:]
            v1 = entry.time.strftime(f1)
            v2 = entry.time.strftime(f2)
            v = v1+v2[:3]+':'+v2[3:]
            elem['time'] = v

            if not entry.html:
                elem.append(entry.text)
            else:
                for html in entry.html:
                    elem.append(html)

            chat.append(elem)
            if i != len(conversation.entries)-1:
                chat.append('\n')

        # images
        dstdir = dirname(path)
        for img_relpath, srcpath in conversation.images_full:
            dstpath = join(dstdir, img_relpath)
            if srcpath != realpath(dstpath):
                shutil.copy(srcpath, dstpath)

        # newline at end
        soup.append('\n')
        with codecs.open(path, 'wb', 'utf-8') as fh:
            fh.write(soup.decode())

formats = [Adium]
