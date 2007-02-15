import dbus.glib
import gobject
import logging
import sys

from time import sleep

from account import connection_from_file

from telepathy.client.channel import Channel
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE as HANDLE_TYPE_NONE,
    CONNECTION_HANDLE_TYPE_ROOM as HANDLE_TYPE_ROOM,
    CONNECTION_STATUS_CONNECTED,
    CHANNEL_TEXT_MESSAGE_TYPE_NORMAL)
from telepathy.interfaces import CHANNEL_TYPE_ROOM_LIST, CONN_INTERFACE

logging.basicConfig()

class RoomListChannel(Channel):
    def __init__(self, *stuff):
        Channel.__init__(self, *stuff)
        self.get_valid_interfaces().add(CHANNEL_TYPE_ROOM_LIST)

class RoomListExample:
    def __init__(self, conn):
        self.conn = conn

        conn[CONN_INTERFACE].connect_to_signal('StatusChanged',
            self.status_changed_cb)
        conn[CONN_INTERFACE].connect_to_signal('NewChannel',
            self.new_channel_cb)

    def run(self):
        print "main loop running"
        self.loop = gobject.MainLoop()
        self.loop.run()

    def quit(self):
        if self.loop:
            self.loop.quit()
            self.loop = None

    def status_changed_cb(self, state, reason):
        if state != CONNECTION_STATUS_CONNECTED:
            return
        print "connection became ready, requesting channel"

        try:
            conn[CONN_INTERFACE].RequestChannel(
                CHANNEL_TYPE_ROOM_LIST, HANDLE_TYPE_NONE, 0, True,
                reply_handler=self.request_channel_cb,
                error_handler=self.request_channel_error_cb)
        except Exception, e:
            print e
            self.quit()

    def request_channel_error_cb(self, exception):
        print 'error returned by RequestChannel:', exception
        self.quit()

    def new_channel_cb(self, object_path, channel_type, handle_type, handle,
            suppress_handler):
        if channel_type != CHANNEL_TYPE_ROOM_LIST:
            return

        print 'New room-list channel created'

    def request_channel_cb(self, object_path):
        print "Got requested channel:", object_path

        channel = RoomListChannel(
            self.conn._dbus_object._named_service, object_path)

        print "Connecting to ListingRooms"
        channel[CHANNEL_TYPE_ROOM_LIST].connect_to_signal('ListingRooms',
                                                         self.listing_cb)
        print "Connecting to GotRooms"
        channel[CHANNEL_TYPE_ROOM_LIST].connect_to_signal('GotRooms',
                                                         self.rooms_cb)
        print "Calling ListRooms"
        channel[CHANNEL_TYPE_ROOM_LIST].ListRooms()

    def listing_cb(self, listing):
        if listing:
            print "Listing rooms..."
        else:
            print "Finished listing rooms"
            self.quit()

    def rooms_cb(self, rooms):
        handles = [room[0] for room in rooms]
        names = self.conn[CONN_INTERFACE].InspectHandles(HANDLE_TYPE_ROOM,
                                                         handles)

        for i in xrange(len(rooms)):
            handle, ctype, info = rooms[i]
            name = names[i]
            print "Found room:", name
            print "\t", ctype
            for key in info:
                print "\t", repr(str(key)), " => ", repr(info[key])

if __name__ == '__main__':
    conn = connection_from_file(sys.argv[1])

    ex = RoomListExample(conn)

    print "connecting"
    conn[CONN_INTERFACE].Connect()

    try:
        ex.run()
    except KeyboardInterrupt:
        print "killed"

    print "disconnecting"
    conn[CONN_INTERFACE].Disconnect()
