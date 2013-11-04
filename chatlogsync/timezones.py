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

import locale
import time
import re
import sys
import pytz
import collections
import datetime as dt
import dateutil.tz as dtz

# timezones in same country have higher priority

tznames = collections.defaultdict(list)
tzabbrevs = {}
tzoffsets_i = {}
tzoffsets_s = {}
country_timezones = []
locale_datetime_fmt = None

def init():
    global locale_datetime_fmt

    # already initialized
    if locale_datetime_fmt:
        print_d('timezones already initialized')
        return

    # use system locale for %c in strftime
    locale.setlocale(locale.LC_ALL, '')
    locale_datetime_fmt = locale.nl_langinfo(locale.D_T_FMT)

    try:
        country = re.sub('.*_', '', locale.getdefaultlocale()[0])
    except Exception:
        country = ''
    if not country:
        print_w('Unable to determine country: '
                'timezone abbreviations may not be what you want')
    country_timezones = pytz.country_timezones[country]

    for name in pytz.common_timezones:
        timezone = dtz.gettz(name)
        now = dt.datetime.now(timezone)

        abbrevs = set()
        for days in xrange(0, 365, 90):
            abbrev = _update_lists(name, now + dt.timedelta(days=days), abbrevs)
            abbrevs.add(abbrev)

    for k in iter(tznames.keys()):
        tznames[k].sort(key=_sort_func)

def _update_lists(name, dt_obj, abbrevs):
    abbrev = dt_obj.strftime('%Z')
    if abbrev in abbrevs:
        return

    offset_s = dt_obj.strftime('%z')
    if not offset_s:
        print_d('no timezone offset for', name)
        return

    o1 = int(offset_s[:-2])
    o2 = int(offset_s[-2:])/0.6
    offset_i = o1 + (o2 if o2 > 0 else -o2)
    offset_i = int(offset_i*3600)

    tznames[offset_s].append((name, abbrev))
    tznames[offset_i].append((name, abbrev))
    tznames[abbrev].append((name, abbrev))

    tzabbrevs[name] = abbrev
    tzoffsets_i[name, abbrev] = offset_i
    tzoffsets_i[offset_s] = offset_i
    tzoffsets_s[name, abbrev] = offset_s

    return abbrev

def _sort_func(entry):
    name, abbrev = entry
    if abbrev in time.tzname:
        return -2
    if name in country_timezones:
        return -1
    return 0

def getoffset(abbrev, offset):
    """Return a dateutil.tz.tzoffset object"""
    if not abbrev:
        abbrev = tznames.get(offset, [None, None])[0][1]

    if offset is None:
        name = tznames.get(abbrev, [None, None])[0][0]
        offset = tzoffsets_i.get((name, abbrev))
    elif not isinstance(offset, int):
        offset = tzoffsets_i.get(offset)

    return dtz.tzoffset(abbrev, offset) \
        if abbrev is not None and offset is not None else 0
