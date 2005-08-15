#!/usr/bin/python

import dbus

bus = dbus.SessionBus()
proxy_obj = bus.get_object('org.freedesktop.ipcf.connectionmanager.msn', '/org/freedesktop/ipcf/connectionmanager/msn')
dbus_iface = dbus.Interface(proxy_obj, 'org.freedesktop.ipcf.connectionmanager')

print dbus_iface.make_connection('msn','foo', {'foo':'bar'})

