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
import telepathy.client
from telepathy import *


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

def dbus_signal_cb(callback, *args):
    # do it directly for now
    #callback(*args)
    #return

    kwargs = { "priority" : gobject.PRIORITY_HIGH }
    gobject.idle_add(callback, *args, **kwargs)

def dbus_call_async(method, *args, **kwargs):
    # do it directly for now
    #method(*args, **kwargs)
    #return

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
    gia_kwargs = { "priority" : gobject.PRIORITY_HIGH }
    our_kwargs = { "reply_handler" : lambda *args: gobject.idle_add(_reply_cb, *args, **gia_kwargs),
                   "error_handler" : lambda *args: gobject.idle_add(_error_cb, *args, **gia_kwargs) }
    method(*args, **our_kwargs)

def _reply_cb(*args):
    global current_call

    method, func_args, func_kwargs = current_call
    if "extra_args" in func_kwargs:
        args += func_kwargs["extra_args"]
    func_kwargs["reply_handler"](*args)

    current_call = None
    _try_next_call()

def _error_cb(*args):
    global current_call

    method, func_args, func_kwargs = current_call
    func_kwargs["error_handler"](*args)
    current_call = None
    _try_next_call()


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
        "closed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                   ()),
    }

    def __init__(self, conn, obj_path, handle_type, handle, type):
        self.__gobject_init__()
        telepathy.client.Channel.__init__(self, conn.bus_name, obj_path)

        self.get_valid_interfaces().add(type)

        self._conn = conn
        self._obj_path = obj_path
        self._handle_type = handle_type
        self._handle = handle
        self._name = handle

    def got_interfaces(self):
        self[CHANNEL_INTERFACE].connect_to_signal("Closed",
                lambda *args: dbus_signal_cb(self._closed_cb, *args))

        gobject.idle_add(self.emit, "ready", priority=gobject.PRIORITY_HIGH)

    def _closed_cb(self):
        self.emit("closed")


class GroupChannel(BaseChannel):
    __gsignals__ = {
        "flags-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ()),
        "members-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, object, object, object, object)),
    }

    def __init__(self, *args):
        BaseChannel.__init__(self, *args)

        self.get_valid_interfaces().add(CHANNEL_INTERFACE_GROUP)

        self._flags = None
        self._members = None
        self._local_p = None
        self._remote_p = None

        self._members_changed_queue = []

        self.connect("ready", self.__ready_cb)

    def __ready_cb(self, channel):
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

        self[CHANNEL_INTERFACE_GROUP].connect_to_signal("GroupFlagsChanged",
                lambda *args: dbus_signal_cb(self._flags_changed_cb, *args))
        self[CHANNEL_INTERFACE_GROUP].connect_to_signal("MembersChanged",
                lambda *args: dbus_signal_cb(self._members_changed_cb, *args))

    def get_flags(self):
        return self._flags

    def get_members(self):
        return self._members

    def get_local_pending(self):
        return self._local_p

    def get_remote_pending(self):
        return self._remote_p

    def add_member(self, member, message=""):
        if not self.__is_ready():
            return

        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].AddMembers,
                        (member,), message,
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def remove_member(self, member, message=""):
        if not self.__is_ready():
            return

        dbus_call_async(self[CHANNEL_INTERFACE_GROUP].RemoveMembers,
                        (member,), message,
                        reply_handler=lambda: None,
                        error_handler=self.__error_cb)

    def __error_cb(self, exception):
        print "GroupChannel.__error_cb: got exception", exception

    def _flags_changed_cb(self, added, removed):
        if self._flags is not None:
            print "added:   0x%x" % added
            print "removed: 0x%x" % removed

            self._flags |= added
            self._flags &= ~removed

        if self.__is_ready():
            self.emit("flags-changed")

    def _members_changed_cb(self, message, added, removed, local_p, remote_p):
        if self.__is_ready():
            for member in added:
                self._members.append(member)

            for member in removed:
                if member in self._members:
                    self._members.remove(member)

            self._local_p = local_p
            self._remote_p = remote_p

            self.emit("members-changed", message, added, removed, local_p, remote_p)
        else:
            self._members_changed_queue.append((message, added, removed,
                                                local_p, remote_p))

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
        self.emit("members-changed", "", self._members, [], self._local_p,
                  self._remote_p)

        for entry in self._members_changed_queue:
            self._members_changed_cb(*entry)

        del self._members_changed_queue


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
        "password-flags-changed": (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                   (gobject.TYPE_UINT, gobject.TYPE_UINT)),
    }

    def __init__(self, conn, obj_path, handle):
        GroupChannel.__init__(self, conn, obj_path, CONNECTION_HANDLE_TYPE_ROOM,
                              handle, CHANNEL_TYPE_TEXT)

        self.get_valid_interfaces().add(PROPERTIES_INTERFACE)

        self._fetched_all = False
        self._messages = []
        self._pw_flags = None

        self.connect("ready", self.__ready_cb)

    def __ready_cb(self, channel):
        self[CHANNEL_TYPE_TEXT].connect_to_signal("Received",
                lambda *args: dbus_signal_cb(self._message_received_cb, *args))

        dbus_call_async(self[CHANNEL_TYPE_TEXT].ListPendingMessages,
                        reply_handler=self._list_pending_messages_reply_cb,
                        error_handler=self.__error_cb)

        self[CHANNEL_INTERFACE_PASSWORD].connect_to_signal("PasswordFlagsChanged",
                lambda *args: dbus_signal_cb(self._password_flags_changed_cb, *args))

        dbus_call_async(self[CHANNEL_INTERFACE_PASSWORD].GetPasswordFlags,
                        reply_handler=self._get_password_flags_reply_cb,
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

    def provide_password(self, password):
        dbus_call_async(self[CHANNEL_INTERFACE_PASSWORD].ProvidePassword,
                        password,
                        reply_handler=self._provide_password_reply_cb,
                        error_handler=self.__error_cb)

    def _provide_password_reply_cb(self, result):
        if result:
            print "Password accepted"
        else:
            print "Password incorrect"

    def _message_received_cb(self, *args):
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

    def _password_flags_changed_cb(self, added, removed):
        if self._pw_flags is None:
            return

        self._pw_flags |= added
        self._pw_flags &= ~removed

        self.emit("password-flags-changed", added, removed)

    def _get_password_flags_reply_cb(self, flags):
        self._pw_flags = flags

        self.emit("password-flags-changed", flags, 0)

    def __error_cb(self, exception):
        print "RoomChannel.__error_cb: got exception", exception


class StreamedMediaChannel(GroupChannel):
    def __init__(self, conn, obj_path):
        GroupChannel.__init__(self, conn, obj_path, 0, 0, CHANNEL_TYPE_STREAMED_MEDIA)
