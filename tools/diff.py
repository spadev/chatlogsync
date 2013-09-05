from __future__ import print_function

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

def diff(file1, file2, dir1, dir2,
         ignore_comments=False, pidgin=False, adium=False, images=True):
    n = 0

    if not file2:
        cp = commonprefix([dir1, dir2])
        path = file1.replace(cp, '')
        print("%s only exists in %s" % (path, dir1))
        print(DIVIDER)
        return 1

    with codecs.open(file1, encoding='utf-8') as f:
        soup1 = BeautifulSoup(f)
    with codecs.open(file2, encoding='utf-8') as f:
        soup2 = BeautifulSoup(f)

    if ignore_comments:
        soup1 = strip_comments(soup1)
        soup2 = strip_comments(soup2)
    if pidgin:
        soup1 = normalize_pidgin(soup1)
        soup2 = normalize_pidgin(soup2)
    if adium:
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
        print('\n'.join(lines))

    return n
