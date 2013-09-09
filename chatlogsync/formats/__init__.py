# Copyright 2013 spadev

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

# Adapted from quodlibet/devices/__init__.py
from __future__ import unicode_literals
from __future__ import absolute_import

import traceback
import sys
from glob import glob
from os.path import dirname, basename, join

base = dirname(__file__)
self = basename(base)
parent = basename(dirname(base))
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["chatlogsync.%s.%s" % (self, basename(m)) for m in modules]

all_formats = {}

for _name in modules:
    try:
        chatlog_format = __import__(_name, {}, {}, self)
    except Exception as err:
        traceback.print_exc()
        continue

    try:
        for d in chatlog_format.formats:
            all_formats[d.type] = d
    except AttributeError:
        print_w(_("%r doesn't contain any chatlog formats.") %
                chatlog_format.__name__, file=sys.stderr)

output_formats = []
input_formats = []
for k, v in sorted(all_formats.items()):
    input_formats.append(k)
    if 'write' in vars(v):
        output_formats.append(k)

def get(type):
    """Return a constructor for a chatlog format given the format type"""
    try:
        return all_formats[type]
    except ValueError:
        return None
