import dbus.glib
import gobject
import logging
import sys

from time import sleep

from account import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_STATUS_CONNECTED,
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL)
from telepathy.interfaces import CHANNEL_TYPE_TEXT, CONN_INTERFACE

logging.basicConfig()

class TextChannel(Channel):
    def __init__(self, *stuff):
        Channel.__init__(self, *stuff)
        self.get_valid_interfaces().add(CHANNEL_TYPE_TEXT)

class Message:
    def __init__(self, conn, *stuff):
        self.conn = conn
        self.contact = None
        self.message = None

        assert len(stuff) in (0, 2)
        if len(stuff) == 2:
            self.contact = stuff[0]
            self.message = stuff[1]

        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        conn[CONN_INTERFACE].connect_to_signal('NewChannel',
            self.new_channel_cb)

    def run(self):
        print "main loop running"
        self.loop = gobject.MainLoop()
        self.loop.run()

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def status_changed_cb(self, state, reason):
        if state != CONNECTION_STATUS_CONNECTED:
            return
        print "connection became ready"

        if self.contact is not None:
            handle = conn[CONN_INTERFACE].RequestHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]

            print 'got handle %d for %s' % (handle, self.contact)

            conn[CONN_INTERFACE].RequestChannel(
                CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_CONTACT, handle, True,
                reply_handler=lambda *stuff: None,
                error_handler=self.request_channel_error_cb)

    def request_channel_error_cb(self, exception):
        print 'error:', exception
        self.quit()

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
            suppress_handler):
        if channel_type != CHANNEL_TYPE_TEXT:
            return

        print 'got text channel with handle (%d,%d)' % (handle_type, handle)
        channel = TextChannel(
            self.conn._dbus_object._named_service, object_path)

        channel[CHANNEL_TYPE_TEXT].connect_to_signal('Sent', self.sent_cb)
        channel[CHANNEL_TYPE_TEXT].connect_to_signal('Received', self.recvd_cb)
        channel[CHANNEL_TYPE_TEXT].connect_to_signal('SendError',
            self.send_error_cb)

        if self.message is not None:
            channel[CHANNEL_TYPE_TEXT].Send(
                CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, self.message)
        else:
            for message in channel[CHANNEL_TYPE_TEXT].ListPendingMessages(True):
                self.recvd_cb(*message)

    def recvd_cb(self, *args):
        print args
        id, timestamp, sender, type, flags, text = args
        print 'message #%d received from handle %d: """%s"""' \
                % (id, sender, text)
        self.quit()

    def sent_cb(self, timestamp, type, text):
        print 'message sent: """%s"""' % text
        gobject.timeout_add(1000, self.quit)

    def send_error_cb(self, error, timestamp, type, text):
        print 'error sending message: code %d' % error
        gobject.timeout_add(1000, self.quit)

if __name__ == '__main__':
    conn = connection_from_file(sys.argv[1])

    msg = Message(conn, *sys.argv[2:])

    print "connecting"
    conn[CONN_INTERFACE].Connect()

    try:
        msg.run()
    except KeyboardInterrupt:
        print "killed"

    conn[CONN_INTERFACE].Disconnect()
