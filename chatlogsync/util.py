# Copyright 2013 Evan Vitero

# This file is part of chatlogsync.

# chatlogsync is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# chatlogsync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with chatlogsync.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import absolute_import

import os
import re
import datetime
from os.path import join, isfile, sep

from bs4.element import Comment
from PIL import Image

from chatlogsync import const
from chatlogsync.errors import ParseError

def get_image_size(fullpath):
    """Return (width, height)"""
    with open(fullpath, 'rb') as fp:
        im = Image.open(fp)
    return im.size

def write_comment(fh, comment_text):
    if not const.NO_COMMENTS:
        fh.write(Comment(comment_text).output_ready())

def parse_string(string, pattern, path=False):
    s = re.split('{(.*?)}', pattern)
    counts = {}
    for i in range(0, len(s), 2):
        s[i] = re.escape(s[i])
    for i in range(1, len(s), 2):
        item = s[i].split(' ', 1)
        key = item[0]
        if len(item) == 1:
            c = '[^'+re.escape(sep)+']' if path else '.'
            fmt = "(?P<%s%i>{}*?)".format(c)
        else:
            escaped_item = re.escape(item[1])
            fmt = "(?P<%s%i>{})?".format(escaped_item)

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
