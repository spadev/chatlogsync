from __future__ import unicode_literals
from __future__ import absolute_import

import os
import re
import datetime
from os.path import join, isfile

from chatlogsync.errors import ParseError

def parse_string(string, pattern):
    s = re.split('<(.*?)>', pattern)
    keys = {}
    for i in range(0, len(s), 2):
        s[i] = re.escape(s[i])
    for i in range(1, len(s), 2):
        key = s[i]
        if key not in keys:
            keys[key] = 0
        keys[key] += 1
        s[i] = "(?P<%s%i>.*?)" % (s[i], keys[key])
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
