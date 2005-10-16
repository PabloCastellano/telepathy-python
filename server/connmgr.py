#!/usr/bin/env python

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import time

CONN_MGR_SERVICE = 'org.freedesktop.telepathy.ConnectionManager'
CONN_MGR_OBJECT = '/org/freedesktop/telepathy/ConnectionManager'
CONN_MGR_INTERFACE = 'org.freedesktop.telepathy.ConnectionManager'

CONN_SERVICE = 'org.freedesktop.telepathy.Connection'
CONN_OBJECT = '/org/freedesktop/telepathy/Connection'
CONN_INTERFACE = 'org.freedesktop.telepathy.Connection'

CONN_INTERFACE_ALIASING = 'org.freedesktop.telepathy.Connection.Interface.ContactAlias'
CONN_INTERFACE_PRESENCE = 'org.freedesktop.telepathy.Connection.Interface.ContactPresence'
CONN_INTERFACE_RENAMING = 'org.freedesktop.telepathy.Connection.Interface.ContactRename'
CONN_INTERFACE_VCARD = 'org.freedesktop.telepathy.Connection.Interface.ContactInfo'

CHANNEL_INTERFACE = 'org.freedesktop.telepathy.Channel'
CHANNEL_TYPE_TEXT = 'org.freedesktop.telepathy.Channel.Type.Text'
CHANNEL_TYPE_LIST = 'org.freedesktop.telepathy.Channel.Type.List'
CHANNEL_TYPE_STREAMED_MEDIA = 'org.freedesktop.telepathy.Channel.Type.StreamedMedia'

CHANNEL_INTERFACE_DTMF = 'org.freedesktop.telepathy.Channel.Interface.DTMF'
CHANNEL_INTERFACE_GROUP = 'org.freedesktop.telepathy.Channel.Interface.Group'
CHANNEL_INTERFACE_INDIVIDUAL = 'org.freedesktop.telepathy.Channel.Interface.Individual'
CHANNEL_INTERFACE_NAMED = 'org.freedesktop.telepathy.Channel.Interface.Named'
CHANNEL_INTERFACE_SUBJECT = 'org.freedesktop.telepathy.Channel.Interface.Subject'

