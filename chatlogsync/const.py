import os
from gettext import gettext as _

VERSION= '0.1'
PROGRAM_NAME = 'chatlogsync'
PROGRAM_DESCRIPTION = _('Sync chatlogs in different formats')

DEBUG = 'CHATLOGSYNC_DEBUG' in os.environ
VERBOSE = 'CHATLOGSYNC_VERBOSE' in os.environ
QUIET = 'CHATLOGSYNC_QUIET' in os.environ
DRYRUN = 'CHATLOGSYNC_DRYRUN' in os.environ
