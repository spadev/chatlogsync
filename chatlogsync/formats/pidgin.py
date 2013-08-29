from __future__ import unicode_literals
from __future__ import absolute_import

# TODO: add support for multi-user chats

import re
import sys
import codecs
import datetime
from os.path import join, dirname, relpath, realpath

from dateutil.parser import parse
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

from chatlogsync.formats._base import ChatlogFormat
from chatlogsync import util
from chatlogsync.errors import ParseError, ArgumentError
from chatlogsync.conversation import Conversation, Message, Status, Event
from chatlogsync.timezones import getoffset

class PidginHtml(ChatlogFormat):
    type = 'pidgin-html'
    SERVICE_MAP = {'jabber': 'jabber',
                   'aim': 'aim'}
    PAM_ECIVRES = {'gtalk': 'jabber',
                   'jabber': 'jabber',
                   'aim': 'aim'}
    FILE_PATTERN = 'logs/<service>/<source>/<destination>/<time>.html'
    TIME_FMT_FILE = '%Y-%m-%d.%H%M%S%z%Z'
    TITLE_PATTERN = _("Conversation with <destination> "
                     "at <time> on <source> (<service>)")

    SOURCE_COLOR = "#16569E"
    DESTINATION_COLOR = "#A82F2F"
    ERROR_COLOR = "#FF0000"
    DELAYED_COLOR = "#062585"
    STATUS_TYPEMAP = {_("<alias> has gone away."): Status.AWAY,
                      _("<alias> is no longer <type>."): Status.AVAILABLE,
                      _("<alias> has signed off."): Status.OFFLINE,
                      _("<alias> has signed on."): Status.ONLINE,
                      _("<sender> is now known as <alias>"): Status.PURPLE,
                      _("<alias> has left the conversation"):
                          Status.PURPLE,
                      _("<alias> has become idle."): Status.IDLE,
                      # special cases for logs converted from adium
                      _("You have disconnected"): Status.DISCONNECTED,
                      _("You have connected"): Status.CONNECTED,
                      }
    TRAILING_SLASH_REGEX = re.compile('/[^/]*$')
    AUTOREPLY_REGEX = re.compile('(?P<alias>.* )(?P<autoreply><AUTO-REPLY>)$')

    TIME_REGEX = re.compile('([+-]\d+)([^0-9- ]+)')

    def parse(self, path, messages=True):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        timestr = info['time'].replace('.', ' ')
        info['time'] = self.TIME_REGEX.sub(r'\2 \1', timestr)
        self._parse_info(info)
        if info['destination'] == '.system':
            print_w('Ignoring system log %s' % path)
            return None

        conversation = Conversation(self, path, info['source'],
                                    info['destination'],
                                    info['service'], info['time'],
                                    [], [])
        if not messages:
            return [conversation]

        # parse html
        with codecs.open(path, encoding='utf-8') as f:
            lines = f.read().strip().split('<br/>\n')
        title_line, first_line = lines[0].split('\n', 1)
        lines[0] = first_line
        info = self._parse_title(title_line, conversation)

        for k, v in iter(info.items()):
            cv = getattr(conversation, k)
            if v != cv:
                raise ParseError('mismatch between filename and header '
                                 '%s: %s != %s' % (k, v, cv))

        prev_time = None
        timedelta = datetime.timedelta(0)
        senders_by_color = {self.SOURCE_COLOR: conversation.source,
                            self.DESTINATION_COLOR: conversation.destination}
        senders_by_alias = {}
        ignore_aliases = set()
        ignore_colors = set()
        attrs_list = []
        for line in lines:
            try:
                cons, attrs = \
                    self._parse_line(line, conversation, senders_by_color)
            except ArgumentError as e:
                print_e('Error on line %s' % line)
                raise e

            if not attrs:
                continue

            if prev_time and attrs['time'] < prev_time:
                timedelta += datetime.timedelta(days=1)
            attrs['time'] += timedelta
            prev_time = attrs['time']

            s = attrs['sender']
            a = attrs['alias']
            c = attrs['color']
            if s and a and a not in ignore_aliases:
                s2 = senders_by_alias.get(a, s)
                if s != s2:
                    print_w('Multiple senders found for %s (%s)'
                            % (a, '%s, %s' % (s, s2)))
                    ignore_aliases.add(a)
                    del senders_by_alias[a]
                senders_by_alias[a] = s
            if s and c and c not in ignore_colors:
                s2 = senders_by_color.get(c, s)
                if s != s2:
                    print_w('Multiple senders found for %s (%s)'
                            % (c, '%s, %s' % (s, s2)))
                    ignore_colors.add(c)
                    del senders_by_color[c]

                senders_by_color[c] = s

            attrs_list.append((cons, attrs))

        conversation.entries = \
            self._get_entries(conversation, senders_by_alias, attrs_list)

        return [conversation]

    def _get_entries(self, conversation, senders_by_alias, attrs_list):
        aliases_by_sender = {v: k for k, v in iter(senders_by_alias.items())}
        entries = []
        for cons, attrs in attrs_list:
            if not attrs['sender']:
                attrs['sender'] = senders_by_alias.get(attrs['alias'], None)
                if not attrs['sender']:
                    # default to destination if no sender
                    attrs['sender'] = conversation.destination
            if not attrs['alias']:
                attrs['alias'] = aliases_by_sender.get(attrs['sender'], '')
            if attrs['sender'] == attrs['alias']:
                attrs['alias'] = ''
            entries.append(cons(**attrs))
        return entries

    def _parse_info(self, info, conversation=None):
        info['service'] = self.SERVICE_MAP[info['service']]
        info['source'] = self.TRAILING_SLASH_REGEX.sub('', info['source'])
        if info['service'] == 'jabber' and \
                (info['destination'].endswith('@gmail.com') or
                 info['source'].endswith('@gmail.com')):
            info['service'] = 'gtalk'

        info['time'] = parse(info['time'], tzinfos=getoffset)
        if not info['time'].tzname():
            newtzinfo = conversation.time.tzinfo
            info['time'] = info['time'].replace(tzinfo=newtzinfo)

        return info

    def _parse_line(self, line, conversation, senders_by_color):
        """Return (cons, attrs)"""
        attrs = dict(alias=None, time=None, sender=conversation.source,
                     type=None, html=None, color=None)
        soup = BeautifulSoup(line, 'lxml')
        if len(soup) == 0:
            print_d("Skipping line %s" % line)
            return None, None
        elem = soup.find('font')
        attrs['color'] = elem.get('color')
        if attrs['color'] == self.DELAYED_COLOR:
            attrs['delayed'] = True
        if elem.has_attr('size'):
            timestr = elem.text
        elif attrs['color'] == self.ERROR_COLOR:
            timestr = elem.find('font').text
            attrs['type'] = Status.CHATERROR
        elif attrs['color']:
            timestr = elem.find('font').text
            attrs['sender'] = senders_by_color.get(attrs['color'])
            attrs['alias'] = elem.find('b').text[:-1] # trailing ':'
            m = self.AUTOREPLY_REGEX.match(attrs['alias'])
            if m:
                attrs['alias'] = m.group('alias')
                attrs['auto'] = True
        else:
            raise ParseError('Unexpected <font> found at line %s' % line)
        timestr = timestr[1:-1] # '(10:10:10)'
        attrs['time'] = parse(timestr, default=conversation.time,
                              ignoretz=True)

        # message
        if attrs['color'] and attrs['color'] != self.ERROR_COLOR:
            html = [e for e in elem.nextSiblingGenerator()]
            cons = Message
        else: # status
            html = [NavigableString(''.join(e.stripped_strings))
                    if isinstance(e, Tag)
                    else e.string for e in elem.nextSiblingGenerator()]
            cons = Status

        if html and isinstance(html[0], NavigableString):
            s = html[0].lstrip()
            if not s:
                del html[0]
            else:
                html[0] = NavigableString(s)
        attrs['html'] = html

        if cons == Status:
            self._parse_status(attrs, conversation,
                               attrs['color'] == self.ERROR_COLOR)
            if not attrs['type']:
                print_w("No type found for status '%s': using purple"
                        % line)
                attrs['type'] = Status.PURPLE

        return (cons, attrs)

    def _parse_status(self, info, conversation, error=False):
        s = ''.join(info['html'])
        info['sender'] = conversation.source \
            if s.startswith(_("You")) else None
        if error:
            info['type'] = Status.CHATERROR
        else:
            for pattern, t in iter(self.STATUS_TYPEMAP.items()):
                i = util.parse_string(s, pattern)
                if i is not None:
                    for k, v in iter(i.items()):
                        info[k] = v
                    info['type'] = t

    def _parse_title(self, line, conversation):
        soup = BeautifulSoup(line)
        info = util.parse_string(soup.text, self.TITLE_PATTERN)
        self._parse_info(info, conversation)

        return info

    def write(self, path, conversations):
        if len(conversations) != 1:
            msg = '%s only supports one conversation per file:\n  %s has %i' % \
                (self.type, path, len(conversations))
            raise ParseError(msg)

        conversation = conversations[0]
        raise NotImplementedError

formats = [PidginHtml]
