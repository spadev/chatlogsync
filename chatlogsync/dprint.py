from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import sys
from chatlogsync import const
from multiprocessing import RLock

_printlock = RLock()
def _print(msg, file, end, flush=False):
    with _printlock:
        print(msg, file=file, end=end)
        if flush:
            file.flush()

def print_e(msg, file=sys.stderr, end='\n'):
    _print('E: %s' % msg, file, end)

def print_w(msg, file=sys.stderr, end='\n'):
    if not const.QUIET:
        _print('W: %s' % msg, file, end)

def print_(msg, file=sys.stdout, end='\n', flush=False):
    _print(msg, file, end, flush)

def print_d(msg, file=sys.stdout, end='\n'):
    if const.DEBUG:
        _print(msg, file, end)

def print_v(msg, file=sys.stdout, end='\n'):
    if const.VERBOSE:
        _print(msg, file, end)
