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

import dbus
import dbus.glib
from telepathy import *
import telepathy.client

import gobject
import pango
import gtk
import gtk.glade
import scw

DEFAULT_CONNECTION_MANAGER = "gabble"
DEFAULT_PROTOCOL = "jabber"
DEFAULT_SERVER = "jabber.no"
DEFAULT_PORT = 5223
DEFAULT_SSL = True
DEFAULT_USERNAME = "oleavr@jabber.no"
DEFAULT_PASSWORD = ""

DEFAULT_ROOM_ENTRY_TEXT = "gajim@conference.jabber.no"

#
# Terrible hack to get around the following two issues:
#  1) Multiple asynchronous calls result in calls
#     getting "lost" (callbacks are never called).
#     The workaround is queuing calls and doing
#     them in a chained fashion.
#  2) No proper backtrace on exceptions raised from
#     within reply and signal callbacks.
#     The workaround is doing the replies transparently
#     through gobject.idle_add().
#

current_call = None
call_queue = []

def dbus_call_async(method, *args, **kwargs):
    global current_call
    global call_queue

    if not kwargs.has_key("reply_handler"):
        raise KeyError("Missing reply_handler argument")

    if not kwargs.has_key("error_handler"):
        raise KeyError("Missing error_handler argument")

    call = (method, args, kwargs)
    call_queue.append(call)
    _try_next_call()

def _try_next_call():
    global current_call
    global call_queue

    # call in progress?
    if current_call is not None:
        return

    # empty queue?
    if not call_queue:
        return

    # get the next call
    current_call = call_queue.pop()

    # do it
    method, args, kwargs = current_call
    our_kwargs = { "reply_handler" : lambda *args: gobject.idle_add(_reply_cb, *args),
                   "error_handler" : lambda *args: gobject.idle_add(_error_cb, *args) }
    method(*args, **our_kwargs)

def _reply_cb(*args):
    global current_call

    method, func_args, func_kwargs = current_call
    func_kwargs["reply_handler"](*args)

    current_call = None
    _try_next_call()

def _error_cb(*args):
    global current_call

    method, func_args, func_kwargs = current_call
    func_kwargs["error_handler"](*args)
    current_call = None
    _try_next_call()


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
        view.set_column_foldable(2)
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

    def _request_room_btn_clicked(self, button):
        name = self._request_room_entry.get_text()
        if not name:
            return

        print "Requesting room '%s'" % name
        dbus_call_async(self._conn[CONN_INTERFACE].RequestHandle,
                        CONNECTION_HANDLE_TYPE_ROOM, name,
                        reply_handler=self._request_room_handle_reply_cb,
                        error_handler=self._conn_error_cb)

    def _request_room_handle_reply_cb(self, handle):
        print "Got handle", handle, "requesting text channel with room"

        dbus_call_async(self._conn[CONN_INTERFACE].RequestChannel,
                        CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_ROOM,
                        handle, False,
                        reply_handler=lambda *args: None,
                        error_handler=self._conn_error_cb)

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
        }

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
                lambda *args: gobject.idle_add(self._conn_status_changed_cb, *args))
        conn[CONN_INTERFACE].connect_to_signal("NewChannel",
                lambda *args: gobject.idle_add(self._conn_new_channel_cb, *args))

        dbus_call_async(conn[CONN_INTERFACE].GetStatus,
                        reply_handler=self._conn_get_status_reply_cb,
                        error_handler=self._conn_error_cb)

        self._conn = conn

    def _conn_get_status_reply_cb(self, status):
        self._conn_status_changed_cb(status, CONNECTION_STATUS_REASON_NONE_SPECIFIED)

    def _conn_status_changed_cb(self, status, reason):
        if status == self._status:
            return

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
                lambda *args: gobject.idle_add(self._presence_update_signal_cb, *args))
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
            self._conn.lookup_handle(handle_type, handle, self._new_room_chan_handle_lookup_cb, channel)
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


    def _new_room_chan_handle_lookup_cb(self, handle_type, handle, name, channel):
        if not handle in self._rooms:
            self._rooms[handle] = Room(self._conn, self._convo_nb, handle, name)

        self._rooms[handle].take_room_channel(channel)
        self._rooms[handle].show()

    def _conn_error_cb(self, exception):
        print "Exception received:", exception

    def _set_contact_list(self, handle_type, handle, name, channel):
        if name == "subscribe":
            self._subscribe = channel
            dbus_call_async(self._subscribe[CHANNEL_INTERFACE_GROUP].GetMembers,
                            reply_handler=self._cl_get_members_reply_cb,
                            error_handler=self._conn_error_cb)
            self._subscribe[CHANNEL_INTERFACE_GROUP].connect_to_signal("MembersChanged",
                    lambda *args: gobject.idle_add(self._cl_subscribe_members_changed_signal_cb, *args))
        elif name == "publish":
            self._publish = channel
        else:
            print "_set_contact_list: got unknown list"

    def _cl_get_members_reply_cb(self, members):
        for member in members:
            self._conn.lookup_handle(CONNECTION_HANDLE_TYPE_CONTACT, member, self._cl_add_contact)

    def _cl_subscribe_members_changed_signal_cb(self, reason, added, removed, local_pending, remote_pending):
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

    def _presence_update_signal_cb(self, presences):
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


