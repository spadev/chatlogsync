#!/usr/bin/python
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import sys
import signal
import traceback
from os.path import join, dirname, exists, expanduser, isfile, isdir
from argparse import ArgumentParser, ArgumentTypeError
from multiprocessing import Process, Queue, cpu_count, RLock, Value

import chatlogsync
from chatlogsync import const, formats, util
from chatlogsync.errors import AbortedError, ParseError

WORKERS = []

class Progress(object):
    """thread safe progress updater"""
    def __init__(self, total):
        self.total = total
        self.n = Value('i', 0)
        self._lock = RLock()

    def update(self, i, path):
        with self._lock:
            self.n.value += i
        print_v(path)
        print_('\r[%i/%i] ' % (self.n.value, self.total), end='')
        print_v('\n')

        if const.DRYRUN:
            print_(' (DRY RUN)')
        sys.stdout.flush()

class Parser(Process):
    def __init__(self, destination, queue, progress):
        super(Parser, self).__init__()
        self.queue = queue
        self.progress = progress
        self.tempfiles = []
        self.destination = destination
        self._num_errors = Value('i', 0)
        self._stopped = False

    def stop(self):
        self._stopped = True

    @property
    def num_errors(self):
        return self._num_errors.value

    def cleanup(self):
        for tempfile in self.tempfiles:
            if exists(tempfile):
                os.unlink(tempfile)

    def run(self):
        while True:
            try:
                dstpath = ''
                item = self.queue.get()
                if item is None:
                    break
                # flush queue if stopped
                if self._stopped:
                    continue

                dstpath, wmodule, src_conversations = item
                if const.DRYRUN:
                    dst_conversations = src_conversations
                else:
                    dst_conversations = []
                    for c in src_conversations:
                        dst_conversations.extend(wmodule.parse(c.path))
                tmppath = dstpath+'.tmp'

                self.tempfiles.append(tmppath)
                realdstpath = join(self.destination, dstpath)
                write_outfile(wmodule, realdstpath,
                              tmppath, dst_conversations)
                del self.tempfiles[-1]

                self.progress.update(len(dst_conversations), dstpath)
            except AbortedError:
                self.stop()
            except Exception as e:
                tb = traceback.format_exc()
                self._num_errors.value += 1
                msg = '%s\n%s' % (dstpath, tb)
                print_e(msg)

        self.cleanup()

def isfileordir(value):
    if not isfile(value) and not isdir(value):
        raise ArgumentTypeError('%s is not a file or directory' % value)

    return value

def isnotfile(value):
    if isfile(value):
        raise ArgumentTypeError('%s is not a file' % value)

    return value

def parse_args():
    parser = \
        ArgumentParser(description=const.PROGRAM_DESCRIPTION,
                       prog=const.PROGRAM_NAME)
    parser.add_argument('source', nargs='+', type=isfileordir,
                        help=_('source file or directory'))
    parser.add_argument('destination', type=isnotfile,
                        help=_('destination directory'))
    parser.add_argument("-d", "--debug",
                        help=_("enable debug output"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-f", "--format",
                        choices=formats.output_formats,
                        help=_("format to use for output files"),
                        default=None,
                        )
    parser.add_argument("-F", "--force",
                        help=_("force regeneration of existing logs at "
                               "destination"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-n", "--dry-run",
                        help=_("perform a trial run with no changes made"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-q", "--quiet",
                        help=_("suppress warnings"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-t", "--threads", metavar="NUM_THREADS",
                        help=_("use NUM_THREADS worker processes for parsing"),
                        type=int,
                        default=cpu_count(),
                        )
    parser.add_argument("-v", "--verbose",
                        help=_("enable verbose output"),
                        action='store_true',
                        default=False,
                        )

    options = parser.parse_args()
    if options.debug:
        const.DEBUG = True
    if options.verbose:
        const.VERBOSE = True
    if options.quiet:
        const.QUIET = True

    return options

fslock = RLock()
def write_outfile(module, path, tmppath, conversations):
    dstdir = dirname(path)
    with fslock:
        if not exists(dstdir):
            os.makedirs(dstdir)

    module.write(tmppath, conversations)
    os.rename(tmppath, path)

    return len(conversations)

def convert(to_write, total, options):
    global WORKERS
    queue = Queue()

    progress = Progress(total)
    WORKERS = [Parser(options.destination, queue, progress)
               for i in range(options.threads)]
    for w in WORKERS:
        w.start()
    for (dstpath, wmodule), src_conversations in iter(to_write.items()):
        queue.put((dstpath, wmodule, src_conversations))
    for w in WORKERS:
        queue.put(None)

    for w in WORKERS:
        w.join()

    return 0

def main(options):
    src_paths = util.get_paths(options.source)
    dst_paths = util.get_paths([options.destination])
    modules =  [x() for x in formats.all_formats.values()]
    modules_map = {x.type: x for x in modules}

    print_('analyzing source...', end='', flush=True)
    src_conversations = util.get_conversations(src_paths, modules)
    nsrc = len(src_conversations)
    print_('\r%i conversation%s found at source' %
           (nsrc, '' if nsrc == 1 else 's'))
    dst_conversations = util.get_conversations(dst_paths, modules)
    ndst = len(dst_conversations)
    print_('analyzing destination...', end='', flush=True)
    print_('\r%i conversation%s found at destination' %
           (ndst, '' if ndst == 1 else 's'))

    conversations = [x for x in src_conversations
                     if x not in dst_conversations]
    num_existing = len(src_conversations) - len(conversations)
    if options.force:
        conversations = src_conversations
    print_('converting %i from source (%i already exist at destination)' %
           (len(conversations), num_existing))

    # (dstpath, wmodule): [conversations for dstpath])
    to_write = {}
    for c in conversations:
        rmodule = c.parsedby
        wmodule = modules_map[options.format] if options.format else rmodule
        key = (wmodule.get_path(c), wmodule)
        if key not in to_write:
            to_write[key] = []
        to_write[key].append(c)

    convert(to_write, len(conversations), options)

    if not options.verbose:
        print_('')
    return 0

def abort(*args):
    raise AbortedError

def cleanup(exitcode):
    num_errors = 0
    for w in WORKERS:
        w.stop()
    for w in WORKERS:
        w.join()
        num_errors += w.num_errors

    return num_errors

if __name__ == "__main__":
    options = None
    try:
        exitcode = 0
        SIGS = [getattr(signal, s, None) for s in
                "SIGINT SIGTERM SIGHUP".split()]
        for sig in [s for s in SIGS if s]:
            signal.signal(sig, abort)
        options = parse_args()
        exitcode = main(options)
    except AbortedError:
        exitcode = 1
        print_e("***aborted***")
    except Exception as e:
        traceback.print_exc()
    finally:
        ne = cleanup(exitcode)
        if ne:
            print_e('%i error%s' % (ne, '' if ne == 1 else 's'))

        sys.exit(ne)
