# Copyright 2013 Evan Vitero

# This file is part of chatlogsync.

# chatlogsync is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# chatlogsync is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with chatlogsync.  If not, see <http://www.gnu.org/licenses/>.

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
