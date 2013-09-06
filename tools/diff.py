from __future__ import print_function
from __future__ import unicode_literals

import codecs
import fnmatch
import os
import re
import sys
from os.path import join, relpath, isfile, isdir, dirname, commonprefix
from difflib import context_diff
from argparse import ArgumentParser, ArgumentTypeError

from bs4 import BeautifulSoup
from bs4.element import Comment

DIVIDER = "\n"+"="*80+'\n'
def isdirectory(value):
    if not isdir(value):
        raise ArgumentTypeError("'%s' is not a file or directory" % value)

    return value

def isnotfile(value):
    if isfile(value):
        raise ArgumentTypeError("'%s' is not a file" % value)

    return value

def gather_files(pattern, source, destination):
    paths = []
    if isfile(source) and isfile(destination):
        paths.append((source, destination))

    for root, tops, files in os.walk(source):
        for f in fnmatch.filter(files, pattern):
            p1 = join(root, f)
            p2 = join(destination, relpath(p1, start=source))
            if not isfile(p2):
                p2 = None
            paths.append((p1, p2))

    return paths

def strip_comments(soup):
    comments = soup.find_all(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]

    return soup

def strip_first_comment(soup):
    first_comment = soup.find(text=lambda text:isinstance(text, Comment))
    if first_comment:
        first_comment.extract()

    return soup

def normalize_pidgin(soup):
    for name in ('h3', 'title'):
        tag = soup.find(name)
        text = re.sub('/.* ', ' ', tag.text)
        list(tag.children)[0].replaceWith(text)

    return soup

def normalize_adium(soup):
    chat = soup.chat
    del chat['buildid']
    del chat['adiumversion']

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
    parser.add_argument("-s", "--strip-first-comment",
                        help="do not consider first comment",
                        action='store_true',
                        default=False,
                        )
    return parser

def check_images(soup, path, lines):
    basedir = dirname(path)
    n = 0
    for img_path in [x.get('src') for x in soup.find_all('img')]:
        p = join(basedir, img_path)
        if not isfile(p):
            lines.append('expected image at %r' % p)
            n += 1

    return n

def print_(*args, **kwargs):
    file = kwargs['file'] = kwargs.get('file', sys.stdout)
    flush = kwargs.pop('flush', True)
    print(*args, **kwargs)
    if flush:
        file.flush()

def diff(file1, file2, options, images=True):
    n = 0
    if not file2:
        cp = commonprefix([options.source, options.destination])
        path = file1.replace(cp, '')
        print_("%s only exists in %s" % (path, options.source))
        print_(DIVIDER)
        return 1

    with codecs.open(file1, encoding='utf-8') as f:
        soup1 = BeautifulSoup(f)
    with codecs.open(file2, encoding='utf-8') as f:
        soup2 = BeautifulSoup(f)

    if options.strip_first_comment:
        soup1 = strip_first_comment(soup1)
        soup2 = strip_first_comment(soup2)
    if options.ignore_comments:
        soup1 = strip_comments(soup1)
        soup2 = strip_comments(soup2)
    if 'pidgin' in options and options.pidgin:
        soup1 = normalize_pidgin(soup1)
        soup2 = normalize_pidgin(soup2)
    if 'adium' in options and options.adium:
        soup1 = normalize_adium(soup1)
        soup2 = normalize_adium(soup2)

    lines = ['%s %s\n' % (file1, file2)]
    if images:
        n += check_images(soup1, file1, lines)
        n += check_images(soup2, file2, lines)

    html1 = soup1.prettify().split('\n')
    html2 = soup2.prettify().split('\n')

    for l in context_diff(html1, html2):
        n += 1
        lines.append(l)

    if n:
        lines.append(DIVIDER)
        n = 1
        s = '\n'.join(lines)
        if not isinstance(s, str):
            s = s.encode('utf-8')
        print_(s)

    return n
