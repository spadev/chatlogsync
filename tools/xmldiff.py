#!/usr/bin/python
from __future__ import print_function

import sys
import traceback

import diff

PROG='xmldiff'
DESCRIPTION='Recursively diff XML files'

def parse_args():
    parser = diff.get_argument_parser(PROG, DESCRIPTION)
    parser.add_argument("-a", "--adium",
                        help="normalize adium chat attributes",
                        action='store_true',
                        default=False,
                        )
    options = parser.parse_args()

    return options

def xmldiff(options):
    n = 0
    for file1, file2 in diff.gather_files('*.xml'):
        n  += diff.diff(file1, file2, ignore_comments=options.ignore_comments,
                        adium=True)

    return n

if __name__ == "__main__":
    options = None
    try:
        exitcode = 0
        options = parse_args()
        exitcode = xmldiff(options)
    except KeyboardInterrupt:
        exitcode = 1
        print("***aborted***", file=sys.stderr)
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(exitcode)
