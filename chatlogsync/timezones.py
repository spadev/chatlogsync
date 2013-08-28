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
try:
    country = re.sub('.*_', '', locale.getdefaultlocale()[0])
except Exception:
    country = ''
country_timezones = []
if not country:
    print_w('Unable to determine country: '
            'timezone abbreviations may not be what you want')
country_timezones = pytz.country_timezones[country]

tznames = collections.defaultdict(list)
tzabbrevs = {}
tzoffsets_i = {}
tzoffsets_s = {}
for name in pytz.common_timezones:
    timezone=dtz.gettz(name)
    now=dt.datetime.now(timezone)

    offset_s=now.strftime('%z')
    o1 = int(offset_s[:-2])
    o2 = int(offset_s[-2:])/0.6
    offset_i = o1 + (o2 if o2 > 0 else -o2)
    offset_i = int(offset_i*3600)

    abbrev=now.strftime('%Z')

    tznames[offset_s].append((name, abbrev))
    tznames[offset_i].append((name, abbrev))
    tznames[abbrev].append((name, abbrev))

    tzabbrevs[name] = abbrev
    tzoffsets_i[name] = offset_i
    tzoffsets_s[name] = offset_s

def _sort_func(entry):
    name, abbrev = entry
    if abbrev in time.tzname:
        return -2
    if name in country_timezones:
        return -1
    return 0

for k in iter(tznames.keys()):
    tznames[k].sort(key=_sort_func)

def getoffset(abbrev, offset):
    """Return a dateutil.tz.tzoffset object"""
    if not abbrev and not offset:
        return 0

    if not abbrev:
        name, abbrev = tznames[offset][0]
        if not isinstance(offset, int):
            offset = tzoffsets_i[name]

    if not offset:
        name = tznames[abbrev][0][0]
        offset = tzoffsets_i[name]

    return dtz.tzoffset(abbrev, offset)
