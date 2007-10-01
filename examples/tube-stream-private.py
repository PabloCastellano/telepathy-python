import sys

from stream_tube_client import StreamTubeJoinerPrivateClient, \
        StreamTubeInitiatorPrivateClient

def usage():
    print "Usage:\n" \
            "Offer a stream tube to [contact] using the trivial stream server:\n" \
            "\tpython %s [account-file] [contact]\n" \
            "Accept a stream tube from a contact and connect it to the trivial stream client:\n" \
            "\tpython %s [account-file]\n" \
            "Offer a stream tube to [contact] using the UNIX socket [socket]:\n" \
            "\tpython %s [account-file] [contact] [socket]\n" \
            "Accept a stream tube from a contact and wait for connections from an external client:\n" \
            "\tpython %s [account-file] --no-trivial-client\n" \
            % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0])

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 2 and args[1] != '--no-trivial-client':
        client = StreamTubeInitiatorPrivateClient(args[0], contact_id=args[1])
    elif len(args) == 1:
        client = StreamTubeJoinerPrivateClient(args[0], True)
    elif len(args) == 3:
        client = StreamTubeInitiatorPrivateClient(args[0], args[1], args[2])
    elif len(args) == 2 and args[1] == '--no-trivial-client':
        client = StreamTubeJoinerPrivateClient(args[0], False)
    else:
        usage()
        sys.exit(0)

    client.run()
