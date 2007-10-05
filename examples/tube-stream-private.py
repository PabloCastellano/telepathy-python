import sys
from telepathy.client import (Connection, Channel)
from telepathy.interfaces import (CONN_INTERFACE, CHANNEL_TYPE_TUBES)
from telepathy.constants import (CONNECTION_HANDLE_TYPE_CONTACT)

from stream_tube_client import StreamTubeJoinerClient, \
        StreamTubeInitiatorClient

class StreamTubeInitiatorPrivateClient(StreamTubeInitiatorClient):
    def __init__(self, account_file, contact_id, socket_address=None):
        StreamTubeInitiatorClient.__init__(self, account_file, None, contact_id, socket_address)

    def connected_cb(self):
        StreamTubeInitiatorClient.connected_cb(self)

        self.tubes_with_contact()
        self.offer_tube()

    def tubes_with_contact(self):
        handle = self.conn[CONN_INTERFACE].RequestHandles(
                CONNECTION_HANDLE_TYPE_CONTACT, [self.contact_id])[0]

        chan_path = self.conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_TUBES, CONNECTION_HANDLE_TYPE_CONTACT,
            handle, True)
        self.channel_tubes = Channel(self.conn.dbus_proxy.bus_name, chan_path)

class StreamTubeJoinerPrivateClient(StreamTubeJoinerClient):
    def __init__(self, account_file, connect_trivial_client):
        StreamTubeJoinerClient.__init__(self, account_file, None, None,
                connect_trivial_client)

    def connected_cb(self):
        StreamTubeJoinerClient.connected_cb(self)

        print "waiting for a tube offer from contacts"

def usage():
    print "Usage:\n" \
            "Offer a stream tube to [contact] using the trivial stream server:\n" \
            "\tpython %s [account-file] [contact]\n" \
            "Accept a stream tube from a contact and connect it to the trivial stream client:\n" \
            "\tpython %s [account-file]\n" \
            "Offer a stream tube to [contact] using the socket [IP]:[port]:\n" \
            "\tpython %s [account-file] [contact] [IP] [port]\n" \
            "Accept a stream tube from a contact and wait for connections from an external client:\n" \
            "\tpython %s [account-file] --no-trivial-client\n" \
            % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0])

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 2 and args[1] != '--no-trivial-client':
        client = StreamTubeInitiatorPrivateClient(args[0], contact_id=args[1])
    elif len(args) == 1:
        client = StreamTubeJoinerPrivateClient(args[0], True)
    elif len(args) == 4:
        client = StreamTubeInitiatorPrivateClient(args[0], args[1], (args[2], int(args[3])))
    elif len(args) == 2 and args[1] == '--no-trivial-client':
        client = StreamTubeJoinerPrivateClient(args[0], False)
    else:
        usage()
        sys.exit(0)

    client.run()
