
import dbus.glib
import gobject
import sys

from account import read_account, connect

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE, CONNECTION_HANDLE_TYPE_CONTACT,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED,
    MEDIA_STREAM_TYPE_AUDIO, MEDIA_STREAM_TYPE_VIDEO)
from telepathy.interfaces import (
    CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_STREAMED_MEDIA,
    CONN_INTERFACE)

def get_stream_engine():
    bus = dbus.Bus()
    return bus.get_object(
        'org.freedesktop.Telepathy.StreamEngine',
        '/org/freedesktop/Telepathy/StreamEngine')

class Call:
    def __init__(self, conn):
        self.conn = conn
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
        Channel(self.conn._dbus_object._named_service, object_path,
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
            self.conn._dbus_object._named_service,
            self.conn._dbus_object._object_path,
            CHANNEL_TYPE_STREAMED_MEDIA,
            channel._dbus_object._object_path,
            self.chan_handle_type,
            self.chan_handle)

        self.channel = channel

    def closed_cb(self):
        print "channel closed"
        self.quit()

    def do_window(self):
        print "trying to open window"

        import gtk

        window = gtk.Window()
        window.set_border_width (5)
        hbox = gtk.HBox(False, 5)
        label1 = gtk.Label('Output')
        label2 = gtk.Label('Preview')
        vbox1 = gtk.VBox(False, 5)
        vbox2 = gtk.VBox(False, 5)
        socket1 = gtk.Socket()
        socket1.set_size_request(320, 240)
        socket2 = gtk.Socket()
        socket2.set_size_request(320, 240)

        vbox1.add(label1)
        vbox1.add(socket1)
        vbox2.add(label2)
        vbox2.add(socket2)
        hbox.add(vbox1)
        hbox.add(vbox2)
        window.add(hbox)
        window.show_all()

        stream_engine = get_stream_engine()
        badger = dbus.Interface(stream_engine,
            'org.freedesktop.Telepathy.StreamEngine')
        chan_path = self.channel._dbus_object._object_path
        badger.SetOutputWindow(chan_path, 2, socket1.get_id())
        badger.AddPreviewWindow(socket2.get_id())
        return False

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        print 'MembersChanged', (
            added, removed, local_pending, remote_pending, actor, reason)

        if added:
            gobject.timeout_add(5000, self.do_window)

class OutgoingCall(Call):
    def __init__(self, conn, contact):
        Call.__init__(self, conn)
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

            self.conn[CONN_INTERFACE].RequestChannel(
                CHANNEL_TYPE_STREAMED_MEDIA, CONNECTION_HANDLE_TYPE_NONE,
                handle, True,
                reply_handler=lambda *stuff: None,
                error_handler=self.request_channel_error_cb)

        Call.status_changed_cb(self, state, reason)

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
    def status_changed_cb (self, state, reason):
        if state == CONNECTION_STATUS_CONNECTED:
            print "waiting for incoming call"

        Call.status_changed_cb(self, state, reason)

    def channel_ready_cb(self, channel):
        Call.channel_ready_cb(self, channel)

        print "accepting incoming call"
        pending = channel[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers()
        channel[CHANNEL_INTERFACE_GROUP].AddMembers(pending, "")

if __name__ == '__main__':
    assert len(sys.argv) in (2, 3)
    account_file = sys.argv[1]

    manager, protocol, account = read_account(account_file)
    conn = connect(manager, protocol, account)

    if len(sys.argv) > 2:
        contact = sys.argv[2]
        call = OutgoingCall(conn, sys.argv[2])
    else:
        call = IncomingCall(conn)

    print "connecting"
    conn[CONN_INTERFACE].Connect()
    call.run()

    try:
        print "disconnecting"
        conn[CONN_INTERFACE].Disconnect()
    except dbus.DBusException:
        pass

