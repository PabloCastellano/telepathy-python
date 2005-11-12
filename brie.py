#!/usr/bin/env python

import dbus
import dbus.glib
import dbus.service

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import gobject
import pyxmpp.jid
import pyxmpp.jabber.client
import signal
import telepathy.server
import time
import traceback

from telepathy import *

class JabberIMChannel(telepathy.server.ChannelTypeText, telepathy.server.ChannelInterfaceIndividual):
    def __init__(self, conn, recipient):
        self._jid = pyxmpp.jid.JID(recipient).bare()
        self._recv_id = 0

        telepathy.server.ChannelTypeText.__init__(self, conn)
        telepathy.server.ChannelInterfaceIndividual.__init__(self, unicode(self._jid))

    def message_handler(self, stanza):
        sender = stanza.get_from().bare()

        if not sender == self._jid:
            return False

        id = self._recv_id
        timestamp = int(time.time())
        sender = unicode(sender)
        type = 'normal'
        text = unicode(stanza.get_body())

        self.Received(id, timestamp, sender, type, text)
        self._recv_id += 1

        return True

    def Send(self, type, text):
        if type != 'normal':
            raise telepathy.NotImplemented('only the normal message type is currently supported')
        msg = pyxmpp.message.Message(to_jid=self._jid, body=text, stanza_type=type)
        self._conn.get_stream().send(msg)

