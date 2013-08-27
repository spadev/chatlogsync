from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import re
import datetime

class ChatlogFormat(object):
    type = 'unknown format'
    SERVICE_MAP = {}
    PAM_ECIVRES = {}
    FILE_PATTERN = ''
    TIME_FMT_FILE = ''

    def __init__(self):
        if not self.PAM_ECIVRES:
            self.PAM_ECIVRES = {v: k for (k, v) in
                                iter(self.SERVICE_MAP.items())}

    def get_path(self, conversation):
        if (not self.FILE_PATTERN or not self.SERVICE_MAP
            or not self.TIME_FMT_FILE):
            raise NotImplementedError

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
        raise NotImplementedError

    def write(self, path, conversations):
        raise NotImplementedError