class Conversation:
    def __init__(self, conn, notebook, handle, name):
        xml = gtk.glade.XML("data/glade/conversation.glade", "main_vbox")
        vbox = xml.get_widget("main_vbox")

        tbtn = xml.get_widget("call_toolbtn")
        tbtn.connect("clicked", self._call_button_clicked_cb)
        chat_sw = xml.get_widget("chat_sw")

        self._members_lbl = xml.get_widget("members_lbl")
        self._local_lbl = xml.get_widget("local_lbl")
        self._remote_lbl = xml.get_widget("remote_lbl")

        self._mem_entry = xml.get_widget("member_entry")

        self._mem_add_btn = xml.get_widget("member_add_btn")
        self._mem_add_btn.connect("clicked", self._mem_add_btn_clicked_cb)

        self._mem_rem_btn = xml.get_widget("member_rem_btn")
        self._mem_rem_btn.connect("clicked", self._mem_rem_btn_clicked_cb)

        self._media_frame = xml.get_widget("smc_debug_frame")

        # Call toolbar button
        image = gtk.Image()
        image.set_from_file("data/images/call.png")

        tbtn.set_icon_widget(image)

        # Chat widget
        self._model = gtk.ListStore(scw.TYPE_TIMESTAMP,
                                    scw.TYPE_PRESENCE,
                                    gobject.TYPE_STRING,
                                    scw.TYPE_ROW_COLOR)

        self._view = scw.View()
        #self._view.connect("activate", self.gtk_view_activate_cb)
        #self._view.connect("context-request", self.gtk_view_context_request_cb)
        #self._view.connect("key-press-event", self.gtk_view_key_press_event_cb)
        self._view.set_property("model", self._model)
        self._view.set_property("align-presences", True)
        self._view.set_property("presence-alignment", pango.ALIGN_CENTER)
        self._view.set_property("scroll-on-append", True)
        self._view.set_property("timestamp-format", "%H:%M")
        self._view.set_property("action-attributes", "underline='single' weight='bold'")
        self._view.set_property("selection-row-separator", "\n\n")
        self._view.set_property("selection-column-separator", "\t")

        chat_sw.add(self._view)

        # Entry widget
        self._entry = scw.Entry()
        #self._entry.connect("activate", self._entry_activate_cb)
        self._entry.set_property("history-size", 100)
        vbox.pack_end(self._entry, False, True, 2)

        self._conn = conn
        self._notebook = notebook

        if name is not None:
            pos = name.index("@")
            title = name[:pos]
        else:
            title = "Conversation"

        self._page_index = notebook.append_page(vbox, gtk.Label(title))

        self._handle = handle
        self._name = name
        self._media_chan = None

        # Show the widgets created by us
        image.show()
        self._view.show()
        self._entry.show()

    def show(self):
        self._notebook.set_current_page(self._page_index)
        gobject.idle_add(self._entry.grab_focus)

    def take_media_channel(self, chan):
        self._media_chan = chan

        chan.connect("flags-changed", self._media_flags_changed_signal_cb)
        chan.connect("members-changed", lambda chan, *args: self._media_update_members(chan))

        self._media_frame.show()

    def _mem_add_btn_clicked_cb(self, button):
        str = self._mem_entry.get_text()
        if not str:
            return

        try:
            handle = int(str)

            self._media_chan.add_member(handle)
        except ValueError:
            return

    def _mem_rem_btn_clicked_cb(self, button):
        str = self._mem_entry.get_text()
        if not str:
            return

        try:
            handle = int(str)

            self._media_chan.remove_member(handle)
        except ValueError:
            return

    def _media_flags_changed_signal_cb(self, chan):
        flags = chan.get_flags()

        print "new flags:", flags

        can_add = (flags & CHANNEL_GROUP_FLAG_CAN_ADD) != 0
        can_rem = (flags & CHANNEL_GROUP_FLAG_CAN_REMOVE) != 0

        self._mem_add_btn.set_sensitive(can_add)
        self._mem_rem_btn.set_sensitive(can_rem)

    def _media_update_members(self, chan):
        members, local, remote = chan.get_members()

        self._members_lbl.set_text(str(members))
        self._local_lbl.set_text(str(local))
        self._remote_lbl.set_text(str(remote))

        if members:
            member = members[0]
        elif local:
            member = local[0]
        elif remote:
            member = remote[0]
        else:
            member = ""

        self._mem_entry.set_text(str(member))

    def _call_button_clicked_cb(self, button):
        print "requesting StreamedMediaChannel with", self._name
        dbus_call_async(self._conn[CONN_INTERFACE].RequestChannel,
                        CHANNEL_TYPE_STREAMED_MEDIA,
                        CONNECTION_HANDLE_TYPE_CONTACT,
                        self._handle, True,
                        reply_handler=self._media_request_channel_reply_cb,
                        error_handler=self._error_cb)

    def _media_request_channel_reply_cb(self, obj_path):
        channel = StreamedMediaChannel(self._conn, obj_path, 0, 0)
        self.take_media_channel(channel)

    def _error_cb(self, error):
        print "_error_cb: got error '%s'" % error


