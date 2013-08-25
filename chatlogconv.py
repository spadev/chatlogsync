#!/usr/bin/python
from __future__ import print_function

import os
import sys
import signal
import traceback
from os.path import join, dirname, exists, expanduser, isfile, isdir
from argparse import ArgumentParser, ArgumentTypeError

from chatlogconv import formats
from chatlogconv import util
from chatlogconv.errors import AbortedError, ParseError

PROGNAME = 'chatlogconv'
VERSION = '0.1'

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
    parser.add_argument("-v", "--verbose",
                        help=("enable verbose output"),
                        action='store_true',
                        default=False,
                        )

    return parser.parse_args()

def convert(options):
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

    # (outpath, wmodule): [conversations in that file])
    to_write = {}
    for c in conversations:
        rmodule = c.parsedby
        wmodule = modules[options.format] if options.format else rmodule
        outpath = join(options.destination, wmodule.get_path(c))
        key = (outpath, wmodule)
        if key not in to_write:
            to_write[key] = []
        to_write[key].append(c)

    t = len(conversations)
    n = 0

    for (outpath, wmodule), old_conversations in iter(to_write.items()):
        if not options.dry_run:
            new_conversations = []
            for c in old_conversations:
                new_conversations.extend(c.parsedby.parse(c.path))
            try:
                outdir = dirname(outpath)
                if not exists(outdir):
                    os.makedirs(outdir)
                wmodule.write(outpath, new_conversations)
            except:
                if isfile(outpath):
                    os.unlink(outpath)
                raise

        n += len(old_conversations)
        if not options.verbose:
            msg = '\r%i/%i' % (n, t)
            end = ''
        else:
            msg = '%s\n    %i/%i' % (outpath, n, t)
            end = '\n'
        if options.dry_run:
            msg += ' (DRY RUN)'
        print(msg, end=end)
        sys.stdout.flush()

    return 0

def abort(*args):
    raise AbortedError

def cleanup(exitcode):
    pass

if __name__ == "__main__":
    options = None
    try:
        exitcode = 0
        SIGS = [getattr(signal, s, None) for s in
                "SIGINT SIGTERM SIGHUP".split()]
        for sig in filter(None, SIGS):
            signal.signal(sig, abort)
        options = parse_args()
        exitcode = convert(options)
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
