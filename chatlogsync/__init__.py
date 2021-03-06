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

from __future__ import unicode_literals
from __future__ import absolute_import

try:
    import __builtin__
except ImportError:
    import builtins as __builtin__
from gettext import gettext as _

from chatlogsync.dprint import print_d, print_e, print_, print_v, print_w

def _python_init():
    __builtin__.__dict__["print_v"] = print_v
    __builtin__.__dict__["print_e"] = print_e
    __builtin__.__dict__["print_d"] = print_d
    __builtin__.__dict__["print_w"] = print_w
    __builtin__.__dict__["print_"] = print_
    __builtin__.__dict__["_"] = _

_python_init()