class Room:
    def __init__(self, conn, notebook, handle, name):
        xml = gtk.glade.XML("data/glade/room.glade", "main_vbox")
        vbox = xml.get_widget("main_vbox")

        chat_sw = xml.get_widget("chat_sw")
        members_sw = xml.get_widget("members_sw")

        # Chat widget
        self._chat_model = gtk.ListStore(scw.TYPE_TIMESTAMP,
                                         scw.TYPE_PRESENCE,
                                         gobject.TYPE_STRING,
                                         scw.TYPE_ROW_COLOR)

        view = scw.View()
        #self._view.connect("activate", self.gtk_view_activate_cb)
        #self._view.connect("context-request", self.gtk_view_context_request_cb)
        #self._view.connect("key-press-event", self.gtk_view_key_press_event_cb)
        view.set_property("model", self._chat_model)
        view.set_property("align-presences", True)
        view.set_property("presence-alignment", pango.ALIGN_CENTER)
        view.set_property("scroll-on-append", True)
        view.set_property("timestamp-format", "%H:%M")
        view.set_property("action-attributes", "underline='single' weight='bold'")
        view.set_property("selection-row-separator", "\n\n")
        view.set_property("selection-column-separator", "\t")

        self._chat_view = view
        chat_sw.add(view)

        # Members widget
        self._members_model = gtk.ListStore(scw.TYPE_PRESENCE, int)

        view = scw.View()
        view.set_property("model", self._members_model)
        view.set_column_visible(1, False)

        self._members_view = view
        members_sw.add(view)

        # Entry widget
        self._entry = scw.Entry()
        self._entry.connect("activate", self._entry_activate_cb)
        self._entry.set_property("history-size", 100)
        vbox.pack_end(self._entry, False, True)

        self._conn = conn
        self._notebook = notebook

        if name is not None:
            pos = name.index("@")
            title = "#%s" % name[:pos]
        else:
            title = "Room"

        self._page_index = notebook.append_page(vbox, gtk.Label(title))

        self._handle = handle
        self._name = name
        self._room_chan = None

        self._pending_messages = {}
        self._lookups_left = 0

        # Show the widgets created by us
        self._chat_view.show()
        self._members_view.show()
        self._entry.show()

    def show(self):
        self._notebook.set_current_page(self._page_index)
        gobject.idle_add(self._entry.grab_focus)

    def take_room_channel(self, chan):
        self._room_chan = chan

        chan.connect("flags-changed", self._flags_changed_signal_cb)
        chan.connect("members-changed", self._members_changed_signal_cb)
        chan.connect("message-received", self._message_received_signal_cb)

    def _flags_changed_signal_cb(self, chan):
        flags = chan.get_flags()

        print "new flags:", flags

    def _members_changed_signal_cb(self, chan, message, added, removed,
                                   local_pending, remote_pending):
        print "_members_changed_signal_cb"
        print "  added:", added
        print "  removed:", removed
        print "  local pending:", local_pending
        print "  remote pending:", remote_pending

        for handle in added:
            self._conn.lookup_handle(CONNECTION_HANDLE_TYPE_CONTACT, handle,
                                     self._add_member_lookup_cb)

        for handle in removed:
            model = self._members_model

            found = False
            iter = model.get_iter_first()
            while iter:
                cur = model.get_value(iter, 1)
                if cur == handle:
                    model.remove(iter)
                    found = True
                    break
                iter = model.iter_next(iter)

            if not found:
                print "_members_changed_signal_cb: eeek, couldn't find user to be removed"

    def _nick_from_jid(self, jid):
        return jid[jid.index("/") + 1:]

    def _add_member_lookup_cb(self, handle_type, handle, name):
        print "_add_member_lookup_cb: adding", name, "[", handle, "]"

        nick = self._nick_from_jid(name)

        model = self._members_model
        iter = model.append()
        model.set(iter,
                  0, nick,
                  1, handle)

    def _message_received_signal_cb(self, chan, id, timestamp, sender, type, text):
        print "_message_received_signal_cb: got message with id", id, "-- acknowledging"
        self._room_chan.ack_message(id)

        self._pending_messages[id] = [timestamp, sender, str(sender), type, text]

        self._lookups_left += 1
        self._conn.lookup_handle(CONNECTION_HANDLE_TYPE_CONTACT, sender,
                                 self._message_sender_lookup_cb, id)

    def _message_sender_lookup_cb(self, handle_type, handle, name, id):
        self._pending_messages[id][2] = name
        self._lookups_left -= 1
        if self._lookups_left > 0:
            return

        ids = self._pending_messages.keys()
        ids.sort()

        for id in ids:
            timestamp, sender, sender_name, type, text = self._pending_messages[id]

            model = self._chat_model
            iter = model.append()
            model.set(iter,
                      0, timestamp,
                      1, self._nick_from_jid(sender_name),
                      2, text)

    def _entry_activate_cb(self, entry):
        self._room_chan.send_message(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL,
                                     entry.get_text())
        entry.set_text("")