class Channel(dbus.service.Object):
    """
    D-Bus Interface: org.freedesktop.telepathy.Channel

    All communication in the Telepathy framework is carried out via channel
    objects which are created and managed by connections. This interface
    must be implemented by all channel objects, along with one single
    channel type, such as ListChannel which represents a list of people
    (such as a buddy list) or a TextChannel which represents a channel
    over which textual messages are sent and received.

    Other optional interfaces can be implemented to indicate other available
    functionality, such as GroupChannelInterface or IndividualChannelInterface
    to manage the members of a channel, NamedChannelInterface for channels with
    names, and PresenceChannelInterface for channels who report presence on
    their members.

    Specific connection manager implementations may implement channel
    types and interfaces which are not contained within this specification
    in order to support further functionality. To aid interoperability
    between client and connection manager implementations, the interfaces
    specified here should be used wherever applicable, and new interfaces
    made protocol-independent wherever possible. Because of the potential
    for 3rd party interfaces adding methods or signals with conflicting
    names, the D-Bus interface names should always be used to invoke
    methods and bind signals.
    """
    count = 0

    def __init__(self, connection, type):
        """
        Initialise the base channel object.

        Parameters:
        connection - the parent Connection object
        type - interface name for the type of this channel
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
        """
        Request that the channel be closed. This is not the case until
        the Closed signal has been emitted, and depending on the connection
        manager this may simply remove you from the channel on the server,
        rather than causing it to stop existing completely.
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE, signature='')
    def Closed(self):
        """
        Emitted when the channel has been closed. Method calls on the
        channel are no longer valid after this signal has been emitted,
        and the connection manager may then remove the object from the bus
        at any point.
        """
        print 'object_path: %s signal: Closed' % (self.object_path)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='s')
    def GetType(self):
        """ Returns the interface name for the type of this channel. """
        return self.type

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """ Returns an array of optional interfaces implemented by the channel. """
        return dbus.Array(self.interfaces, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetMembers(self):
        """ Returns an array of identifiers for the members of this channel. """
        return dbus.Array(self.members, signature='s')

class IndividualChannelInterface(object):
    """
    D-Bus Interface: org.freedesktop.telepathy.IndividualChannelInterface

    An interface for channels which can only ever contain the user of the
    framework and a single other individual, and if either party leaves, the
    channel closes. If there is the potential for other members to join, be
    invited, or request to join, GroupChannelInterface should be used.

    This interface must never be implemented alongside GroupChannelInterface.
    """
    def __init__(self, recipient):
        """
        Initialise the individual channel interface.

        Parameters:
        recipient - the identifier for the other member of the channel
        """
        self.interfaces.add(CHANNEL_INTERFACE_INDIVIDUAL)
        self.members.add(recipient)
        self.recipient = recipient

class GroupChannelInterface(object):
    """
    D-Bus Interface: org.freedesktop.telepathy.GroupChannelInterface

    Interface for channels which have multiple members, and where your
    presence in the channel cannot be presumed by the channel's existence (for
    example, a channel you may request membership of but your request may
    not be granted).

    This interface implements three lists, members, invited and requested.
    Only 

    This interface must never be implemented alongside IndividualChannelInterface.
    

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
        self.interfaces.add(CHANNEL_INTERFACE_GROUP)
        self.requested = set()
        self.invited = set()

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def InviteMembers(self, contacts):
        """
        Invite all the given contacts in into the channel, or approve
        their requests for channel membership.
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def RemoveMembers(self, members):
        """
        Requests the removal of members from a channel, or refuses their
        requests for channel membership 
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetRequestedMembers(self):
        """ Returns an array of the currently requested members"""
        return dbus.Array(self.requested, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetInvitedMembers(self):
        """ Returns an array of the currently invited members"""
        return dbus.Array(self.invited, signature='s')

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='asasasas')
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
        self.interfaces.add(CHANNEL_INTERFACE_NAMED)
        self.name = name

    @dbus.service.method(CHANNEL_INTERFACE_NAMED, in_signature='', out_signature='s')
    def GetName(self):
        """ Get the immutable name of this channel. """
        return self.name

class SubjectChannelInterface(object):
    """
    D-Bus Interface: org.freedesktop.telepathy.Channel.Interface.Subject

    Interface for channels that have a modifiable subject or topic. A
    SubjectChanged signal should be emitted whenever the subject is changed,
    and once when the subject is initially discovered from the server.
    """
    def __init__(self):
        self.interfaces.add(CHANNEL_INTERFACE_SUBJECT)
        self.subject = ''
        self.subject_set_by = ''
        self.subject_set_at = 0

    @dbus.service.method(CHANNEL_INTERFACE_SUBJECT, in_signature='', out_signature='ssu')
    def GetSubject(self):
        """
        Get this channel's current subject.

        Returns:
        the subject text
        the contact who set the subject (blank if unknown)
        the unix timestamp of the last change (zero if unknown)
        """
        return self.subject, self.subject_set_by, self.subject_set_at

    @dbus.service.method(CHANNEL_INTERFACE_SUBJECT, in_signature='s', out_signature='')
    def SetSubject(self, subject):
        """
        Request that the subject of this channel be changed. Success will be
        indicated by an emission of the SubjectChanged signal.
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_SUBJECT, signature='ssu')
    def SubjectChanged(self, subject, set_by, set_at):
        """
        Emitted when the subject changes or is initially discovered from the server.

        Parameters:
        subject - the new subject string
        contact - the identifier of the contact who was responsible for this change, which may be blank if unknown
        time - the unix timestamp of the subject change, which may be zero if unknown
        """
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
        Channel.__init__(self, connection, CHANNEL_TYPE_TEXT)

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

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='s', out_signature='u')
    def Send(self, text):
        """ 
        Send a message on this channel.
        
        Returns a numeric id for the message
        """
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.sendCallback, id, text)
        return id

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='u', out_signature='b')
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

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='', out_signature='a(uuss)')
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

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uus')
    def Sent(self, id, timestamp, text):
        """
        Signals that a message with the given id, timestamp and text has 
        been sent on the parent connection.
        """
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uuss')
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
        self.interfaces.add(CHANNEL_INTERFACE_DTMF)

    @dbus.service.method(CHANNEL_INTERFACE_DTMF, in_signature='uu', out_signature='')
    def SendDTMF(signal, duration):
        """Send a DTMF tone of type 'signal' of duration milliseconds"""
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_DTMF, signature='uu')
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
        Channel.__init__(self, connection, CHANNEL_TYPE_STREAMED_MEDIA)
        self.lastSendSDP=""
        self.lastReceivedSDP=""

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='ss', out_signature='u')
    def Send(self, recipient, sdp):
        """ 
        Attempt to send a message on this channel to the named recipient on this channel.
        returns an id for this send attempt
        """
        pass
       
    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='uss')
    def Sent(self, id, recipient, sdp):
        """
        Signals that an sdp message with the given id has 
        been sent on this channel to the given recipient.
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='uss')
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

    Other interfaces may also be added for connection services that provide
    extra connection-wide functionality. (eg presence, setting own name) 

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

        Defined states strings are:

        'connecting' - this Connection is still in the process of connecting to
        the messiging service

        'disconnected' - this Connection is not connected to a messaging service.

        'connected' - This Connection is connected to a messaging service.
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