class JabberConnection(telepathy.server.Connection, pyxmpp.jabber.client.JabberClient):
    _protocol_parameters = {'server':'s', 'port':'q', 'password':'s'}

    def __init__(self, manager, account, parameters):
        self._die = False
        self._manager = manager

        jid = pyxmpp.jid.JID(account)
        if not jid.resource:
            jid = pyxmpp.jid.JID(jid.node, jid.domain, 'Telepathy')

        for (parm, value) in parameters.iteritems():
            if parm in self._protocol_parameters.keys():
                sig = self._protocol_parameters[parm]
                if sig == 's':
                    if not isinstance(value, unicode):
                        raise telepathy.InvalidArgument('incorrect type to %s parameter, got %s, expected dbus.String' % (parm, type(value)))
                elif sig == 'q':
                    if not isinstance(value, int):
                        raise telepathy.InvalidArgument('incorrect type to %s parameter, got %s, expected dbus.UInt16' % (parm, type(value)))
                else:
                    raise TypeError('unknown type signature %s in _protocol_parameters' % type)
            else:
                raise telepathy.InvalidArgument('unknown parameter name %s' % parm)

        if not 'password' in parameters:
            raise telepathy.InvalidArgument('required parameter \'password\' not given')

        parts = []
        for j in ['jabber', jid.domain, jid.node, jid.resource]:
            parts += j.split('.')[::-1]

        telepathy.server.Connection.__init__(self, 'jabber', jid.as_unicode(), parts)

        del parts

        # this passes in jid, password, server and port for us. yay. :)
        # we need to do this because u'foo' isn't accepted by **keywords
        parameters = dict((str(k), v) for (k, v) in parameters.iteritems())
        parameters['jid'] = jid
        pyxmpp.jabber.client.JabberClient.__init__(self, **parameters)

        gobject.idle_add(self.connect_cb)
        gobject.timeout_add(500, self.idle_cb)

    def connect_cb(self):
        print "connect cb"
        self.connect()
        socket = self.get_socket()

        flags = gobject.IO_IN ^ gobject.IO_ERR ^ gobject.IO_HUP
        gobject.io_add_watch(socket, flags, self.stream_io_cb)

        return False

    def idle_cb(self):
        if self._status == CONNECTION_STATUS_DISCONNECTED:
            print "removing idle cb"
            return False

        self.idle()

        return True

    def stream_created(self, stream):
        print "stream created"

    def session_started(self):
        print "session started"
        pyxmpp.jabber.client.JabberClient.session_started(self)

        # set up handlers for <presence/> stanzas
        self.stream.set_presence_handler("available",self.presence_handler)
        self.stream.set_presence_handler("unavailable",self.presence_handler)

        # set up handlers for <presence/> stanzas which deal with subscriptions
        self.stream.set_presence_handler("subscribe",self.subscription_handler)
        self.stream.set_presence_handler("subscribed",self.subscription_handler)
        self.stream.set_presence_handler("unsubscribe",self.subscription_handler)
        self.stream.set_presence_handler("unsubscribed",self.subscription_handler)

        # set up handler for <message/> stanzas
        self.stream.set_message_handler('normal', self.message_handler)

        self.StatusChanged(CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_REASON_REQUESTED)

    def stream_io_cb(self, fd, condition):
        print "stream io cb, condition", condition

        try:
            stream = self.get_stream()
            stream.process()
        except Exception, e:
            print "exception in stream_io_cb"
            print e.__class__
            print e
            traceback.print_exc()
            return False

        if self._status == CONNECTION_STATUS_DISCONNECTED:
            print "removing stream io cb"
            return False

        return True

    def connected(self):
        print "connected"

    def roster_updated(self, item=None):
        pyxmpp.jabber.client.JabberClient.roster_updated(self, item)

        print "roster update, item=%s, roster=%s" % (item, self.roster)
        if self.roster:
            for i in self.roster.get_items():
                print "roster item:", i

    def presence_handler(self, stanza):
        """Handle 'available' (without 'type') and 'unavailable' <presence/>."""
        msg=u"%s has become " % (stanza.get_from())
        t=stanza.get_type()
        if t=="unavailable":
            msg+=u"unavailable"
        else:
            msg+=u"available"

        show=stanza.get_show()
        if show:
            msg+=u"(%s)" % (show,)

        status=stanza.get_status()
        if status:
            msg+=u": "+status
        print msg

    def subscription_handler(self, stanza):
        """Handle subscription control <presence/> stanzas -- acknowledge
        them."""
        msg=unicode(stanza.get_from())
        t=stanza.get_type()
        if t=="subscribe":
            msg+=u" has requested subscription to our presence."
        elif t=="subscribed":
            msg+=u" has accepted our presence subscription request."
        elif t=="unsubscribe":
            msg+=u" has cancelled subscription to our presence."
        elif t=="unsubscribed":
            msg+=u" has cancelled our subscription of his presence."

        print msg
        p=stanza.make_accept_response()
        self.stream.send(p)
        return True

    def message_handler(self, stanza):
        subject=stanza.get_subject()
        body=stanza.get_body()
        t=stanza.get_type()

        print u'Message from %s received.' % (unicode(stanza.get_from(),)),
        if subject:
            print u'Subject: "%s".' % (subject,),
        if body:
            print u'Body: "%s".' % (body,),
        if t:
            print u'Type: "%s".' % (t,)
        else:
            print u'Type: "normal".' % (t,)

        handled = False

        for chan in self._channels:
            if getattr(chan, 'message_handler', None):
                handled = chan.message_handler(stanza)
                if handled:
                    break

        if not handled:
            chan = JabberIMChannel(self, stanza.get_from())
            self.add_channel(chan, requested=False)
            handled = chan.message_handler(stanza)

        return handled

    def Disconnect(self):
        self._die = True
        self.disconnect()

    def disconnected(self):
        print "disconnected"
        if self._die:
            self.StatusChanged(CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_REASON_REQUESTED)
            gobject.idle_add(self._manager.disconnected, self)
        else:
            self.StatusChanged(CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_REASON_REQUESTED)
            gobject.idle_add(self.connect_cb())

    def RequestChannel(self, type, interfaces):
        chan = None

        if type == CHANNEL_TYPE_TEXT:
            if interfaces.keys() == [CHANNEL_INTERFACE_INDIVIDUAL]:
                recipient = interfaces[CHANNEL_INTERFACE_INDIVIDUAL]
                jid = pyxmpp.jid.JID(recipient).bare()

                for c in self._channels:
                    if isinstance(c, JabberIMChannel):
                        if c._members == [jid]:
                            chan = c
                            break

                chan = JabberIMChannel(self, jid)
            else:
                raise telepathy.NotAvailable('requested interfaces %s unavailable' % interfaces.keys())
        else:
            raise telepathy.NotImplemented('unknown channel type %s', type)

        assert(chan)

        if not chan in self._channels:
            self.add_channel(chan, requested=True)

        return chan._object_path


class JabberConnectionManager(telepathy.server.ConnectionManager):
    def __init__(self):
        telepathy.server.ConnectionManager.__init__(self, 'brie')
        self._protos['jabber'] = JabberConnection

    def quit(self):
        for c in self._connections:
            c.Disconnect()

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()

    def quit_cb():
        manager.quit()
        mainloop.quit()

    def sigterm_cb():
        gobject.idle_add(quit_cb)

    signal.signal(signal.SIGTERM, sigterm_cb)

    while mainloop.is_running():
        try:
            mainloop.run()
        except KeyboardInterrupt:
            quit_cb()