class Connection(telepathy.client.Connection):
    def __init__(self, bus_name, obj_path):
        telepathy.client.Connection.__init__(self, bus_name, obj_path)

        self._handle_cache = {}
        self._handle_callbacks = {}

    def got_interfaces(self):
        print "Connection::got_interfaces"

    def lookup_handle(self, handle_type, handle_id, func, *args):
        if handle_id in self._handle_cache:
            func_args = self._handle_cache[handle_id] + args
            func(handle_id, *func_args)
        else:
            if not handle_id in self._handle_callbacks:
                dbus_call_async(self[CONN_INTERFACE].InspectHandle,
                                handle_type, handle_id,
                                reply_handler=lambda name: self._inspect_handle_reply_cb(handle_type, handle_id, name),
                                error_handler=self.__error_cb)
                self._handle_callbacks[handle_id] = []

            self._handle_callbacks[handle_id].append((func, args))

    def _inspect_handle_reply_cb(self, handle_type, handle_id, name):
        self._handle_cache[handle_id] = (handle_type, name)

        for func, args in self._handle_callbacks[handle_id]:
            func(handle_type, handle_id, name, *args)

        del self._handle_callbacks[handle_id]

    def __error_cb(self, exception):
        print "Connection.__error_cb: Exception received:", exception


class BaseChannel(gobject.GObject, telepathy.client.Channel):
    __gsignals__ = {
        "ready": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                  ()),
    }

    def __init__(self, conn, obj_path, handle_type, handle, type):
        self.__gobject_init__()
        telepathy.client.Channel.__init__(self, conn.bus_name, obj_path)

        self.get_valid_interfaces().add(type)

        self._conn = conn
        self._handle_type = handle_type
        self._handle = handle
        self._name = handle

    def got_interfaces(self):
        gobject.idle_add(self.emit, "ready")


