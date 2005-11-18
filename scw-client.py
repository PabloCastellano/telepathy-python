#!/usr/bin/env python

# scw-client - Simple GUI client for testing parts of Telepathy connection managers
#
# Copyright (C) 2005 Collabora Limited
# Copyright (C) 2005 Nokia Corporation
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

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import getpass
import gobject
import signal
import sys

import pygtk
pygtk.require('2.0')
import gtk
import pango
import scw

from telepathy import *

import telepathy.client

class ContactWindow:
    def __init__(self, conn):
        self._conn = conn
        self._conn[CONN_INTERFACE].GetSelfHandle(reply_handler=self.get_self_handle_reply_cb,
                                                 error_handler=self.error_cb)

        if CONN_INTERFACE_PRESENCE in self._conn.get_valid_interfaces():
            self._conn[CONN_INTERFACE_PRESENCE].connect_to_signal('PresenceUpdate', self.presence_update_signal_cb)
            self._conn[CONN_INTERFACE_PRESENCE].GetStatuses(reply_handler=self.get_statuses_reply_cb,
                                                            error_handler=self.error_cb)

        self._subscribe = None
        self._publish = None

        self._statuses = None

        self._window = gtk.Window()
        self._window.connect("delete-event", self.gtk_delete_event_cb)
        self._window.set_size_request(400, 300)

        self._box = gtk.VBox(False, 6)
        self._window.add(self._box)

        self._swin = gtk.ScrolledWindow(None, None)
        self._swin.set_policy (gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self._box.add(self._swin)

        self._model = gtk.ListStore(gtk.gdk.Pixbuf,
                                    scw.TYPE_PRESENCE,
                                    gobject.TYPE_STRING)
        self._model_rows = {}

        self._view = scw.View()
        self._view.connect("activate", self.gtk_view_activate_cb)
        self._view.set_property("model", self._model)
        self._view.set_column_foldable(2)
        self._swin.add(self._view)

        self._toolbar = gtk.Toolbar()
        self._box.pack_end(self._toolbar, False, True, 0)

        self._window.set_title("Contacts")
        self._window.show_all()

        self._icon = gtk.gdk.pixbuf_new_from_file_at_size("face-surprise.png", 22, 22)

    def set_window_title_cb(self, handle, handle_type, name):
        self._window.set_title("Contacts for %s" % name)

    def get_self_handle_reply_cb(self, handle):
        self._conn.call_with_handle(handle, self.set_window_title_cb)

    def get_statuses_reply_cb(self, statuses):
        self._statuses = statuses

    def presence_update_signal_cb(self, presences):
        for (handle, presence) in presences.iteritems():
            self.update_contact(handle, presence)

    def update_contact(self, handle, presence):
        idle, statuses = presence
        for (name, params) in statuses.iteritems():
             print "update contact with presence", handle, name, params
#            row = self._model_rows[handle]
#            path = row.get_path()
#            iter = self._model.get_iter()
#            self._model.set_value(iter, 2, name)

    def add_contact(self, handle, handle_type, name):
        iter = self._model.append()
        self._model.set(iter,
                        0, self._icon,
                        1, "<b><action id='click%s'>%s</action></b>" % (handle, name),
                        2, "")
#        path = self._model.get_path(iter)
#        row = gtk.TreeRowReference(self._model, path)
#        self._model_rows[handle] = row
        if CONN_INTERFACE_PRESENCE in self._conn.get_valid_interfaces():
            self._conn[CONN_INTERFACE_PRESENCE].RequestPresence([handle],
                                                                reply_handler=(lambda: None),
                                                                error_handler=self.error_cb)

    def subscribe_get_members_reply_cb(self, members):
        for member in members:
            print "subscribe_get_members_reply_cb", member
            self._conn.call_with_handle(member, self.add_contact)

    def subscribe_members_changed_signal_cb(self, reason, added, removed, local_pending, remote_pending):
        for member in added:
            print "subscribe_members_changed_signal_cb", member
            self._conn.call_with_handle(member, self.add_contact)

    def set_subscribe_list(self, subscribe):
        self._subscribe = subscribe
        self._subscribe[CHANNEL_INTERFACE].GetMembers(reply_handler=self.subscribe_get_members_reply_cb, error_handler=self.error_cb)
        self._subscribe[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged', self.subscribe_members_changed_signal_cb)

    def set_publish_list(self, publish):
        self._publish = publish

    def error_cb(self, error):
        print "Exception received from asynchronous method call:"
        print error

    def gtk_delete_event_cb(self, window, event):
        self._conn[CONN_INTERFACE].Disconnect(reply_handler=(lambda: None),
                                              error_handler=self.error_cb)

    def gtk_view_activate_cb(self, view, action_id, action_data):
        if action_id[:5] == 'click':
            handle = int(action_id[5:])
            print "requesting channel to", handle
            self._conn[CONN_INTERFACE].RequestChannel(CHANNEL_TYPE_TEXT, handle, False,
                                                      reply_handler=(lambda chan: None),
                                                      error_handler=self.error_cb)

class ContactListChannel(telepathy.client.Channel):
    def __init__(self, conn, object_path, handle):
        telepathy.client.Channel.__init__(self, conn._service_name, object_path)
        self.get_valid_interfaces().add(CHANNEL_TYPE_CONTACT_LIST)
        self._conn = conn
        self._handle = handle
        self._name = handle

    def got_interfaces(self):
        self._conn[CONN_INTERFACE].InspectHandle(self._handle, reply_handler=self.inspect_handle_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE].GetMembers(reply_handler=self.get_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers(reply_handler=self.get_local_pending_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].GetRemotePendingMembers(reply_handler=self.get_remote_pending_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged', self.members_changed_signal_cb)

    def inspect_handle_reply_cb(self, handle_type, name):
        print "CLC", self._name, "is", name
        self._name = name
        if name == 'subscribe':
            gobject.idle_add(self.subscribe_list_idle_cb)
        elif name == 'publish':
            gobject.idle_add(self.publish_list_idle_cb)

    def subscribe_list_idle_cb(self):
#        handle = self._conn[CONN_INTERFACE].RequestHandle(CONNECTION_HANDLE_TYPE_CONTACT, 'test2@localhost')
#        self[CHANNEL_INTERFACE_GROUP].AddMembers([handle])
        return False

    def publish_list_idle_cb(self):
        return False

    def members_changed_signal_cb(self, message, added, removed, local_p, remote_p):
        print "MembersChanged on CLC", self._name
        print "Message: ", message
        print "Added: ", added
        print "Removed: ", removed
        print "Local Pending: ", local_p
        print "Remote Pending: ", remote_p
#        if added and self._name == 'subscribe':
#            self[CHANNEL_INTERFACE_GROUP].RemoveMembers(added)
#        if removed and self._name == 'subscribe':
#            self[CHANNEL_INTERFACE_GROUP].AddMembers(added)
        
#        if added:
#            self[CHANNEL_INTERFACE_GROUP].RemoveMembers(added)
#        if local_p:
#            self[CHANNEL_INTERFACE_GROUP].AddMembers(local_p)

    def get_members_reply_cb(self, members):
        print "got members on CLC %s: %s" % (self._name, members)
#        if members and self._name == 'subscribe':
#            self[CHANNEL_INTERFACE_GROUP].RemoveMembers(members)
#        if members:
#            self[CHANNEL_INTERFACE_GROUP].RemoveMembers(members)

    def get_local_pending_members_reply_cb(self, members):
        print "got local pending members on CLC %s: %s" % (self._name, members)
#        if members:
#            self[CHANNEL_INTERFACE_GROUP].AddMembers(members)
#            print "sending addmembers"


    def get_remote_pending_members_reply_cb(self, members):
        print "got remote pending members on CLC %s: %s" % (self._name, members)

class TextChannel(telepathy.client.Channel):
    def __init__(self, conn, object_path, handle):
        telepathy.client.Channel.__init__(self, conn._service_name, object_path)
        self.get_valid_interfaces().add(CHANNEL_TYPE_TEXT)
        self[CHANNEL_TYPE_TEXT].connect_to_signal('Received', self.received_signal_cb)
        self[CHANNEL_TYPE_TEXT].connect_to_signal('Sent', self.sent_signal_cb)
        self._conn = conn
        self._object_path = object_path

        self._self_handle = None
        self._self_handle_cb = []

        self._window = gtk.Window()
        self._window.connect("delete-event", self.gtk_delete_event_cb)
        self._window.set_size_request(400, 300)

        self._box = gtk.VBox(False, 6)
        self._window.add(self._box)

        self._swin = gtk.ScrolledWindow(None, None)
        self._swin.set_policy (gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self._box.add(self._swin)

        self._model = gtk.ListStore(scw.TYPE_TIMESTAMP,
                                    scw.TYPE_PRESENCE,
#                                    gtk.gdk.Pixbuf,
                                    gobject.TYPE_STRING,
                                    scw.TYPE_ROW_COLOR)

        self._view = scw.View()
        self._view.connect("activate", self.gtk_view_activate_cb)
        self._view.connect("context-request", self.gtk_view_context_request_cb)
        self._view.connect("key-press-event", self.gtk_view_key_press_event_cb)
        self._view.set_property("model", self._model)
        self._view.set_property("align-presences", True)
        self._view.set_property("presence-alignment", pango.ALIGN_CENTER)
        self._view.set_property("scroll-on-append", True)
        self._view.set_property("timestamp-format", "%H:%M")
        self._view.set_property("action-attributes", "underline='single' weight='bold'")
        self._view.set_property("selection-row-separator", "\n\n")
        self._view.set_property("selection-column-separator", "\t")
        self._swin.add(self._view)

        self._entry = scw.Entry()
        self._entry.connect("activate", self.gtk_entry_activate_cb)
        self._entry.set_property("history-size", 100)
        self._box.pack_end(self._entry, False, True, 0)

        # set the window title according to who you're talking to
        self._window.set_title("Conversation")
        if handle:
            self._conn.call_with_handle(handle, self.set_window_title_cb)

        self._window.show_all()

        # asynchronously retrieve messages that have not been
        self._handled_pending_message = None
        self[CHANNEL_TYPE_TEXT].ListPendingMessages(reply_handler=self.list_pending_messages_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE].GetSelfHandle(reply_handler=self.get_self_handle_reply_cb, error_handler=self.error_cb)

    def list_pending_messages_reply_cb(self, pending_messages):
        print "got pending messages", pending_messages
        for msg in pending_messages:
            (id, timestamp, sender, message_type, message) = msg
            print "Handling pending message", id
            self.received_signal_cb(id, timestamp, sender, message_type, message)
            self._handled_pending_message = id

    def gtk_delete_event_cb(self, window, event):
        self[CHANNEL_INTERFACE].Close(reply_callback=(lambda: None), error_callback=self.error_cb)
        del self._conn._channels[self._object_path]

    def gtk_entry_activate_cb(self, entry):
        self[CHANNEL_TYPE_TEXT].Send(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, entry.get_text())
        entry.set_text("")

    def gtk_view_activate_cb(self, view, action_id, action_data):
        print "Activated id %s which has data %s" % (action_id, action_data)

    def gtk_view_key_press_event_cb(self, view, event):
        # TODO: cunningness to find out whether we should focus
        # the input window
        pass

    def gtk_view_context_request_cb(self, view, action_id, action_data, x, y):
        if action_id is not None:
            print "Context request at (%i,%i) for id %s which has data %s" % \
            (x, y, action_id, action_data)
        else:
            print "Context request at (%i,%i) for global context menu" % (x,y)

    def set_window_title_cb(self, handle, handle_type, name):
        if handle_type == CONNECTION_HANDLE_TYPE_CONTACT:
            title = "Conversation with %s" % name
        elif handle_type == CONNECTION_HANDLE_TYPE_ROOM:
            title = "Conversation in %s" % name
        else:
            title = "Conversation with a list? What's going on?"
        self._window.set_title(title)

    def show_received_cb(self, id, timestamp, message_type, message, sender):
        iter = self._model.append()
        self._model.set(iter,
                        0, timestamp,
                        1, "<b>%s</b>" % sender,
                        2, message)
        self[CHANNEL_TYPE_TEXT].AcknowledgePendingMessage(id, reply_handler=(lambda: None), error_handler=self.error_cb)

    def received_signal_cb(self, id, timestamp, sender, message_type, message):
        if self._handled_pending_message != None:
            if id > self._handled_pending_message:
                print "Now handling messages directly"
                self._handled_pending_message = None
            else:
                print "Skipping already handled message", id
                return

        self._conn.call_with_handle(sender, (lambda handle, handle_type, sender: self.show_received_cb(id, timestamp, message_type, message, sender)))

    def show_sent_cb(self, timestamp, message_type, message, sender):
        iter = self._model.append()
        self._model.set(iter,
                        0, timestamp,
                        1, "<i>%s</i>" % sender,
                        2, message)

    def get_self_handle_reply_cb(self, handle):
        self._self_handle = handle
        for func in self._self_handle_cb:
            self._conn.call_with_handle(handle, func)

    def sent_signal_cb(self, timestamp, message_type, message):
        func = (lambda handle, handle_type, sender: self.show_sent_cb(timestamp, message_type, message, sender))
        if self._self_handle:
            self._conn.call_with_handle(self._self_handle, func)
        else:
            self._self_handle_cb.append(func)

class TestConnection(telepathy.client.Connection):
    def __init__(self, service_name, object_path, mainloop):
        telepathy.client.Connection.__init__(self, service_name, object_path)

        self._mainloop = mainloop
        self._service_name = service_name

        self._status = CONNECTION_STATUS_CONNECTING
        self._channels = {}

        self._handle_cache = {}
        self._handle_callbacks = {}

        self._contact_window = None
        self._lists = {}

        self[CONN_INTERFACE].connect_to_signal('StatusChanged', self.status_changed_signal_cb)
        self[CONN_INTERFACE].connect_to_signal('NewChannel', self.new_channel_signal_cb)

        # handle race condition when connecting completes
        # before the signal handlers are registered
        self[CONN_INTERFACE].GetStatus(reply_handler=self.get_status_reply_cb, error_handler=self.error_cb)

    def error_cb(self, exception):
        print "Exception received from asynchronous method call:"
        print exception

    def get_status_reply_cb(self, status):
        self.status_changed_signal_cb(status, CONNECTION_STATUS_REASON_NONE_SPECIFIED)

    def list_channels_reply_cb(self, channels):
        for (obj_path, channel_type, handle) in channels:
            self.new_channel_signal_cb(obj_path, channel_type, handle, False)

    def give_list_to_contact_window(self, channel, name):
        if self._contact_window:
            if name == 'subscribe':
                self._contact_window.set_subscribe_list(channel)
            elif name == 'publish':
                self._contact_window.set_publish_list(channel)
        else:
            self._lists[name] = channel

    def new_channel_signal_cb(self, obj_path, channel_type, handle, supress_handler):
        if obj_path in self._channels:
            return

        print 'NewChannel', obj_path, channel_type, handle, supress_handler

        channel = None

        if channel_type == CHANNEL_TYPE_TEXT:
            channel = TextChannel(self, obj_path, handle)
        elif channel_type == CHANNEL_TYPE_CONTACT_LIST:
            channel = ContactListChannel(self, obj_path, handle)
            self.call_with_handle(handle, (lambda id, channel_type, name: self.give_list_to_contact_window(channel, name)))

        if channel != None:
            self._channels[obj_path] = channel
        else:
            print 'Unknown channel type', channel_type

    def connected_cb(self):
        print "connected"
        self[CONN_INTERFACE_PRESENCE].connect_to_signal('PresenceUpdate', self.presence_update_signal_cb)
#        handle = self[CONN_INTERFACE].RequestHandle(CONNECTION_HANDLE_TYPE_CONTACT, 'test2@localhost')
#        self[CONN_INTERFACE].RequestChannel(CHANNEL_TYPE_TEXT, handle, True)
#        print self[CONN_INTERFACE_PRESENCE].GetStatuses()
        self._contact_window = ContactWindow(self)
        if 'subscribe' in self._lists:
            self._contact_window.set_subscribe_list(self._lists['subscribe'])
            del self._lists['subscribe']
        if 'publish' in self._lists:
            self._contact_window.set_publish_list(self._lists['publish'])
            del self._lists['publish']
        return False

    def presence_update_signal_cb(self, presence):
        print "got presence update:", presence

    def get_interfaces_reply_cb(self, interfaces):
        self.get_valid_interfaces().update(interfaces)
        self[CONN_INTERFACE].ListChannels(reply_handler=self.list_channels_reply_cb, error_handler=self.error_cb)
        gobject.idle_add(self.connected_cb)

    def status_changed_signal_cb(self, status, reason):
        if self._status == status:
            return
        else:
            self._status = status

        print 'StatusChanged', status, reason

        if status == CONNECTION_STATUS_CONNECTED:
            self[CONN_INTERFACE].GetInterfaces(reply_handler=self.get_interfaces_reply_cb, error_handler=self.error_cb)
        if status == CONNECTION_STATUS_DISCONNECTED:
            self._mainloop.quit()

    def inspect_handle_reply_cb(self, id, handle_type, name):
        self._handle_cache[id] = (handle_type, name)

        for func in self._handle_callbacks[id]:
            func(id, handle_type, name)

        del self._handle_callbacks[id]

    def call_with_handle(self, handle_id, func):
        if handle_id in self._handle_cache:
            func(handle_id, *self._handle_cache[handle_id])
        else:
            if handle_id not in self._handle_callbacks:
                self[CONN_INTERFACE].InspectHandle(handle_id, reply_handler=(lambda *args: self.inspect_handle_reply_cb(handle_id, *args)), error_handler=self.error_cb)
                self._handle_callbacks[handle_id] = set()

            self._handle_callbacks[handle_id].add(func)

if __name__ == '__main__':
    reg = telepathy.client.ManagerRegistry()
    reg.LoadManagers()

    protos=reg.GetProtos()

    if len(protos) == 0:
        print "Sorry, no connection managers found!"
        sys.exit(1)

    if len(sys.argv) > 2:
        protocol = sys.argv[2]
    else:
        protocol=''

    while (protocol not in protos):
        protocol = raw_input('Protocol (one of: %s) [%s]: ' % (' '.join(protos),protos[0]))
        if protocol == '':
            protocol = protos[0]

    if len(sys.argv) > 1:
        manager = sys.argv[1]
    else:
        manager = ''
    managers = reg.GetManagers(protocol)

    while (manager not in managers):
        manager = raw_input('Manager (one of: %s) [%s]: ' % (' '.join(managers),managers[0]))
        if manager == '':
            manager = managers[0]

    mgr_bus_name = reg.GetBusName(manager)
    mgr_object_path = reg.GetObjectPath(manager)

    cmdline_params = dict((p.split('=') for p in sys.argv[3:]))
    params={}

    for (name, (dbus_type, default)) in reg.GetParams(manager, protocol)[0].iteritems():
        if name in cmdline_params:
            params[name] = dbus.Variant(cmdline_params[name],dbus_type)
        elif name == 'password':
            params[name] = dbus.Variant(getpass.getpass(),dbus_type)
        else:
            params[name] = dbus.Variant(raw_input(name+': '),dbus_type)

    mgr = telepathy.client.ConnectionManager(mgr_bus_name, mgr_object_path)
    bus_name, object_path = mgr[CONN_MGR_INTERFACE].Connect(protocol, params)

    mainloop = gobject.MainLoop()
    connection = TestConnection(bus_name, object_path, mainloop)

    def quit_cb():
        connection[CONN_INTERFACE].Disconnect()
        mainloop.quit()

    def sigterm_cb():
        gobject.idle_add(quit_cb)

    signal.signal(signal.SIGTERM, sigterm_cb)

    while mainloop.is_running():
        try:
            mainloop.run()
        except KeyboardInterrupt:
            quit_cb()
