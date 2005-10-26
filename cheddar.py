#!/usr/bin/env python

import calendar
import gobject
import time
import xmpp

import telepathy.server

class JabberRosterChannel(telepathy.server.ChannelTypeList, telepathy.server.ChannelInterfaceGroup, telepathy.server.ChannelInterfaceNamed):
    def __init__(self, conn):
        telepathy.server.Channel.__init__(self, conn, telepathy.server.CHANNEL_TYPE_LIST)
        telepathy.server.GroupChannelInterface.__init__(self)
        telepathy.server.NamedChannelInterface.__init__(self, 'subscribe')

    def InviteMembers(self, members):
        print members

class JabberIMChannel(telepathy.server.ChannelTypeText, telepathy.server.ChannelInterfaceIndividual):
    def __init__(self, conn, recipient):
        telepathy.server.ChannelTypeText.__init__(self, conn)
        telepathy.server.ChannelInterfaceIndividual.__init__(self, recipient)

    def sendCallback(self, id, text):
        msg = xmpp.protocol.Message(self.recipient, text)
        self.conn.client.send(msg)
        self.stampMessage(id, text)

    def messageHandler(self, node):
        # todo: match by resource/subject if possible?
        # only handle message if it's for us
        print "messageHandler", node

        sender = node.getFrom()
        if not sender.bareMatch(self.recipient):
            return False

        # ignore typing notifications et al
        # todo, get active tag and check this properly
        if not node.getBody():
            return True

        timestamp = int(time.time())

        delaytime = node.getTimestamp()
        if delaytime != None:
            try:
                tuple = time.strptime(delaytime, '%Y%m%dT%H:%M:%S')
                timestamp = int(calendar.timegm(tuple))
            except ValueError:
                print "Delayed message timestamp %s invalid, using current time" % delaytime

        text = node.getBody()
        print "queuingMessage", timestamp, sender, text
        self.queueMessage(timestamp, sender.getStripped(), text)

        return True

class JabberConnection(telepathy.server.Connection):
    def __init__(self, manager, account, conn_info):
        self.jid = xmpp.protocol.JID(account)
        if self.jid.getResource() == '':
            self.jid.setResource('Telepathy')

        parts = []
        for j in ['jabber', self.jid.getDomain(), self.jid.getNode(), self.jid.getResource()]:
            parts += j.split('.')[::-1]

        telepathy.server.Connection.__init__(self, manager, 'jabber', account, parts)

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
            self.StatusChanged('disconnected')

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
            gobject.idle_add(self.manager.disconnected, self)
        else:
            self.StatusChanged('connecting')
            self.client.reconnectAndReauth()

    def iqHandler(self, conn, node):
        pass

    def messageHandler(self, conn, node):
        handled = False

        for chan in self.channels:
            try:
                handled = chan.messageHandler(node)
                if handled:
                    break
            except AttributeError:
                pass

        if not handled:
            chan = JabberIMChannel(self, node.getFrom())
            self.addChannel(chan)
            chan.messageHandler(node)

    def presenceHandler(self, conn, node):
        print "presence", node
        pass

    def Disconnect(self):
        print "Disconnect called"
        self.die = True
        self.client.disconnect()

    def RequestChannel(self, type, interfaces):
        chan = None

        if type == LIST_CHANNEL_INTERFACE:
            pass
#            if self.lists.has_key( == None:
#                self.contact_list = JabberRosterChannel(self)
#            chan = self.contact_list
        if type == TEXT_CHANNEL_INTERFACE:
            if interfaces.keys() == [INDIVIDUAL_CHANNEL_INTERFACE]:
                chan = JabberIMChannel(self, interfaces[INDIVIDUAL_CHANNEL_INTERFACE])

        if chan != None:
            if not chan in self.channels:
                self.addChannel(chan)
            return chan.object_path
        else:
            raise IOError('Unknown channel type %s' % type)

class JabberConnectionManager(telepathy.server.ConnectionManager):
    def __init__(self):
        telepathy.server.ConnectionManager.__init__(self, "cheddar")
        self.protos['jabber'] = JabberConnection

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()
    mainloop.run()
