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
LIST_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.ListChannel'

INDIVIDUAL_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.IndividualChannelInterface'
GROUP_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.GroupChannelInterface'
NAMED_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.NamedChannelInterface'
PRESENCE_CHANNEL_INTERFACE = 'org.freedesktop.ipcf.PresenceChannelInterface'

class Channel(dbus.service.Object):
    count = 0

    def __init__(self, conn, type):
        self.conn = conn
        self.object_path = self.conn.object_path+'/channel'+str(Channel.count)
        Channel.count += 1
        dbus.service.Object.__init__(self, self.conn.bus_name, self.object_path)

        self.type = type
        self.interfaces = set()
        self.members = set()

    @dbus.service.method(CHANNEL_INTERFACE)
    def Close(self):
        pass

    @dbus.service.signal(CHANNEL_INTERFACE)
    def Closed(self):
        print 'object_path: %s signal: Closed' % (self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE)
    def GetType(self):
        return dbus.String(self.type)

    @dbus.service.method(CHANNEL_INTERFACE)
    def GetInterfaces(self):
        return dbus.Array(self.interfaces, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE)
    def GetMembers(self):
        return dbus.Array(self.members, signature='s')

class IndividualInterface(object):
    def __init__(self, recipient):
        self.interfaces.add(INDIVIDUAL_CHANNEL_INTERFACE)
        self.members.add(recipient)
        self.recipient = recipient

class PresenceInterface(object):
    def __init__(self):
        self.interfaces.add(PRESENCE_CHANNEL_INTERFACE)

class GroupInterface(object):
    def __init__(self):
        self.interfaces.add(GROUP_CHANNEL_INTERFACE)

    @dbus.service.method(GROUP_CHANNEL_INTERFACE)
    def InviteMembers(self, members):
        pass

    @dbus.service.method(GROUP_CHANNEL_INTERFACE)
    def RemoveMembers(self, members):
        pass

    @dbus.service.signal(GROUP_CHANNEL_INTERFACE)
    def MembersChanged(self, added, removed):
        self.members.update(added)
        self.members.difference_update(removed)

"""
Base class for a simple TextChannel implementation.
to use, override sendCallback to send a mesage,
"""
class TextChannel(Channel):
    def __init__(self, connection):
        Channel.__init__(self, connection, TEXT_CHANNEL_INTERFACE)

        self.send_id = 0
        self.recv_id = 0
        self.pending_messages = {}

    def sendCallback(self, id, text):
        pass

    def stampMessage(self, id, text):
        timestamp = int(time.time())
        self.Sent(id, timestamp, text)

    def queueMessage(self, timestamp, text):
        id = self.recv_id
        self.recv_id += 1

        self.pending_messages[id] = (timestamp, text)
        self.Received(id, timestamp, text)


    @dbus.service.method(TEXT_CHANNEL_INTERFACE)
    def Send(self, text):
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.sendCallback, id, text)
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
        return dbus.Array(messages, signature='(iis)')

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE)
    def Sent(self, id, timestamp, text):
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE)
    def Received(self, id, timestamp, text):
        print 'object_path: %s signal: Received %d %d %s' % (self.object_path, id, timestamp, text)

"""
Base class to implement a connection object. 
override Disconnect to disconnect this connection
override RequestChannel to create the reuested channel types, or IOError if not
possible
"""

class Connection(dbus.service.Object):
    def __init__(self, manager, name_parts):
        self.service_name = '.'.join([CONN_SERVICE] + name_parts)
        self.object_path = '/'.join([CONN_OBJECT] + name_parts)
        self.bus_name = dbus.service.BusName(self.service_name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)

        self.channels = set()
        self.lists = {}
        self.manager = manager

    def addChannel(self, channel):
        self.channels.add(channel)
        self.NewChannel(channel.type, channel.object_path)

    @dbus.service.signal(CONN_INTERFACE)
    def StatusChanged(self, status):
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self.status = status

    @dbus.service.method(CONN_INTERFACE)
    def GetStatus(self):
        return self.status

    @dbus.service.method(CONN_INTERFACE)
    def Disconnect(self):
        self.disconnect()

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
        raise IOError('Unknown channel type %s' % type)

class ConnectionManager(dbus.service.Object):
    def __init__(self):
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.cheddar', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/cheddar')

        self.connections = set()
        self.protos = {}

    def __del__(self):
        print "explodes"
        dbus.service.Object.__del__(self)

    def disconnected(self, conn):
        self.connections.remove(conn)
        del conn

    @dbus.service.method(CONN_MGR_INTERFACE)
    def ListProtocols(self):
        return self.protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE)
    def Connect(self, proto, account, connect_info):
        if self.protos.has_key(proto):
            conn = self.protos[proto](self, account, connect_info)
            self.connections.add(conn)
            return (conn.service_name, conn.object_path)
        else:
            raise IOError('Unknown protocol %s' % (proto))

