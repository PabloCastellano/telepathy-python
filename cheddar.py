#!/usr/bin/env python

import calendar
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import time
import xmpp

CONN_MGR_INTERFACE = 'org.freedesktop.ipcf.ConnectionManager'
CONN_MGR_OBJECT = '/org/freedesktop/ipcf/ConnectionManager'
CONN_MGR_SERVICE = 'org.freedesktop.ipcf.ConnectionManager'

CONN_INTERFACE = 'org.freedesktop.ipcf.Connection'
CONN_OBJECT = '/org/freedesktop/ipcf/Connection'
CONN_SERVICE = 'org.freedesktop.ipcf.Connection'

CHANNEL_INTERFACE = 'org.freedesktop.ipcf.Channel'
TEXT_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.TextChannel'

class JabberChannel(dbus.service.Object):
    count = 0

    def __init__(self, conn):
        self.conn = conn
        self.object_path = self.conn.object_path+'/channel'+str(JabberChannel.count)
        JabberChannel.count += 1
        dbus.service.Object.__init__(self, self.conn.bus_name, self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE)
    def Close(self):
        pass

    @dbus.service.signal(CHANNEL_INTERFACE)
    def Closed(self):
        print 'object_path: %s signal: Closed' % (self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE)
    def GetType(self):
        assert(self.type != '')
        return self.type

    @dbus.service.method(CHANNEL_INTERFACE)
    def GetInterfaces(self):
        assert(self.interfaces != None)
        return self.interfaces.keys()

class JabberTextChannel(JabberChannel):
    def __init__(self, conn, interfaces):
        JabberChannel.__init__(self, conn)

        self.type = TEXT_CHANNEL_INTERFACE
        self.interfaces = interfaces

        self.send_id = 0
        self.recv_id = 0
        self.pending_messages = {}

        for i in interfaces.keys():
            if i == 'recipient':
                self.recipient = interfaces[i]
            print i, interfaces[i]

    def send_callback(self, id, text):
        msg = xmpp.protocol.Message(self.recipient, text)
        self.conn.client.send(msg)
        timestamp = int(time.time())
        self.Sent(id, timestamp, text)

    def receive_callback(self, node):
        # todo: match by resource/subject if possible?
        # only handle message if it's for us
        sender = node.getFrom()
        if not sender.bareMatch(self.interfaces['recipient']):
            return False

        id = self.recv_id
        timestamp = int(time.time())
        text = node.getBody()
        self.recv_id += 1

        delaytime = node.getTimestamp()
        if delaytime != None:
            try:
                tuple = time.strptime(delaytime, '%Y%m%dT%H:%M:%S')
                timestamp = int(calendar.timegm(tuple))
            except ValueError:
                print "Delayed message timestamp %s invalid, using current time" % delaytime

        self.pending_messages[id] = (timestamp, text)
        self.Received(id, timestamp, text)

        return True

    @dbus.service.method(TEXT_CHANNEL_INTERFACE)
    def Send(self, text):
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.send_callback, id, text)
        return id

    @dbus.service.method(TEXT_CHANNEL_INTERFACE)
    def AcknowledgePendingMessage(self, id):
        if self.pending_messages.has_key(id):
            del self.pending_messages[id]
            return True
        else:
            return False

    @dbus.service.method(TEXT_CHANNEL_INTERFACE)
    def ListPendingMessages(self):
        messages = []
        for id in self.pending_messages.keys():
            (timestamp, text) = self.pending_messages[id]
            message = (id, timestamp, text)
            messages.append(message)
        messages.sort(cmp=lambda x,y:cmp(x[1], y[1]))
        return dbus.Array(messages, signature='(iis)h')

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE)
    def Sent(self, id, timestamp, text):
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE)
    def Received(self, id, timestamp, text):
        print 'object_path: %s signal: Received %d %d %s' % (self.object_path, id, timestamp, text)

class JabberConnection(dbus.service.Object):
    def __init__(self, manager, account, conn_info):
        self.jid = xmpp.protocol.JID(account)
        if self.jid.getResource() == '':
            self.jid.setResource('IPCF')

        parts = []
        for j in ['jabber', self.jid.getDomain(), self.jid.getNode(), self.jid.getResource()]:
            parts += j.split('.')[::-1]
        self.service_name = '.'.join([CONN_SERVICE] + parts)
        self.object_path = '/'.join([CONN_OBJECT] + parts)
        self.bus_name = dbus.service.BusName(self.service_name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)

        self.channels = set()
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

    def createChannel(self, type, interfaces):
        if type == TEXT_CHANNEL_INTERFACE:
            channel = JabberTextChannel(self, interfaces)
            self.channels.add(channel)
            self.NewChannel(type, channel.object_path)
            return channel
        else:
            return None

    def disconnectHandler(self):
        if self.die:
            self.StatusChanged('disconnected')
            gobject.idle_add(self.manager.disconnected, self)
        else:
            self.StatusChanged('connecting')
            self.client.reconnectAndReauth()

    def iqHandler(self, conn, node):
        pass

    def messageHandler(self, conn, node):
        handled = False

        for chan in self.channels:
            if chan.type == TEXT_CHANNEL_INTERFACE:
                handled = chan.receive_callback(node)
                if handled:
                    break

        if not handled:
            interfaces = {'recipient':node.getFrom()}
            chan = self.createChannel(TEXT_CHANNEL_INTERFACE, interfaces)
            chan.receive_callback(node)

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

    @dbus.service.signal(CONN_INTERFACE)
    def NewChannel(self, type, object_path):
        print 'service_name: %s object_path: %s signal: NewChannel %s %s' % (self.service_name, self.object_path, type, object_path)

    @dbus.service.method(CONN_INTERFACE)
    def ListChannels(self):
        ret = []
        for channel in self.channels:
            chan = (channel.type, channel.object_path)
            ret.append(chan)
        return dbus.Array(ret, signature='(ss)')

    @dbus.service.method(CONN_INTERFACE)
    def RequestChannel(self, type, interfaces):
        chan = self.createChannel(type, interfaces)
        if chan != None:
            return chan.object_path
        else:
            raise IOError('Unknown channel type %s' % type)

class JabberConnectionManager(dbus.service.Object):
    def __init__(self):
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.cheddar', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/cheddar')

        self.connections = set()
        self.protos = set(['jabber'])

    def __del__(self):
        print "explodes"
        dbus.service.Object.__del__(self)

    def disconnected(self, conn):
        self.connections.remove(conn)
        del conn

    @dbus.service.method(CONN_MGR_INTERFACE)
    def ListProtocols(self):
        return self.protos

    @dbus.service.method(CONN_MGR_INTERFACE)
    def Connect(self, proto, account, connect_info):
        if proto in self.protos:
            conn = JabberConnection(self, account, connect_info)
            self.connections.add(conn)
            return (conn.service_name, conn.object_path)
        else:
            raise IOError('Unknown protocol %s' % (proto))

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()
    mainloop.run()
