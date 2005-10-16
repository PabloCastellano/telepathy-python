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
DTMF_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.DTMFChannel'

INDIVIDUAL_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.IndividualChannelInterface'
GROUP_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.GroupChannelInterface'
NAMED_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.NamedChannelInterface'
PRESENCE_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.PresenceChannelInterface'
SUBJECT_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.SubjectChannelInterface'
STREAMED_MEDIA_CHANNEL_INTERFACE = 'org.freedesktop.telepathy.StreamedMediaChannelInterface'

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
        self.conn = connection
        self.object_path = self.conn.object_path+'/channel'+str(Channel.count)
        Channel.count += 1
        dbus.service.Object.__init__(self, self.conn.bus_name, self.object_path)

        self.type = type
        self.interfaces = set()
        self.members = set()

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='')
    def Close(self):
        """ Close this channel. """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE, signature='')
    def Closed(self):
        """ Emitted when this channel is closed. """
        print 'object_path: %s signal: Closed' % (self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='s')
    def GetType(self):
        """ Returns an interface name for the type of this channel """
        return dbus.String(self.type)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """ 
        Get the interfaces this channel implements.
    
        returns an array of interface names.
        """
        return dbus.Array(self.interfaces, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
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

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature='as', out_signature='')
    def InviteMembers(self, contacts):
        """ Invite all the contacts in contacts into the channel 
        """
        pass

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature='as', out_signature='')
    def RemoveMembers(self, members):
        """
        Requests the removal of members from a channel
        """
        pass

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetRequestedMembers(self):
        """ Returns an array of the currently requested members"""
        return requested

    @dbus.service.method(GROUP_CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetInvitedMembers(self):
        """ Returns an array of the currently invited members"""
        return invited

    @dbus.service.signal(GROUP_CHANNEL_INTERFACE, signature='asasasas')
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

    @dbus.service.method(NAMED_CHANNEL_INTERFACE, in_signature='', out_signature='s')
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

    @dbus.service.method(SUBJECT_CHANNEL_INTERFACE, in_signature='', out_signature='s')
    def GetSubject(self):
        """ Get this channel's current subject. """
        return self.subject

    @dbus.service.method(SUBJECT_CHANNEL_INTERFACE, in_signature='s', out_signature='')
    def SetSubject(self, subject):
        """ Set this channels subject."""
        pass

    @dbus.service.signal(SUBJECT_CHANNEL_INTERFACE, signature='s')
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

    def queueMessage(self, timestamp, sender, text):
        """
        Place a message 'text' from 'sender' 
        into the messagequeue with the given timestamp,
        and signal it as received
        """
        id = self.recv_id
        self.recv_id += 1

        self.pending_messages[id] = (timestamp, sender, text)
        self.Received(id, timestamp, sender, text)

    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature='s', out_signature='u')
    def Send(self, text):
        """ 
        Send a message on this channel.
        
        Returns a numeric id for the message
        """
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.sendCallback, id, text)
        return id

    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature='u', out_signature='b')
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

    @dbus.service.method(TEXT_CHANNEL_INTERFACE, in_signature='', out_signature='a(uuss)')
    def ListPendingMessages(self):
        """
        List the messages currently in the pending queue.

        Returns an array of structs conataining (id, timestamp, sender, text)
        """
        messages = []
        for id in self.pending_messages.keys():
            (timestamp, sender, text) = self.pending_messages[id]
            message = (id, timestamp, sender, text)
            messages.append(message)
        messages.sort(cmp=lambda x,y:cmp(x[1], y[1]))
        return dbus.Array(messages, signature='(uuss)')

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE, signature='uus')
    def Sent(self, id, timestamp, text):
        """
        Signals that a message with the given id, timestamp and text has 
        been sent on the parent connection.
        """
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(TEXT_CHANNEL_INTERFACE, signature='uuss')
    def Received(self, id, timestamp, sender, text):
        """
        Signals that a message with the given id, timestamp, sender and text 
        has been received on the parent connection.

        Applications that catch this signal and reliably inform the user should
        acknowledge that they have dealt with the message.
        """
        print 'object_path: %s signal: Received %d %d %s %s' % (self.object_path, id, timestamp, sender, text)


class DTMFChannelInterface(object):
    """
    An interface that gives a Channel the ability to send or receive DTMF. 
    This usually only makes sense for channels transporting audio.
    """
    def __init__(self):
        self.interfaces.add(DTMF_CHANNEL_INTERFACE)

    @dbus.service.method(DTMF_CHANNEL_INTERFACE, in_signature='uu', out_signature='')
    def SendDTMF(signal, duration):
        """Send a DTMF tone of type 'signal' of duration milliseconds"""
        pass

    @dbus.service.signal(DTMF_CHANNEL_INTERFACE, signature='uu')
    def RecievedDTMF(signal, duration):
        """
        Signals that this channel recieved a DTMF tone of type signal
        and of duration milliseconds.
        """
        pass

