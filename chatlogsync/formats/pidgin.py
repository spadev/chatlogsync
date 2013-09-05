from __future__ import unicode_literals
from __future__ import absolute_import

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
    IMAGE_DIRECTORY = '.'

    SERVICE_MAP = {'jabber': 'jabber',
                   'aim': 'aim',
                   }
    PAM_ECIVRES = {'gtalk': 'jabber',
                   'jabber': 'jabber',
                   'facebook': 'jabber',
                   'aim': 'aim',
                   }
    FILE_PATTERN = ('/logs/{service}/{source}/{destination}{isgroup .chat}/'
                    '{time}.html')
    TIME_FMT_FILE = '%Y-%m-%d.%H%M%S%z%Z'
    STRPTIME_FMT_FILE = '%Y-%m-%d.%H%M%S'
    TITLE_PATTERN = _("Conversation with {destination} "
                      "at {time} on {source} ({service})")

    SOURCE_COLOR = "#16569E"
    DESTINATION_COLOR = "#A82F2F"
    ERROR_COLOR = "#FF0000"
    ALTERNATE_COLOR = "#062585"

    AUTOREPLY_HTML = '&lt;AUTO-REPLY&gt;'

    MESSAGE_LINE_FMT = ('<font color="%s"><font size="2">%s</font>'
                        ' <b>%s%s:</b></font> ')
    MESSAGE_LINE_END = '<br/>'
    MESSAGE_LINE_RE = \
        re.compile(MESSAGE_LINE_FMT % ('(?P<color>.*?)',
                                       '\((?P<time>.*?)\)',
                                       '(?P<name>.*?)',
                                       '(?P<auto>%s)?' % AUTOREPLY_HTML)
                   + '(?P<html>.*)' + MESSAGE_LINE_END, re.DOTALL)

    STATUS_LINE_FMT = '<font size="2">%s</font><b> '
    STATUS_LINE_END = '</b><br/>'
    STATUS_LINE_RE = \
        re.compile((STATUS_LINE_FMT % '\((?P<time>.*?)\)')
                   + '(?P<html>.*)' + STATUS_LINE_END, re.DOTALL)

    ERROR_LINE_FMT = ('<font color="'+ERROR_COLOR+'"><font size="2">%s</font>'
                      '<b> ')
    ERROR_LINE_END = '</b></font><br/>'
    ERROR_LINE_RE = \
        re.compile((ERROR_LINE_FMT % '\((?P<time>.*?)\)')
                   + '(?P<html>.*)' + ERROR_LINE_END, re.DOTALL)

    TITLE_LINE_FMT = ('<html><head><meta http-equiv="content-type" '
                      'content="text/html; charset=UTF-8"><title>%s</title>'
                      '</head><body><h3>%s</h3>')
    TITLE_LINE_RE = \
        re.compile((TITLE_LINE_FMT % ('.*?', '(?P<titlestr>.*?)')))

    COMMENT_RE = re.compile('^%s(?P<commentstr>.*?)%s' % (Comment.PREFIX,
                                                          Comment.SUFFIX))
    SOURCE_RE = re.compile('/[^/]*$')

    TIME_FMT_CONVERSATION = "(%X)"
    TIME_FMT_CONVERSATION_WITH_DATE = "(%x %X)"

    STATUS_TYPEMAP = {_("{alias} has gone away."): Status.AWAY,
                      _("{alias} is no longer {type}."): Status.AVAILABLE,
                      _("{alias} has signed off."): Status.OFFLINE,
                      _("{alias} has signed on."): Status.ONLINE,
                      _("{alias} has become idle."): Status.IDLE,
                      _("{alias} is mobile."): Status.MOBILE,
                      }

    CHAT_STATUS_TYPEMAP = {_("{alias} entered the room."): Status.SYSTEM,
                           _("{alias} left the room."): Status.SYSTEM,
                           }

    def __init__(self, *args):
        super(PidginHtml, self).__init__(*args)
        self.TIME_FMT_TITLE = timezones.locale_datetime_fmt

    def parse_path(self, path):
        info = util.parse_string(path, self.FILE_PATTERN)
        if not info:
            return None

        self._parse_info(info)
        if info['destination'] == '.system':
            print_d('Ignoring system log %s' % path)
            return None

        conversation = Conversation(self, path, info['source'],
                                    info['destination'],
                                    info['service'], info['time'],
                                    [], [], info['isgroup'])

        return [conversation]

    def _get_line_data(self, line):
        """Return (line, comment)"""
        data = self.COMMENT_RE.split(line)
        if len(data) == 3:
            comment = data[1]
            l = data[2]
        else:
            l = data[0]
            comment = ''

        return l, comment

    def parse_conversation(self, conversation):
        with codecs.open(conversation.path, encoding='utf-8') as f:
            data = f.read().strip()
            lines = data.split('\n')
            if not lines[-1]:
                del lines[-1]
            if lines[-1].endswith('</html>'):
                del lines[-1]
        title_line, comment = self._get_line_data((lines.pop(0)))
        info, conversation.original_parser_name = \
            self._parse_title(title_line, comment, conversation)

        for k, v in iter(info.items()):
            cv = getattr(conversation, k)
            if v != cv:
                raise ParseError("mismatch between filename and header "
                                 "%s: '%s' != '%s'" % (k, v, cv))

        prev_time = conversation.time
        senders_by_alias = {}
        ignore_aliases = set()
        attrs_list = []
        i = 0

        while i < len(lines):
            line = lines[i]
            while True:
                if line.endswith('<br/>') or line.startswith('<!--'):
                    break
                line += '\n'+lines[i+1]
                i += 1
            i += 1

            try:
                cons, attrs = self._parse_line(line, conversation, prev_time)
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
            if s and a and a not in ignore_aliases:
                s2 = senders_by_alias.get(a, s)
                if s != s2:
                    print_d('Multiple senders found for %s (%s)'
                            % (a, '%s, %s' % (s, s2)))
                    ignore_aliases.add(a)
                    del senders_by_alias[a]
                senders_by_alias[a] = s

            attrs_list.append((cons, attrs))

        conversation.entries, conversation.images = \
            self._get_entries_and_images(conversation, senders_by_alias,
                                         attrs_list)

        return conversation

    def _get_entries_and_images(self, conversation, senders_by_alias,
                                attrs_list):
        aliases_by_sender = {v: k for k, v in iter(senders_by_alias.items())}
        entries = []
        images = []
        for cons, attrs in attrs_list:
            if not attrs['sender']:
                attrs['sender'] = senders_by_alias.get(attrs['alias'], '')
                if not attrs['sender']:
                    print_d('Unable to determine sender for attrs %r' % attrs)
                    # default to source
                    attrs['sender'] = conversation.source

            if not attrs['alias']:
                attrs['alias'] = aliases_by_sender.get(attrs['sender'], '')
            if attrs['sender'] == attrs['alias']:
                attrs['alias'] = ''
            if 'isuser' not in attrs:
                attrs['isuser'] = attrs['sender'] == conversation.source

            for h in (x for x in attrs['html'] if isinstance(x, Tag)):
                images.extend([x.get('src') for x in h.find_all('img')])
            entries.append(cons(**attrs))

        return entries, list(set(images))

    def _parse_info(self, info, conversation=None):
        info['service'] = self.SERVICE_MAP[info['service']]
        info['source'] = self.SOURCE_RE.sub('', info['source'])
        if info['service'] == 'jabber':
            if info['destination'].endswith('@gmail.com') or \
                    info['source'].endswith('@gmail.com'):
                info['service'] = 'gtalk'
            if info['destination'].endswith('@chat.facebook.com') or \
                    info['source'].endswith('@chat.facebook.com'):
                info['service'] = 'facebook'


        if not conversation: # parsing a path
            pos = info['time'].rfind('-')
            ts1, ts2 = info['time'][:pos], info['time'][pos:]
            t = datetime.datetime.strptime(ts1, self.STRPTIME_FMT_FILE)
            info['time'] = t.replace(tzinfo=getoffset(ts2[5:], ts2[:5]))
        else:
            info['time'] = parse(info['time'], tzinfos=getoffset)
            if not info['time'].tzname():
                newtzinfo = conversation.time.tzinfo
                info['time'] = info['time'].replace(tzinfo=newtzinfo)

        return info

    def _parse_line(self, line, conversation, base_time):
        """Return (cons, attrs)"""
        attrs = dict(alias=None, time=None, sender=None, type=None, html=None)
        line, comment = self._get_line_data(line)
        if not line and not comment:
            print_d("Skipping line %s" % line)
            return None, None

        # unrepresentable entry dump
        if not line:
            cons, attrs = Entry.from_dump(comment)
            return cons, attrs

        matched = False
        for regex in (self.MESSAGE_LINE_RE, self.STATUS_LINE_RE,
                      self.ERROR_LINE_RE):
            m = regex.match(line)
            if m:
                matched = True
                break

        if not matched:
            raise ParseError("could not parse line '%s'" % line)
        # Message
        elif regex == self.MESSAGE_LINE_RE:
            color = m.group('color')
            attrs['alternate'] = color == self.ALTERNATE_COLOR
            timestr = m.group('time')
            attrs['alias'] = m.group('name')
            attrs['auto'] = m.group('auto')
            htmlstr = m.group('html')

            if color == self.SOURCE_COLOR:
                attrs['sender'] = conversation.source
                attrs['isuser'] = True
            elif conversation.isgroup: # groupchats don't use aliases
                attrs['sender'] = comment if comment else attrs['alias']
            elif color == self.DESTINATION_COLOR:
                attrs['sender'] = conversation.destination
                attrs['isuser'] = False

            cons = Message
        # Status
        elif regex == self.STATUS_LINE_RE:
            timestr = m.group('time')
            htmlstr = m.group('html')
            cons = Status
        # Error
        elif regex == self.ERROR_LINE_RE:
            timestr = m.group('time')
            htmlstr = m.group('html')
            attrs['color'] = self.ERROR_COLOR
            cons = Status
            attrs['type'] = Status.ERROR

        parsed = parse(timestr, default=datetime.datetime.min, ignoretz=True)
        # delayed has full date in timestamp
        if parsed.date() == datetime.date.min:
            attrs['delayed'] = False
            attrs['time'] = parsed.replace(day=base_time.day,
                                           month=base_time.month,
                                           year=base_time.year,
                                           tzinfo=base_time.tzinfo)
        else:
            attrs['delayed'] = True
            attrs['time'] = parsed.replace(tzinfo=base_time.tzinfo)


        attrs['html'] = \
            list(BeautifulSoup('<foo>%s</foo>' % htmlstr).foo.children)

        # parse status
        if cons == Status:
            self._parse_status(comment, attrs, conversation)
            if not attrs['type']:
                print_d("No type found for status '%s': using SYSTEM" % line)
                attrs['type'] = Status.SYSTEM

        return (cons, attrs)

    def _parse_status(self, comment, info, conversation):
        if comment:
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

        if not info['type']:
            typemap = dict(self.STATUS_TYPEMAP, **self.CHAT_STATUS_TYPEMAP) if \
                conversation.isgroup else self.STATUS_TYPEMAP
            for pattern, t in iter(typemap.items()):
                i = util.parse_string(s, pattern)
                if i is not None:
                    for k, v in iter(i.items()):
                        info[k] = v
                    # special case for 'is no longer <type>'
                    typestr = i.get('type')
                    if typestr:
                        info['type'] = \
                            Status.OPPOSITES[Status.PAM_EPYT[typestr]]
                    else:
                        info['type'] = t
                    break

    def _parse_title(self, line, comment, conversation):
        m = self.TITLE_LINE_RE.match(line)
        info = util.parse_string(m.group('titlestr'), self.TITLE_PATTERN)
        self._parse_info(info, conversation)
        original_parser_name = comment.split('/')[1] if comment else self.type

        return info, original_parser_name

    def write(self, path, conversations):
        if len(conversations) != 1:
            raise ParseError(
                ("'%s' only supports one conversation "
                 "per file:\n  '%s' has %i") % (self.type, path,
                                                len(conversations))
                )

        conversation = conversations[0]
        titlestr = self.fill_pattern(conversation, self.TITLE_PATTERN,
                                     self.TIME_FMT_TITLE)
        titlestr = NavigableString(titlestr).output_ready()
        fh = codecs.open(path, 'wb', 'utf-8')
        util.write_comment(fh, const.HEADER_COMMENT %
                           conversation.original_parser_name)
        fh.write(self.TITLE_LINE_FMT % (titlestr, titlestr) + '\n')

        for entry in conversation.entries:
            timefmt = self.TIME_FMT_CONVERSATION_WITH_DATE if entry.delayed \
                else self.TIME_FMT_CONVERSATION
            self._write_entry(fh, entry, conversation, timefmt)
            fh.write('\n')

        # newline at end
        fh.write('</body></html>\n')
        fh.close()

        self.copy_images(path, conversation)

    def _write_entry(self, fh, entry, conversation, timefmt):
        timestr = entry.time.strftime(timefmt)
        if isinstance(entry, Message):
            if entry.alternate:
                color = self.ALTERNATE_COLOR
            elif entry.isuser:
                color = self.SOURCE_COLOR
            else:
                color = self.DESTINATION_COLOR
            name = entry.alias if entry.alias else entry.sender
            autoreply = self.AUTOREPLY_HTML if entry.auto else ''
            timestr = entry.time.strftime(timefmt)

            # write real sender in groupchat Message
            if conversation.isgroup and entry.alias:
                util.write_comment(fh, entry.sender)

            fh.write(self.MESSAGE_LINE_FMT % (color, timestr, name, autoreply))
            self._write_entry_html(fh, entry)
            fh.write(self.MESSAGE_LINE_END)
        elif isinstance(entry, Status):
            # append comment indicating this Status was not parsed by us
            if conversation.original_parser_name != self.type:
                text = "%s|%s|%s" % (entry.type,
                                     '1' if entry.system else '',
                                     entry.sender)
                util.write_comment(fh, text)

            if entry.type == Status.ERROR:
                fmt = self.ERROR_LINE_FMT
                end = self.ERROR_LINE_END
            else:
                fmt = self.STATUS_LINE_FMT
                end = self.STATUS_LINE_END

            fh.write(fmt % timestr)
            self._write_entry_html(fh, entry)
            fh.write(end)
        else:
            util.write_comment(fh, entry.dump())

    def _write_entry_html(self, fh, entry):
        for e in entry.html:
            if isinstance(e, Tag):
                fh.write(e.decode())
            else:
                fh.write(e.output_ready())

formats = [PidginHtml]
