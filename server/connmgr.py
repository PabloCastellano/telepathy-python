#!/usr/bin/env python

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import time

CONN_MGR_INTERFACE = 'org.freedesktop.telepathy.ConnectionManager'
CONN_MGR_OBJECT = '/org/freedesktop/telepathy/ConnectionManager'
CONN_MGR_SERVICE = 'org.freedesktop.telepathy.ConnectionManager'

CONN_INTERFACE = 'org.freedesktop.telepathy.Connection'
CONN_OBJECT = '/org/freedesktop/telepathy/Connection'
CONN_SERVICE = 'org.freedesktop.telepathy.Connection'

CHANNEL_INTERFACE = 'org.freedesktop.telepathy.Channel'
TEXT_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.TextChannel'
LIST_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.ListChannel'

INDIVIDUAL_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.IndividualChannelInterface'
GROUP_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.GroupChannelInterface'
NAMED_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.NamedChannelInterface'
PRESENCE_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.PresenceChannelInterface'
SUBJECT_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.SubjectChannelInterface'

class Channel(dbus.service.Object):
    """
    Base type for all Channels.
    """
    count = 0

    def __init__(self, connection, type):
        """
        Channel constructor. 
        Paramters:
        connection - the parent Connection object
        type - 
        """
        self.conn = conn
        self.object_path = self.conn.object_path+'/channel'+str(Channel.count)
        Channel.count += 1
        dbus.service.Object.__init__(self, self.conn.bus_name, self.object_path)

        self.type = type
        self.interfaces = set()
        self.members = set()

    @dbus.service.method(CHANNEL_INTERFACE, in_signature="", out_signature="")
    def Close(self):
        """ Close this channel. """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE, signature="")
    def Closed(self):
        """ Emitted when this channel is closed. """
        print 'object_path: %s signal: Closed' % (self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature="", out_signature="s")
    def GetType(self):
        """ Returns an interface name for the type of this channel """
        return dbus.String(self.type)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature="", out_signature="as")
    def GetInterfaces(self):
        """ 
        Get the interfaces this channel implements.
    
        returns an array of interface names.
        """
        return dbus.Array(self.interfaces, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE, in_signature="", out_signature="as")
    def GetMembers(self):
        """ Returns an array of identifiers for the members of this channel."""
        return dbus.Array(self.members, signature='s')

class IndividualChannelInterface(object):
    """ 
    A mixin that implements channels that have only
    you and another as members.
    implemented by dbus interface 
    org.freedesktop.telepathy.IndividualChannelInterface
    """
    def __init__(self, recipient):
        """
        recipient parameter is an identifier for the other member of 
        the channel
        """
        self.interfaces.add(INDIVIDUAL_CHANNEL_INTERFACE)
        self.members.add(recipient)
        self.recipient = recipient

class GroupChannelInterface(object):
    """
    Interface for channels which have multiple members.

    implemented by dbus interface
    org.freedesktop.telepathy.GroupChannelInterface

    Channels implementing this interface may have multiple members.
    If a  contact is in the channel, they may have the states:
    Invited - they were invited to the channel, but have not yet accepted the 
              invitation.
    Requested - they requested membership of the channel, but the request has
                not yet been granted.
    Present - they are currently present in the channel

    If a contact accepts an invitation, this is signalled by that contact going
    from Invited to Present.
    If the user wishes to acknowlege a Requested contact, they simply invite 
    them and they will become Present. If they wish do decline a request, they
    remove that member from the channel
    If the user opens a groupchannel which they need to request membership of, 
    they will be placed in the Requested state and be unable to send messages
    until an authorizing party acknowledges their rewuest, at wich pouint they 
    will transition to Present.
    """
 
    def __init__(self):
        self.interfaces.add(GROUP_CHANNEL_INTERFACE)
        self.requested = set()
        self.invited = set()

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature="as", out_signature="")
    def InviteMembers(self, contacts):
        """ Invite all the contacts in contacts into the channel 
        """

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signatiure="as", out_signature="")
    def RemoveMembers(self, members):
        """
        Requests the removal of members from a channel
        """
        pass

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature="", out_signature="as")
    def GetRequestedMembers(self):
        """ Returns an array of the currently requested members"""
        return requested

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature="", out_signature="as")
    def GetInvitedMembers(self):
        """ Returns an array of the currently invited members"""
        return invited

    @dbus.service.signal(GROUP_CHANNEL_INTERFACE, signature="asasasas")
    def MembersChanged(self, added, removed, requested, invited):
        """
        Emitted when members change state.

        members in added became Present
        members in removed left the channel (and hence are no longer
        Present, Requested or Invited)
        members in requested became Requested
        members in invited became Invited
        """

        self.members.update(added)
        self.members.difference_update(removed)

        self.requested.update(requested)
        self.requested.difference_update(added)
        self.requested.difference_update(removed)

        self.invited.update(invited)
        self.invited.difference_update(added)
        self.invited.difference_update(removed)

