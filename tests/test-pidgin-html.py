#!/usr/bin/python
from os.path import join, dirname

import testing

NAME = 'pidgin-html'
EXTENSION = 'html'
SOURCE_DIR = join(dirname(__file__), NAME)
TO_TEST = (('adium', 'xml'),)

if __name__ == "__main__":
    testing.main(testing.test_all, NAME, EXTENSION, SOURCE_DIR, TO_TEST)
