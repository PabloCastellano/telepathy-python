#!/usr/bin/python
import sys
import telepathy
from telepathy.interfaces import CONN_MGR_INTERFACE

if len(sys.argv) >= 2:
    manager_name = sys.argv[1]
else:
    manager_name = "haze"
service_name = "org.freedesktop.Telepathy.ConnectionManager.%s" % manager_name
object_path = "/org/freedesktop/Telepathy/ConnectionManager/%s" % manager_name

object = telepathy.client.ConnectionManager(service_name, object_path)
manager = object[CONN_MGR_INTERFACE]

print "[ConnectionManager]"
print "BusName=%s" % service_name
print "ObjectPath=%s" % object_path
print

for protocol in manager.ListProtocols():
    print "[Protocol %s]" % protocol
    for param in manager.GetParameters(protocol):
        print "param-%s=%s" % (param[0], param[2]),
        # FIXME: deal with the "register" flag
        if param[1] == 1L:
            print "required",
        print
    print
