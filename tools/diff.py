from __future__ import print_function

import codecs
import fnmatch
import os
import re
import sys
from os.path import join, relpath, isfile, isdir
from difflib import context_diff
from argparse import ArgumentParser, ArgumentTypeError

from bs4 import BeautifulSoup
from bs4.element import Comment


DIVIDER = "\n"+"-"*80+'\n'
def isdirectory(value):
    if not isdir(value):
        raise ArgumentTypeError("'%s' is not a file or directory" % value)

    return value

def isnotfile(value):
    if isfile(value):
        raise ArgumentTypeError("'%s' is not a file" % value)

    return value

def gather_files(pattern):
    if len(sys.argv) < 3:
        print('need two topdirs', file=sys.stderr)
        sys.exit(1)

    top1, top2 = sys.argv[1:3]

    paths = []
    if isfile(top1) and isfile(top2):
        paths.append((top1, top2))
    for root, tops, files in os.walk(top1):
        for f in fnmatch.filter(files, pattern):
            p1 = join(root, f)
            p2 = join(top2, relpath(p1, start=top1))
            if not isfile(p2):
                p2 = None
            paths.append((p1, p2))

    return paths

def ignore_comments(soup):
    comments = soup.find_all(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]

    return soup

def normalize_pidgin_html(soup):
    for name in ('h3', 'title'):
        tag = soup.find(name)
        text = re.sub('/.* ', ' ', tag.text)
        list(tag.children)[0].replaceWith(text)

    return soup

def get_argument_parser(prog, description):
    parser = \
        ArgumentParser(description=description, prog=prog)
    parser.add_argument('source', type=isdirectory,
                        help='source directory')
    parser.add_argument('destination', type=isnotfile,
                        help='destination directory')
    parser.add_argument("-i", "--ignore-comments",
                        help="do not consider comments in when comparing",
                        action='store_true',
                        default=False,
                        )
    return parser

def diff(file1, file2, ignore_comments=False, pidgin=False):
    n = 0
    if not file2:
        print("%s only exists in source directory" % file1)
        print(DIVIDER)
        return 1

    with codecs.open(file1, encoding='utf-8') as f:
        soup1 = BeautifulSoup(f)
    with codecs.open(file2, encoding='utf-8') as f:
        soup2 = BeautifulSoup(f)

    if ignore_comments:
        soup1 = ignore_comments(soup1)
        soup2 = ignore_comments(soup2)
    if pidgin:
        soup1 = normalize_pidgin_html(soup1)
        soup2 = normalize_pidgin_html(soup2)

    html1 = soup1.prettify().split('\n')
    html2 = soup2.prettify().split('\n')

    lines = ['%s %s' % (file1, file2)]
    for l in context_diff(html1, html2):
        n += 1
        lines.append(l)

    if n:
        lines.append(DIVIDER)
        n = 1
        print('\n'.join(lines))

    return n
