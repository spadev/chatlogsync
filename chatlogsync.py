#!/usr/bin/python
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import sys
import signal
import traceback
from os.path import join, dirname, exists, isfile, isdir, realpath
from argparse import ArgumentParser, ArgumentTypeError
from multiprocessing import Process, cpu_count, Value, Manager, Lock

import chatlogsync
from chatlogsync import const, formats, util

WORKERS = []

class Progress(object):
    """Thread-safe progress updater"""
    def __init__(self):
        self._nread = Value('i', 0, lock=False)
        self._nwrote = Value('i', 0, lock=False)
        self._nskipped = Value('i', 0, lock=False)
        self._nerrors = Value('i', 0, lock=False)
        self._lock = Lock()

    def print_status(self, msg):
        dryrun = ' (DRY RUN)' if const.DRYRUN else ''
        print_v(msg)
        print_('\r[read:%i wrote:%i skipped:%i errors:%i]%s ' %
               (self.nread, self.nwrote, self.nskipped, self.nerrors, dryrun),
               end='', flush=True)
        print_v('\n')

    def _incr(self, var, n=1):
        with self._lock:
            var.value += n

    def read(self, path):
        self._incr(self._nread)

    def wrote(self, path):
        self._incr(self._nwrote)
        self.print_status('wrote %s' % path)

    def error(self, path):
        tb = traceback.format_exc()
        self._incr(self._nerrors)
        print_e('%s\n%s' % (path, tb))

    def skipped(self, path):
        self._incr(self._nskipped)
        print_v('skipped %s' % path)

    @property
    def nerrors(self):
        return self._nerrors.value
    @property
    def nwrote(self):
        return self._nwrote.value
    @property
    def nread(self):
        return self._nread.value
    @property
    def nskipped(self):
        return self._nskipped.value

class Parser(Process):
    def __init__(self, outformat, force, destination, queue, files,
                 progress, fslock):
        super(Parser, self).__init__()
        self.queue = queue
        self.progress = progress
        self.tempfiles = []
        self.destination = destination
        self.outformat = outformat
        self.force = force
        self._files = files
        self._fslock = fslock
        self._modules =  [x() for x in formats.all_formats.values()]
        self._stopped = Value('i', 0)
        self._curpath = ''

    def stop(self):
        self._stopped.value = 1

    @property
    def stopped(self):
        return self._stopped.value == 1

    def cleanup(self):
        for tempfile in self.tempfiles:
            if exists(tempfile):
                os.unlink(tempfile)

    def _process_path(self, path):
        self._curpath = path

        for i, rmodule in enumerate(self._modules):
            parsed = rmodule.parse_path(path)
            if parsed:
                # try this module first next time
                if i != 0:
                    self._modules[i] = self._modules[0]
                    self._modules[0] = rmodule
                break
        # file is not a chatlog
        if not parsed:
            return None

        self.progress.read(path)

        wmodule = self._modules_map[self.outformat] \
            if self.outformat else rmodule
        for c in parsed:
            self._curpath = path
            dstpath = wmodule.get_path(c)
            real_dstpath = realpath(join(self.destination, dstpath))
            with self._fslock:
                if real_dstpath in self._files:
                    f = 1
                elif exists(real_dstpath):
                    f = 2
                else:
                    f = 0
                self._files[real_dstpath] = f
                if f and not self.force:
                    self.progress.skipped(dstpath)
                    continue
            if const.DRYRUN:
                conversation = c
            else:
                conversation = rmodule.parse_conversation(c)
                tmppath = real_dstpath+'.tmp'
                self.tempfiles.append(tmppath)
                self._curpath = real_dstpath
                self._write_outfile(wmodule, real_dstpath, tmppath,
                                    [conversation])
                del self.tempfiles[-1]
            self.progress.wrote(dstpath)

    def _write_outfile(self, module, path, tmppath, conversations):
        # return len(conversations)
        dstdir = dirname(path)
        with self._fslock:
            if not exists(dstdir):
                os.makedirs(dstdir)

        module.write(tmppath, conversations)
        os.rename(tmppath, path)

        return len(conversations)

    def run(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        path = ''
        while True:
            try:
                path = self.queue.get()
                if path is None:
                    break
                self._process_path(path)
            except IOError as e:
                break
            except Exception as e:
                self.progress.error(self._curpath)

        self.cleanup()

def isfileordir(value):
    if not isfile(value) and not isdir(value):
        raise ArgumentTypeError("'%s' is not a file or directory" % value)

    return value

def isnotfile(value):
    if isfile(value):
        raise ArgumentTypeError("'%s' is not a file" % value)

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

def convert(paths, options):
    global WORKERS
    manager = Manager()
    fslock = Lock()
    progress = Progress()
    queue = manager.Queue()
    files = manager.dict()

    WORKERS = [Parser(options.format, options.force, options.destination,
                      queue, files, progress, fslock)
               for i in xrange(options.threads)]

    for w in WORKERS:
        w.start()

    for path in paths:
        queue.put(path)

    for w in WORKERS:
        queue.put(None)

    for w in WORKERS:
        w.join()

    return 0

def main(options):
    print_('gathering paths...', end='', flush=True)
    src_paths = util.get_paths(options.source)
    print_('done')

    convert(src_paths, options)

    return 0

def cleanup(exitcode):
    for w in WORKERS:
        progress = w.progress
        w.stop()
    for w in WORKERS:
        w.join()

    progress.print_status('done')
    if not const.VERBOSE:
        print_('')

    return progress.nerrors + exitcode

if __name__ == "__main__":
    options = None
    try:
        exitcode = 0
        options = parse_args()
        exitcode = main(options)
    except KeyboardInterrupt:
        exitcode = 1
        print_e("***aborted***")
    except Exception as e:
        exitcode = 1
        traceback.print_exc()
    finally:
        sys.exit(cleanup(exitcode))
