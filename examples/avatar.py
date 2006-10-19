
"""
Telepathy example which requests the avatar for the user's own handle and
displays it in a Gtk window.
"""

import dbus
import dbus.glib
import gtk
import sys

from pprint import pprint

from telepathy.constants import CONNECTION_STATUS_CONNECTED
from telepathy.interfaces import (
    CONN_MGR_INTERFACE, CONN_INTERFACE, CONN_INTERFACE_AVATARS)
import telepathy.client

from account import read_account, connect

def window_closed_cb(window):
    gtk.main_quit()

def status_changed_cb(state, reason):
    print 'status changed'

    if state != CONNECTION_STATUS_CONNECTED:
        return

    print 'connected'
    handle = conn[CONN_INTERFACE].GetSelfHandle()
    tokens = conn[CONN_INTERFACE_AVATARS].GetAvatarTokens([handle])
    print 'token:', tokens[0]

    if len(sys.argv) > 2:
        avatar = file('avatar.png').read()
        new_token = conn[CONN_INTERFACE_AVATARS].SetAvatar(avatar, 'image/png')
        print 'new token:', new_token
        gtk.main_quit()
        return

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
    account_file = sys.argv[1]
    manager, protocol, account = read_account(account_file)
    conn = connect(manager, protocol, account)

    # XXX: hack!
    conn._valid_interfaces = [CONN_INTERFACE, CONN_INTERFACE_AVATARS]
    conn[CONN_INTERFACE].connect_to_signal('StatusChanged', status_changed_cb)

    print 'connecting'
    conn[CONN_INTERFACE].Connect()
    gtk.main()
    conn[CONN_INTERFACE].Disconnect()

