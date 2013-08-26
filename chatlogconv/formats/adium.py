from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import datetime
import re
import codecs
import shutil
from os.path import join, dirname, relpath, realpath
from xml.dom import minidom

from dateutil.parser import parse

from chatlogconv.formats._base import ChatlogFormat
from chatlogconv import util
from chatlogconv.errors import ParseError
from chatlogconv.conversation import Conversation, Message, Status, Event

class Adium(ChatlogFormat):
    type = 'adium'
    SERVICE_MAP = {'GTalk' : 'gtalk',
                   'AIM' : 'aim'
                   }
    PAM_ECIVRES = {v: k for (k, v) in iter(SERVICE_MAP.items())}

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
    PAMEPYT_SUTATS = {v: k for (k, v) in iter(STATUS_TYPEMAP.items())}

    EVENT_TYPEMAP = {'windowClosed': Event.WINDOWCLOSED,
                     'windowOpened': Event.WINDOWOPENED,
                     }
    PAMEPYT_TNEVE = {v: k for (k, v) in iter(EVENT_TYPEMAP.items())}

    FILE_PATTERN = ('Logs/<service>.<source>/'
                    '<destination>/'
                    '<destination> (<time>).chatlog/'
                    '<destination> (<time>).xml')
    IMAGE_DIRECTORY = '.'
    TIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S%z'
    TIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S%z'
    XMLNS = "http://purl.org/net/ulf/ns/0.4-02"

    def get_path(self, conversation):
        s = re.split('<(.*?)>', self.FILE_PATTERN)
        for i in range(1, len(s), 2):
            a = getattr(conversation, s[i])
            if s[i] == 'service':
                a = self.PAM_ECIVRES[a]
            elif isinstance(a, datetime.datetime):
                a = a.strftime(self.TIME_FMT_FILE)
            s[i] = a

        return ''.join(s)

    def parse(self, path, messages=True):
        info = util.parse_path(path, self.FILE_PATTERN)
        if not info:
            return None

        time = parse(info['time'].replace('.', ':'))
        source = info['source']
        destination = info['destination']
        service = self.SERVICE_MAP[info['service']]

        dp = dirname(path)
        images = [relpath(join(dp, x), start=dp) for x in os.listdir(dp)
                  if not x.endswith('.xml')]

        conversation = Conversation(path, source, destination,
                                    service, time, images)
        if not messages:
            return [conversation]

        doc = minidom.parse(path)

        for e in [x for x in doc.getElementsByTagName('chat')[0].childNodes
                  if x.nodeType == x.ELEMENT_NODE]:
            alias = e.getAttribute('alias')
            sender = e.getAttribute('sender')
            time = parse(e.getAttribute('time'))

            html =  e.childNodes

            type_attr = e.getAttribute('type')
            if e.localName == 'status':
                try:
                    type = self.STATUS_TYPEMAP[type_attr]
                except KeyError:
                    raise ParseError("unknown type '%s' for status" % type_attr)
                entry = Status(alias, sender, time, type, html=html)
            elif e.localName == 'event':
                try:
                    type = self.EVENT_TYPEMAP[type_attr]
                except KeyError:
                    raise ParseError("unknown type '%s' for event" % type_attr)
                entry = Event(alias, sender, time, type, html=html)
            elif e.localName == 'message':
                entry = Message(alias, sender, time, html=html)
            else:
                raise ParseError("unknown type '%s' for entry" % e.localName)
            conversation.entries.append(entry)

        chatinfo = doc.getElementsByTagName('chat')[0]
        csource = chatinfo.getAttribute('account')
        cservice = self.SERVICE_MAP[chatinfo.getAttribute('service')]
        if source != csource or service != cservice:
            raise ParseError('mismatch between path and chatinfo for %s' % path)

        return [conversation]

    def write(self, path, conversations):
        if len(conversations) != 1:
            msg = '%s only supports one conversation per file:\n  %s has %i' % \
                  (self.type, path, len(conversations))
            raise ParseError(msg)
        conversation = conversations[0]
        impl = minidom.getDOMImplementation()
        doc = impl.createDocument(None, "chat", None)

        chat = doc.documentElement

        chat.setAttribute('account', conversation.source)
        chat.setAttribute('service', self.PAM_ECIVRES[conversation.service])
        chat.setAttribute('xmlns', self.XMLNS)

        chat.appendChild(doc.createTextNode('\n'))
        for entry in conversation.entries:
            if isinstance(entry, Message):
                name = 'message'
            elif isinstance(entry, Status):
                name = 'status'
            elif isinstance(entry, Event):
                name = 'event'
            elem = doc.createElement(name)

            for k in ('alias', 'sender'):
                v = getattr(entry, k)
                if v:
                    elem.setAttribute(k, v)

            if entry.type:
                if isinstance(entry, Status):
                    t = self.PAMEPYT_SUTATS[entry.type]
                elif isinstance(entry, Event):
                    t = self.PAMEPYT_TNEVE[entry.type]
                elem.setAttribute('type', t)

            if entry.time:
                f1 = self.TIME_FMT_CONVERSATION[:-2]
                f2 = self.TIME_FMT_CONVERSATION[-2:]
                v1 = entry.time.strftime(f1)
                v2 = entry.time.strftime(f2)
                v = v1+v2[:3]+':'+v2[3:]
                elem.setAttribute('time', v)

            if entry.html:
                for child in entry.html:
                    elem.appendChild(child)
            elif entry.text:
                elem.appendChild(doc.createTextNode(entry.text))

            chat.appendChild(elem)
            chat.appendChild(doc.createTextNode('\n'))
        chat.removeChild(chat.lastChild)

        # images
        for img_relpath in conversation.images:
            srcdir = dirname(conversation.path)
            dstdir = dirname(path)
            srcimg = join(srcdir, img_relpath)
            dstimg = join(dstdir, img_relpath)
            if realpath(srcimg) != realpath(dstimg):
                shutil.copy(srcimg, dstimg)

        with codecs.open(path, 'wb', 'utf-8') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            chat.writexml(fh)
            fh.write('\n')

formats = [Adium]
