
import dbus.glib
import gobject
import sys

from telepathy.constants import (
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED
from telepathy.interfaces import (
    CONN_INTERFACE, CONN_INTERFACE_AVATARS)

from account import read_account, connect

registered = False
loop = None

def status_changed_cb(state, reason):
    print 'status changed', state

    if state == CONNECTION_STATUS_CONNECTED:
        print 'registered'
        registered = True
        conn.Disconnect()
    elif state == CONNECTION_STATUS_DISCONNECTED:
        if !registered:
            print 'failed'

    loop.quit()

if __name__ == '__main__':
    manager, protocol, account = read_account(sys.argv[1])
    account['register'] = True
    conn = connect(manager, protocol, account)

    # XXX: hack!
    conn._valid_interfaces = [CONN_INTERFACE]
    conn[CONN_INTERFACE].connect_to_signal('StatusChanged', status_changed_cb)

    print 'connecting'
    conn[CONN_INTERFACE].Connect()
    loop = gobject.MainLoop()
    loop.run()
    conn[CONN_INTERFACE].Disconnect()

