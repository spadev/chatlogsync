from __future__ import unicode_literals
from __future__ import absolute_import

import re
import datetime

class ChatlogFormat(object):
    type = 'unknown format'
    SERVICE_MAP = {}
    PAM_ECIVRES = {}
    STATUS_TYPEMAP = {}
    PAMEPYT_SUTATS = {}
    EVENT_TYPEMAP = {}
    PAMEPYT_TNEVE = {}
    FILE_PATTERN = ''
    TIME_FMT_FILE = ''

    def __init__(self):
        if not self.PAM_ECIVRES:
            self.PAM_ECIVRES = {v: k for (k, v) in
                                iter(self.SERVICE_MAP.items())}
        if not self.PAMEPYT_SUTATS:
            self.PAMEPYT_SUTATS = {v: k for (k, v) in
                                   iter(self.STATUS_TYPEMAP.items())}
        if not self.PAMEPYT_TNEVE:
            self.PAMEPYT_TNEVE = {v: k for (k, v) in
                                  iter(self.EVENT_TYPEMAP.items())}

    def get_path(self, conversation):
        if not self.FILE_PATTERN:
            raise NotImplementedError

        return self.fill_pattern(conversation, self.FILE_PATTERN[1:],
                                 self.TIME_FMT_FILE)

    def fill_pattern(self, conversation, pattern, time_fmt):
        if (not self.SERVICE_MAP):
            raise NotImplementedError

        s = re.split('{(.*?)}', pattern)
        for i in range(1, len(s), 2):
            item = s[i].split(' ', 1)
            attr = item[0]
            value = getattr(conversation, attr)
            if len(item) == 2:
                value = item[1] if item else ''
            if attr == 'service':
                value = self.PAM_ECIVRES[value]
            elif isinstance(value, datetime.datetime):
                value = value.strftime(time_fmt)
            s[i] = value

        return ''.join(s)

    def parse_path(self, path):
        """Parse path and return list of conversations without
        entries filled in."""
        raise NotImplementedError

    def parse_conversation(self, conversation):
        """Fill in entries of conversation.
        Return modifeid conversation."""
        raise NotImplementedError

    def write(self, path, conversations):
        raise NotImplementedError
