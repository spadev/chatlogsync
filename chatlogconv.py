#!/usr/bin/python
from __future__ import print_function

import os
import sys
import signal
import traceback
from os.path import join, dirname, exists, expanduser, isfile, isdir
from argparse import ArgumentParser, ArgumentTypeError
from multiprocessing import Process, Queue, cpu_count, RLock, Value

from chatlogconv import formats
from chatlogconv import util
from chatlogconv.errors import AbortedError, ParseError

PROGNAME = 'chatlogconv'
VERSION = '0.1'

WORKERS = []

class Progress(object):
    """thread safe progress updater"""
    def __init__(self, total, options):
        self.total = total
        self.options = options
        self.n = Value('i', 0)
        self._lock = RLock()

    def update(self, i, path):
        with self._lock:
            self.n.value += i
            if not self.options.verbose:
                msg = '\r%i/%i' % (self.n.value, self.total)
                end = ''
            else:
                msg = '%s\n    %i/%i' % (path, self.n.value, self.total)
                end = '\n'
            if self.options.dry_run:
                msg += ' (DRY RUN)'
            print(msg, end=end)
            sys.stdout.flush()

class Parser(Process):
    def __init__(self, queue, options, progress):
        super(Parser, self).__init__()
        self.queue = queue
        self.options = options
        self.progress = progress
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        while True:
            try:
                item = self.queue.get()
                if item is None:
                    break
                # flush queue if stopped
                if self._stopped:
                    continue
                dstpath, wmodule, src_conversations = item
                if self.options.dry_run:
                    dst_conversations = src_conversations
                else:
                    dst_conversations = []
                    for c in src_conversations:
                        dst_conversations.extend(wmodule.parse(c.path))
                write_outfile(wmodule, dstpath, dst_conversations)
                self.progress.update(len(dst_conversations), dstpath)
            except AbortedError:
                self.stop()

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
        ArgumentParser(description='Convert chatlogs',
                       prog=PROGNAME)
    parser.add_argument('source', nargs='+', type=isfileordir,
                        help='source file or directory')
    parser.add_argument('destination', type=isnotfile,
                        help='destination directory')
    parser.add_argument("-f", "--format",
                        choices=formats.output_formats,
                        help=("format to use for output files"),
                        default=None,
                        )
    parser.add_argument("-F", "--force",
                        help=("force regeneration of existing logs at "
                              "destination"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-n", "--dry-run",
                        help=("perform a trial run with no changes made"),
                        action='store_true',
                        default=False,
                        )
    parser.add_argument("-t", "--threads", metavar="NUM_THREADS",
                        help=("use NUM_THREADS worker processes for parsing"),
                        type=int,
                        default=cpu_count(),
                        )
    parser.add_argument("-v", "--verbose",
                        help=("enable verbose output"),
                        action='store_true',
                        default=False,
                        )

    return parser.parse_args()

fslock = RLock()
def write_outfile(module, path, conversations):
    dstdir = dirname(path)
    with fslock:
        if not exists(dstdir):
            os.makedirs(dstdir)
    try:
        module.write(path, conversations)
        n = len(conversations)
    except:
        n = 0
        if isfile(path):
            os.unlink(path)
        raise

    return n

def convert(to_write, total, options):
    global WORKERS
    queue = Queue()

    progress = Progress(total, options)
    WORKERS = [Parser(queue, options, progress)
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

    src_conversations = util.get_conversations(src_paths, modules)
    nsrc = len(src_conversations)
    print('%i conversation%s found at source' %
          (nsrc, '' if nsrc == 1 else 's'))
    dst_conversations = util.get_conversations(dst_paths, modules)
    ndst = len(dst_conversations)
    print('%i conversation%s found at destination' %
          (ndst, '' if ndst == 1 else 's'))

    conversations = [x for x in src_conversations
                     if x not in dst_conversations]
    num_existing = len(src_conversations) - len(conversations)
    if options.force:
        conversations = src_conversations
    print('converting %i from source (%i already exist at destination)' %
          (len(conversations), num_existing))

    # (dstpath, wmodule): [conversations for dstpath])
    to_write = {}
    for c in conversations:
        rmodule = c.parsedby
        wmodule = modules[options.format] if options.format else rmodule
        dstpath = join(options.destination, wmodule.get_path(c))
        key = (dstpath, wmodule)
        if key not in to_write:
            to_write[key] = []
        to_write[key].append(c)

    convert(to_write, len(conversations), options)

    if not options.verbose:
        print('')
    return 0

def abort(*args):
    raise AbortedError

def cleanup(exitcode):
    for w in WORKERS:
        w.stop()
    for w in WORKERS:
        w.join()

if __name__ == "__main__":
    options = None
    try:
        exitcode = 0
        SIGS = [getattr(signal, s, None) for s in
                "SIGINT SIGTERM SIGHUP".split()]
        for sig in filter(None, SIGS):
            signal.signal(sig, abort)
        options = parse_args()
        exitcode = main(options)
    except AbortedError:
        exitcode = 1
        print("***aborted***", file=sys.stderr)
    except ParseError as e:
        exitcode = 2
        print(e, file=sys.stderr)
    except Exception as e:
        traceback.print_exc()
    finally:
        cleanup(exitcode)
        sys.exit(exitcode)
