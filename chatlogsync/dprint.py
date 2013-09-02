from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

from sys import stdout, stderr

from chatlogsync import const
from multiprocessing import RLock

_printlock = RLock()
def _print(*args, **kwargs):
    flush = kwargs.pop('flush', False)
    with _printlock:
        print(*args, **kwargs)
        if flush:
            kwargs.get('file', stdout).flush()

def print_e(*args, **kwargs):
    kwargs['file'] = stderr
    _print('E:', *args, **kwargs)

def print_w(*args, **kwargs):
    if not const.QUIET:
        kwargs['file'] = stderr
        _print('W:', *args, **kwargs)

def print_(*args, **kwargs):
    _print(*args, **kwargs)

def print_d(*args, **kwargs):
    if const.DEBUG:
        _print(*args, **kwargs)

def print_v(*args, **kwargs):
    if const.VERBOSE:
        _print(*args, **kwargs)
