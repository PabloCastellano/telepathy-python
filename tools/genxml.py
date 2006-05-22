#!/usr/bin/python2.4

from elementtree.ElementTree import fromstring, tostring
from xml.dom.minidom import parseString
from telepathy.server import *

import sys

def strip (element):
    if element.text:
        element.text = element.text.strip()
    if element.tail:
        element.tail = element.tail.strip()
    for child in element:
        strip (child)

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
    for i, e in enumerate(root):
        if e.get('name') == 'org.freedesktop.DBus.Introspectable':
            del root[i]

    root[:] = sorted(root[:], key=lambda e: e.get('name'))

    for interface in root:
        interface[:] = sorted(interface[:], key=lambda e: e.get('name'))

    # pretty print
    strip(root)
    xml = tostring(root)
    dom = parseString(xml)

    file = open(filename, 'w')
    file.write(dom.toprettyxml('  ', '\n'))
    file.close()
