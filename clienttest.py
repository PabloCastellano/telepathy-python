#!/usr/bin/python

import dbus
import getpass
import gobject
import sys

class Connection:
    def __init__(self, mainloop, manager, proto, account, conn_opts):
        self.bus = dbus.SessionBus()
        self.conn_mgr_obj = self.bus.get_object('org.freedesktop.ipcf.connectionmanager.'+manager, '/org/freedesktop/ipcf/connectionmanager/'+manager)
        self.conn_mgr = dbus.Interface(self.conn_mgr_obj, 'org.freedesktop.ipcf.connectionmanager')

        self.conn_mgr.connect_to_signal('Connected', self.connected_callback)
        self.conn_mgr.connect_to_signal('ConnectionError', self.connection_error_callback)

        self.id = self.conn_mgr.make_connection(proto, account, conn_opts)

    def connected_callback(self, identifier, obj_path):
        print 'Connected: %s as %s' % (identifier, obj_path)
        if identifier == self.id:
            print 'Connected: %s' % (obj_path)
            print dir(self.c)

    def connection_error_callback(self, identifier, message):
        if identifier == pending_conn:
            print 'Connection error: %s' % (message)
            mainloop.quit()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        manager = argv[1]
    else:
        manager = raw_input('Manager [cheddar]: ')
        if manager == '':
            manager = 'cheddar'

    if len(sys.argv) > 2:
        protocol = argv[2]
    else:
        protocol = raw_input('Protocol [jabber]: ')
        if protocol == '':
            protocol = 'jabber'

    if len(sys.argv) > 3:
        account = argv[3]
    else:
        account = raw_input('Account: ')

    if len(sys.argv) > 4:
        pw = argv[4]
    else:
        pw = getpass.getpass()

    mainloop = gobject.MainLoop()
    connection = Connection(mainloop, manager, protocol, account, {'password':pw})
    mainloop.run()
