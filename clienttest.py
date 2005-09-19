#!/usr/bin/env python

import dbus
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import getpass
import gobject
import sys

CONN_INTERFACE = 'org.freedesktop.ipcf.Connection'
CONN_OBJECT = '/org/freedesktop/ipcf/Connection'
CONN_SERVICE = 'org.freedesktop.ipcf.Connection'

CONN_MGR_INTERFACE = 'org.freedesktop.ipcf.ConnectionManager'
CONN_MGR_OBJECT = '/org/freedesktop/ipcf/ConnectionManager'
CONN_MGR_SERVICE = 'org.freedesktop.ipcf.ConnectionManager'

class Connection:
    def status_callback(self, status):
        if self.status == status:
            return
        else:
            self.status = status

        if status == 'connected':
            self.conn.Disconnect()
        if status == 'disconnected':
            self.mainloop.quit()

        print 'StatusChanged', status

    def __init__(self, mainloop, manager, proto, account, conn_opts):
        self.bus = dbus.SessionBus()
        self.mainloop = mainloop

        mgr_serv_name = CONN_MGR_SERVICE+'.'+manager
        mgr_obj_path = CONN_MGR_OBJECT+'/'+manager
        mgr_obj = self.bus.get_object(mgr_serv_name, mgr_obj_path)
        mgr = dbus.Interface(mgr_obj, CONN_MGR_INTERFACE)
        serv_name, obj_path = mgr.Connect(proto, account, conn_opts)

        self.conn_obj = self.bus.get_object(serv_name, obj_path)
        self.conn = dbus.Interface(self.conn_obj, CONN_INTERFACE)

        self.conn.connect_to_signal('StatusChanged', self.status_callback)

        # handle race condition when connecting completes before this method completes
        self.status = 'connecting'
        self.status_callback(self.conn.GetStatus())

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
