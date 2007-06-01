
import sys

import pygtk
pygtk.require('2.0')

import dbus
import gobject
import gtk

from account import connection_from_file
from call import IncomingCall, OutgoingCall, get_stream_engine

from telepathy.interfaces import CONN_INTERFACE

class CallWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        hbox = gtk.HBox()
        hbox.set_border_width(10)
        vbox = gtk.VBox()

        output_frame = gtk.Frame()
        output_frame.set_shadow_type(gtk.SHADOW_IN)

        preview_frame = gtk.Frame()
        preview_frame.set_shadow_type(gtk.SHADOW_IN)

        self.output = gtk.Socket()
        self.output.set_size_request(400, 300)
        self.preview = gtk.Socket()
        self.preview.set_size_request(200, 150)

        self.call_button = gtk.Button('Call')
        self.call_button.connect('clicked', self._call_button_clicked)

        output_frame.add(self.output)
        preview_frame.add(self.preview)
        vbox.pack_start(preview_frame, False)
        vbox.pack_end(self.call_button, False)
        hbox.add(output_frame)
        hbox.pack_start(vbox, padding=10)
        self.add(hbox)

    def _call_button_clicked(self, button):
        pass

class GtkLoopMixin:
    def run(self):
        try:
            gtk.main()
        except KeyboardInterrupt:
            print "killed"
            self.quit()

    def quit(self):
        gtk.main_quit()

class BaseGtkCall:
    def __init__(self):
        self.window = CallWindow()
        self.window.connect('destroy', gtk.main_quit)
        self.window.show_all()

    def add_preview_window(self):
        se = dbus.Interface(get_stream_engine(),
            'org.freedesktop.Telepathy.StreamEngine')
        se.AddPreviewWindow(self.window.preview.get_id())

        return False

    def add_output_window(self):
        se = dbus.Interface(get_stream_engine(),
            'org.freedesktop.Telepathy.StreamEngine')
        chan_path = self.channel.object_path
        se.SetOutputWindow(chan_path, 2, self.window.output.get_id())

        return False

class GtkOutgoingCall(GtkLoopMixin, BaseGtkCall, OutgoingCall):
    def __init__(self, conn, contact):
        OutgoingCall.__init__(self, conn, contact)
        BaseGtkCall.__init__(self)

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        OutgoingCall.members_changed_cb(self, message, added, removed,
            local_pending, remote_pending, actor, reason)

        if self.handle in added:
            gobject.timeout_add(5000, self.add_output_window)
            gobject.timeout_add(5000, self.add_preview_window)

class GtkIncomingCall(GtkLoopMixin, BaseGtkCall, IncomingCall):
    def __init__(self, conn):
        IncomingCall.__init__(self, conn)
        BaseGtkCall.__init__(self)

    def members_changed_cb(self, message, added, removed, local_pending,
            remote_pending, actor, reason):
        IncomingCall.members_changed_cb(self, message, added, removed,
            local_pending, remote_pending, actor, reason)

        if self.conn[CONN_INTERFACE].GetSelfHandle() in added:
            gobject.timeout_add(5000, self.add_output_window)
            gobject.timeout_add(5000, self.add_preview_window)

if __name__ == '__main__':
    args = sys.argv[1:]

    assert len(args) in (1, 2)
    conn = connection_from_file(args[0])

    if len(args) > 1:
        contact = args[1]
        call = GtkOutgoingCall(conn, args[1])
    else:
        call = GtkIncomingCall(conn)

    print "connecting"
    conn[CONN_INTERFACE].Connect()
    call.run()

    try:
        print "disconnecting"
        conn[CONN_INTERFACE].Disconnect()
    except dbus.DBusException:
        pass
