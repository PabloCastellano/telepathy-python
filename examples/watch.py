
"""
Example of how to discover exisiting Telepathy connections on the bus, and be
notified when connections appear and disappear.
"""

import dbus
import dbus.glib
import gobject

from telepathy.interfaces import CONN_INTERFACE
from telepathy.client import Connection

conn_prefix = 'org.freedesktop.Telepathy.Connection.'
mgr_prefix = 'org.freedesktop.Telepathy.ConnectionManager.'
connection_status = ['Connected', 'Connecting', 'Disconnected']

def prefix_filter(prefix, iter):
    prefix_len = len(prefix)

    for x in iter:
        if x.startswith(prefix):
            yield x[prefix_len:]

class Watcher:
    def __init__(self, bus):
        self.bus = bus

        dbus = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        names = dbus.ListNames()
        conn_names = list(prefix_filter(conn_prefix, names))

        for name in conn_names:
            conn = self._get_conn(name)
            self._watch_conn(conn)
            status = connection_status[conn[CONN_INTERFACE].GetStatus()]
            print 'found connection: %s (%s)' % (name, status)

        dbus.connect_to_signal('NameOwnerChanged', self._name_owner_changed_cb)

    def _get_conn(self, name):
        mgr, protocol, account = name.split('.')
        path = '/org/freedesktop/Telepathy/Connection/%s/%s/%s' % (
            mgr, protocol, account)
        return Connection(conn_prefix + name, path)

    def _watch_conn(self, conn):
        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            lambda status, reason:
                self._status_changed_cb(name, status, reason))

    def _name_owner_changed_cb(self, service, old, new):
        if service.startswith(conn_prefix):
            name = service[len(conn_prefix):]

            if old == '':
                conn = self._get_conn(name)
                self._watch_conn(conn)
                status = connection_status[conn[CONN_INTERFACE].GetStatus()]
                print 'new connection: %s (%s)' % (name, status)
            elif new == '':
                print 'connection gone: %s' % name

    def _status_changed_cb(self, name, status, reason):
        print 'status changed: %s: %s' % (
            name, connection_status[status])

if __name__ == '__main__':
    Watcher(dbus.Bus())
    loop = gobject.MainLoop()

    try:
        loop.run()
    except KeyboardInterrupt:
        pass

