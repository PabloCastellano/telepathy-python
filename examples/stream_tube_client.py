import dbus.glib
import gobject
import sys
import time
import os
import socket
import tempfile
import random
import string

from telepathy.client import (
        Connection, Channel)
from telepathy.interfaces import (
        CONN_INTERFACE, CHANNEL_INTERFACE_GROUP, CHANNEL_TYPE_TUBES,
        CHANNEL_TYPE_TEXT)
from telepathy.constants import (
        CONNECTION_HANDLE_TYPE_CONTACT,
        CONNECTION_HANDLE_TYPE_ROOM, CONNECTION_STATUS_CONNECTED,
        CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING,
        TUBE_TYPE_DBUS, TUBE_TYPE_STREAM, TUBE_STATE_LOCAL_PENDING,
        TUBE_STATE_REMOTE_PENDING, TUBE_STATE_OPEN,
        SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ADDRESS_TYPE_ABSTRACT_UNIX,
        SOCKET_ADDRESS_TYPE_IPV4, SOCKET_ADDRESS_TYPE_IPV6,
        SOCKET_ACCESS_CONTROL_LOCALHOST, SOCKET_ACCESS_CONTROL_PORT,
        SOCKET_ACCESS_CONTROL_NETMASK, SOCKET_ACCESS_CONTROL_CREDENTIALS)

from account import connection_from_file

tube_type = {TUBE_TYPE_DBUS: "D-Bus",\
             TUBE_TYPE_STREAM: "Stream"}

tube_state = {TUBE_STATE_LOCAL_PENDING : 'local pending',\
              TUBE_STATE_REMOTE_PENDING : 'remote pending',\
              TUBE_STATE_OPEN : 'open'}

SERVICE = "x-example"

loop = None

class StreamTubeClient:
    def __init__(self, account_file, muc_id, contact_id):
        self.conn = connection_from_file(account_file)
        self.muc_id = muc_id
        self.contact_id = contact_id

        assert self.muc_id is None or self.contact_id is None

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        self.conn[CONN_INTERFACE].connect_to_signal("NewChannel",
                self.new_channel_cb)

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

    def join_muc(self):
        # workaround to be sure that the muc service is fully resolved in
        # Salut.
        time.sleep(2)

        print "join muc", self.muc_id
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_ROOM, [self.muc_id])[0]

        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_ROOM,
            handle, True)

        self.channel_text = Channel(self.conn.dbus_proxy.bus_name, chan_path)

        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_TUBES, CONNECTION_HANDLE_TYPE_ROOM,
            handle, True)
        self.channel_tubes = Channel(self.conn.dbus_proxy.bus_name, chan_path)

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
        suppress_handler):
      if channel_type == CHANNEL_TYPE_TUBES:
            self.channel_tubes = Channel(self.conn.dbus_proxy.bus_name,
                    object_path)

            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal(
                    "TubeStateChanged", self.tube_state_changed_cb)
            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal(
                    "NewTube", self.new_tube_cb)
            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal(
                    "TubeClosed", self.tube_closed_cb)
            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal(
                   "StreamTubeNewConnection",
                   self.stream_tube_new_connection_cb)

            for tube in self.channel_tubes[CHANNEL_TYPE_TUBES].ListTubes():
                id, initiator, type, service, params, state = (tube[0],
                        tube[1], tube[2], tube[3], tube[4], tube[5])
                self.new_tube_cb(id, initiator, type, service, params, state)

    def new_tube_cb(self, id, initiator, type, service, params, state):
        initiator_id = self.conn[CONN_INTERFACE].InspectHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [initiator])[0]

        print "new %s tube (%d) offered by %s. Service: %s. State: %s" % (
                tube_type[type], id, initiator_id, service, tube_state[state])

        if state == TUBE_STATE_OPEN:
            self.tube_opened(id)

    def tube_opened(self, id):
        pass

    def tube_state_changed_cb(self, id, state):
        if state == TUBE_STATE_OPEN:
            self.tube_opened(id)

    def tube_closed_cb(self, id):
        print "tube closed", id

    def stream_tube_new_connection_cb(self, id, handle):
       print "new socket connection on tube %u from %s" % (id,
               self.conn[CONN_INTERFACE].InspectHandles(
                   CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0])

