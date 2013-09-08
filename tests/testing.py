#!/usr/bin/env python
from __future__ import print_function

import shutil
import subprocess
import sys
import traceback
import re
import os
import datetime
import locale
from os.path import join, dirname, exists

from dateutil.parser import parse

from chatlogsync import timezones
from chatlogsync.timezones import getoffset
from chatlogsync.formats import pidgin

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

def convert_pidgin_times(path, revert=False):
    parser = pidgin.PidginHtml()

    shortfmt = "%H:%M:%S" if revert else "%X"
    longfmt = "%Y-%m-%d %H:%M:%S" if revert else "%x %X"
    title_fmt = "%a %d %b %Y %H:%M:%S %Z" if revert else "%c"

    with open(path) as fh:
        lines = fh.read().strip().split('\n')

    newlines = []

    conversation_time = parser.parse_path(path)[0].time
    pat = '(.*<title>.*? at )(.*?)( on .*<h3>.* at )(.*?)( on .*)'
    m = re.search(pat, lines.pop(0))
    before, timestr1, middle, timestr2, after = m.groups()
    parsed_dt = parse(timestr1, default=conversation_time)
    new_timestr = parsed_dt.strftime(title_fmt)
    newlines.append("%s%s%s%s%s" % (before, new_timestr, middle,
                                    new_timestr, after))
    for line in lines:
        m = re.search('(.*?<font size="2">\()(.*?)(\)</font>.*)', line)
        if m:
            before, timestr, after = m.groups()
            parsed_dt = parse(timestr, default=datetime.datetime.min)
            if parsed_dt.year == datetime.datetime.min.year:
                fmt = shortfmt
                parsed_dt = parsed_dt.replace(year=1900)
            else:
                fmt = longfmt
            new_timestr = parsed_dt.strftime(fmt)
            newlines.append("%s%s%s" % (before, new_timestr, after))
        else:
            newlines.append(line)

    with open(path+'.tmp', 'w') as fh:
        fh.write('\n'.join(newlines))
        fh.write('\n')
    os.rename(path+'.tmp', path)

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

    sfunc, ext = APPLY_FUNCS.get(source_format, (None, None))
    dfunc, ext = APPLY_FUNCS.get(dest_format, (None, None))
    if sfunc:
        apply_function(source_dir, ext, sfunc)
    if dfunc:
        apply_function(expected_dir, ext, dfunc)

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

    if sfunc:
        apply_function(source_dir, ext, sfunc, kwargs={'revert':True})
    if dfunc:
        apply_function(expected_dir, ext, dfunc, kwargs={'revert':True})

    return n

def apply_function(directory, ext, func, kwargs={}):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if ext == os.path.splitext(file)[1]:
                func(join(root, file), **kwargs)

def test_all(source_dir, source_ext, source_format, dest_ef_pairs):
    locale.setlocale(locale.LC_ALL, '')
    timezones.init()
    n = 0
    for dest_ext, dest_format in dest_ef_pairs:
        n += test_one(source_dir, source_ext, source_format,
                      dest_ext, dest_format, stop=False)

    return n

APPLY_FUNCS = {'pidgin-html': (convert_pidgin_times, '.html')}
