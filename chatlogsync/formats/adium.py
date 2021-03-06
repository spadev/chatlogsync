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

# TODO: handle <action>

import os
import re
import codecs
import shutil
import datetime
from os.path import join, dirname, relpath

from bs4 import BeautifulSoup
from bs4.element import Tag, Comment, NavigableString

from chatlogsync import util, const
from chatlogsync.formats._base import ChatlogFormat
from chatlogsync.errors import ParseError
from chatlogsync.conversation import Conversation, Message, Status, Event
from chatlogsync.timezones import getoffset

class Adium(ChatlogFormat):
    type = 'adium'
    SERVICE_MAP = {
        'GTalk' : 'gtalk',
        'AIM' : 'aim',
        'Facebook' : 'facebook',
    }

    STATUS_TYPEMAP = {
        'offline': Status.OFFLINE,
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


    EVENT_TYPEMAP = {
        'windowClosed': Event.WINDOWCLOSED,
        'windowOpened': Event.WINDOWOPENED,
    }

    FILE_PATTERN = join(
        '{service}.{source}',
        '{destination}',
        '{destination} ({time}).chatlog',
        '{destination} ({time}).xml'
    )
    IMAGE_DIRECTORY = '.'
    TIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S%z'
    STRPTIME_FMT_FILE = '%Y-%m-%dT%H.%M.%S'
    TIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S%z'
    STRPTIME_FMT_CONVERSATION = '%Y-%m-%dT%H:%M:%S'
    XMLNS = "http://purl.org/net/ulf/ns/0.4-02"
    XML_HEADER = '<?xml version="1.0" encoding="UTF-8" ?>'

    ATTRS = {
        'chat': ('xmlns', 'account', 'service', 'resource', 'groupchat'),
        'message': ('sender', 'time', 'auto', 'alias'),
        'status': ('type', 'sender', 'time', 'alias'),
        'event': ('type', 'sender', 'time', 'alias'),
    }

    # adium doesn't include the @chat.facebook.com for the source
    TRANSFORMS = {
        'source': (lambda s, c: s+'@chat.facebook.com'
                   if c.service == 'facebook' else s),
    }
    UNTRANSFORMS = {
        'source': (lambda s, c: s.replace('@chat.facebook.com', '')
                   if c.service == 'facebook' else s),
    }

    SENDER_RE = re.compile('<[^<>]*sender="(?P<sender>.*?)".*?>')
    IMGTAG_RE = re.compile('<img (.*?)([/]?)>(.*)')
    TIMESTR_RE = re.compile('^(?P<ts1>.*)(?P<ts2>[-+][\d:]+)$')

    def _parse_time(self, timestr, fmt):
        match = re.match(self.TIMESTR_RE, timestr)
        try:
            ts1, ts2 = match.groups()
            ts2 = ts2.replace(':', '')
        except:
            raise ParseError("problem parsing time string %s" % timestr)

        dt = datetime.datetime.strptime(ts1, fmt)
        return dt.replace(tzinfo=getoffset(None, ts2))

    def _isgroup(self, lines, path, source, destination):
        senders = set((source, destination, None))
        if 'groupchat="true"' in lines[1]:
            return True
        for line in lines:
            m = self.SENDER_RE.search(line)
            if m and m.group('sender') not in senders:
                return True
        return False

    def parse_path(self, path):
        info = util.parse_string(path, self.FILE_PATTERN, path=True)
        if not info:
            return None

        time = self._parse_time(info['time'], self.STRPTIME_FMT_FILE)
        destination = info['destination']
        service = self.SERVICE_MAP[info['service']]
        source = info['source']

        with codecs.open(path, encoding='utf-8') as f:
            data = f.read().strip()
            lines = data.split('\n')
        isgroup = self._isgroup(lines, path, source, destination)

        dp = join(dirname(path), self.IMAGE_DIRECTORY)
        images = [relpath(join(dp, x), start=dp) for x in os.listdir(dp)
                  if not x.endswith('.xml')]

        # create conversation with tranformed source
        conversation = Conversation(self, path, source, destination,
                                    service, time, entries=[], images=images,
                                    isgroup=isgroup,
                                    transforms=self.TRANSFORMS)
        conversation.lines = lines

        return [conversation]

    def parse_conversation(self, conversation):
        lines = conversation.lines
        xml_header = lines.pop(0)
        conversation.original_parser_name = self.type
        for e in BeautifulSoup(lines.pop(0), ['lxml', 'xml']).children:
            if isinstance(e, Comment):
                conversation.original_parser_name = e.split('/')[1]
            else:
                service = self.SERVICE_MAP[e.get('service')]
                source = e.get('account')
                conversation.resource = e.get('resource')
                transformed_source = \
                    self.TRANSFORMS['source'](source, conversation)

        if transformed_source != conversation.source or \
                service != conversation.service:
            raise ParseError("mismatch between path and chatinfo for '%s" %
                             conversation.path)

        latest_time = conversation.time
        for line in lines:
            if line == "</chat>":
                continue
            cons, attrs = self._parse_line(line, conversation, source,
                                           transformed_source)
            if attrs['time'] < latest_time:
                attrs['delayed'] = True
            else:
                latest_time = attrs['time']

            try:
                conversation.entries.append(cons(**attrs))
            except Exception as err:
                print_e("Problem with element %s" % e)
                raise err

        return conversation

    def _parse_line(self, line, conversation, source, transformed_source):
        """Return (cons, attrs)"""
        status_html = []
        attrs = {}
        cons = None

        for elem in BeautifulSoup(line, ['lxml', 'xml']).children:
            if isinstance(elem, Comment):
                alternate, status_html = elem.split('|', 1)
                attrs['alternate'] = True if alternate else False
                status_html = [NavigableString(status_html)]
                continue

            for key in ('alias', 'sender', 'auto', 'time'):
                attrs[key] = elem.get(key, '')

            if attrs['sender'] == source:
                attrs['sender'] = transformed_source
                attrs['isuser'] = True
            else:
                attrs['isuser'] = False

            attrs['auto'] = bool(attrs['auto'])
            if attrs['time']:
                fmt = self.STRPTIME_FMT_CONVERSATION
                attrs['time'] = self._parse_time(attrs['time'], fmt)

            attrs['html'] =  list(elem.children)

            if elem.name == 'status':
                cons = Status
                attrs['type'] = self.STATUS_TYPEMAP.get(elem.get('type'), None)
                if attrs['type'] in Status.USER_TYPES:
                    attrs['msg_html'] = attrs['html']
                    attrs['html'] = status_html
            elif elem.name == 'event':
                cons = Event
                attrs['type'] = self.EVENT_TYPEMAP.get(elem.get('type'), None)
            elif elem.name == 'message':
                cons = Message
            else:
                raise TypeError("unknown type '%s' for entry" % elem.name)

            if not attrs['sender'] and not attrs['alias']:
                print_d("%s is a system entry" % elem)
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

        file_object = codecs.open(path, 'wb', 'utf-8')
        file_object.write(self.XML_HEADER+'\n')
        untransformed_source = self.UNTRANSFORMS['source'](conversation.source,
                                                           conversation)
        attrs = dict(xmlns=self.XMLNS, account=untransformed_source,
                     service=self.PAM_ECIVRES[conversation.service],
                     resource=conversation.resource)

        # this attribute will only be useful if we're not the original parser
        if conversation.isgroup and \
                conversation.original_parser_name != self.type:
            attrs['groupchat'] = "true"

        util.write_comment(file_object, const.HEADER_COMMENT %
                           conversation.original_parser_name)
        self._write_xml(file_object, 'chat', attrs, conversation,close=False)
        file_object.write('\n')

        for i, entry in enumerate(conversation.entries):
            attrs = {'alias': entry.alias,
                     'sender': (untransformed_source
                                if entry.sender == conversation.source
                                else entry.sender)
                     }
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
                # no alias for event
                attrs['alias'] = ''

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

            # comments should look like 1|status text
            comment = ['1', ''] if entry.alternate else ['', '']

            if isinstance(entry, Status) and entry.type in Status.USER_TYPES:
                htmlattr = 'msg_html'
                if entry.has_other_html:
                    comment[1] = ''.join([x.string for x in entry.html])
            else:
                htmlattr = 'html'

            if [x for x in comment if x]:
                util.write_comment(file_object, '|'.join(comment))

            self._write_xml(file_object, name, attrs, conversation,
                            contents=getattr(entry, htmlattr))
            if i != len(conversation.entries)-1:
                file_object.write('\n')

        file_object.write('</chat>')
        file_object.close()

        self.copy_images(path, conversation)

    def _write_xml(self, file_object, name, attrs, conversation,
                   contents=[], close=True):
        attrlist = []
        for n in self.ATTRS[name]:
            v = attrs.get(n, None)
            if v:
                attrlist.append((n, v))
        attrstr = " ".join(['%s="%s"' % (n,v)  for n, v in attrlist])
        file_object.write("<%s %s>" % (name, attrstr))

        for elem in contents:
            if isinstance(elem, NavigableString) or isinstance(elem, Comment):
                elem.setup() # workaround for BeautifulSoup issue

            if isinstance(elem, Tag):
                # must include size of the image to display properly in adium
                # log viewer. width and height attributes must come before src.
                if elem.name == 'img':
                    src = elem.get('src')
                    if src in conversation.images and \
                            not elem.has_attr('width') or \
                            not elem.has_attr('height'):
                        idx = conversation.images.index(src)
                        fullpath = conversation.images_full[idx][1]
                        elem['width'], elem['height'] = util.get_image_size(fullpath)
                    m = self.IMGTAG_RE.match(elem.decode())
                    attributes, close, rest = m.groups()
                    attributes = attributes.split()
                    attributes.sort(key=lambda x: 'b' if x.startswith('width') or
                                    x.startswith('height') else x)
                    file_object.write('<img %s%s>%s' %
                             (' '.join(attributes), close, rest))
                else:
                    file_object.write(elem.decode())
            else:
                file_object.write(elem.output_ready())

        if close:
            file_object.write("</%s>" % name)

formats = [Adium]
