#!/usr/bin/python
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