class GroupChannel(BaseChannel):
    __gsignals__ = {
        "flags-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ()),
        "members-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, object, object, object, object)),
    }

    def __init__(self, *args):
        BaseChannel.__init__(self, *args)

        self._flags = None
        self._members = None
        self._local_p = None
        self._remote_p = None

        self.connect("ready", self.__ready_signal_cb)

    def __ready_signal_cb(self, channel):
        self[CHANNEL_INTERFACE_GROUP].connect_to_signal("GroupFlagsChanged", lambda *args: gobject.idle_add(self._flags_changed_signal_cb, *args))
        self[CHANNEL_INTERFACE_GROUP].connect_to_signal("MembersChanged", lambda *args: gobject.idle_add(self._members_changed_signal_cb, *args))

        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].GetGroupFlags,
                        reply_handler=self._get_flags_reply_cb,
                        error_handler=self.__error_cb)
        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].GetMembers,
                        reply_handler=self._get_members_reply_cb,
                        error_handler=self.__error_cb)
        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers,
                        reply_handler=self._get_local_pending_members_reply_cb,
                        error_handler=self.__error_cb)
        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].GetRemotePendingMembers,
                        reply_handler=self._get_remote_pending_members_reply_cb,
                        error_handler=self.__error_cb)

    def get_flags(self):
        return self._flags

    def get_members(self):
        return self._members

    def get_local_pending(self):
        return self._local_p

    def get_remote_pending(self):
        return self._remote_p

    def add_member(self, member):
        if not self.__is_ready():
            return

        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].AddMembers,
                        (member,), "",
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def remove_member(self, member):
        if not self.__is_ready():
            return

        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].RemoveMembers,
                        (member,), "",
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def __error_cb(self, exception):
        print "GroupChannel.__error_cb: got exception", exception

    def _flags_changed_signal_cb(self, added, removed):
        if self._flags is not None:
            print "added:   0x%x" % added
            print "removed: 0x%x" % removed

            self._flags |= added
            self._flags &= ~removed

        if self.__is_ready():
            self.emit("flags-changed")

    def _members_changed_signal_cb(self, message, added, removed, local_p, remote_p):
        if self._members is not None:
            for member in added:
                self._members.append(member)

            for member in removed:
                if member in self._members:
                    self._members.remove(member)

        if self._local_p is not None:
            self._local_p = local_p

        if self._remote_p is not None:
            self._remote_p = remote_p

        if self.__is_ready():
            self.emit("members-changed", message, added, removed, local_p, remote_p)

    def _get_flags_reply_cb(self, flags):
        self._flags = flags
        self.__try_initial_emits()

    def _get_members_reply_cb(self, members):
        self._members = members
        self.__try_initial_emits()

    def _get_local_pending_members_reply_cb(self, members):
        self._local_p = members
        self.__try_initial_emits()

    def _get_remote_pending_members_reply_cb(self, members):
        self._remote_p = members
        self.__try_initial_emits()

    def __is_ready(self):
        return (self._flags is not None) and \
               (self._members is not None) and \
               (self._local_p is not None) and \
               (self._remote_p is not None)

    def __try_initial_emits(self):
        if not self.__is_ready():
            return

        self.emit("flags-changed")
        self.emit("members-changed", "", self._members, (), self._local_p,
                  self._remote_p)


class ContactListChannel(GroupChannel):
    def __init__(self, conn, obj_path, handle):
        GroupChannel.__init__(self, conn, obj_path, CONNECTION_HANDLE_TYPE_LIST,
                              handle, CHANNEL_TYPE_CONTACT_LIST)


class RoomChannel(GroupChannel):
    __gsignals__ = {
        "message-received": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             (gobject.TYPE_UINT, gobject.TYPE_UINT,
                              gobject.TYPE_UINT, gobject.TYPE_UINT,
                              gobject.TYPE_STRING)),
    }

    def __init__(self, conn, obj_path, handle):
        GroupChannel.__init__(self, conn, obj_path, CONNECTION_HANDLE_TYPE_ROOM,
                              handle, CHANNEL_TYPE_TEXT)

        self._fetched_all = False
        self._messages = []

        self.connect("ready", self.__ready_signal_cb)

    def __ready_signal_cb(self, channel):
        self[CHANNEL_TYPE_TEXT].connect_to_signal("Received",
                                                  lambda *args: gobject.idle_add(self._message_received_signal_cb, *args))
        dbus_call_async(self[CHANNEL_TYPE_TEXT].ListPendingMessages,
                        reply_handler=self._list_pending_messages_reply_cb,
                        error_handler=self.__error_cb)

    def ack_message(self, message_id):
        dbus_call_async(self[CHANNEL_TYPE_TEXT].AcknowledgePendingMessage,
                        message_id,
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def send_message(self, type, text):
        dbus_call_async(self[CHANNEL_TYPE_TEXT].Send,
                        type, text,
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def _message_received_signal_cb(self, *args):
        if self._fetched_all:
            self.emit("message-received", *args)
        else:
            self._messages.append(args)

    def _list_pending_messages_reply_cb(self, messages):
        self._messages += messages
        self._fetched_all = True

        for message in self._messages:
            self.emit("message-received", *message)

        del self._messages

    def __error_cb(self, exception):
        print "RoomChannel.__error_cb: got exception", exception


class StreamedMediaChannel(GroupChannel):
    def __init__(self, conn, obj_path):
        GroupChannel.__init__(self, conn, obj_path, 0, 0, CHANNEL_TYPE_STREAMED_MEDIA)


win = MainWindow()
win.connect("destroy", gtk.main_quit)
gtk.main()

