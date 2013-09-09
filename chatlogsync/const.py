# Copyright 2013 spadev

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

import os
from gettext import gettext as _

VERSION= '0.1'
PROGRAM_NAME = 'chatlogsync'
PROGRAM_DESCRIPTION = _('Sync chatlogs in different formats')
HEADER_COMMENT = '%s-v%s/%%s' % (PROGRAM_NAME, VERSION)

DEBUG = 'CHATLOGSYNC_DEBUG' in os.environ
VERBOSE = 'CHATLOGSYNC_VERBOSE' in os.environ
QUIET = 'CHATLOGSYNC_QUIET' in os.environ
DRYRUN = 'CHATLOGSYNC_DRYRUN' in os.environ
NO_COMMENTS = 'CHATLOGSYNC_NO_COMMENTS' in os.environ
