#!/usr/bin/env python

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import xmpp

CONN_INTERFACE = 'org.freedesktop.ipcf.Connection'
CONN_OBJECT = '/org/freedesktop/ipcf/Connection'
CONN_SERVICE = 'org.freedesktop.ipcf.Connection'

CONN_MGR_INTERFACE = 'org.freedesktop.ipcf.ConnectionManager'
CONN_MGR_OBJECT = '/org/freedesktop/ipcf/ConnectionManager'
CONN_MGR_SERVICE = 'org.freedesktop.ipcf.ConnectionManager'

class JabberTextChannel(dbus.service.Object):
    def __init__(self, conn):
        self.conn = conn
        self.service_name = CHANNEL_SERVICE
        self.object_path = CHANNEL_OBJECT
#        self.bus_name = dbus.service.BusName(CHANNEL_SERVICE+
        pass

class JabberConnection(dbus.service.Object):
    def __init__(self, manager, account, conn_info):
        self.jid = xmpp.protocol.JID(account)
        if self.jid.getResource() == '':
            self.jid.setResource('IPCF')

        self.service_name = '.'.join((CONN_SERVICE, 'jabber', self.jid.getDomain(), self.jid.getNode(), self.jid.getResource()))
        self.object_path = '/'.join((CONN_OBJECT, 'jabber', self.jid.getDomain(), self.jid.getNode(), self.jid.getResource()))
        self.bus_name = dbus.service.BusName(self.service_name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)

        self.manager = manager
        self.password = conn_info['password']

        if conn_info.has_key('server'):
            if conn_info.has_key('port'):
                self.client = xmpp.client.Client(conn_info['server'], conn_info['port'])
            else:
                self.client = xmpp.client.Client(conn_info['server'])
        else:
            if conn_info.has_key('port'):
                self.client = xmpp.client.Client(self.jid.getDomain(), conn_info['port'])
            else:
                self.client = xmpp.client.Client(self.jid.getDomain())

        gobject.idle_add(self.connect)

    def connect(self):
        self.StatusChanged('connecting')

        if not self.client.connect():
            self.StatusChange('disconnected')

        if not self.client.auth(self.jid.getNode(), self.password, self.jid.getResource()):
            self.StatusChanged('disconnected')

        self.client.RegisterDisconnectHandler(self.disconnectHandler)
        self.client.RegisterHandler('iq', self.iqHandler)
        self.client.RegisterHandler('message', self.messageHandler)
        self.client.RegisterHandler('presence', self.presenceHandler)
        self.client.sendInitPresence()

        self.StatusChanged('connected')

        gobject.idle_add(self.poll)

        return False # run once

    def poll(self):
        if self.client.isConnected():
            self.client.Process(0.01)
            return True # keep running
        else:
            return False # stop running

    def disconnectHandler(self):
        if self.die:
            self.StatusChanged('disconnected')
        else:
            self.StatusChanged('connecting')
            self.client.reconnectAndReauth()

    def iqHandler(self, conn, node):
        pass

    def messageHandler(self, conn, node):
        pass

    def presenceHandler(self, conn, node):
        pass

    @dbus.service.signal(CONN_INTERFACE)
    def StatusChanged(self, status):
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self.status = status

    @dbus.service.method(CONN_INTERFACE)
    def GetStatus(self):
        return self.status

    @dbus.service.method(CONN_INTERFACE)
    def Disconnect(self):
        print "Disconnect called"
        self.die = True
        self.client.disconnect()

    @dbus.service.method(CONN_INTERFACE)
    def Send(self, recipient, message):
        self.client.send(xmppy.protocol.Message(recipient, message))

class JabberConnectionManager(dbus.service.Object):
    def __init__(self):
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.cheddar', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/cheddar')

        self.connections = []
        self.protos = set(['jabber'])

    @dbus.service.method(CONN_MGR_INTERFACE)
    def ListProtocols(self):
        return self.protos

    @dbus.service.method(CONN_MGR_INTERFACE)
    def Connect(self, proto, account, connect_info):
        if proto in self.protos:
            conn = JabberConnection(self, account, connect_info)
            self.connections.append(conn)
            return (conn.service_name, conn.object_path)
        else:
            raise IOError('Unknown protocol %s' % (proto))

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()
    mainloop.run()
