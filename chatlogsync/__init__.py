from __future__ import unicode_literals
from __future__ import absolute_import

import __builtin__
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
