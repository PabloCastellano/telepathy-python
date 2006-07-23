
"""
Telepathy example which requests the avatar for the user's own handle and
displays it in a Gtk window.
"""

import dbus.glib
import gtk
import sys

from telepathy.constants import CONNECTION_STATUS_CONNECTED
from telepathy.interfaces import (
    CONN_MGR_INTERFACE, CONN_INTERFACE, CONN_INTERFACE_AVATARS)
import telepathy.client

def parse_account(s):
    lines = s.splitlines()
    pairs = []

    for line in lines:
        k, v = line.split(':', 1)
        k = k.strip()
        v = v.strip()
        pairs.append((k, v))

    return dict(pairs)

def window_closed_cb(window):
    gtk.main_quit()

def status_changed_cb(state, reason):
    if state != CONNECTION_STATUS_CONNECTED:
        return

    handle = conn[CONN_INTERFACE].GetSelfHandle()
    tokens = conn[CONN_INTERFACE_AVATARS].GetAvatarTokens([handle])
    print 'token:', tokens[0]
    image, mime = conn[CONN_INTERFACE_AVATARS].RequestAvatar(handle)
    image = ''.join(chr(i) for i in image)

    window = gtk.Window()
    loader = gtk.gdk.PixbufLoader()
    loader.write(image)
    loader.close()
    image = gtk.Image()
    image.set_from_pixbuf(loader.get_pixbuf())
    window.add(image)
    window.show_all()
    window.connect('destroy', gtk.main_quit)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        account_file = sys.argv[1]
    else:
        account_file = 'account'

    reg = telepathy.client.ManagerRegistry()
    reg.LoadManagers()

    account = parse_account(file(account_file).read())
    manager = account['manager']
    protocol = account['protocol']
    del account['manager']
    del account['protocol']

    mgr = reg.GetManager(manager)
    conn_bus_name, conn_object_path = mgr[CONN_MGR_INTERFACE].Connect(
        protocol, account)
    conn = telepathy.client.Connection(conn_bus_name, conn_object_path)
    conn[CONN_INTERFACE].connect_to_signal('StatusChanged', status_changed_cb)

    gtk.main()
    conn[CONN_INTERFACE].Disconnect()

