chatlogsync
===========
command-line chatlog converter/synchronizer

Features
-----
* Designed to convert to and from different chatlog formats with no loss of
  information
* Currently supports Adium and Pidgin HTML logs
* Multithreaded (using Python's multiprocessing module)
* Handles many cases including group chats, normal messages, errors, and status
  changes

Dependencies
------------
* Beautiful Soup 4
* python-dateutil
* pytz
* Python imaging library (PIL)

*Ubuntu*

```apt-get install python-bs4 python-dateutil python-tz python-imaging```

Usage
-----
* Vaguely similar to ```rsync```

```
usage: chatlogsync [-h] [-d] [-f {adium,pidgin-html}] [-F] [-n]
                   [--no-comments] [-q] [-t NUM_THREADS] [-v]
                   source [source ...] destination

Sync chatlogs in different formats

positional arguments:
  source                source log file or directory
  destination           destination log directory

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           enable debug output
  -f {adium,pidgin-html}, --format {adium,pidgin-html}
                        format to use for output files
  -F, --force           force regeneration of existing logs at destination
  -n, --dry-run         perform a trial run with no changes made
  --no-comments         do not write comments to converted logs
  -q, --quiet           suppress warnings
  -t NUM_THREADS, --threads NUM_THREADS
                        use NUM_THREADS worker processes for parsing
  -v, --verbose         enable verbose output
```

*Example:*

```./chatlogsync.py ~/.purple/logs ~/Library/Application\ Support/Adium\ 2.0/Users/Default/Logs -f adium```

will convert all Pidgin logs to Adium logs (that don't already exist).


Adding the ```-F``` argument would convert all the logs even if they
already exist at the destination.

Notes
-----
* Mostly tested and designed for Linux, but works on OS X if all dependencies
  are installed. Untested but should work on Windows without too much trouble.
* Handles many cases, but certainly not all -- definitely needs more testing.

License
-------
GPLv3
