#!/usr/bin/python2.4
from telepathy.server import *
import sys

defs = file(sys.argv[1])
for line in defs:
    (filename, name, basenames) = line.split('\t')
    bases = eval(basenames)
    if type(bases) != tuple:
        bases = (bases,)
    # classes half-baked to order... :)
    cls = type(name, bases, {'__init__':lambda self: None,
                             '__del__':lambda self: None,
                             '_object_path':name,
                             '_name':name})
    instance = cls()
    xml = instance.Introspect()
    file = open(filename, 'w')
    file.write(xml)
    file.close()
