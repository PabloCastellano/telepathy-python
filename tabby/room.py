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

import gobject
import pango
import gtk
import scw
from telepathy import *
from widgets import EntryDialog

class Room(gobject.GObject):
    __gsignals__ = {
        "closed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                   (gobject.TYPE_UINT, gobject.TYPE_INT,)),
    }

    def __init__(self, window, notebook, conn, handle, name):
        self.__gobject_init__()

        xml = gtk.glade.XML("data/glade/room.glade", "main_vbox")
        vbox = xml.get_widget("main_vbox")

        chat_sw = xml.get_widget("chat_sw")
        members_sw = xml.get_widget("members_sw")
        btn = xml.get_widget("invite_tbtn")
        btn.connect("clicked", self._invite_clicked_cb)

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
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_UINT)
        model.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self._members_model = model
        
        view = gtk.TreeView(model=self._members_model)
        
        view.insert_column_with_attributes(0, "Nick", gtk.CellRendererText(),
                                           text=0)
        view.connect("row-activated", self._member_activated_cb)
        view.connect("button-press-event", self._member_button_cb)
        view.connect("popup-menu", self._member_popup_cb)
        view.set_headers_visible(False)
        self._members_view = view
        members_sw.add(view)
        
        # Member popup menu
        menu = gtk.Menu()
        item = gtk.MenuItem("_Kick user")
        item.connect("activate", self._kick_user_activate_cb)
        menu.append(item)
        menu.show_all()
        self._member_popup = menu

        # Entry widget
        self._entry = scw.Entry()
        self._entry.connect("activate", self._entry_activate_cb)
        self._entry.set_property("history-size", 100)
        vbox.pack_end(self._entry, False, True)

        self._window = window
        self._notebook = notebook
        self._conn = conn

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

        chan.connect("closed", lambda chan: self.close())
        chan.connect("flags-changed", self._flags_changed_cb)
        chan.connect("members-changed", self._members_changed_cb)
        chan.connect("message-received", self._message_received_cb)
        chan.connect("password-flags-changed", self._password_flags_changed_cb)
    
    def close(self):
        self.emit("closed", self._handle, self._page_index)

    def _flags_changed_cb(self, chan):
        flags = chan.get_flags()

        print "new flags:", flags

    def _member_activated_cb(self, view, path, column):
        model = self._members_model
        nick, handle = model[path]
        print "nick:", nick
        print "handle:", handle

    def _member_button_cb(self, view, event):
        if event.button == 3:
            info = view.get_path_at_pos(int(event.x), int(event.y))
            if info is not None:
                path, col, cell_x, cell_y = info
                view.grab_focus()
                view.set_cursor(path, col, 0)
                self._member_popup.popup(None, None, None, event.button,
                                         event.time)
    
    def _member_popup_cb(self, view):
        print "_member_popup_cb: FIXME"
        
    def _invite_clicked_cb(self, button):
        user_dlg = EntryDialog(self._window, "Invite user", "Enter username to invite:", False)
        if user_dlg.run() == gtk.RESPONSE_ACCEPT:
            username = user_dlg.get_text()
            
            if username:
                msg_dlg = EntryDialog(self._window, "Invite user", "Enter invite message or leave blank for none:", False)
                
                if msg_dlg.run() == gtk.RESPONSE_ACCEPT:
                    message = msg_dlg.get_text()
                    
                    handle = self._conn[CONN_INTERFACE].RequestHandle(CONNECTION_HANDLE_TYPE_CONTACT,
                                                                      username)
                    if handle != 0:
                        self._room_chan.add_member(handle, message)             

        user_dlg.destroy()
        msg_dlg.destroy()
            
    def _kick_user_activate_cb(self, item):
        model, iter = self._members_view.get_selection().get_selected()
        if iter is not None:
            handle = self._members_model.get_value(iter, 1)

            dlg = EntryDialog(self._window, "Kick reason", "Enter kick reason or leave blank for none:", False)
            if dlg.run() == gtk.RESPONSE_ACCEPT:
                self._room_chan.remove_member(handle, dlg.get_text())
            dlg.destroy()

    def _members_changed_cb(self, chan, message, added, removed,
                            local_pending, remote_pending):
        print "_members_changed_cb"
        print "  message: '%s'" % message
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
                print "_members_changed_cb: eeek, couldn't find user to be removed"

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

    def _message_received_cb(self, chan, id, timestamp, sender, type, text):
        print "_message_received_cb: got message with id", id, "-- acknowledging"
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
      
        self._pending_messages = {}

    def _entry_activate_cb(self, entry):
        self._room_chan.send_message(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL,
                                     entry.get_text())
        entry.set_text("")

    def _password_flags_changed_cb(self, chan, added, removed):
        if added & CHANNEL_PASSWORD_FLAG_PROVIDE:
            dlg = EntryDialog(self._window, "Password required", "Enter password:", True)
            if dlg.run() == gtk.RESPONSE_ACCEPT:
                chan.provide_password(dlg.get_text())
            dlg.destroy()
