#!/usr/bin/python
from os.path import join, dirname

import testing

NAME = 'adium'
EXTENSION = 'xml'
SOURCE_DIR = join(dirname(__file__), NAME)
TO_TEST = (('pidgin-html', 'html'),)

if __name__ == "__main__":
    testing.main(testing.test_all, NAME, EXTENSION, SOURCE_DIR, TO_TEST)