class StreamTubeInitiatorClient(StreamTubeClient):
    def __init__(self, account_file, muc_id, contact_id, socket_path=None):
        StreamTubeClient.__init__(self, account_file, muc_id, contact_id)

        if socket_path is None:
            self.server = TrivialStreamServer()
            self.server.run()
            self.socket_path = self.server.socket_path
        else:
            print "Will export UNIX socket %s" % socket_path
            self.socket_path = socket_path

    def offer_tube(self):
        params = {"login": "badger", "a_int" : 69}
        print "offer tube"
        id = self.channel_tubes[CHANNEL_TYPE_TUBES].OfferStreamTube(SERVICE,
                params, SOCKET_ADDRESS_TYPE_UNIX, dbus.ByteArray(self.socket_path),
                SOCKET_ACCESS_CONTROL_LOCALHOST, "")

class StreamTubeJoinerClient(StreamTubeClient):
    def __init__(self, account_file, muc_id, contact_id, connect_trivial_client):
        StreamTubeClient.__init__(self, account_file, muc_id, contact_id)

        self.tube_accepted = False
        self.connect_trivial_client = connect_trivial_client

    def new_tube_cb(self, id, initiator, type, service, params, state):
        StreamTubeClient.new_tube_cb(self, id, initiator, type, service, params, state)

        if state == TUBE_STATE_LOCAL_PENDING and service == SERVICE and\
                not self.tube_accepted:
            print "accept tube", id
            self.tube_accepted = True
            self.channel_tubes[CHANNEL_TYPE_TUBES].AcceptStreamTube(id,
                    SOCKET_ADDRESS_TYPE_UNIX, SOCKET_ACCESS_CONTROL_LOCALHOST, "")

    def tube_opened(self, id):
        StreamTubeClient.tube_opened(self, id)

        address_type, address = self.channel_tubes[CHANNEL_TYPE_TUBES].GetStreamTubeSocketAddress(
                id, byte_arrays=True)
        assert address_type == SOCKET_ADDRESS_TYPE_UNIX
        print "tube opened. Clients can connect to %s" % address

        if self.connect_trivial_client:
            self.client = TrivialStreamClient(address)
            self.client.connect()

class TrivialStream:
    def __init__(self, socket_path):
        self.socket_path = socket_path

    def read_socket(self, s):
        try:
            data = s.recv(1024)
            if len(data) > 0:
                print "received:", data
        except socket.error, e:
            pass
        return True

    def write_socket(self, s, msg):
        print "send:", msg
        try:
            s = s.send(msg)
        except socket.error, e:
            pass
        return True

class TrivialStreamServer(TrivialStream):
    def __init__(self):
        # generate a socket path
        letters = [random.choice(string.ascii_letters) for i in range(10)]
        socket_path = os.path.join(tempfile.gettempdir(), ''.join(letters))

        TrivialStream.__init__(self, socket_path)

    def run(self):
        print "launch server on socket: %s" % self.socket_path
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.setblocking(1)
        s.settimeout(0.1)
        s.bind(self.socket_path)
        s.listen(1)

        gobject.timeout_add(1000, self.accept_client, s)

    def accept_client(self, s):
        try:
            s2, addr = s.accept()
            s2.setblocking(1)
            s2.setblocking(0.1)
            self.handle_client(s2)
            return True
        except socket.timeout:
            return True

    def handle_client(self, s):
        gobject.timeout_add(5000, self.write_socket, s, "hi !")

class TrivialStreamClient(TrivialStream):
    def __init__(self, socket_path):
        TrivialStream.__init__(self, socket_path)

    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.setblocking(0.1)
        s.connect(self.socket_path)
        print "connected to", self.socket_path
        gobject.timeout_add(1000, self.read_socket, s)
