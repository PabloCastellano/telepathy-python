#!/usr/bin/env python
#
# Copyright (C) 2006 Collabora Limited
# Copyright (C) 2006 Nokia Corporation
#   @author Ole Andre Vadla Ravnaas <ole.andre.ravnaas@collabora.co.uk>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import dbus
import dbus.glib
import gtk
import gtk.glade
import scw

from room import *
from conversation import *
from widgets import *
from util import *

DEFAULT_CONNECTION_MANAGER = "gabble"
DEFAULT_PROTOCOL = "jabber"
DEFAULT_SERVER = "jabber.no"
DEFAULT_PORT = 5223
DEFAULT_SSL = True
DEFAULT_USERNAME = "oleavr@jabber.no"
DEFAULT_PASSWORD = ""

DEFAULT_ROOM_ENTRY_TEXT = "tryggve@conference.jabber.belnet.be"

class MainWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.set_title("Tabby")

        self.set_default_size(350, 566)
        self.set_border_width(5)

        nb = gtk.Notebook()
        nb.set_show_tabs(False)
        nb.set_show_border(False)
        self.add(nb)
        self._nb = nb

        # login page
        xml = gtk.glade.XML("data/glade/login.glade", "main_table")
        self._login_table = xml.get_widget("main_table")
        self._user_entry = xml.get_widget("user_entry")
        self._pass_entry = xml.get_widget("pass_entry")
        self._login_btn = xml.get_widget("login_btn")

        nb.append_page(self._login_table)

        self._user_entry.set_text(DEFAULT_USERNAME)
        self._pass_entry.set_text(DEFAULT_PASSWORD)

        self._login_btn.connect("clicked", self._login_btn_clicked_cb)

        # contact list/conversations notebook
        convo_nb = gtk.Notebook()
        self._convo_nb = convo_nb
        nb.append_page(convo_nb)

        vbox = gtk.VBox()
        convo_nb.append_page(vbox, gtk.Label("Contacts"))

        # contact list page
        self._model = gtk.ListStore(gtk.gdk.Pixbuf,
                                    scw.TYPE_PRESENCE,
                                    gobject.TYPE_STRING,
                                    int)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_NONE)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        vbox.pack_start(sw)

        view = scw.View()
        view.connect("activate", self._view_activate_cb)
        view.set_property("model", self._model)
        view.set_column_foldable(2, True)
        view.set_column_visible(3, False)
        sw.add(view)
        self._view = view

        # input hbox
        input_hbox = gtk.HBox()
        vbox.pack_start(input_hbox, expand=False)

        entry = gtk.Entry()
        entry.set_text(DEFAULT_ROOM_ENTRY_TEXT)
        input_hbox.pack_start(entry, expand=True)
        self._request_room_entry = entry

        btn = gtk.Button("Request room")
        btn.connect("clicked", self._request_room_btn_clicked)
        input_hbox.pack_start(btn, expand=False)

        # initialize
        nb.set_current_page(0)

        self.show_all()

        self._conn = None

        self._conversations = {}
        self._rooms = {}
        self._channels = {}
        self._status = CONNECTION_STATUS_DISCONNECTED

        self._icon = gtk.gdk.pixbuf_new_from_file("data/images/face-surprise.png")

        self._login_btn.grab_focus()

        self.connect("delete-event", self._delete_event_cb)

    def _delete_event_cb(self, widget, event):
        if self._conn is not None:
            self._conn[CONN_INTERFACE].Disconnect()
        return False

    def _request_room_btn_clicked(self, button):
        name = self._request_room_entry.get_text()
        if not name:
            return

        print "Requesting room '%s'" % name
        dbus_call_async(self._conn[CONN_INTERFACE].RequestHandle,
                        CONNECTION_HANDLE_TYPE_ROOM, name,
                        reply_handler=self._request_room_handle_reply_cb,
                        error_handler=self._conn_error_cb,
                        extra_args=(name,))

    def _request_room_handle_reply_cb(self, handle, name):
        print "Got handle", handle, "requesting text channel with room '%s'" % name

        dbus_call_async(self._conn[CONN_INTERFACE].RequestChannel,
                        CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_ROOM,
                        handle, True,
                        reply_handler=self._request_room_channel_reply_cb,
                        error_handler=self._conn_error_cb,
                        extra_args=(handle, name,))

    def _request_room_channel_reply_cb(self, obj_path, handle, name):
        print "Got room channel with '%s' [%d]" % (name, handle)
        channel = RoomChannel(self._conn, obj_path, handle)

        if not handle in self._rooms:
            room = Room(self, self._convo_nb, self._conn, handle, name)
            room.connect("closed", self._room_closed_cb)
            self._rooms[handle] = room

        self._rooms[handle].take_room_channel(channel)
        self._rooms[handle].show()

    def _view_activate_cb(self, view, action_id, action_data):
        if action_id[:5] == "click":
            handle = int(action_id[5:])

            found = False
            iter = self._model.get_iter_first()
            while iter:
                cur_status, cur_handle = self._model.get(iter, 2, 3)
                if cur_handle == handle:
                    found = True
                    break
                iter = self._model.iter_next(iter)

            if not found:
                return

            if cur_status == "Offline":
                return

            if not handle in self._conversations:
                self._conversations[handle] = Conversation(self._conn, self._convo_nb, handle, action_data)

            self._conversations[handle].show()

    def _login_btn_clicked_cb(self, button):
        self._pending_presence_lookups = []

        button.set_sensitive(False)

        bus = dbus.Bus()
        voip_obj = bus.get_object("org.freedesktop.Telepathy.VoipEngine",
                                  "/org/freedesktop/Telepathy/VoipEngine")
        self._voip_chandler = dbus.Interface(voip_obj, "org.freedesktop.Telepathy.ChannelHandler")

        bus.add_signal_receiver(self._conn_handle_new_channel,
                                "NewChannel",
                                CONN_INTERFACE,
                                sender_keyword="connection_sender",
                                path_keyword="connection_path")

        reg = telepathy.client.ManagerRegistry()
        reg.LoadManagers()

        mgr_bus_name = reg.GetBusName(DEFAULT_CONNECTION_MANAGER)
        mgr_object_path = reg.GetObjectPath(DEFAULT_CONNECTION_MANAGER)

        params = {
                "server"   : DEFAULT_SERVER,
                "port"     : dbus.UInt32(DEFAULT_PORT),
                "old-ssl"  : DEFAULT_SSL,
                "account"  : self._user_entry.get_text(),
                "password" : self._pass_entry.get_text(),
                "resource" : "Tabby",
        }

        if False:
            params["https-proxy-server"] = "127.0.0.1"
            params["https-proxy-port"] = dbus.UInt32(8888)

        self._mgr = telepathy.client.ConnectionManager(mgr_bus_name, mgr_object_path)

        dbus_call_async(self._mgr[CONN_MGR_INTERFACE].Connect,
                        DEFAULT_PROTOCOL, params,
                        reply_handler=self._connect_reply_cb,
                        error_handler=self._conn_error_cb)

    def _connect_reply_cb(self, bus_name, obj_path):
        conn = Connection(bus_name, obj_path)
        conn.bus_name = bus_name
        conn.obj_path = obj_path

        conn[CONN_INTERFACE].connect_to_signal("StatusChanged",
                lambda *args: dbus_signal_cb(self._conn_status_changed_cb, *args))
        conn[CONN_INTERFACE].connect_to_signal("NewChannel",
                lambda *args: dbus_signal_cb(self._conn_new_channel_cb, *args))

        dbus_call_async(conn[CONN_INTERFACE].GetStatus,
                        reply_handler=self._conn_get_status_reply_cb,
                        error_handler=self._conn_error_cb)

        self._conn = conn

    def _conn_get_status_reply_cb(self, status):
        self._conn_status_changed_cb(status, CONNECTION_STATUS_REASON_NONE_SPECIFIED)

    def _conn_status_changed_cb(self, status, reason):
        if status == self._status:
            return

        if status == CONNECTION_STATUS_CONNECTED:
            self.self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()

        self._status = status

        if status == CONNECTION_STATUS_CONNECTED:
            self._nb.set_current_page(1)
            dbus_call_async(self._conn[CONN_INTERFACE].GetInterfaces,
                            reply_handler=self._get_interfaces_reply_cb,
                            error_handler=self._conn_error_cb)
        elif status == CONNECTION_STATUS_DISCONNECTED:
            self._channels = {}
            self._nb.set_current_page(0)
            self._login_btn.set_sensitive(True)

    def _get_interfaces_reply_cb(self, interfaces):
        self._conn.get_valid_interfaces().update(interfaces)
        dbus_call_async(self._conn[CONN_INTERFACE].ListChannels,
                        reply_handler=self._conn_list_channels_reply_cb,
                        error_handler=self._conn_error_cb)
        self._conn[CONN_INTERFACE_PRESENCE].connect_to_signal("PresenceUpdate",
                lambda *args: dbus_signal_cb(self._presence_update_cb, *args))
        self._process_presence_queue()

    def _conn_list_channels_reply_cb(self, channels):
        for (obj_path, channel_type, handle_type, handle) in channels:
            self._conn_new_channel_cb(obj_path, channel_type, handle_type, handle, False)

    def _conn_new_channel_cb(self, obj_path, channel_type, handle_type, handle, suppress_handler):
        if suppress_handler:
            return

        if obj_path in self._channels:
            return

        channel = None

        if channel_type == CHANNEL_TYPE_CONTACT_LIST:
            channel = ContactListChannel(self._conn, obj_path, handle)
            self._conn.lookup_handle(handle_type, handle,
                                     self._set_contact_list, channel)
        elif channel_type == CHANNEL_TYPE_TEXT and handle_type == CONNECTION_HANDLE_TYPE_ROOM:
            channel = RoomChannel(self._conn, obj_path, handle)

            # find out who invited us
            inviter_handle = channel[CHANNEL_INTERFACE_GROUP].GetMembers()[0]
            inviter_name = self._conn[CONN_INTERFACE].InspectHandle(
                    CONNECTION_HANDLE_TYPE_CONTACT,
                    inviter_handle)

            # and check if there's a message
            pending = channel[CHANNEL_TYPE_TEXT].ListPendingMessages()
            msg_text = ""
            if pending:
                msg_id, msg_stamp, msg_sender, msg_type, msg_text = pending[0]

                msg_text = " with the reason '%s'" % msg_text

            name = self._conn[CONN_INTERFACE].InspectHandle(handle_type, handle)
            dlg = gtk.MessageDialog(parent=self,
                                    flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                    type=gtk.MESSAGE_QUESTION,
                                    buttons=gtk.BUTTONS_YES_NO,
                                    message_format="%s is inviting you to %s%s, accept?" %
                                        (inviter_name, name, msg_text))
            response = dlg.run()
            dlg.destroy()

            if response == gtk.RESPONSE_YES:
                room = Room(self, self._convo_nb, self._conn, handle, name)
                room.connect("closed", self._room_closed_cb)
                room.take_room_channel(channel)
                room.show()
                self._rooms[handle] = room

                channel.add_member(self.self_handle, "")
            else:
                channel[CHANNEL_INTERFACE].Close()
                return
        elif channel_type == CHANNEL_TYPE_STREAMED_MEDIA:
            channel = StreamedMediaChannel(self._conn, obj_path)

            if not handle in self._conversations:
                self._conversations[handle] = Conversation(self._conn, self._convo_nb, handle, None)

            self._conversations[handle].take_media_channel(channel)
            self._conversations[handle].show()

        if channel != None:
            self._channels[obj_path] = channel
        else:
            print "Unknown channel type", channel_type

    def _room_closed_cb(self, room, handle, page_index):
        obj_path = room._room_chan._obj_path
        if obj_path in self._channels:
            del self._channels[obj_path]
        if handle in self._rooms:
            del self._rooms[handle]
        self._convo_nb.remove_page(page_index)

    def _conn_error_cb(self, exception):
        print "Exception received:", exception

    def _set_contact_list(self, handle_type, handle, name, channel):
        if name == "subscribe":
            self._subscribe = channel
            dbus_call_async(self._subscribe[CHANNEL_INTERFACE_GROUP].GetMembers,
                            reply_handler=self._cl_get_members_reply_cb,
                            error_handler=self._conn_error_cb)
            self._subscribe[CHANNEL_INTERFACE_GROUP].connect_to_signal("MembersChanged",
                    lambda *args: dbus_signal_cb(self._cl_subscribe_members_changed_cb, *args))
        elif name == "publish":
            self._publish = channel
        else:
            print "_set_contact_list: got unknown list"

    def _cl_get_members_reply_cb(self, members):
        for member in members:
            self._conn.lookup_handle(CONNECTION_HANDLE_TYPE_CONTACT, member, self._cl_add_contact)

    def _cl_subscribe_members_changed_cb(self, reason, added, removed, local_pending, remote_pending):
        for member in added:
            self._conn.lookup_handle(CONNECTION_HANDLE_TYPE_CONTACT, member, self._cl_add_contact)

    def _cl_add_contact(self, handle_type, handle, name):
        iter = self._model.append()
        self._model.set(iter,
                        0, self._icon,
                        1, "<b><action id='click%s'>%s</action></b>" % (handle, name),
                        2, "Offline",
                        3, handle)

        self._pending_presence_lookups.append(handle)
        self._process_presence_queue()

    def _process_presence_queue(self):
        if CONN_INTERFACE_PRESENCE in self._conn.get_valid_interfaces():
            for handle in self._pending_presence_lookups:
                dbus_call_async(self._conn[CONN_INTERFACE_PRESENCE].RequestPresence,
                                (handle,),
                                reply_handler=lambda: None,
                                error_handler=self._conn_error_cb)
            self._pending_presence_lookups = []

    def _presence_update_cb(self, presences):
        for handle, presence in presences.iteritems():
            idle, statuses = presence

            found = False
            iter = self._model.get_iter_first()
            while iter:
                cur = self._model.get_value(iter, 3)
                if cur == handle:
                    found = True
                    break
                iter = self._model.iter_next(iter)

            if not found:
                return

            for name, params in statuses.iteritems():
                status = self._get_status_message(name, params)
                self._model.set_value(iter, 2, status)
                break

    def _get_status_message(self, name, parameters):
        if name == 'available':
            msg = 'Available'
        elif name == 'away':
            msg = 'Away'
        elif name == 'brb':
            msg = 'Be Right Back'
        elif name == 'busy':
            msg = 'Busy'
        elif name == 'dnd':
            msg = 'Do Not Disturb'
        elif name == 'xa':
            msg = 'Extended Away'
        elif name == 'hidden':
            msg = 'Hidden'
        elif name == 'offline':
            msg = 'Offline'
        else:
            msg = 'Unknown'

        if "message" in parameters and parameters["message"]:
            msg = "%s: %s" % (msg, parameters['message'])

        return msg

    def _conn_handle_new_channel(self, channel_path, channel_type, handle_type, handle, suppress_handler, **kwargs):
        if not channel_type == CHANNEL_TYPE_STREAMED_MEDIA:
            return

        print "Detected a CHANNEL_TYPE_STREAMED_MEDIA channel, giving it to voip-engine"

        self._voip_chandler.HandleChannel(kwargs["connection_sender"],
                                          kwargs["connection_path"],
                                          channel_type,
                                          channel_path,
                                          handle_type,
                                          handle)


win = MainWindow()
win.connect("destroy", gtk.main_quit)
gtk.main()

