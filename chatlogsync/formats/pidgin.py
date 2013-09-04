from __future__ import unicode_literals
from __future__ import absolute_import

# TODO: add support for multi-user chats
# TODO: handle attached files

import re
import sys
import codecs
import datetime
from os.path import join, dirname, relpath, realpath

from dateutil.parser import parse
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString, Comment

from chatlogsync import util, const, timezones
from chatlogsync.formats._base import ChatlogFormat
from chatlogsync.errors import ParseError, ArgumentError
from chatlogsync.conversation import Conversation, Message, Status, Event, Entry
from chatlogsync.timezones import getoffset

class PidginHtml(ChatlogFormat):
    type = 'pidgin-html'
    SERVICE_MAP = {'jabber': 'jabber',
                   'aim': 'aim',
                   }
    PAM_ECIVRES = {'gtalk': 'jabber',
                   'jabber': 'jabber',
                   'facebook': 'jabber',
                   'aim': 'aim',
                   }
    FILE_PATTERN = 'logs/<service>/<source>/<destination>/<time>.html'
    TIME_FMT_FILE = '%Y-%m-%d.%H%M%S%z%Z'
    TITLE_PATTERN = _("Conversation with <destination> "
                     "at <time> on <source> (<service>)")

    SOURCE_COLOR = "#16569E"
    DESTINATION_COLOR = "#A82F2F"
    ERROR_COLOR = "#FF0000"
    ALTERNATE_COLOR = "#062585"

    TIME_FMT_CONVERSATION = "(%X)"
    TIME_FMT_CONVERSATION_WITH_DATE = "(%x %X)"

    STATUS_TYPEMAP = {_("<alias> has gone away."): Status.AWAY,
                      _("<alias> is no longer <type>."): Status.AVAILABLE,
                      _("<alias> has signed off."): Status.OFFLINE,
                      _("<alias> has signed on."): Status.ONLINE,
                      _("<alias> has become idle."): Status.IDLE,
                      _("<alias> is mobile."): Status.MOBILE,
                      }

    SOURCE_REGEX = re.compile('/[^/]*$')
    AUTOREPLY_REGEX = re.compile('(?P<alias>.* )(?P<autoreply><AUTO-REPLY>)$')

    TIME_REGEX = re.compile('([+-]\d+)([^0-9- ]+)')

    def __init__(self, *args):
        super(PidginHtml, self).__init__(*args)
        self.TIME_FMT_TITLE = timezones.locale_datetime_fmt

    def parse_path(self, path):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        timestr = info['time'].replace('.', ' ')
        info['time'] = self.TIME_REGEX.sub(r'\2 \1', timestr)
        self._parse_info(info)
        if info['destination'] == '.system':
            print_d('Ignoring system log %s' % path)
            return None

        conversation = Conversation(self, path, info['source'],
                                    info['destination'],
                                    info['service'], info['time'],
                                    [], [])

        return [conversation]

    def parse_conversation(self, conversation):
        with codecs.open(conversation.path, encoding='utf-8') as f:
            data = f.read()
            lines = data.split('\n')
            if not lines[-1]:
                del lines[-1]
            if lines[-1].endswith('</html>'):
                del lines[-1]
        title_line = lines.pop(0)
        info, conversation.original_parser_name = \
            self._parse_title(title_line, conversation)

        for k, v in iter(info.items()):
            cv = getattr(conversation, k)
            if v != cv:
                raise ParseError("mismatch between filename and header "
                                 "%s: '%s' != '%s'" % (k, v, cv))

        prev_time = conversation.time
        senders_by_color = {self.SOURCE_COLOR: conversation.source,
                            self.DESTINATION_COLOR: conversation.destination}
        senders_by_alias = {}
        ignore_aliases = set()
        ignore_colors = set()
        attrs_list = []
        i = 0
        while i < len(lines):
            line = lines[i]
            while True:
                if line.endswith('<br/>'):
                    line = line[:-5]
                    break
                elif line.startswith('<!--'):
                    break
                line += '\n'+lines[i+1]
                i += 1
            i += 1
            try:
                cons, attrs = self._parse_line(line, conversation, prev_time,
                                               senders_by_color)
            except ArgumentError as e:
                print_e('Error on line %s' % line)
                raise e

            if not attrs:
                continue

            if attrs['time'] < prev_time and not attrs['delayed']:
                attrs['time'] += datetime.timedelta(days=1)
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

        return conversation

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
        info['source'] = self.SOURCE_REGEX.sub('', info['source'])
        if info['service'] == 'jabber':
            if info['destination'].endswith('@gmail.com') or \
                    info['source'].endswith('@gmail.com'):
                info['service'] = 'gtalk'
            if info['destination'].endswith('@chat.facebook.com') or \
                    info['source'].endswith('@chat.facebook.com'):
                info['service'] = 'facebook'

        info['time'] = parse(info['time'], tzinfos=getoffset)
        if not info['time'].tzname():
            newtzinfo = conversation.time.tzinfo
            info['time'] = info['time'].replace(tzinfo=newtzinfo)

        return info

    def _parse_line(self, line, conversation, base_time, senders_by_color):
        """Return (cons, attrs)"""
        attrs = dict(alias=None, time=None, sender=conversation.source,
                     type=None, html=None, color=None)
        soup = BeautifulSoup(line, 'lxml')
        if len(soup) == 0:
            print_d("Skipping line %s" % line)
            return None, None

        fonttag = soup.font

        # unrepresentable entry dump
        if not fonttag:
            cons, attrs = Entry.from_dump(soup.text)
            if 'color' not in attrs:
                attrs['color'] = None
            return cons, attrs

        attrs['color'] = fonttag.get('color')
        if attrs['color'] == self.ALTERNATE_COLOR:
            attrs['alternate'] = True

        if fonttag.has_attr('size'):
            cons = Status
            timestr = fonttag.text
        elif attrs['color'] == self.ERROR_COLOR:
            cons = Status
            timestr = fonttag.font.text
            attrs['type'] = Status.ERROR
        elif attrs['color']:
            cons = Message
            timestr = fonttag.font.text
            attrs['sender'] = senders_by_color.get(attrs['color'])
            attrs['alias'] = fonttag.b.text[:-1] # trailing ':'
            m = self.AUTOREPLY_REGEX.match(attrs['alias'])
            if m:
                attrs['alias'] = m.group('alias')
                attrs['auto'] = True
        else:
            raise ParseError("unexpected <font> found at line '%s'" % line)
        # normal -> (10:10:10)
        # delayed -> (2010-12-12 10:10:10)
        timestr = timestr[1:-1]
        parsed = parse(timestr, default=datetime.datetime.min, ignoretz=True)
        if parsed.date() == datetime.date.min:
            attrs['delayed'] = False
            attrs['time'] = parsed.replace(day=base_time.day,
                                           month=base_time.month,
                                           year=base_time.year,
                                           tzinfo=base_time.tzinfo)
        else:
            attrs['delayed'] = True
            attrs['time'] = parsed.replace(tzinfo=base_time.tzinfo)

        # isuser
        color = attrs['color']
        if color == self.SOURCE_COLOR:
            attrs['isuser'] = True
        elif color == self.DESTINATION_COLOR:
            attrs['isuser'] = False
        elif attrs.get('sender') == conversation.source:
            attrs['isuser'] = True

        # message
        if attrs['color'] and attrs['color'] != self.ERROR_COLOR:
            html = [e for e in fonttag.next_siblings]
        # status: html in <b> tag
        else:
            html = list(soup.b.children)

        if html and isinstance(html[0], NavigableString):
            s = html[0].lstrip()
            if not s:
                del html[0]
            else:
                html[0] = NavigableString(s)
        attrs['html'] = html

        if cons == Status:
            self._parse_status(soup, attrs, conversation,
                               attrs['color'] == self.ERROR_COLOR)
            if not attrs['type']:
                print_d("No type found for status '%s': using system"
                        % line)
                attrs['type'] = Status.SYSTEM

        return (cons, attrs)

    def _parse_status(self, soup, info, conversation, error=False):
        # already converted using another module
        comment = soup.html.previous
        if isinstance(comment, Comment):
            info['type'], info['system'], info['sender'] = \
                comment.split("|", 2)
            info['type'] = int(info['type'])
            if info['type'] in Status.USER_TYPES:
                l = info['html'][0].split(': ', 1)
                if len(l) > 1:
                    info['msg_html'] = l[1]
                del info['html']
            return

        s = ''.join([x.text if isinstance(x, Tag) else x.string
                     for x in info['html']])
        info['sender'] = conversation.source \
            if s.startswith(_("You")) else None
        if error:
            info['type'] = Status.ERROR
        else:
            for pattern, t in iter(self.STATUS_TYPEMAP.items()):
                i = util.parse_string(s, pattern)
                if i is not None:
                    for k, v in iter(i.items()):
                        info[k] = v
                    info['type'] = t

    def _parse_title(self, line, conversation):
        soup = BeautifulSoup(line)
        info = util.parse_string(soup.title.text, self.TITLE_PATTERN)
        self._parse_info(info, conversation)

        header_comment = soup.html.previous
        if isinstance(header_comment, Comment):
            original_parser_name = header_comment.split('/')[1]
        else:
            original_parser_name = self.type

        return info, original_parser_name

    def write(self, path, conversations):
        if len(conversations) != 1:
            raise ParseError(
                ("'%s' only supports one conversation "
                 "per file:\n  '%s' has %i") % (self.type, path,
                                                len(conversations))
                )

        conversation = conversations[0]
        soup = BeautifulSoup(features='html')
        html = soup.new_tag(name='html')
        head = soup.new_tag(name='head')
        body = soup.new_tag(name='body')
        attrs = {'http-equiv': 'content-type',
                 'content': 'text/html; charset=UTF-8'}
        meta = soup.new_tag(name='meta', **attrs)
        h3 = soup.new_tag(name='h3')
        title = soup.new_tag(name='title')

        titlestr = self.fill_pattern(conversation, self.TITLE_PATTERN,
                                     self.TIME_FMT_TITLE)

        soup.append(Comment(const.HEADER_COMMENT %
                            conversation.original_parser_name))
        soup.append(html)

        html.append(head)
        html.append(body)

        head.append(meta)
        head.append(title)

        body.append(h3)
        body.append('\n')

        h3.append(titlestr)
        title.append(titlestr)

        for entry in conversation.entries:
            timefmt = self.TIME_FMT_CONVERSATION_WITH_DATE if entry.delayed \
                else self.TIME_FMT_CONVERSATION
            if self._append_html(entry, body, conversation, soup, timefmt):
                body.append(soup.new_tag(name='br'))
                body.append('\n')

        # newline at end
        soup.append('\n')
        with codecs.open(path, 'wb', 'utf-8') as fh:
            fh.write(soup.decode())

    def _append_html(self, entry, body, conversation, soup, timefmt):
        if isinstance(entry, Message):
            if entry.alternate:
                color = self.ALTERNATE_COLOR
            elif entry.isuser:
                color = self.SOURCE_COLOR
            else:
                color = self.DESTINATION_COLOR
            f = soup.new_tag(name='font', color=color)
            timetag = soup.new_tag(name='font', size=2)
            timetag.append(entry.time.strftime(timefmt))
            nametag = soup.new_tag(name='b')
            nametag.append('%s%s:' % (entry.alias if entry.alias
                                      else entry.sender,
                                      '&lt;AUTO-REPLY&gt;' if entry.auto
                                      else ''))
            f.append(timetag)
            f.append(' ')
            f.append(nametag)

            body.append(f)
            body.append(' ')
            for e in entry.html:
                body.append(e)
        elif isinstance(entry, Status):
            # error:
            # <font color="#FF0000"><font size="2">(_t)</font><b> m</b></font>
            # normal:
            # <font size="2">(_t)</font><b> _m</b>
            msgtag = soup.new_tag(name='b')
            timetag = soup.new_tag(name='font', size=2)

            timetag.append(entry.time.strftime(timefmt))

            # append comment indicating this Status was not parsed by us
            if conversation.original_parser_name != self.type:
                text = "%s|%s|%s" % (entry.type,
                                     '1' if entry.system else '',
                                     entry.sender)
                body.append(Comment(text))

            msgtag.append(' ')
            for e in entry.html:
                msgtag.append(e)
            if entry.type == Status.ERROR:
                color = self.ERROR_COLOR
                f = soup.new_tag(name='font', color=color)
                f.append(timetag)
                f.append(msgtag)
                body.append(f)
            else:
                body.append(timetag)
                body.append(msgtag)
        else:
            body.append(Comment(entry.dump()))
            body.append('\n')
            return False
        return True

formats = [PidginHtml]
