#!/usr/bin/python
from __future__ import print_function

import shutil
import subprocess
import sys
import traceback
from os.path import join, dirname, exists

CHATLOGSYNC = join(dirname(__file__), "..", 'chatlogsync.py')
HTMLDIFF = join(dirname(__file__), "..", 'tools', 'htmldiff.py')
XMLDIFF = join(dirname(__file__), "..", 'tools', 'xmldiff.py')

def print_(*args, **kwargs):
    file = kwargs['file'] = kwargs.get('file', sys.stdout)
    flush = kwargs.pop('flush', True)
    print(*args, **kwargs)
    if flush:
        file.flush()

def test_one(source_dir, format_from, format_to, extension_from,
             extension_to, expected_dir=None, stop=True):
    sys.stdout.flush()
    print_('=====testing %s to %s=====' % (format_from, format_to))
    sys.stdout.flush()

    dest_basename = '%s-to-%s' % (format_from, format_to)
    dest_dir = join(dirname(__file__), dest_basename)

    if not expected_dir:
        expected_dir = join(dirname(__file__), dest_basename+'.expected')

    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    args = [CHATLOGSYNC, source_dir, dest_dir, '-f', format_to]
    n = subprocess.call(args)
    if n > 0:
        print_('chatlogsync failed', file=sys.stderr)
        return n

    if extension_to == 'xml':
        diffprog = XMLDIFF
    elif extension_to == 'html':
        diffprog = HTMLDIFF
    else:
        print_("unknown extension %r" % extension_to)

    args = [diffprog, dest_dir, expected_dir]
    if stop:
        args.append('-s')

    if format_to == 'pidgin':
        args.append('-p')
    elif format_to == 'adium':
        args.append('-a')

    n += subprocess.call(args)

    if n == 0 and not stop:
        print_('=====%i failures=====\n' % n)
        n += test_one(dest_dir, dest_basename, format_from, extension_to,
                      extension_from, expected_dir=source_dir, stop=True)
    else:
        print_('=====%i failures=====' % n)

    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    return n

def test_all(format_from, extension_from, source_dir, to_test):
    n = 0
    for format_to, extension_to in to_test:
        n += test_one(source_dir, format_from, format_to, extension_from,
                      extension_to, stop=False)

    return n

def main(func, *args, **kwargs):
    options = None
    try:
        exitcode = 0
        exitcode = func(*args)
    except KeyboardInterrupt:
        exitcode = 1
        print_("***aborted***", file=sys.stderr)
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(exitcode)
