#!/usr/bin/env python

import dbus
import dbus.glib

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import getpass
import gobject
import signal
import sys

from telepathy import *

import telepathy.client

class ContactListChannel(telepathy.client.Channel):
    def __init__(self, service_name, object_path, handle):
        telepathy.client.Channel.__init__(self, service_name, object_path)
        self.get_valid_interfaces().add(CHANNEL_TYPE_CONTACT_LIST)
        self._handle = handle

    def got_interfaces(self):
        self[CHANNEL_INTERFACE].GetMembers(reply_handler=self.get_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].GetLocalPendingMembers(reply_handler=self.get_local_pending_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].GetRemotePendingMembers(reply_handler=self.get_remote_pending_members_reply_cb, error_handler=self.error_cb)
        self[CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged', self.members_changed_signal_cb)

    def members_changed_signal_cb(self, message, added, removed, local_p, remote_p):
        print "MembersChanged on ContactListChannel ", self._handle
        print "Message: ", message
        print "Added: ", added
        print "Removed: ", removed
        print "Local Pending: ", local_p
        print "Remote Pending: ", remote_p

    def get_members_reply_cb(self, members):
        print "got members on CLC %s: %s" % (self._handle, members)

    def get_local_pending_members_reply_cb(self, members):
        print "got local pending members on CLC %s: %s" % (self._handle, members)

    def get_remote_pending_members_reply_cb(self, members):
        print "got remote pending members on CLC %s: %s" % (self._handle, members)

class TextChannel(telepathy.client.Channel):
    def __init__(self, service_name, object_path, handle):
        telepathy.client.Channel.__init__(self, service_name, object_path)
        self.get_valid_interfaces().add(CHANNEL_TYPE_TEXT)
        self[CHANNEL_TYPE_TEXT].connect_to_signal('Received', self.received_callback)
        self.doack = True

        self._handled_pending_message = None
        pending_messages = self.text.ListPendingMessages()
        print pending_messages
        for msg in pending_messages:
            (id, timestamp, sender, type, message) = msg
            print "Handling pending message", id
            self.received_callback(id, timestamp, sender, type, message)
            self._handled_pending_message = id

    def received_callback(self, id, timestamp, sender, type, message):
        if self._handled_pending_message != None:
            if id > self._handled_pending_message:
                print "Now handling messages directly"
                self._handled_pending_message = None
            else:
                print "Skipping already handled message", id
                return

        print "Received", id, timestamp, sender, type, message
        self.text.Send(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, 'got message ' + str(id) + '(' + message + ')')
        if self.doack:
            print "Acknowledging...", id
            self.text.AcknowledgePendingMessage(id)

class TestConnection(telepathy.client.Connection):
    def __init__(self, service_name, object_path, mainloop):
        telepathy.client.Connection.__init__(self, service_name, object_path)

        self._mainloop = mainloop
        self._service_name = service_name

        self._status = CONNECTION_STATUS_CONNECTING
        self._channels = {}

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

    def new_channel_signal_cb(self, obj_path, type, handle, supress_handler):
        if obj_path in self._channels:
            return

        print 'NewChannel', obj_path, type, handle, supress_handler

        channel = None

        if type == CHANNEL_TYPE_TEXT:
            channel = TextChannel(self._service_name, obj_path, handle)
        elif type == CHANNEL_TYPE_CONTACT_LIST:
            channel = ContactListChannel(self._service_name, obj_path, handle)

        if channel != None:
            self._channels[obj_path] = channel
        else:
            print 'Unknown channel type', type

    def connected_cb(self):
#        handle = self[CONN_INTERFACE].RequestHandle(CONNECTION_HANDLE_TYPE_CONTACT, 'test2@localhost')
#        self[CONN_INTERFACE].RequestChannel(CHANNEL_TYPE_TEXT, handle, True)
#        print self[CONN_INTERFACE_PRESENCE].GetStatuses()
        return False

    def get_interfaces_reply_cb(self, interfaces):
        self.get_valid_interfaces().update(interfaces)
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
            self.mainloop.quit()

if __name__ == '__main__':
    reg = telepathy.client.ManagerRegistry()
    reg.LoadManagers()

    protocol=''
    protos=reg.GetProtos()

    if len(protos) == 0:
        print "Sorry, no connection managers found!"
        sys.exit(1)

    if len(sys.argv) > 2:
        protocol = sys.argv[2]
    else:
        while (protocol not in protos):
            protocol = raw_input('Protocol (one of: %s) [%s]: ' % (' '.join(protos),protos[0]))
            if protocol == '':
                protocol = protos[0]

    manager=''
    managers=reg.GetManagers(protocol)

    while (manager not in managers):
        if len(sys.argv) > 1:
            manager = sys.argv[1]
        else:
            manager = raw_input('Manager (one of: %s) [%s]: ' % (' '.join(managers),managers[0]))
            if manager == '':
                manager = managers[0]

    mgr_bus_name = reg.GetBusName(manager)
    mgr_object_path = reg.GetObjectPath(manager)

    cmdline_params = dict((p.split('=') for p in sys.argv[3:]))
    params={}

    for (name, (type, default)) in reg.GetParams(manager, protocol)[0].iteritems():
        if name in cmdline_params:
            params[name] = dbus.Variant(cmdline_params[name],type)
        elif name == 'password':
            params[name] = dbus.Variant(getpass.getpass(),type)
        else:
            params[name] = dbus.Variant(raw_input(name+': '),type)

    mgr = telepathy.client.ConnectionManager(mgr_bus_name, mgr_object_path)
    bus_name, object_path = mgr[CONN_MGR_INTERFACE].Connect(protocol, params)

    mainloop = gobject.MainLoop()
    connection = TestConnection(bus_name, object_path, mainloop)

    def quit_cb():
        connection.conn.Disconnect()
        mainloop.quit()

    def sigterm_cb():
        gobject.idle_add(quit_cb)

    signal.signal(signal.SIGTERM, sigterm_cb)

    while mainloop.is_running():
        try:
            mainloop.run()
        except KeyboardInterrupt:
            quit_cb()