class NamedChannelInterface(object):
    """
    Interface for channels which have an immutable name

    Implemented by dbus interface
    org.freedesktop.telepathy.NamedChannelInterface
    """
    def __init__(self, name):
        """ name is the immutable name of this channel. """
        self.interfaces.add(NAMED_CHANNEL_INTERFACE)
        self.name = name

    @dbus.service.method(NAMED_CHANNEL_INTERFACE, in_signature="", out_signature="s")
    def GetName(self):
        """ Get the immutable name of this channel. """
        return self.name

class PresenceChannelInterface(object):
    """ 
    Interface for channels that can signal presence changes

    Implemented by dbus interface
    org.freedesktop.telepathy.NamedChannelInterface
    """
    def __init__(self):
        self.interfaces.add(PRESENCE_CHANNEL_INTERFACE)

class SubjectChannelInterface(object):
    """ 
    Interface for channels that have a modifiable subject or topic

    Implemented by dbus interface
    org.freedesktop.telepathy.SubjectChannelInterface
    """
    def __init__(self, subject):
        """ subject is a string for the initial subject of the channel"""
        self.interfaces.add(SUBJECT_CHANNEL_INTERFACE)
        self.subject = subject

    @dbus.service.method(SUBJECT_CHANNEL_INTERFACE, in_signature="", out_signature="s")
    def GetSubject(self):
        """ Get this channel's current subject. """
        return self.subject

    @dbus.service.method(SUBJECT_CHANNEL_INTERFACE, in_signature="s", out_signature="")
    def SetSubject(self, subject)
        """ Set this channels subject."""
        pass

    @dbus.service.signal(SUBJECT_CHANNEL_INTERFACE, signature="s")
    def SubjectChanged(self, subject):
        """ Emitted when the subject changes. """
        self.subject = subject

class TextChannel(Channel):
    """
    Base class for Text type Channel implementation.
    to use,  mixin the appropriate interfaces and
    override sendCallback to send a mesage,

    If a message has been received on a text channel, a 'Received' signal is
    emitted and the message is placed in a pending queue. Any appliaction that
    has reliably informed the user of that message can then acknowledge that
    pending message with its ID. The message will then be removed from the
    pending queue.
    """
    def __init__(self, connection):
        """ connection is the parent telepathy Connection object """
        Channel.__init__(self, connection, TEXT_CHANNEL_INTERFACE)

        self.send_id = 0
        self.recv_id = 0
        self.pending_messages = {}

    def sendCallback(self, id, text):
        """ Ovveride this stub to send a message over the parent Connection. """
        pass

    def stampMessage(self, id, text):
        """Stamp a message's timestamp signal it as sent"""
        timestamp = int(time.time())
        self.Sent(id, timestamp, text)

    def queueMessage(self, timestamp, text):
        """
        Place a message into the messagequeue with the given timestamp,
        and signal it as received
        """
        id = self.recv_id
        self.recv_id += 1

        self.pending_messages[id] = (timestamp, text)
        self.Received(id, timestamp, text)

    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature="s", out_signature="u")
    def Send(self, text):
        """ 
        Send a message on this channel.
        
        Returns a numeric id for the message
        """
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.sendCallback, id, text)
        return id

    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature="u", out_signature="b")
    def AcknowledgePendingMessage(self, id):
        """
        Inform the channel that you have responsibly dealt with a pending 
        message id

        Returns true if message was pending, false if the id was unknown
        """
        if self.pending_messages.has_key(id):
            del self.pending_messages[id]
            return True
        else:
            return False
    
    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature="", out_signature="a(uus)")
    def ListPendingMessages(self):
        """
        List the messages currently in the pending queue.

        Returns an array of structs conataining (id, timestamp, text)
        """
        messages = []
        for id in self.pending_messages.keys():
            (timestamp, text) = self.pending_messages[id]
            message = (id, timestamp, text)
            messages.append(message)
        messages.sort(cmp=lambda x,y:cmp(x[1], y[1]))
        return dbus.Array(messages, signature='(uus)')

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE, signature="uus"))
    def Sent(self, id, timestamp, text):
        """
        Signals that a message with the given id, timestamp and text has 
        been sent on the parent connection.
        """
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE, sigature="uus")
    def Received(self, id, timestamp, text):
        """
        Signals that a message with the given id, timestamp and text has 
        been received on the parent connection.

        Applications that catch this signal and reliably inform the user should
        acknowledge that they have dealt with the message.
        """
        print 'object_path: %s signal: Received %d %d %s' % (self.object_path, id, timestamp, text)


