
import dbus.glib
import gobject
import sys
import time
import random
import pprint
from dbus.service import method, signal, Object
from dbus import Interface

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
        TUBE_STATE_REMOTE_PENDING, TUBE_STATE_OPEN)

from account import connection_from_file
from tubeconn import TubeConnection

SERVICE = "org.freedesktop.Telepathy.Tube.Test"
IFACE = SERVICE
PATH = "/org/freedesktop/Telepathy/Tube/Test"

tube_type = {TUBE_TYPE_DBUS: "D-Bus",\
             TUBE_TYPE_STREAM: "Stream"}

tube_state = {TUBE_STATE_LOCAL_PENDING : 'local pending',\
              TUBE_STATE_REMOTE_PENDING : 'remote pending',\
              TUBE_STATE_OPEN : 'open'}

loop = None

class Client:
    def __init__(self, account_file, muc_id):
        self.conn = connection_from_file(account_file)
        self.muc_id = muc_id

        self.conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        self.conn[CONN_INTERFACE].connect_to_signal ("NewChannel",
                self.new_channel_cb)

        self.test = None

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
        print "join muc", self.muc_id
        handle = self.conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_ROOM, [self.muc_id])[0]

        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_TEXT, CONNECTION_HANDLE_TYPE_ROOM,
            handle, True)

        self.channel_text = Channel(self.conn._dbus_object._named_service,
                chan_path)

        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_TUBES, CONNECTION_HANDLE_TYPE_ROOM,
            handle, True)
        self.channel_tubes = Channel(self.conn._dbus_object._named_service,
                chan_path)

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
        suppress_handler):
      if channel_type == CHANNEL_TYPE_TUBES:
            self.channel_tubes = Channel(self.conn._dbus_object._named_service,
                    object_path)

            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal (
                    "TubeStateChanged", self.tube_state_changed_cb)
            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal (
                    "NewTube", self.new_tube_cb)
            self.channel_tubes[CHANNEL_TYPE_TUBES].connect_to_signal (
                    "TubeClosed", self.tube_closed_cb)

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
            self.tube_opened (id)

    def tube_opened (self, id):
        group_iface = self.channel_text[CHANNEL_INTERFACE_GROUP]

        tube_conn = TubeConnection(self.conn,
                self.channel_tubes[CHANNEL_TYPE_TUBES],
                id, group_iface=group_iface)

        self.test = Test (tube_conn, self.conn)

    def tube_state_changed_cb(self, id, state):
        if state == TUBE_STATE_OPEN:
            self.tube_opened(id)

    def tube_closed_cb (self, id):
        print "tube closed", id


class InitiatorClient(Client):
    def __init__(self, account_file, muc_id):
        Client.__init__(self, account_file, muc_id)

    def connected_cb(self):
        Client.connected_cb(self)

        self.join_muc()
        self.offer_tube()

    def tube_opened (self, id):
        Client.tube_opened(self, id)

        self._emit_test_signal();
        gobject.timeout_add (20000, self._emit_test_signal)

    def offer_tube(self):
        params = {"login": "badger", "a_int" : 69}
        print "offer tube"
        id = self.channel_tubes[CHANNEL_TYPE_TUBES].OfferDBusTube(SERVICE,
                params)

    def _emit_test_signal (self):
        print "emit Hello"
        self.test.Hello()
        return True

class JoinerClient(Client):
    def __init__(self, account_file, muc_id):
        Client.__init__(self, account_file, muc_id)

    def connected_cb(self):
        Client.connected_cb(self)

        self.join_muc()

    def new_tube_cb(self, id, initiator, type, service, params, state):
        Client.new_tube_cb(self, id, initiator, type, service, params, state)

        if state == TUBE_STATE_LOCAL_PENDING and service == SERVICE and\
                self.test is None:
            print "accept tube", id
            self.channel_tubes[CHANNEL_TYPE_TUBES].AcceptDBusTube(id)


    def tube_opened (self, id):
        Client.tube_opened(self, id)

        self.test.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
            path=PATH, sender_keyword='sender')

    def hello_cb (self, sender=None):
        sender_handle = self.test.tube.bus_name_to_handle[sender]
        sender_id = self.conn[CONN_INTERFACE].InspectHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [sender_handle])[0]
        self_id = self.conn[CONN_INTERFACE].InspectHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [self.self_handle])[0]

        print "Hello from %s" % sender

        text = "I'm %s and thank you for your hello" % self_id
        print "call remote Say"
        self.test.tube.get_object(sender, PATH).Say(text, dbus_interface=IFACE)

class Test(Object):
    def __init__(self, tube, conn):
        super(Test, self).__init__(tube, PATH)
        self.tube = tube
        self.conn = conn

    @signal(dbus_interface=IFACE, signature='')
    def Hello(self):
        pass

    @method(dbus_interface=IFACE, in_signature='s', out_signature='b')
    def Say(self, text):
        print "I say: %s" % text
        return True

def usage():
    print "python %s [account-file] [muc]\n" \
            "python %s [account-file] [muc] --initiator"\
            % (sys.argv[0], sys.argv[0])

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 2:
        client = JoinerClient(args[0], args[1])
    elif len(args) == 3 and args[2] == '--initiator':
        client = InitiatorClient(args[0], args[1])
    else:
        usage()
        sys.exit(0)

    client.run()
