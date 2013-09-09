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

from __future__ import print_function

import sys
import traceback

import diff

PROG='htmldiff'
DESCRIPTION='Recursively diff HTML files'

def parse_args():
    parser = diff.get_argument_parser(PROG, DESCRIPTION)
    parser.add_argument("-p", "--pidgin",
                        help="normalize pidgin-html header",
                        action='store_true',
                        default=False,
                        )

    options = parser.parse_args()

    return options

def htmldiff(options):
    n = 0
    for file1, file2 in diff.gather_files('*.html', options.source,
                                          options.destination):
        n  += diff.diff(file1, file2, options)
    return n

if __name__ == "__main__":
    options = parse_args()
    exitcode = 0
    try:
        exitcode = htmldiff(options)
    except KeyboardInterrupt:
        exitcode = 1
        print("***aborted***", file=sys.stderr)
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(exitcode)
