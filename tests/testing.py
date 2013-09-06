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
CHAR = '#'
REPS = 10

def print_(*args, **kwargs):
    file = kwargs['file'] = kwargs.get('file', sys.stdout)
    flush = kwargs.pop('flush', True)
    print(*args, **kwargs)
    if flush:
        file.flush()

def test_one(source_dir, source_ext, source_format, dest_ext, dest_format,
             expected_dir=None, stop=True):
    sys.stdout.flush()
    titlestr = (CHAR*REPS +' %s -> %s') % (source_format, dest_format)
    print_(titlestr)
    sys.stdout.flush()

    dest_basename = '%s-to-%s' % (source_format, dest_format)
    dest_dir = join(dirname(__file__), dest_basename)

    if not expected_dir:
        expected_dir = join(dirname(__file__), dest_basename+'.expected')

    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    args = [CHATLOGSYNC, source_dir, dest_dir, '-f', dest_format]
    n = subprocess.call(args)
    if n > 0:
        print_('chatlogsync failed', file=sys.stderr)
        return n

    if dest_ext == 'xml':
        diffprog = XMLDIFF
    elif dest_ext == 'html':
        diffprog = HTMLDIFF
    else:
        print_("unknown extension %r" % dest_ext)

    args = [diffprog, dest_dir, expected_dir]
    if stop:
        args.append('-s')

    if dest_format == 'pidgin':
        args.append('-p')
    elif dest_format == 'adium':
        args.append('-a')

    n += subprocess.call(args)

    if n == 0 and not stop:
        print_(titlestr +': %i failures \n' % n)
        n += test_one(dest_dir, dest_ext, dest_basename, source_ext,
                      source_format, expected_dir=source_dir, stop=True)
    else:
        print_(titlestr +': %i failures\n' % n)

    if exists(dest_dir):
        shutil.rmtree(dest_dir)

    return n

def test_all(source_dir, source_ext, source_format, dest_ef_pairs):
    n = 0
    for dest_ext, dest_format in dest_ef_pairs:
        n += test_one(source_dir, source_ext, source_format,
                      dest_ext, dest_format, stop=False)

    return n
