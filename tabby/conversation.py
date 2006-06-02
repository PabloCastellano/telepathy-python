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
import pango
import scw
from util import *

from util import dbus_call_async

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
        self._entry.connect("activate", self._entry_activate_cb)
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

        self._im_chan = None

        dbus_call_async(self._conn[CONN_INTERFACE].RequestChannel,
            CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_CONTACT,
            handle, True,
            reply_handler=self._request_im_channel_reply_cb,
            error_handler=None,
            extra_args=(handle, name,))

        # Show the widgets created by us
        image.show()
        self._view.show()
        self._entry.show()

    def _message_received_cb(self, chan, id, timestamp, sender, type, text):
        print "_message_received_cb: got message with id", id, "-- acknowledging"
        self._im_chan.ack_message(id)

        print "type: %d" % type
        print "text: '%s'" % text

        name = self._conn[CONN_INTERFACE].InspectHandle(
                CONNECTION_HANDLE_TYPE_CONTACT, sender)

        model = self._model
        iter = model.append()
        model.set(iter, 2, text)

    def _request_im_channel_reply_cb(self, obj_path, handle, name):
        print "Got IM channel with '%s' [%d]" % (name, handle)
        self._im_chan = ImChannel(self._conn, obj_path, handle)
        self._im_chan.connect("message-received", self._message_received_cb)
        self._im_chan.connect("closed", lambda chan: self.close())

    def _entry_activate_cb(self, entry):
        self._im_chan.send_message(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, entry.get_text())
        entry.set_text("")

    def show(self):
        self._notebook.set_current_page(self._page_index)
        gobject.idle_add(self._entry.grab_focus)

    def take_media_channel(self, chan):
        self._media_chan = chan

        chan.connect("flags-changed", self._media_flags_changed_cb)
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

    def _media_flags_changed_cb(self, chan):
        flags = self._media_chan[CHANNEL_INTERFACE_GROUP].GetGroupFlags()

        print "new flags:", flags

        can_add = (flags & CHANNEL_GROUP_FLAG_CAN_ADD) != 0
        can_rem = (flags & CHANNEL_GROUP_FLAG_CAN_REMOVE) != 0

        self._mem_add_btn.set_sensitive(can_add)
        self._mem_rem_btn.set_sensitive(can_rem)

    def _media_update_members(self, chan):
        members = self._media_chan[CHANNEL_INTERFACE_GROUP].GetMembers()
        local = self._media_chan[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers()
        remote = self._media_chan[CHANNEL_INTERFACE_GROUP].GetRemotePendingMembers()

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
        channel = StreamedMediaChannel(self._conn, obj_path)
        self.take_media_channel(channel)

    def _error_cb(self, error):
        print "_error_cb: got error '%s'" % error
