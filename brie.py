#!/usr/bin/env python

import dbus
import dbus.glib
import dbus.service

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import gobject
import pyxmpp.jid
import pyxmpp.jabber.client
import telepathy
import telepathy.server
import time
import traceback

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
        
        self.idle()
        return True

    def stream_created(self, stream):
        print "stream created"
        print stream
        #fd = stream.fileno()

    def session_started(self):
        print "session started"
        pyxmpp.jabber.client.JabberClient.session_started(self)
        self.StatusChanged('connected', 'requested')
        stream=self.get_stream()
        stream.set_message_handler('normal', self.message_handler)

    def stream_io_cb(self, fd, condition):
        print "stream io cb"
        try:
            stream = self.get_stream()
            stream.process()
        except Exception, e:
            print "exception in stream_io_cb"
            print e.__class__
            print e
            traceback.print_exc()
            return False
        return True

    def connected(self):
        print "connected"

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


class JabberConnectionManager(telepathy.server.ConnectionManager):
    def __init__(self):
        telepathy.server.ConnectionManager.__init__(self, 'brie')
        self._protos['jabber'] = JabberConnection

if __name__ == '__main__':
    manager = JabberConnectionManager()
    mainloop = gobject.MainLoop()
    mainloop.run()