class Connection(dbus.service.Object):
    """
    Base class to implement a connection object. 
    override Disconnect to disconnect this connection
    override RequestChannel to create the requested channel types,
    or IOError if not possible
    """
    def __init__(self, manager, proto, account, name_parts):
        self.service_name = '.'.join([CONN_SERVICE] + name_parts)
        self.object_path = '/'.join([CONN_OBJECT] + name_parts)
        self.bus_name = dbus.service.BusName(self.service_name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)

        self.channels = set()
        self.lists = {}
        self.manager = manager
        self.proto = proto
        self.account = account

    def addChannel(self, channel):
        self.channels.add(channel)
        self.NewChannel(channel.type, channel.object_path)

    @dbus.service.method(CONN_INTERFACE)
    def GetProtocol(self):
        return self.proto

    @dbus.service.method(CONN_INTERFACE)
    def GetAccount(self):
        return self.account

    @dbus.service.signal(CONN_INTERFACE)
    def StatusChanged(self, status):
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self.status = status

    @dbus.service.method(CONN_INTERFACE)
    def GetStatus(self):
        return self.status

    @dbus.service.method(CONN_INTERFACE)
    def Disconnect(self):
        pass

    @dbus.service.signal(CONN_INTERFACE)
    def NewChannel(self, type, object_path):
        print 'service_name: %s object_path: %s signal: NewChannel %s %s' % (self.service_name, self.object_path, type, object_path)

    @dbus.service.method(CONN_INTERFACE)
    def ListChannels(self):
        ret = []
        for channel in self.channels:
            chan = (channel.type, channel.object_path)
            ret.append(chan)
        return dbus.Array(ret, signature='(ss)')

    @dbus.service.method(CONN_INTERFACE)
    def RequestChannel(self, type, interfaces):
        raise IOError('Unknown channel type %s' % type)

class ConnectionManager(dbus.service.Object):
    def __init__(self, name):
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.'+name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/'+name')

        self.connections = set()
        self.protos = {}

    def __del__(self):
        print "explodes"
        dbus.service.Object.__del__(self)

    def disconnected(self, conn):
        self.connections.remove(conn)
        del conn

    @dbus.service.method(CONN_MGR_INTERFACE)
    def ListProtocols(self):
        return self.protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE)
    def Connect(self, proto, account, connect_info):
        if self.protos.has_key(proto):
            conn = self.protos[proto](self, account, connect_info)
            self.connections.add(conn)
            self.NewConnection(conn.service_name, conn.object_path, conn.proto, conn.account)
            return (conn.service_name, conn.object_path)
        else:
            raise IOError('Unknown protocol %s' % (proto))

    @dbus.service.signal(CONN_MGR_INTERFACE)
    def NewConnection(self, service_name, object_path, proto, account):
        pass
