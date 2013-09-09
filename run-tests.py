#!/usr/bin/env python

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

import os
import sys
import traceback
from os.path import join, dirname, isdir
from collections import defaultdict

from tests import testing

BASE_DIR = join(dirname(__file__), 'tests')

def get_extension(directory):
    extensions = defaultdict(int)
    for root, dirs, files in os.walk(directory):
        for file in files:
            extension = os.path.splitext(file)[1]
            if extension == '.tmp':
                os.unlink(join(root, file))
            if extension:
                extensions[extension] += 1
    return max(extensions.items(), key=lambda x: x[1])[0][1:]

def gather():
    sources = {} # sformat: (sdir, sext)
    destinations = {} # dformat: (ddir, dext)
    pairs = [] # (sformat, dformat)
    for name in next(os.walk(BASE_DIR))[1]:
        if name.startswith('.') or name.startswith('_'):
            continue

        directory = join(BASE_DIR, name)
        if name.endswith('.expected'):
            sformat, dformat = name.replace('.expected', '').split('-to-')
            if dformat not in destinations:
                destinations[dformat] = (directory, get_extension(directory))
            pairs.append((sformat, dformat))
        else:
            sources[name] = (directory, get_extension(directory))

    gathered = defaultdict(list) # (sdir, sext, sfmt): [(dext, dformat)]
    for sformat, dformat in pairs:
        if sformat not in sources or dformat not in destinations:
            continue
        sdir, sext = sources[sformat]
        ddir, dext = destinations[dformat]
        gathered[(sdir, sext, sformat)].append((dext, dformat))

    return [list(k)+list([v]) for k, v in iter(gathered.items())]

def main():
    n = 0
    for args in gather():
        n += testing.test_all(*args)

    return n

if __name__ == "__main__":
    try:
        exitcode = 0
        exitcode = main()
    except KeyboardInterrupt:
        exitcode = 1
        print_("***aborted***", file=sys.stderr)
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(exitcode)
