#!/usr/bin/python

import os

from chatlogconv import util
from chatlogconv.adium import Adium

a = Adium()
baseout = '/home/evan/src/chatlogconv/tests/adium2'
for root, dirs, files in os.walk('/home/evan/src/chatlogconv/tests/adium'):
    for f in files:
        if not f.endswith('.xml'):
            continue
        path = os.path.join(root, f)
        conversations = a.parse(path, True)
        newpath = os.path.join(baseout, a.get_path(conversations[0]))
        newdir = os.path.dirname(newpath)
        if not os.path.exists(newdir):
            os.makedirs(newdir)
        a.write(newpath, conversations[0])
