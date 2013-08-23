#!/usr/bin/python

import os

from chatlogconv.adium import AdiumParser

a = AdiumParser()
for root, dirs, files in os.walk('/home/evan/src/chatlogconv/tests/adium'):
    for f in files:
        if not f.endswith('.xml'):
            continue
        path = os.path.join(root, f)
        conversations = a.parse(path)
