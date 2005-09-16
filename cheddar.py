#!/usr/bin/env python

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import random
import xmpp

CONN_INTERFACE = 'org.freedesktop.ipcf.connection'
CONN_OBJECT = '/org/freedesktop/ipcf/connection'
CONN_SERVICE = 'org.freedesktop.ipcf.connection'

CONN_MGR_INTERFACE = 'org.freedesktop.ipcf.connectionmanager'
CONN_MGR_OBJECT = '/org/freedesktop/ipcf/connectionmanager'
CONN_MGR_SERVICE = 'org.freedesktop.ipcf.connectionmanager'

class JabberTextChannel(dbus.service.Object):
    def __init__(self, conn):
        self.conn = conn
        self.service_name = CHANNEL_SERVICE
        self.object_path = CHANNEL_OBJECT
#        self.bus_name = dbus.service.BusName(CHANNEL_SERVICE+
        pass

class JabberConnection(dbus.service.Object):
    count = 0

    def __init__(self, manager, id, account, conn_info):
        self.manager = manager
        self.id = id
        self.service_name = CONN_SERVICE+'.jabber'+str(JabberConnection.count)
        self.object_path = CONN_OBJECT+'/jabber'+str(JabberConnection.count)
        self.bus_name = dbus.service.BusName(CONN_SERVICE+'.jabber'+str(JabberConnection.count), bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)
        JabberConnection.count += 1

        self.jid = xmpp.protocol.JID(account)
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

    def poll(self):
        if self.client.isConnected():
            self.client.Process(0.01)
            return True
        else:
            return False

    def messageHandler(self, conn, node):
        pass

    def presenceHandler(self, conn, node):
        pass

    def connect(self):
        if not self.client.connect():
            self.manager.ConnectionError(self.identifier, 'Connection failed')

        if not self.client.auth(self.jid.getNode(), self.password, self.jid.getResource()):
            self.manager.ConnectionError(self.identifier, 'Authenticaton failed')

        self.client.RegisterHandler('message', self.messageHandler)
        self.client.RegisterHandler('presence', self.presenceHandler)
        self.client.sendInitPresence()

        self.manager.Connected(self.id, self.service_name, self.object_path)

        gobject.idle_add(self.poll)

        return False

    @dbus.service.method(CONN_INTERFACE)
    def woot(self):
        print 'woot'

class JabberConnectionManager(dbus.service.Object):
    protos = set(['jabber'])

    def __init__(self):
        self.connections = []
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.cheddar', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/cheddar')

    @dbus.service.method(CONN_MGR_INTERFACE)
    def list_protocols(self):
        return protos

    @dbus.service.method(CONN_MGR_INTERFACE)
    def make_connection(self, proto, account, connect_info):
        if proto in JabberConnectionManager.protos:
            id = random.randint(0, 2^16)
            conn = JabberConnection(self, id, account, connect_info)
            self.connections.append(conn)
            gobject.idle_add(conn.connect)
            return id
        else:
            raise IOError('Unknown protocol %s' % (proto))

    @dbus.service.signal(CONN_MGR_INTERFACE)
    def Connected(self, identifier, serv_name, obj_path):
        print 'Sending Connected signal: %s connected as (%s, %s)' % (identifier, serv_name, obj_path)

    @dbus.service.signal(CONN_MGR_INTERFACE)
    def ConnectionError(self, identifier, message):
        print "ConnectionError on %s: %s" % (identifier, message)

if __name__ == '__main__':
    random.seed()
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()
    mainloop.run()
