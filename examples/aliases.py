
"""
Print out the aliases of all contacts on the known list.
"""

import dbus.glib
import gobject
import sys

from account import connection_from_file

from telepathy.client import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_HANDLE_TYPE_LIST,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED)
from telepathy.interfaces import (
    CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_CONTACT_LIST, CONN_INTERFACE,
    CONN_INTERFACE_ALIASING)

class AliasesClient:
    def __init__(self, conn):
        self.conn = conn

        conn[CONN_INTERFACE].connect_to_signal(
            'StatusChanged', self.status_changed_cb)

    def _request_list_channel(self, name):
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_LIST, [name])[0]
        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_CONTACT_LIST, CONNECTION_HANDLE_TYPE_LIST,
            handle, True)
        channel = Channel(self.conn._dbus_object._named_service, chan_path)
        # hack
        channel._valid_interfaces.add(CHANNEL_INTERFACE_GROUP)
        return channel

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_DISCONNECTED:
            print 'disconnected: %s' % reason
            self.quit()
            return

        if state != CONNECTION_STATUS_CONNECTED:
            return

        print 'connected'
        known_channel = self._request_list_channel('known')
        current, local_pending, remote_pending = (
            known_channel[CHANNEL_INTERFACE_GROUP].GetAllMembers())
        names = self.conn[CONN_INTERFACE].InspectHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, current)
        # hack
        conn._valid_interfaces.add(CONN_INTERFACE_ALIASING)
        aliases = self.conn[CONN_INTERFACE_ALIASING].RequestAliases(current)

        for handle, name, alias in zip(current, names, aliases):
            print ' % 3d: %s (%s)' % (handle, alias, name)

        self.quit()

    def members_changed_cb(self, name, message, added, removed, local_pending,
            remote_pending, actor, reason):
        if added:
            for handle in added:
                print '%s: added: %d' % (name, added)

        if removed:
            for handle in removed:
                print '%s: removed: %d' % (name, added)

    def run(self):
        self.loop = gobject.MainLoop()

        try:
            self.loop.run()
        except KeyboardInterrupt:
            print 'interrupted'

    def quit(self):
        self.loop.quit()

if __name__ == '__main__':
    assert len(sys.argv) == 2
    conn = connection_from_file(sys.argv[1])
    client = AliasesClient(conn)

    print "connecting"
    conn[CONN_INTERFACE].Connect()
    client.run()
    print "disconnecting"

    try:
        conn[CONN_INTERFACE].Disconnect()
    except dbus.dbus_bindings.DBusException:
        pass

