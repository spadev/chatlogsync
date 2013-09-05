#!/usr/bin/python
from __future__ import print_function

import sys
import shutil
import subprocess
import traceback
from os.path import join, dirname, exists

CHATLOGSYNC = join(dirname(__file__), "..", 'chatlogsync.py')
HTMLDIFF = join(dirname(__file__), "..", 'tools', 'htmldiff.py')
XMLDIFF = join(dirname(__file__), "..", 'tools', 'xmldiff.py')

def test_expected(source_dir, format_from, format_to, extension_from,
                  extension_to):
    print('testing %s to %s' % (format_from, format_to))

    dest_dir = join(dirname(__file__),
                    '%s-to-%s' % (format_from, format_to))
    expected_dir = join(dirname(__file__),
                        '%s-to-%s.expected' % (format_from, format_to))
    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    args = [CHATLOGSYNC, source_dir, dest_dir, '-f', format_to]
    n = subprocess.call(args)
    if n > 0:
        print('chatlogsync failed', file=sys.stderr)
        return n

    if extension_to == 'xml':
        diffprog = XMLDIFF
    elif extension_to == 'html':
        diffprog = HTMLDIFF
    else:
        print("unknown extension %r" % extension_to)

    args = [diffprog, dest_dir, expected_dir]
    if format_to == 'pidgin':
        args.append('-p')

    n += subprocess.call(args)

    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    return n

def test_all(format_from, extension_from, source_dir, to_test):
    n = 0
    for format_to, extension_to in to_test:
        n += test_expected(source_dir, format_from, format_to, extension_from,
                           extension_to)

    return n

def main(func, *args, **kwargs):
    options = None
    try:
        exitcode = 0
        exitcode = func(*args)
    except KeyboardInterrupt:
        exitcode = 1
        print("***aborted***", file=sys.stderr)
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(exitcode)