class StreamedMediaChannel(Channel):
    """
    A channel that can send and receive streamed media.

    All communication on this channel takes the form of exchnaged messages in
    SDP (see IETF RFC 2327). at any given time,this channel can be queried for
    the last received SDP.
    In general negotiations over this channel will take the form of
    IETF RFC 3264 - " An Offer/Answer Model with the Session Description 
    Protocol"
    """
    def __init__(self, connection):
        """ connection is the parent telepathy Connection object """
        Channel.__init__(self, connection, STREAMED_MEDIA_CHANNEL_INTERFACE)
        self.lastSendSDP=""
        self.lastReceivedSDP=""

    @dbus.service.method(STREAMED_MEDIA_CHANNEL_INTERFACE, in_signature='s', out_signature='id')
    def Send(self, recipient, sdp):
        """ 
        Attempt to send a message on this channel to the named recipient on this channel.
        returns an id for this send attempt
        """
        pass
       
    @dbus.service.signal(STREAMED_MEDIA_CHANNEL_INTERFACE, signature='uus')
    def Sent(self, id, recipient, sdp):
        """
        Signals that an sdp message with the given id has 
        been sent on this channel to the given recipient.
        """
        pass

    @dbus.service.signal(STREAMED_MEDIA_CHANNEL_INTERFACE, signature='uuss')
    def Received(self, id, sender, sdp):
        """
        Signals that an sdp message with the given id has 
        been received on this channel to the given recipient.
        """
        pass



class Connection(dbus.service.Object):
    """
    Base class to implement org.freedesktop.telepathy.Connection. 

    This models a connection to a single user account on a communication
    service. Its basic capability is to create channels on which to communicate.

    Other interfaces may also be added for conncetion services that provide
    extra connection-wide functionality. (eg ???)

    override Disconnect to disconnect this connection
    override RequestChannel to create the requested channel types,

    """
    def __init__(self, manager, proto, account, name_parts):
        """
        parameters:
        manager - the Telepathy ConectionManager that created this Connection.
        proto - the name of the protcol this conection should be handling. 
        account - a protocol-specific account name
        name_parts - a list of strings with which to form the service and      
        object names.
        """
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
        """ add a new channel and signal its creation""" 
        self.channels.add(channel)
        self.NewChannel(channel.type, channel.object_path)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        """
        Get the protocol this connection is using
        
        returns the name of the protocol as a string
        """
        return self.proto

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetAccount(self):
        """
        Get the acount this connection is using
        """
        return self.account

    @dbus.service.signal(CONN_INTERFACE, signature='s')
    def StatusChanged(self, status):
        """ 
        Emitted when the status of the connection changes with a string
        indicating the new state
        TODO: list of basic states?
        """
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self.status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetStatus(self):
        """ Get the current status """
        return self.status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='')
    def Disconnect(self):
        """ 
        Stub handler. Overridden in concrete subclasses to disconnect the
        connection.
        """
        pass

    @dbus.service.signal(CONN_INTERFACE, signature='so')
    def NewChannel(self, type, object_path):
        """
        Emitted when a new Channel object is created, either through
        user request or from the service delivering a message which 
        maps to no current channel
        type is a dbus interface name for the basic type of the new channel
        object_path is the dbus object path where the new channel can be found
        on this dbus connection.
        """
        print 'service_name: %s object_path: %s signal: NewChannel %s %s' % (self.service_name, self.object_path, type, object_path)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='a(so)')
    def ListChannels(self):
        """
        List all the channels currently availaible on this connection.
        Returns an array of (channel type, channel object_path) where type is a
        dbus interface name for the basic type of the new channel and 
        object_path is the dbus object path where the new channel can be found.
         """
        ret = []
        for channel in self.channels:
            chan = (channel.type, channel.object_path)
            ret.append(chan)
        return dbus.Array(ret, signature='(ss)')

    @dbus.service.method(CONN_INTERFACE, in_signature='sa{sv}', out_signature='o')
    def RequestChannel(self, type, interfaces):
        """
        Attempt to create a new channel.
    
        type is a dbus interface name indicating the base type of channel to 
        create.
        interfaces is a list of Telepathy interface names with which this
        channel should be created.
        params is a dict of string->string containing parameters for creating 
        the channel.

        This is a stub implementation that should be overridden in a concrete
        subclass.
        """
        raise IOError('Unknown channel type %s' % type)

class ConnectionManager(dbus.service.Object):
    """
    A dbus service that can be used to request a Connection to one or moew
    protocols.
    To use, subclass and populate self.protos with constructors for Connections.
    the constructors should take a string for the parent manager, a string for
    the account that connection is handling and a dict for various parameters.
    """
    def __init__(self, name):
        """
        name is a string to be used for the name of this connection manager.
        The service will appear as the service
        org.freedesktop.telepathy.ConnectionManager.name
        with this object as /org/freedesktop/telepathy/ConnectionManager/name
        """
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.'+name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/'+name)

        self.connections = set()
        self.protos = {}

    def __del__(self):
        print "explodes"
        dbus.service.Object.__del__(self)

    def disconnected(self, conn):
        """
        remove a given Connection
        """
        self.connections.remove(conn)
        del conn

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='', out_signature='as')
    def ListProtocols(self):
        """
        return a list of protocols that this ConnectionManager knows how to 
        handle.
        """
        return self.protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='ssa{sv}', out_signature='so')
    def Connect(self, proto, account, connect_info):
        """
        Connect to a given account with a given protocol with the given 
        information.
        
        Returns a dbus service name and object patch where the
        new Connection object can be found.
        """
        if self.protos.has_key(proto):
            conn = self.protos[proto](self, account, connect_info)
            self.connections.add(conn)
            self.NewConnection(conn.service_name, conn.object_path, conn.proto, conn.account)
            return (conn.service_name, conn.object_path)
        else:
            raise IOError('Unknown protocol %s' % (proto))

    @dbus.service.signal(CONN_MGR_INTERFACE, signature='soss')
    def NewConnection(self, service_name, object_path, proto, account):
        """
        Emitted when a new connection is created.
        service_name, object_patch are the dbus busname and object path where 
        the new Connection object can found.
        proto is the protocol that Connection is handling.
        account is the user account that Connection is for.
        """
        pass


