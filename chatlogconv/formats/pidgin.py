from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import re
import codecs
from os.path import join, dirname, relpath, realpath
from datetime import datetime

from dateutil.parser import parse

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

    # def parse(self, path, messages=True):
    #     info = util.parse_path(path, self.FILE_PATTERN)
    #     if not info:
    #         return None

    #     timestr = info['time'].replace('.', ' ')
    #     timestr = re.sub('([+-]\d+)([^0-9- ]+)', r'\2\1', timestr)
    #     time = parse(timestr, tzinfos=getoffset)

    #     source = info['source']
    #     destination = info['destination']
    #     service = self.SERVICE_MAP[info['service']]
    #     if service == 'jabber' and (destination.endswith('@gmail.com') or
    #                                 source.endswith('@gmail.com')):
    #         service = 'gtalk'

    #     conversation = Conversation(path, source, destination,
    #                                 service, time)
    #     if not messages:
    #         return [conversation]

    #     # parse html


    # def write(self, path, conversations):
    #     if len(conversations) != 1:
    #         msg = '%s only supports one conversation per file:\n  %s has %i' % \
    #             (self.type, path, len(conversations))
    #         raise ParseError(msg)

    #     conversation = conversations[0]

formats = [PidginHtml]
