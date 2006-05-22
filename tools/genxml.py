#!/usr/bin/python2.4
from elementtree.ElementTree import fromstring, tostring
from telepathy.server import *
import sys

defs = file(sys.argv[1])
for line in defs:
    if line[0] == '#':
        continue
    elif line == '\n':
        continue

    (filename, name, basenames) = line.split('\t')
    bases = eval(basenames)
    if type(bases) != tuple:
        bases = (bases,)
    # classes half-baked to order... :)
    cls = type(name, bases, {'__init__':lambda self: None,
                             '__del__':lambda self: None,
                             '_object_path':'/'+name,
                             '_name':name})
    instance = cls()
    xml = instance.Introspect()

    # sort
    root = fromstring(xml)
    root[:] = sorted(root[:], key=lambda e: e.get('name'))

    for interface in root:
        interface[:] = sorted(interface[:], key=lambda e: e.get('name'))

    file = open(filename, 'w')
    file.write(tostring(root))
    file.close()
