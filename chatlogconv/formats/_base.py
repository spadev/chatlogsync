from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

class ChatlogFormat(object):
    type = 'unknown format'

    def get_path(self, conversation):
        raise NotImplementedError

    def parse(self, path, messages=True):
        raise NotImplementedError

    def write(self, path, conversations):
        raise NotImplementedError
