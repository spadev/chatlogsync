from __future__ import unicode_literals
from __future__ import absolute_import

import os
import re
import datetime
from os.path import join, isfile
from bs4.element import Comment

from chatlogsync import const
from chatlogsync.errors import ParseError

def write_comment(fh, comment_text):
    if not const.NO_COMMENTS:
        fh.write(Comment(comment_text).output_ready())

def parse_string(string, pattern):
    s = re.split('{(.*?)}', pattern)
    counts = {}
    for i in range(0, len(s), 2):
        s[i] = re.escape(s[i])
    for i in range(1, len(s), 2):
        item = s[i].split(' ', 1)
        key = item[0]
        fmt = "(?P<%s%i>.*?)" if len(item) == 1 else \
            "(?P<%s%i>{})?".format(item[1])

        if key not in counts:
            counts[key] = 0
        counts[key] += 1

        s[i] = fmt % (key, counts[key])
    regex_pattern = ''.join(s)
    s = re.search(regex_pattern, string)
    if not s:
        return None

    results = {}
    for key, value in iter(s.groupdict().items()):
        k = re.sub('\d', '', key)
        if k in results and results[k] != value:
            raise ParseError("Problem parsing string '%s'" % string)
        results[k] = value

    return results

def get_paths(paths):
    newpaths = set()
    for path in paths:
        if isfile(path):
            newpaths.add(path)
        else:
            for root, dirs, files in os.walk(path):
                for f in files:
                    p = join(root, f)
                    newpaths.add(p)

    return sorted(newpaths)
