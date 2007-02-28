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


def proxy_get_object_path(proxy):
    if getattr(dbus, 'version', (0,0,0)) < (0, 80):
        # non-public API in dbus-python < 0.80
        return proxy._object_path
    else:
        # actually official API in 0.80+
        return proxy.__dbus_object_path__


def proxy_get_service_name(proxy):
    # FIXME: using non-public API
    return proxy._named_service


def get_stream_engine():
    bus = dbus.Bus()
    return bus.get_object(
        'org.freedesktop.Telepathy.StreamEngine',
        '/org/freedesktop/Telepathy/StreamEngine')

class Call:
    def __init__(self, conn, options):
        self.conn = conn
        self.options = options
        self.channel = None

        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        conn[CONN_INTERFACE].connect_to_signal('NewChannel',
            self.new_channel_cb)

    def run(self):
        self.loop = gobject.MainLoop()

        try:
            self.loop.run()
        except KeyboardInterrupt:
            print "killed"

            if self.channel:
                print "closing channel"
                self.channel[CHANNEL_INTERFACE].Close()

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_DISCONNECTED:
            print 'connection closed'
            self.quit()

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
        Channel(proxy_get_service_name(self.conn._dbus_object), object_path,
                ready_handler=self.channel_ready_cb)

    def channel_ready_cb(self, channel):
        print "channel ready"
        channel[CHANNEL_INTERFACE].connect_to_signal('Closed', self.closed_cb)
        channel[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged',
            self.members_changed_cb)

        stream_engine = get_stream_engine()
        handler = dbus.Interface(stream_engine,
            'org.freedesktop.Telepathy.ChannelHandler')
        handler.HandleChannel(
            proxy_get_service_name(self.conn._dbus_object),
            proxy_get_object_path(self.conn._dbus_object),
            CHANNEL_TYPE_STREAMED_MEDIA,
            proxy_get_object_path(channel._dbus_object),
            self.chan_handle_type,
            self.chan_handle)

        self.channel = channel

    def closed_cb(self):
        print "channel closed"
        self.quit()

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        print 'MembersChanged', (
            added, removed, local_pending, remote_pending, actor, reason)

class OutgoingCall(Call):
    def __init__(self, conn, contact, options):
        Call.__init__(self, conn, options)
        self.contact = contact

    def status_changed_cb (self, state, reason):
        if state == CONNECTION_STATUS_CONNECTED:
            handle = self.conn[CONN_INTERFACE].RequestHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]
            self.handle = handle

            print 'got handle %d for %s' % (handle, self.contact)

            # hack
            import time
            time.sleep(5)

            if self.options.directed:
                self.conn[CONN_INTERFACE].RequestChannel(
                    CHANNEL_TYPE_STREAMED_MEDIA,
                    CONNECTION_HANDLE_TYPE_CONTACT, handle, True,
                    reply_handler=lambda *stuff: None,
                    error_handler=self.request_channel_error_cb)
            else:
                self.conn[CONN_INTERFACE].RequestChannel(
                    CHANNEL_TYPE_STREAMED_MEDIA, CONNECTION_HANDLE_TYPE_NONE,
                    0, True,
                    reply_handler=lambda *stuff: None,
                    error_handler=self.request_channel_error_cb)

        Call.status_changed_cb(self, state, reason)

    def channel_ready_cb(self, channel):
        Call.channel_ready_cb(self, channel)

        if not self.options.directed:
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
    def status_changed_cb (self, state, reason):
        if state == CONNECTION_STATUS_CONNECTED:
            print "waiting for incoming call"

            self.conn._valid_interfaces.add(CONN_INTERFACE_CAPABILITIES)
            self.conn[CONN_INTERFACE_CAPABILITIES].AdvertiseCapabilities(
                [(CHANNEL_TYPE_STREAMED_MEDIA, 3)], [])

        Call.status_changed_cb(self, state, reason)

    def channel_ready_cb(self, channel):
        Call.channel_ready_cb(self, channel)

        print "accepting incoming call"
        pending = channel[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers()
        channel[CHANNEL_INTERFACE_GROUP].AddMembers(pending, "")

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--directed', dest='directed', default=False,
                      action='store_true',
                      help='Make the call by creating a channel to a contact; '
                           'if not given, create a channel then add the '
                           'desired contact')

    (options, args) = parser.parse_args()

    assert len(args) in (1, 2)
    conn = connection_from_file(args[0])

    if len(args) > 1:
        contact = args[1]
        call = OutgoingCall(conn, args[1], options)
    else:
        call = IncomingCall(conn, options)

    print "connecting"
    conn[CONN_INTERFACE].Connect()
    call.run()

    try:
        print "disconnecting"
        conn[CONN_INTERFACE].Disconnect()
    except dbus.DBusException:
        pass

