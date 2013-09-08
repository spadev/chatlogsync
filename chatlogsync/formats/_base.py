from __future__ import unicode_literals
from __future__ import absolute_import

import re
import datetime
import shutil
from os.path import dirname, join, realpath

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
    TRANSFORMS = {}
    UNTRANSFORMS = {}
    IMAGE_DIRECTORY = ''

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

    def copy_images(self, path, conversation):
        if not self.IMAGE_DIRECTORY:
            raise NotImplementedError

        dstdir = join(dirname(path), self.IMAGE_DIRECTORY)
        for img_relpath, srcpath in conversation.images_full:
            dstpath = join(dstdir, img_relpath)
            if srcpath != realpath(dstpath):
                shutil.copy(srcpath, dstpath)

    def get_path(self, conversation):
        if not self.FILE_PATTERN:
            raise NotImplementedError

        return self.fill_pattern(conversation, self.FILE_PATTERN,
                                 self.TIME_FMT_FILE, untransform=True)

    def fill_pattern(self, conversation, pattern, time_fmt, untransform=False):
        if (not self.SERVICE_MAP):
            raise NotImplementedError

        s = re.split('{(.*?)}', pattern)
        for i in range(1, len(s), 2):
            item = s[i].split(' ', 1)
            attr = item[0]
            value = getattr(conversation, attr)
            if untransform and attr in self.UNTRANSFORMS:
                value = self.UNTRANSFORMS[attr](value, conversation)

            if len(item) == 2:
                value = item[1].replace(attr, str(value)) if value else ''

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
