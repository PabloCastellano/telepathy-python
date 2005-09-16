#!/usr/bin/env python

import dbus
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import getpass
import gobject
import sys

CONN_INTERFACE = 'org.freedesktop.ipcf.connection'
CONN_OBJECT = '/org/freedesktop/ipcf/connection'
CONN_SERVICE = 'org.freedesktop.ipcf.connection'

CONN_MGR_INTERFACE = 'org.freedesktop.ipcf.connectionmanager'
CONN_MGR_OBJECT = '/org/freedesktop/ipcf/connectionmanager'
CONN_MGR_SERVICE = 'org.freedesktop.ipcf.connectionmanager'

class Connection:
    def connected_callback(self, identifier, serv_name, obj_path):
        if identifier == self.id:
            print 'Connected: %s' % (obj_path)
            self.conn_obj = self.bus.get_object(serv_name, obj_path)
            self.conn = dbus.Interface(self.conn_obj, CONN_INTERFACE)
            self.conn.woot()

    def connection_error_callback(self, identifier, message):
        if identifier == pending_conn:
            print 'Connection error: %s' % (message)
            self.mainloop.quit()

    def __init__(self, mainloop, manager, proto, account, conn_opts):
        self.bus = dbus.SessionBus()
        self.conn_mgr_obj = self.bus.get_object(CONN_MGR_SERVICE+'.'+manager, CONN_MGR_OBJECT+'/'+manager)
        self.conn_mgr = dbus.Interface(self.conn_mgr_obj, CONN_MGR_INTERFACE)

        self.conn_mgr.connect_to_signal('Connected', self.connected_callback)
        self.conn_mgr.connect_to_signal('ConnectionError', self.connection_error_callback)

        self.id = self.conn_mgr.make_connection(proto, account, conn_opts)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        manager = sys.argv[1]
    else:
        manager = raw_input('Manager [cheddar]: ')
        if manager == '':
            manager = 'cheddar'

    if len(sys.argv) > 2:
        protocol = sys.argv[2]
    else:
        protocol = raw_input('Protocol [jabber]: ')
        if protocol == '':
            protocol = 'jabber'

    if len(sys.argv) > 3:
        account = sys.argv[3]
    else:
        account = raw_input('Account: ')

    if len(sys.argv) > 4:
        pw = sys.argv[4]
    else:
        pw = getpass.getpass()

    mainloop = gobject.MainLoop()
    connection = Connection(mainloop, manager, protocol, account, {'password':pw})
    mainloop.run()
