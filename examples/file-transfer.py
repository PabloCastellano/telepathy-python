import dbus.glib
import sys
import dbus
import gobject
import socket
import os
import sys

from dbus import PROPERTIES_IFACE
from telepathy.client import (Connection, Channel)
from telepathy.interfaces import (CONN_INTERFACE, CONNECTION_INTERFACE_REQUESTS, CHANNEL)
from telepathy.constants import (CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_CONNECTED,
        CONNECTION_STATUS_DISCONNECTED, SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST)

from account import connection_from_file

loop = None

# FIXME: use constants from tp-python
CHANNEL_TYPE_FILE_TRANSFER = 'org.freedesktop.Telepathy.Channel.Type.FileTransfer.DRAFT'

FT_STATE_NONE = 0
FT_STATE_NOT_OFFERED = 1
FT_STATE_ACCEPTED = 2
FT_STATE_LOCAL_PENDING = 3
FT_STATE_REMOTE_PENDING = 4
FT_STATE_OPEN = 5
FT_STATE_COMPLETED = 6
FT_STATE_CANCELLED = 7

ft_states = ['none', 'not offered', 'accepted', 'local pending', 'remote pending', 'open', 'completed', 'cancelled']

class FTClient:
    def __init__(self, account_file):
        self.conn = connection_from_file(account_file)

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        # hack
        self.conn._valid_interfaces.add(CONNECTION_INTERFACE_REQUESTS)
        self.conn[CONNECTION_INTERFACE_REQUESTS].connect_to_signal('NewChannels',
            self.new_channels_cb)

    def run(self):
        self.conn[CONN_INTERFACE].Connect()

        loop = gobject.MainLoop()
        try:
            loop.run()
        finally:
            try:
                self.conn[CONN_INTERFACE].Disconnect()
            except:
                pass

    def status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_CONNECTING:
            print 'connecting'
        elif state == CONNECTION_STATUS_CONNECTED:
            print 'connected'
            self.connected_cb()
        elif state == CONNECTION_STATUS_DISCONNECTED:
            print 'disconnected'
            loop.quit()

    def connected_cb(self):
        self.self_handle = self.conn[CONN_INTERFACE].GetSelfHandle()
        self.self_id = self.conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT,
            [self.self_handle])[0]
        print "I am %s" % self.self_id

        if not self.is_ft_present():
            print "FileTransfer is not implemented on this ConnectionManager"
            sys.exit(1)

    def is_ft_present(self):
        # check if we can request FT channels
        properties = self.conn[PROPERTIES_IFACE].GetAll(CONNECTION_INTERFACE_REQUESTS)
        classes =  properties['RequestableChannelClasses']
        for fixed_prop, allowed_prop in classes:
            if fixed_prop[CHANNEL + '.ChannelType'] == CHANNEL_TYPE_FILE_TRANSFER:
                return True

        return False

    def new_channels_cb(self, channels):
        for path, props in channels:
            if props[CHANNEL + '.ChannelType'] == CHANNEL_TYPE_FILE_TRANSFER:
                print "new FileTransfer channel"
                self.ft_channel = Channel(self.conn.service_name, path)

                self.ft_channel[CHANNEL_TYPE_FILE_TRANSFER].connect_to_signal('FileTransferStateChanged',
                        self.ft_state_changed_cb)
                self.got_ft_channel()

                self.file_name = props[CHANNEL_TYPE_FILE_TRANSFER + '.Filename']
                self.file_size = props[CHANNEL_TYPE_FILE_TRANSFER + '.Size']

    def ft_state_changed_cb(self, state, reason):
        print "file transfer is now in state %s" % ft_states[state]

class FTReceiverClient(FTClient):
    def connected_cb(self):
        FTClient.connected_cb(self)

        print "waiting for file transfer offer"

    def got_ft_channel(self):
        print "accept FT"
        self.sock_addr = self.ft_channel[CHANNEL_TYPE_FILE_TRANSFER].AcceptFile(
            SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST, "", 0)

    def ft_state_changed_cb(self, state, reason):
        FTClient.ft_state_changed_cb(self, state, reason)

        if state == FT_STATE_OPEN:
            # receive file
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.sock_addr)

            path = self.create_output_path()
            out = file(path, 'w')
            read = 0
            while read < self.file_size:
                data = s.recv(self.file_size - read)
                read += len(data)
                out.write(data)

            print "received file: %s" % path

    def create_output_path(self):
        for i in range(30):
            if i == 0:
                name = self.file_name
            else:
                name = "%s.%d" % (self.file_name, i)

            path = os.path.join('/tmp', name)
            if not os.path.exists(path):
                return path

class FTSenderClient(FTClient):
    def __init__(self, account_file, contact, filename):
        FTClient.__init__(self, account_file)

        self.contact = contact
        self.file_to_offer = filename

    def connected_cb(self):
        FTClient.connected_cb(self)

        handle = self.conn.RequestHandles(CONNECTION_HANDLE_TYPE_CONTACT, [self.contact])[0]

        file_name = os.path.basename(self.file_to_offer)
        info = os.stat(self.file_to_offer)
        size = info.st_size

        # Request FT channel
        self.conn[CONNECTION_INTERFACE_REQUESTS].CreateChannel({
            CHANNEL + '.ChannelType': CHANNEL_TYPE_FILE_TRANSFER,
            CHANNEL + '.TargetHandleType': CONNECTION_HANDLE_TYPE_CONTACT,
            CHANNEL + '.TargetHandle': handle,
            CHANNEL_TYPE_FILE_TRANSFER + '.ContentType': 'application/octet-stream',
            CHANNEL_TYPE_FILE_TRANSFER + '.Filename': file_name,
            CHANNEL_TYPE_FILE_TRANSFER + '.Size': size,
            CHANNEL_TYPE_FILE_TRANSFER + '.Description': "I'm testing file transfer using Telepathy",
            CHANNEL_TYPE_FILE_TRANSFER + '.InitialOffset': 0})

    def got_ft_channel(self):
        print "Offer %s to %s" % (self.file_to_offer, self.contact)
        self.sock_addr = self.ft_channel[CHANNEL_TYPE_FILE_TRANSFER].OfferFile(SOCKET_ADDRESS_TYPE_UNIX,
            SOCKET_ACCESS_CONTROL_LOCALHOST, "")

    def ft_state_changed_cb(self, state, reason):
        FTClient.ft_state_changed_cb(self, state, reason)

        if state == FT_STATE_OPEN:
            # receive file
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.sock_addr)

            s.send(file(self.file_to_offer).read())

def usage():
    print "Usage:\n" \
            "Send [file] to [contact]:\n" \
            "\tpython %s [account-file] [contact] [file]\n" \
            "Accept a file transfer from a contact:\n" \
            "\tpython %s [account-file]\n" \
            % (sys.argv[0], sys.argv[0])

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 3:
        account_file = args[0]
        contact = args[1]
        filename = args[2]
        client = FTSenderClient(account_file, contact, filename)
    elif len(args) == 1:
        account_file = args[0]
        client = FTReceiverClient(account_file)
    else:
        usage()
        sys.exit(0)

    client.run()
