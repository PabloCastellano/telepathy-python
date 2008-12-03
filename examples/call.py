import dbus
import dbus.glib
import gobject
import sys

from account import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE, CONNECTION_HANDLE_TYPE_CONTACT,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED,
    MEDIA_STREAM_TYPE_AUDIO, MEDIA_STREAM_TYPE_VIDEO)
from telepathy.interfaces import (
    CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_STREAMED_MEDIA,
    CONN_INTERFACE, CONN_INTERFACE_CAPABILITIES)

import logging
logging.basicConfig()


def get_stream_engine():
    bus = dbus.Bus()
    return bus.get_object(
        'org.freedesktop.Telepathy.StreamEngine',
        '/org/freedesktop/Telepathy/StreamEngine')

class Call:
    def __init__(self, account_file):
        self.conn = connection_from_file(account_file,
            ready_handler=self.ready_cb)
        self.channel = None

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        self.conn[CONN_INTERFACE].connect_to_signal('NewChannel',
            self.new_channel_cb)

    def run_main_loop(self):
        self.loop = gobject.MainLoop()
        self.loop.run()

    def run(self):
        print "connecting"
        self.conn[CONN_INTERFACE].Connect()

        try:
            self.run_main_loop()
        except KeyboardInterrupt:
            print "killed"

            if self.channel:
                print "closing channel"
                self.channel[CHANNEL_INTERFACE].Close()

        try:
            print "disconnecting"
            self.conn[CONN_INTERFACE].Disconnect()
        except dbus.DBusException:
            pass

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_DISCONNECTED:
            print 'connection closed'
            self.quit()

    def ready_cb(self, conn):
        pass

    def request_channel_error_cb(self, exception):
        print 'error:', exception
        self.quit()

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
            suppress_handler):
        if channel_type != CHANNEL_TYPE_STREAMED_MEDIA:
            return

        self.chan_handle_type = handle_type
        self.chan_handle = handle

        print "new streamed media channel"
        Channel(self.conn.service_name, object_path,
                ready_handler=self.channel_ready_cb)

    def channel_ready_cb(self, channel):
        print "channel ready"
        channel[CHANNEL_INTERFACE].connect_to_signal('Closed', self.closed_cb)
        channel[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged',
            self.members_changed_cb)
        channel[CHANNEL_TYPE_STREAMED_MEDIA].connect_to_signal(
            'StreamError', self.stream_error_cb)

        stream_engine = get_stream_engine()
        handler = dbus.Interface(stream_engine,
            'org.freedesktop.Telepathy.ChannelHandler')
        handler.HandleChannel(
            self.conn.service_name,
            self.conn.object_path,
            CHANNEL_TYPE_STREAMED_MEDIA,
            channel.object_path,
            self.chan_handle_type,
            self.chan_handle)

        self.channel = channel

    def stream_error_cb(self, *foo):
        print 'error: %r' % (foo,)
        self.channel.close()

    def closed_cb(self):
        print "channel closed"
        self.quit()

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        print 'MembersChanged', (
            added, removed, local_pending, remote_pending, actor, reason)

class OutgoingCall(Call):
    def __init__(self, account_file, contact):
        Call.__init__(self, account_file)
        self.contact = contact
        self.calling = False

    def got_handle_capabilities(self, caps):
        if self.calling:
            return
        for c in caps:
            if c[1] == CHANNEL_TYPE_STREAMED_MEDIA:
                self.calling = True
                self.conn[CONN_INTERFACE].RequestChannel(
                    CHANNEL_TYPE_STREAMED_MEDIA, CONNECTION_HANDLE_TYPE_NONE,
                    0, True,
                    reply_handler=lambda *stuff: None,
                    error_handler=self.request_channel_error_cb)
                return
        print "No media capabilities found, waiting...."

    def capabilities_changed_cb(self, caps):
        for x in caps:
            if x[0] == self.handle:
                self.got_handle_capabilities([[x[0],x[1],x[3],x[5]]])

    def ready_cb(self, conn):
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]
        self.handle = handle

        self.conn[CONN_INTERFACE_CAPABILITIES].connect_to_signal(
            'CapabilitiesChanged', self.capabilities_changed_cb)
        self.got_handle_capabilities(
            self.conn[CONN_INTERFACE_CAPABILITIES].GetCapabilities([handle]))

    def channel_ready_cb(self, channel):
        Call.channel_ready_cb(self, channel)

        channel[CHANNEL_INTERFACE_GROUP].AddMembers([self.handle], "")

        print "requesting audio/video streams"

        try:
            channel[CHANNEL_TYPE_STREAMED_MEDIA].RequestStreams(
                self.handle,
                [MEDIA_STREAM_TYPE_AUDIO, MEDIA_STREAM_TYPE_VIDEO]);
        except dbus.DBusException, e:
            print "failed:", e
            print "requesting audio stream"

            try:
                channel[CHANNEL_TYPE_STREAMED_MEDIA].RequestStreams(
                    self.handle, [MEDIA_STREAM_TYPE_AUDIO]);
            except dbus.DBusException, e:
                print "failed:", e
                print "giving up"
                self.quit()

class IncomingCall(Call):
    def ready_cb(self, conn):
        self.conn[CONN_INTERFACE_CAPABILITIES].AdvertiseCapabilities(
            [(CHANNEL_TYPE_STREAMED_MEDIA, 3)], [])

    def channel_ready_cb(self, channel):
        Call.channel_ready_cb(self, channel)

        print "accepting incoming call"
        pending = channel[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers()
        channel[CHANNEL_INTERFACE_GROUP].AddMembers(pending, "")

    def closed_cb(self):
        print "channel closed"
        self.channel = None
        print "waiting for incoming call"

if __name__ == '__main__':
    args = sys.argv[1:]

    assert len(args) in (1, 2)

    if len(args) > 1:
        call = OutgoingCall(args[0], args[1])
    else:
        call = IncomingCall(args[0])

    call.run()
