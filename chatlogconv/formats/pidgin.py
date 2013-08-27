from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import re
import codecs
import datetime
from os.path import join, dirname, relpath, realpath

from dateutil.parser import parse
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

from chatlogconv.formats._base import ChatlogFormat
from chatlogconv import util
from chatlogconv.errors import ParseError
from chatlogconv.conversation import Conversation, Message, Status, Event
from chatlogconv.timezones import getoffset

class PidginHtml(ChatlogFormat):
    type = 'pidgin-html'
    SERVICE_MAP = {'jabber': 'jabber',
                   'aim': 'aim'}
    PAM_ECIVRES = {'gtalk': 'jabber',
                   'jabber': 'jabber',
                   'aim': 'aim'}
    FILE_PATTERN = 'logs/<service>/<source>/<destination>/<time>.html'
    TIME_FMT_FILE = '%Y-%m-%d.%H%M%S%z%Z'
    TITLE_PATTERN = ('Conversation with <destination> '
                     'at <time> on <source> (<service>)')

    SOURCE_COLOR = "#16569E"
    DESTINATION_COLOR = "#A82F2F"
    ERROR_COLOR = "#16569E"

    def parse_info(self, info):
        info['service'] = self.SERVICE_MAP[info['service']]
        if info['service'] == 'jabber' and \
                (info['destination'].endswith('@gmail.com') or
                 info['source'].endswith('@gmail.com')):
            info['service'] = 'gtalk'
        info['time'] = parse(info['time'], tzinfos=getoffset)

        return info

    def parse(self, path, messages=True):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        timestr = info['time'].replace('.', ' ')
        info['time'] = re.sub('([+-]\d+)([^0-9- ]+)', r'\2 \1', timestr)
        info = self.parse_info(info)

        conversation = Conversation(self, path, info['source'],
                                    info['destination'],
                                    info['service'], info['time'])
        if not messages:
            return [conversation]

        # parse html
        with open(path) as f:
            soup = BeautifulSoup(f, 'lxml')
        body = soup.find('body')
        children = body.children
        info = util.parse_string(children.next().text, self.TITLE_PATTERN)
        info = self.parse_info(info)

        for k, v in iter(info.items()):
            if v != getattr(conversation, k):
                raise ParseError('%s: mismatch between filename and header'
                                 % path)

        timedelta = datetime.timedelta(days=0)
        prev_time = None
        for c in children:
            if c == "\n": # newline, new entry
                continue
            if not isinstance(c, Tag):
                raise ParseError("unexpected element '%s' (expected Tag)"
                                 % c)
            if c.name != 'font':
                raise ParseError('unexpected tag %s (expected font)'
                                 % c.name)
            color = c.get('color')
            alias = None
            time = None
            for x in c.children:
                if not isinstance(x, Tag):
                    continue
                if x.name == 'font':
                    timestr = re.sub('[\(\)]', '', x.text)
                    time = parse(timestr, default=conversation.time,
                                 ignoretz=True)
                    if prev_time and time < prev_time:
                        timedelta += timedelta(days=1)
                    if timedelta:
                        time += timedelta
                    prev_time = time
                elif x.name == 'b':
                    alias = x.text[:-1]

            if color == self.SOURCE_COLOR:
                sender = conversation.source
                html = self.parse_message(c, children)
                entry = Message(alias, sender, time, html)
            elif color == self.DESTINATION_COLOR:
                sender = conversation.destination
                html = self.parse_message(c, children)
                entry = Message(alias, sender, time, html)
            elif color == self.ERROR_COLOR:
                sender = conversation.source
                html = self.parse_error(c, children)
                entry = Status(alias, sender, time, STATUS.CHATERROR, html)
            elif not color:
                html, type, sender = self.parse_status(c, children,
                                                       conversation)
                entry = Status(alias, sender, time, type, html)

            if isinstance(entry, Message) and not alias:
                raise ParseError('Expected alias in message: %s' % entry)
            if not time:
                raise ParseError('Expected time in entry: %s' % entry)

        raise NotImplementedError

    def parse_message(self, c, children):
        html = []

        # lstrip first element
        c = children.next()
        if isinstance(c, NavigableString):
            html.append(NavigableString(c.lstrip()))
        while(c.next != '\n'):
            c = children.next()
            html.append(c)

        if html[-1].name == 'br':
            html = html[:-1]

        return html

    def parse_status(self, c, children, conversation):
        raise NotImplementedError

    def parse_error(self, c, children):
        raise NotImplementedError

    def write(self, path, conversations):
        if len(conversations) != 1:
            msg = '%s only supports one conversation per file:\n  %s has %i' % \
                (self.type, path, len(conversations))
            raise ParseError(msg)

        conversation = conversations[0]
        raise NotImplementedError

formats = [PidginHtml]
