#!/usr/bin/env python

import dbus
import dbus.glib

assert(getattr(dbus, 'version', (0,0,0)) >= (0,51,0))

import getpass
import gobject
import signal
import sys

from managerregistry import *

from telepathy import *

class Channel(object):
    def __init__(self, conn, obj_path):
        self.bus = conn.bus
        self.conn = conn
        self.mainloop = conn.mainloop

        self.chan_obj = self.bus.get_object(self.conn.serv_name, obj_path)
        self.chan = dbus.Interface(self.chan_obj, CHANNEL_INTERFACE)

class ListChannel(Channel):
    def __init__(self, conn, obj_path):
        Channel.__init__(self, conn, obj_path)

class TextChannel(Channel):
    def __init__(self, conn, obj_path):
        Channel.__init__(self, conn, obj_path)
        self.text = dbus.Interface(self.chan_obj, CHANNEL_TYPE_TEXT)
        self.text.connect_to_signal('Received', self.received_callback)
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
        self.text.Send('normal', 'got message ' + str(id) + '(' + message + ')')
        if self.doack:
            print "Acknowledging...", id
            self.text.AcknowledgePendingMessage(id)

class Connection:
    def channel_callback(self, type, obj_path, requested):
        if self.channels.has_key(obj_path):
            return

        print 'NewChannel', type, obj_path, requested

        channel = None

        if type == CHANNEL_TYPE_TEXT:
            channel = TextChannel(self, obj_path)
        elif type == CHANNEL_TYPE_CONTACT_LIST:
            channel = ListChannel(self, obj_path)

        if channel != None:
            self.channels[obj_path] = channel
        else:
            print 'Unknown channel type', type

    def status_callback(self, status, reason):
        if self.status == status:
            return
        else:
            self.status = status

        #if status == 'connected':
            #obj_path = self.conn.RequestChannel(CHANNEL_TYPE_TEXT, {'recipient':'test2@localhost'})
        if status == 'disconnected':
            self.mainloop.quit()

        print 'StatusChanged', status

    def __init__(self, mainloop, mgr_bus_name, mgr_object_path, proto, account, conn_opts):
        self.bus = dbus.SessionBus()
        self.mainloop = mainloop

        mgr_obj = self.bus.get_object(mgr_bus_name, mgr_object_path)
        mgr = dbus.Interface(mgr_obj, CONN_MGR_INTERFACE)
        self.serv_name, obj_path = mgr.Connect(proto, account, conn_opts)

        self.conn_obj = self.bus.get_object(self.serv_name, obj_path)
        self.conn = dbus.Interface(self.conn_obj, CONN_INTERFACE)

        self.status = 'connecting'
        self.conn.connect_to_signal('StatusChanged', self.status_callback)

        # handle race condition when connecting completes before the
        # status changed signal handler is registered
        self.status_callback(self.conn.GetStatus(), 'request')

        self.channels = {}
        self.conn.connect_to_signal('NewChannel', self.channel_callback)

        # handle race condition when a channel arrives before the new
        # channel signature 
        channels = self.conn.ListChannels()
        for channel in channels:
            (type, obj_path) = channel
            self.channel_callback(type, obj_path, True)

if __name__ == '__main__':
    reg = ManagerRegistry()
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

     
    if len(sys.argv) > 3:
        account = sys.argv[3]
    else:
        account = raw_input('Account: ')

    cmdline_params = dict((p.split('=') for p in sys.argv[4:]))
    params={}

    for (name, (type, default)) in reg.GetParams(manager, protocol)[0].iteritems():
        if name in cmdline_params:
            params[name] = dbus.Variant(cmdline_params[name],type)    
        elif name == 'password':
            params[name] = dbus.Variant(getpass.getpass(),type)
        else:
            params[name] = dbus.Variant(raw_input(name+': '),type)
            
    mainloop = gobject.MainLoop()
    connection = Connection(mainloop, mgr_bus_name, mgr_object_path, protocol, account, params)

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
