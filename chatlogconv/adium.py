import sys
import datetime
from os.path import join, dirname
from xml.dom import minidom

from dateutil.parser import parse

import util
from errors import ParseError
from conversation import Conversation, Message, Status, Event

PROTO_MAP = { 'GTalk' : 'gtalk',
              'AIM' : 'aim' }

PAM_OTORP = {v: k for (k, v) in iter(PROTO_MAP.items())}

class Adium(object):
    directory_pattern = ('Logs/<proto>.<src>/<dst>/<dst> (<time>).chatlog/'
                         '<dst> (<time>).xml')
    image_directory = 'Logs/<proto>.<src>/<dst>/<dst> (<time>).chatlog'

class AdiumParser(Adium):
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

    def parse(self, path, messages=True):
        info = util.parse_path(path, self.directory_pattern)
        time = parse(info['time'].replace('.', ':'))
        source = info['src']
        destination = info['dst']
        protocol = PROTO_MAP[info['proto']]

        conversation = Conversation(source, destination, protocol, time)
        if not messages:
            return [conversation]

        doc = minidom.parse(path)

        entries = []
        for e in [x for x in doc.getElementsByTagName('chat')[0].childNodes
                  if x.nodeType == x.ELEMENT_NODE]:
            alias = e.getAttribute('alias')
            sender = e.getAttribute('sender')
            time = parse(e.getAttribute('time'))

            text = util.get_text(e.childNodes)
            html = util.get_html(e.childNodes)
            type_attr = e.getAttribute('type')
            if e.localName == 'status':
                try:
                    type = self.STATUS_TYPEMAP[type_attr]
                except KeyError:
                    print e.toxml()
                    raise ParseError("unknown type '%s' for status" % type_attr)
                entry = Status(alias, sender, time, type, text, html)
            elif e.localName == 'message':
                entry = Message(alias, sender, time, text, html=html)
            elif e.localName == 'event':
                try:
                    type = self.EVENT_TYPEMAP[type_attr]
                except KeyError:
                    raise ParseError("unknown type '%s' for event" % type_attr)
                entry = Event(alias, sender, time, type, text, html)
            else:
                raise ParseError("unknown type '%s' for entry" % e.localName)
        conversation.entries = entries

        chatinfo = doc.getElementsByTagName('chat')[0]
        csource = chatinfo.getAttribute('account')
        cprotocol = PROTO_MAP[chatinfo.getAttribute('service')]
        if source != csource or protocol != cprotocol:
            raise ParseError('mismatch between path and chatinfo for %s' % path)

        return [conversation]
