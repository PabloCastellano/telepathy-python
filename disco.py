#!/usr/bin/python

"""Simple Jabber client that sends disco#info requests."""

import ConfigParser
import sys

import gobject

import pyxmpp.jid
import pyxmpp.jabber.client
import pyxmpp.iq

import libxml2

loop = None

def indent(s):
    return ''.join(['  %s\n' % line for line in s.splitlines()])

def xml_pp(s):
    node = libxml2.parseDoc(s).getRootElement()
    print indent(node.serialize(format=1)).rstrip()

class JabberClient(pyxmpp.jabber.client.JabberClient):
    def __init__(self, target_jid, **kw):
        self.target_jid = target_jid
        pyxmpp.jabber.client.JabberClient.__init__(self, **kw)
        gobject.idle_add(self.cb_connect)
        gobject.idle_add(self.cb_idle)

    def cb_connect(self):
        self.connect()
        socket = self.get_socket()
        flags = gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP
        gobject.io_add_watch(socket, flags, self.cb_io)
        gobject.timeout_add(500, self.cb_send_iq)

    def cb_send_iq(self):
        iq = pyxmpp.iq.Iq(
            from_jid=self.stream.my_jid,
            to_jid=self.target_jid,
            stanza_type='get')
        iq.new_query('http://jabber.org/protocol/disco#info')
        print 'sending:'
        xml_pp(iq.serialize())
        self.stream.set_response_handlers(
            iq, self.cb_iq_result, self.cb_iq_error, self.cb_iq_timeout, 10)
        self.stream.send(iq)
        return False

    def cb_idle(self):
        self.idle()
        return True

    def cb_io(self, fd, condition):
        stream = self.get_stream()
        stream.process()
        return True

    def cb_iq_result(self, stanza):
        print 'result:'
        xml_pp(stanza.serialize())
        loop.quit()

    def cb_iq_error(self, stanza):
        print 'error:'
        xml_pp(stanza.serialize())
        loop.quit()

    def cb_iq_timeout(self, arg1, arg2):
        print 'timeout'
        loop.quit()

def read_config(path):
    parser = ConfigParser.SafeConfigParser()
    parser.read(path)
    jid = parser.get('jabber', 'jid')
    password = parser.get('jabber', 'password')
    return jid, password

if __name__ == '__main__':
    loop = gobject.MainLoop()
    jid, password = read_config('config')
    client = JabberClient(
        target_jid=sys.argv[1],
        jid=pyxmpp.jid.JID(jid),
        password=password)
    loop.run()

