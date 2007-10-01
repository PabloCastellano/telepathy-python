import sys

from stream_tube_client import StreamTubeJoinerClient, \
        StreamTubeInitiatorClient

def usage():
    print "Usage:\n" \
            "Offer a stream tube to [muc] using the trivial stream server:\n" \
            "\tpython %s [account-file] [muc] --initiator\n" \
            "Accept a stream tube from [muc] and connect it to the trivial stream client:\n" \
            "\tpython %s [account-file] [muc]\n" \
            "Offer a stream tube to [muc] using the UNIX socket [socket]:\n" \
            "\tpython %s [account-file] [muc] --initiator [socket]\n" \
            "Accept a stream tube from [muc] and wait for connections from an external client:\n" \
            "\tpython %s [account-file] [muc] --no-trivial-client\n" \
            % (sys.argv[0], sys.argv[0], sys.argv[0], sys.argv[0])

if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) == 3 and args[2] == '--initiator':
        client = StreamTubeInitiatorClient(args[0], args[1])
    elif len(args) == 2:
        client = StreamTubeJoinerClient(args[0], args[1], True)
    elif len(args) == 4 and args[2] == '--initiator':
        client = StreamTubeInitiatorClient(args[0], args[1], args[3])
    elif len(args) == 3 and args[2] == '--no-trivial-client':
        client = StreamTubeJoinerClient(args[0], args[1], False)
    else:
        usage()
        sys.exit(0)

    client.run()
