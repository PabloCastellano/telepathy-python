#!/usr/bin/env python
import gtk
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import msnlib
import msncb

class MSNConnection(dbus.service.Object):
    def __init__(self,bus_name,object_path, account, connect_info):
        bus.service.Object.__init__(self, bus_name,object_path)
        self.m = msnlib.msnd()
        self.m.cb = msncb.cb()
 
    @dbus.service.method('org.freedesktop.org.ipcf.connection')
    def create_contact_channel(contact_account, caps):
        pass

class MSNConnectionManager(dbus.service.Object):
    def __init__(self):
        # Here the service name
        self.bus_name = dbus.service.BusName('org.freedesktop.ipcf.connectionmanager.msn',bus=dbus.SessionBus())
        # Here the object path
        dbus.service.Object.__init__(self, self.bus_name, '/org/freedesktop/ipcf/connectionmanager/msn')
	
    # Here the interface name, and the method is named same as on dbus.
    @dbus.service.method('org.freedesktop.org.ipcf.connectionmanager')
    def make_connection(self, proto, account, connect_info):
        if proto!='msn':
                return None
        else:
                connection = MSNConnection(self.bus_name, '/org/freedesktop/ipcf/connection/msn/'+account, account, connect_info)
                return account
        

server = MSNConnectionManager()
gtk.main()
