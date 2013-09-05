from __future__ import unicode_literals
from __future__ import absolute_import

# TODO: handle <action>

import os
import codecs
import shutil
import datetime
from os.path import join, dirname, relpath, realpath

from bs4 import BeautifulSoup
from bs4.element import Tag, Comment, NavigableString

from chatlogsync import util, const
from chatlogsync.formats._base import ChatlogFormat
from chatlogsync.errors import ParseError
from chatlogsync.conversation import Conversation, Message, Status, Event
from chatlogsync.timezones import getoffset

import sys

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
                      'mobile': Status.MOBILE,
                      'purple': Status.SYSTEM,
                      'available': Status.AVAILABLE,
                      'chat-error': Status.ERROR,
                      }


    EVENT_TYPEMAP = {'windowClosed': Event.WINDOWCLOSED,
                     'windowOpened': Event.WINDOWOPENED,
                     }

    FILE_PATTERN = ('/Logs/{service}.{source}/'
                    '{destination}/'
                    '{destination} ({time}).chatlog/'
                    '{destination} ({time}).xml')
    IMAGE_DIRECTORY = '.'
    TIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S%z'
    STRPTIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S'
    TIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S%z'
    STRPTIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S'
    XMLNS = "http://purl.org/net/ulf/ns/0.4-02"
    XML_HEADER = '<?xml version="1.0" encoding="UTF-8" ?>'

    ATTRS = {'chat': ('xmlns', 'account', 'service'),
             'message': ('sender', 'time', 'auto', 'alias'),
             'status': ('type', 'sender', 'time', 'alias'),
             'event': ('type', 'sender', 'time', 'alias'),
             }

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
        with codecs.open(conversation.path, encoding='utf-8') as f:
            data = f.read().strip()
            lines = data.split('\n')

        xml_header = lines.pop(0)
        conversation.original_parser_name = self.type
        for e in BeautifulSoup(lines.pop(0), ['lxml', 'xml']).children:
            if isinstance(e, Comment):
                conversation.original_parser_name = e.split('/')[1]
            else:
                service = self.SERVICE_MAP[e.get('service')]
                source = e.get('account')

        for line in lines:
            if line == "</chat>":
                continue
            cons, attrs = self._parse_line(line, conversation)
            try:
                conversation.entries.append(cons(**attrs))
            except Exception as err:
                print_e("Problem with element %s" % e)
                raise err

        if source != conversation.source or service != conversation.service:
            raise ParseError("mismatch between path and chatinfo for '%s" %
                             conversation.path)

        return conversation

    def _parse_line(self, line, conversation):
        """Return (cons, attrs)"""
        status_html = []
        attrs = {}
        cons = None

        for e in BeautifulSoup(line, ['lxml', 'xml']).children:
            if isinstance(e, Comment):
                status_html = [NavigableString(e)]
                continue
            for a in ('alias', 'sender', 'auto', 'time'):
                attrs[a] = e.get(a, '')

            if attrs['sender'] == conversation.source:
                attrs['isuser'] = True
            elif attrs['sender'] == conversation.destination:
                attrs['isuser'] = False
            else:
                attrs['isuser'] = False
                # if user is not source or destination, this is a group chat
                conversation.isgroup = True

            attrs['auto'] = True if attrs['auto'] else False
            if attrs['time']:
                attrs['time'] = self._parse_ctime(attrs['time'])
            attrs['html'] =  list(e.children)

            if e.name == 'status':
                cons = Status
                attrs['type'] = self.STATUS_TYPEMAP.get(e.get('type'), None)
                if attrs['type'] in Status.USER_TYPES:
                    attrs['msg_html'] = attrs['html']
                    attrs['html'] = status_html
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

        if not cons:
            raise(ParseError("could not parse line: '%s'" % line))

        return cons, attrs

    def write(self, path, conversations):
        if len(conversations) != 1:
            raise ParseError(
                ("'%s' only supports one conversation per file:"
                 "\n  %s has %i") % (self.type, path, len(conversations))
                )
        conversation = conversations[0]

        fh = codecs.open(path, 'wb', 'utf-8')
        fh.write(self.XML_HEADER+'\n')
        attrs = dict(xmlns=self.XMLNS, account=conversation.source,
                     service=self.PAM_ECIVRES[conversation.service])

        util.write_comment(fh, const.HEADER_COMMENT %
                           conversation.original_parser_name)
        self._write_xml(fh, 'chat', attrs, close=False)
        fh.write('\n')

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
            elif not attrs['alias']:
                del attrs['alias']

            f1 = self.TIME_FMT_CONVERSATION[:-2]
            f2 = self.TIME_FMT_CONVERSATION[-2:]
            v1 = entry.time.strftime(f1)
            v2 = entry.time.strftime(f2)
            v = v1+v2[:3]+':'+v2[3:]
            attrs['time'] = v

            if isinstance(entry, Status) and entry.type in Status.USER_TYPES:
                htmlattr = 'msg_html'
                if entry.has_other_html:
                    util.write_comment(fh, ''.join([x.string for x
                                                    in entry.html]))
            else:
                htmlattr = 'html'

            self._write_xml(fh, name, attrs, contents=getattr(entry, htmlattr))
            if i != len(conversation.entries)-1:
                fh.write('\n')

        fh.write('</chat>')
        fh.close()

        # images
        dstdir = dirname(path)
        for img_relpath, srcpath in conversation.images_full:
            dstpath = join(dstdir, img_relpath)
            if srcpath != realpath(dstpath):
                shutil.copy(srcpath, dstpath)

    def _write_xml(self, fh, name, attrs, contents=[], close=True):
        attrlist = []
        for n in self.ATTRS[name]:
            v = attrs.get(n, None)
            if v:
                attrlist.append((n, v))
        attrstr = " ".join(['%s="%s"' % (n,v)  for n, v in attrlist])
        fh.write("<%s %s>" % (name, attrstr))

        for e in contents:
            if isinstance(e, Tag):
                fh.write(e.decode())
            else:
                fh.write(e.output_ready())

        if close:
            fh.write("</%s>" % name)

formats = [Adium]
