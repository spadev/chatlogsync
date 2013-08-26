# Adapted from quodlibet/devices/__init__.py
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import traceback
import sys
from glob import glob
from os.path import dirname, basename, join

base = dirname(__file__)
self = basename(base)
parent = basename(dirname(base))
modules = [f[:-3] for f in glob(join(base, "[!_]*.py"))]
modules = ["chatlogconv.%s.%s" % (self, basename(m)) for m in modules]

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
        print(_("%r doesn't contain any chatlog formats.") %
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
