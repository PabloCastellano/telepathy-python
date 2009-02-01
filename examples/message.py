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
from telepathy.interfaces import (
    CHANNEL_TYPE_TEXT, CONN_INTERFACE, CHANNEL_INTERFACE,
    CONNECTION_INTERFACE_REQUESTS, CONNECTION_INTERFACE_SIMPLE_PRESENCE)

logging.basicConfig()

class Message:
    def __init__(self, *stuff):
        self.contact = None
        self.message = None

        assert len(stuff) in (0, 2)
        if len(stuff) == 2:
            self.contact = stuff[0]
            self.message = stuff[1]

        self.conn = connection_from_file(sys.argv[1],
            ready_handler=self.ready_cb)

        print "connecting"
        self.conn[CONN_INTERFACE].Connect()

    def ready_cb(self, conn):
        print "connected"
        conn[CONNECTION_INTERFACE_REQUESTS].connect_to_signal('NewChannels',
            self.new_channels_cb)

        # This is required for MSN.
        conn[CONNECTION_INTERFACE_SIMPLE_PRESENCE].SetPresence('available', '')

        if self.contact is not None:
            gobject.timeout_add(1000, self.send_message)

    def send_message(self):
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]

        print 'got handle %d for %s' % (handle, self.contact)

        self.conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel(dbus.Dictionary(
            {
                CHANNEL_INTERFACE + '.ChannelType': CHANNEL_TYPE_TEXT,
                CHANNEL_INTERFACE + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
                CHANNEL_INTERFACE + '.TargetHandle': handle
            }, signature='sv'))

    def run(self):
        print "main loop running"
        self.loop = gobject.MainLoop()

        try:
            self.loop.run()
        finally:
            self.conn[CONN_INTERFACE].Disconnect()

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def new_channels_cb(self, channels):
        for object_path, props in channels:
            channel_type = props[CHANNEL_INTERFACE + '.ChannelType']

            if channel_type != CHANNEL_TYPE_TEXT:
                return

            handle_type = props[CHANNEL_INTERFACE + '.TargetHandleType']
            handle = props[CHANNEL_INTERFACE + '.TargetHandle']

            print 'got text channel with handle (%d,%d)' % (handle_type, handle)
            channel = Channel(self.conn.service_name, object_path)

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
        # if we Disconnect() immediately, the message might not actually
        # make it to the network before the socket is shut down (this can
        # be the case in Gabble) - as a workaround, delay before disconnecting
        gobject.timeout_add(5000, self.quit)

    def send_error_cb(self, error, timestamp, type, text):
        print 'error sending message: code %d' % error
        self.quit()

if __name__ == '__main__':
    msg = Message(*sys.argv[2:])

    msg.run()
