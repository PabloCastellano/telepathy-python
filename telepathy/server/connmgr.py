#!/usr/bin/env python

import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
import gobject
import time
from telepathy import *

class Channel(dbus.service.Object):
    """
    All communication in the Telepathy framework is carried out via channel
    objects which are created and managed by connections. This interface must
    be implemented by all channel objects, along with one single channel type,
    such as Channel.Type.List which represents a list of people (such as a
    buddy list) or a Channel.Type.Text which represents a channel over which
    textual messages are sent and received.

    Other optional interfaces can be implemented to indicate other available
    functionality, such as Channel.Interface.Individual or
    Channel.Interface.Group to manage the members of a channel,
    Channel.Interface.Named for channels with names, and
    Channel.Interface.Subject for channels with a subject or topic line. The
    interfaces implemented may not vary after the channel's creation has been
    signalled to the bus (with the connection's NewChannel signal).

    Specific connection manager implementations may implement channel types and
    interfaces which are not contained within this specification in order to
    support further functionality. To aid interoperability between client and
    connection manager implementations, the interfaces specified here should be
    used wherever applicable, and new interfaces made protocol-independent
    wherever possible. Because of the potential for 3rd party interfaces adding
    methods or signals with conflicting names, the D-Bus interface names should
    always be used to invoke methods and bind signals.
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
        rather than causing it to stop existing entirely.
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
        """
        Get the optional interfaces implemented by the channel.

        Returns:
        an array of the D-Bus interface names
        """
        return dbus.Array(self.interfaces, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetMembers(self):
        """ Returns an array of identifiers for the members of this channel. """
        return dbus.Array(self.members, signature='s')

class ChannelInterfaceIndividual(dbus.service.Interface):
    """
    An interface for channels which can only ever contain the owner of the
    connection and a single other individual, and if either party leaves, the
    channel closes. If there is the potential for other members to join, be
    invited, or request to join, the group channel interface should be used.

    This interface must never be implemented alongside Channel.Interface.Group.
    """
    def __init__(self, recipient):
        """
        Initialise the individual channel interface.

        Parameters:
        recipient - the identifier for the other member of the channel
        """
        assert(CHANNEL_INTERFACE_GROUP not in self.interfaces)
        self.interfaces.add(CHANNEL_INTERFACE_INDIVIDUAL)
        self.members.add(recipient)
        self.recipient = recipient

    @dbus.service.method(CHANNEL_INTERFACE_INDIVIDUAL, in_signature='', out_signature='s')
    def GetRecipient(self):
        """
        Return the identifier of the other member of the channel (besides
        yourself).
        """
        return self.recipient

class ChannelInterfaceGroup(dbus.service.Interface):
    """
    Interface for channels which have multiple members, and where your
    presence in the channel cannot be presumed by the channel's existence (for
    example, a channel you may request membership of but your request may
    not be granted).

    As well as the basic Channel's member list, this interface implements a
    further two lists: invited and requested members. Contacts on the invited
    list have been invited to the channel, but the remote user has not accepted
    the invitation. Contacts on the requested list have requested membership of
    the channel, but the user of the framework must accept their request before
    they may join. A single contact should never appear on more than one of the
    three lists. The lists are empty when the interface is created, and the
    MembersChanged signal should be emitted when information is retrieved from
    the server, or changes occur.

    Addition of members to the channel may be requested by using AddMembers. If
    remote acknowledgement is required, use of the AddMembers method will cause
    users to appear on the invited list. If no acknowledgement is required,
    AddMembers will add contacts to the member list directly.  If a contact is
    awaiting authorisation on the requested list, AddMembers will grant their
    membership request.

    Removal of contacts from the channel may be requested by using
    RemoveMembers.  If a contact is awaiting authorisation on the requested
    list, RemoveMembers will refuse their membership request. If a contact has
    been invited to the channel but not yet joined, RemoveMembers may rescind
    their request.

    It should not be presumed that the requestor of a channel implementing this
    interface is immediately granted membership, or indeed that they are a
    member at all, unless they appear in the list. They may, for instance,
    be placed into the requested list until a connection has been established
    or the request acknowledged remotely.

    This interface must never be implemented alongside Channel.Interface.Individual.
    """
 
    def __init__(self, me):
        assert(CHANNEL_INTERFACE_INDIVIDUAL not in self.interfaces)
        self.interfaces.add(CHANNEL_INTERFACE_GROUP)
        self.requested = set()
        self.invited = set()
        self.me = me

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def AddMembers(self, contacts):
        """
        Invite all the given contacts into the channel, or approve
        their requests for channel membership.
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def RemoveMembers(self, contacts):
        """
        Requests the removal of contacts from a channel, refuse their request
        for channel membership, or rescind their invitation.
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='s')
    def GetSelf(self):
        """
        Returns the identifier of the connection owner on this particular channel,
        as some protocols allow individuals to set their identity per channel.
        """
        return self.me

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetRequestedMembers(self):
        """ Returns an array of identifiers for the contacts requesting channel membership. """
        return dbus.Array(self.requested, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetInvitedMembers(self):
        """ Returns an array of identifiers for contacts who have been invited to the channel. """
        return dbus.Array(self.invited, signature='s')

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='asasasas')
    def MembersChanged(self, added, removed, requested, invited):
        """
        Emitted when contacts join any of the three lists (members, requested or invited).
        Contacts are listed in the removed list when they leave any of the three lists.
        """

        self.members.update(added)
        self.members.difference_update(removed)

        self.requested.update(requested)
        self.requested.difference_update(added)
        self.requested.difference_update(removed)

        self.invited.update(invited)
        self.invited.difference_update(added)
        self.invited.difference_update(removed)

class ChannelInterfaceNamed(dbus.service.Interface):
    """
    Interface for channels which have an immutable name. When requesting
    channels, this interface accepts the parameter of a name to obtain,
    with dbus type 's'.
    """
    def __init__(self, name):
        """ Initialise the interface.

        Parameters:
        name - the immutable name of this channel
        """
        self.interfaces.add(CHANNEL_INTERFACE_NAMED)
        self.name = name

    @dbus.service.method(CHANNEL_INTERFACE_NAMED, in_signature='', out_signature='s')
    def GetName(self):
        """ Get the immutable name of this channel. """
        return self.name

class ChannelInterfaceSubject(dbus.service.Interface):
    """
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

class ChannelTypeList(Channel):
    """
    A channel type for representing a list of people on the server which is
    not used for communication. This is intended for use with the interface
    Channel.Interface.Group for managing buddy lists and privacy lists
    on the server.

    The following named instances (obtained by specifying as an argument to
    Channel.Interface.Named) of this channel type may be created by the connection
    manager to allow clients to manipulate certain server-side lists:
    subscribe - the group of contacts for whom you wish to receive presence
    publish - the group of contacts who may recieve your presence
    hide - a group of contacts who are on the publish list but are temporarily disallowed from recieving your presence
    allow - a group of contacts who may send you messages
    deny - a group of contacts who may not send you messages
    """
    _dbus_interfaces = [CHANNEL_TYPE_LIST]

    def __init__(self):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_LIST)


class ChannelTypeText(Channel):
    """
    A channel type for sending and receiving messages in plain text, with no
    formatting.

    When a message is received, an identifier is assigned and a Received signal
    emitted, and the message placed in a pending queue which can be inspected
    with GetPendingMessages. A client which has handled the message by showing
    it to the user (or equivalent) should acknowledge the receipt using the
    AcknowledgePendingMessage method, and the message will then be removed from
    the pending queue.

    Sending messages can be requested using the Send method, which allocates a
    message identifier, and the Sent signal will be emitted when the message has been
    delivered to the server. Numeric identifiers for sent and recieved messages
    may collide and may be reused over the lifetime of the channel.
    """

    def __init__(self, connection):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_TEXT)

        self.send_id = 0
        self.recv_id = 0
        self.pending_messages = {}

    def sendCallback(self, id, text):
        """ Ovveride this stub to send a message over the parent Connection. """
        pass

    def stampMessage(self, id, text):
        """ Stamp a message with a timestamp and signal it as sent. FIXME server time? """
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
        Request that a message be sent on this channel. The Sent signal will be
        emitted when the message has been sent.

        Parameters:
        text - the message to send

        Returns:
        a numeric identifier
        """
        id = self.send_id
        self.send_id += 1
        gobject.idle_add(self.sendCallback, id, text)
        return id

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='u', out_signature='b')
    def AcknowledgePendingMessage(self, id):
        """
        Inform the channel that you have handled a message by displaying it to
        the user (or equivalent), so it can be removed from the pending queue.

        Parameters:
        id - the message to acknowledge

        Returns:
        a boolean indicating if the message was found on the pending queue and removed
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

        Returns:
        an array of structs containing:
            a numeric identifier
            a unix timestamp indicating when the message was received
            the contact who sent the message
            the text of the message
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
        been successfully sent on the parent connection.

        Parameters:
        the numeric identifier of the message
        the unix timestamp indicating when the message was sent
        the text of the message
        """
        print 'object_path: %s signal: Sent %d %d %s' % (self.object_path, id, timestamp, text)

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uuss')
    def Received(self, id, timestamp, sender, text):
        """
        Signals that a message with the given id, timestamp, sender and text
        has been received on the parent connection. Applications that catch
        this signal and reliably inform the user of the message should
        acknowledge that they have dealt with the message with the
        AcknowledgePendingMessage method.

        Parameters:
        a numeric identifier
        a unix timestamp indicating when the message was received
        the contact who sent the message
        the text of the message
        """
        print 'object_path: %s signal: Received %d %d %s %s' % (self.object_path, id, timestamp, sender, text)


class ChannelInterfaceDTMF(dbus.service.Interface):
    """
    An interface that gives a Channel the ability to send or receive DTMF signalling
    tones. This usually only makes sense for channels transporting audio.
    """
    def __init__(self):
        self.interfaces.add(CHANNEL_INTERFACE_DTMF)

    @dbus.service.method(CHANNEL_INTERFACE_DTMF, in_signature='uu', out_signature='')
    def SendDTMF(self, signal, duration):
        """
        Requests that a DTMF tone is sent.

        Parameters:
        a numeric signal number
        a numeric duration in milliseconds
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_DTMF, signature='uu')
    def ReceivedDTMF(self, signal, duration):
        """
        Signals that this channel received a DTMF tone.

        Parameters:
        a numeric signal number
        a numeric duration in milliseconds
        """
        pass

class ChannelTypeStreamedMedia(Channel):
    """
    A channel that can send and receive streamed media such as audio or video.
    All communication on this channel takes the form of messages exchanged in
    SDP (see IETF RFC 2327).

    In general, negotiations over this channel will take the form of IETF RFC
    3264, "An Offer/Answer Model with the Session Description Protocol". At
    any given time, this channel can be queried for the last received SDP
    information from a given member to allow negotiation to proceed even
    if a Received signal from a recipient has been missed.
    """
    def __init__(self, connection):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_STREAMED_MEDIA)
        self.last_received = {}

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='ss', out_signature='u')
    def Send(self, recipient, sdp):
        """
        Attempt to send an SDP message on this channel.

        Parameters:
        recipient - the member to send to
        sdp - the SDP message to send

        Returns:
        a numeric identifier for the message
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='uss')
    def Sent(self, id, recipient, sdp):
        """
        Signals that an SDP message has been sent to the given recipient on this channel.

        Parameters:
        id - the numeric identifier returned by Send
        recipient - the member the message was sent to
        sdp - the SDP message itself
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='ss')
    def Received(self, sender, sdp):
        """
        Signals that an SDP message has been received on this channel.

        Parameters:
        sender - the member the message was sent by
        sdp - the SDP message itself
        """
        self.last_received[sender] = sdp
        pass

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='s', out_signature='s')
    def GetLastMessage(self, contact):
        """
        Retrieve the last SDP message received from a given contact.

        Parameters:
        contact - the member to retrieve the last message from

        Returns:
        a string of the message (which may be blank if nothing has been received from the given contact)
        """
        if contact in self.last_received:
            return self.last_received[contact]
        else:
            return ''

class ConnectionInterfacePresence(dbus.service.Interface):
    """
    This interface is for services which have a concept of presence which can
    be published for yourself and monitored on your contacts. Telepathy's
    definition of presence based on that used by the Galago project
    (see http://www.galago-project.org/).

    Presence on an individual (yourself or one of your contacts) is modelled as
    an idle time along with a set of zero or more statuses, each of which may
    have arbitrary key/value parameters. Valid statuses are defined per
    connection, and a list of them can be obtained with the GetStatuses method.

    Each status has an arbitrary string identifier which should have an agreed
    meaning between the connection manager and any client which is expected to
    make use of it. The following well-known values (in common with those in
    Galago) should be used where possible to allow clients to identify common
    choices:

    - available
    - away
    - brb (Be Right Back)
    - busy
    - dnd (Do Not Disturb),
    - xa (Extended Away)
    - hidden (aka Invisible)
    - offline

    As well as these well-known status identifiers, every status also has a
    numerical string value which can be used by the client to classify even
    unknown statuses into different fundamental types:
    1 - offline
    2 - available
    3 - away
    4 - extended away
    5 - hidden

    The dictionary of variant types allows the connection manager to exchange
    further protocol-specific information with the client. It is recommended
    that the string (s) argument 'message' be interpreted as an optional
    message which can be associated with a presence status.

    PresenceUpdate signals should be emitted to indicate changes in your own
    presence, the presence of the members of any channels belonging to the
    connection, and when RequestPresence returns information about a specific
    contact.
    """

    def __init__(self):
        self.interfaces.add(CONN_INTERFACE_PRESENCE)

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='', out_signature='a{s(ubba{sg})}')
    def GetStatuses(self):
        """
        Get a dictionary of the valid presence statuses for this connection.

        Returns:
        a dictionary of string identifiers mapped to a struct for each status, containing:
        - a type value from one of the values above
        - a boolean to indicate if this status may be set on yourself
        - a boolean to indicate if this is an exclusive status which you may not set alongside any other
        - a dictionary of valid optional string argument names mapped to their types
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='as', out_signature='')
    def RequestPresence(self, contacts):
        """
        Request the presence for contacts on this connection. A PresenceUpdate
        signal will be emitted when they are received.

        Parameters:
        contacts - an array of the contacts whose presence should be obtained
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_PRESENCE, signature='a{s(ua{sa{sv}})}')
    def PresenceUpdate(self, presence):
        """
        This signal should be emitted when your own presence has been changed,
        or the presence of the member of any of the connection's channels has
        been changed, or when the presence requested by RequestPresence is available.

        Parameters:
        a dictionary of contacts mapped to a struct containing:
        - the idle time of the contact in seconds
        - a dictionary mapping the contact's current status identifiers to:
          a dictionary of optional parameter names mapped to their 
          variant-boxed values
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='u', out_signature='')
    def SetIdle(self, time):
        """
        Request that the user's idle time be updated.

        Parameters:
        time - the idle time of the user in seconds
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='a{sa{sv}}', out_signature='')
    def SetStatus(self, statuses):
        """
        Request that the user's presence be changed to the given statuses and
        desired parameters. Changes will be reflected by PresenceUpdate
        signals being emitted.

        Parameters:
        a dictionary of status identifiers mapped to:
            a dictionary of optional parameter names mapped to their variant-boxed values
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='', out_signature='')
    def ClearStatus(self):
        """
        Request that all of a user's presence statuses be removed. Be aware
        that this request may simply result in the statuses being replaced by a
        default available status. Changes will be indicated by PresenceUpdate
        signals being emitted.
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='sa{sv}', out_signature='')
    def AddStatus(self, status, parms):
        """
        Request that a single presence status is published for the user, along
        with any desired parameters. Changes will be indicated by PresenceUpdate
        signals being emitted.

        Parameters:
        status - the string identifier of the desired status
        parms - a dictionary of optional parameter names mapped to their variant-boxed values
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='s', out_signature='')
    def RemoveStatus(self, status):
        """
        Request that the given presence status is no longer published for the
        user. Changes will be indicated by PresenceUpdate signals being emitted.
        """
        pass

class ConnectionInterfaceRenaming(dbus.service.Interface):
    """
    An interface on connections to support protocols where the unique identifiers
    of contacts can change.
    """
    _dbus_interfaces = [CONN_INTERFACE_RENAMING]

    def __init__(self):
        self.interfaces.add(CONN_INTERFACE_RENAMING)

class ConnectionInterfaceAliasing(dbus.service.Interface):
    """
    An interface on connections to support protocols where contacts have an
    alias which they can change at will, but their underlying unique identifier
    remains unchanged. Provides a method for the user to set their own alias,
    and a signal which should be emitted when a contact's alias is changed
    or first discovered.
    """

    def __init__(self):
        self.interfaces.add(CONN_INTERFACE_ALIASING)

    @dbus.service.signal(CONN_INTERFACE_ALIASING, signature='ss')
    def AliasUpdate(self, contact, alias):
        """
        Signal emitted when a contact's alias (or that of the user) is changed.

        Parameters:
        contact - the identifier of the contact
        alias - the new alias
        """
        pass

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='s', out_signature='')
    def RequestAlias(self, contact):
        """
        Request the value of a contact's alias (or that of the user themselves).
        The value is returned in an AliasUpdate signal.
        """
        pass

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='s', out_signature='')
    def SetAlias(self, alias):
        """
        Request that the user's alias be changed. Success will be indicated by
        emitting an AliasUpdate signal.

        Parameters:
        alias - the new alias to set
        """
        pass

class Connection(dbus.service.Object):
    """
    This models a connection to a single user account on a communication
    service. Its basic capability is to provide the facility to request
    and receive channels of differing types (such as text channels or streaming
    media channels) which are used to carry out further communication.

    A Connection object should always endeavour to remain connected to
    the server until instructed to the contrary with the Disconnect
    method.

    As well as the methods and signatures below, a arbitrary interfaces
    may be provided by the Connection object to represent extra
    connection-wide functionality, such as the Connection.Interface.Presence
    for receiving and reporting presence information, and
    Connection.Interface.Aliasing for connections where contacts
    may set and change an alias for themselves. These interfaces
    can be discovered using GetInterfaces, and must not change
    at runtime.
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

        self.interfaces = set()
        self.channels = set()
        self.lists = {}
        self.manager = manager
        self.proto = proto
        self.account = account

    def addChannel(self, channel):
        """ add a new channel and signal its creation""" 
        self.channels.add(channel)
        self.NewChannel(channel.type, channel.object_path)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """
        Get the optional interfaces supported by the connection.

        Returns:
        an array of D-Bus interface names
        """
        return self.interfaces

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        """
        Get the protocol this connection is using.

        Returns:
        a string identifier for the protocol
        """
        return self.proto

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetAccount(self):
        """
        Get the identifier for this connection's account.

        Returns:
        a string identifier for the user
        """
        return self.account

    @dbus.service.signal(CONN_INTERFACE, signature='s')
    def StatusChanged(self, status):
        """
        Emitted when the status of the connection changes. The currently
        defined states are:

        connected - The connection is alive and all methods are available.

        connecting - The connection has not yet been established, or has been
        severed and reconnection is being attempted. Some methods may fail
        until the connection has been established.

        disconnected - The connection has been severed and no method calls are
        valid. The object may be removed from the bus at any time.

        Parameters:
        status - a string indicating the new status
        """
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self.status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetStatus(self):
        """
        Get the current status as defined in the StatusChanged signal.

        Returns:
        a string representing the current status
        """
        return self.status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='')
    def Disconnect(self):
        """
        Request that the connection be closed.
        """
        pass

    @dbus.service.signal(CONN_INTERFACE, signature='so')
    def NewChannel(self, type, object_path):
        """
        Emitted when a new Channel object is created, either through user
        request or incoming information from the service.

        Parameters:
        type - a D-Bus interface name representing the channel type
        object_path - a D-Bus object path for the channel object on this service
        """
        print 'service_name: %s object_path: %s signal: NewChannel %s %s' % (self.service_name, self.object_path, type, object_path)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='a(so)')
    def ListChannels(self):
        """
        List all the channels currently available on this connection.

        Returns:
        an array of structs containing:
            a D-Bus interface name representing the channel type
            a D-Bus object path for the channel object on this service
        """
        ret = []
        for channel in self.channels:
            chan = (channel.type, channel.object_path)
            ret.append(chan)
        return dbus.Array(ret, signature='(ss)')

    @dbus.service.method(CONN_INTERFACE, in_signature='sa{sv}', out_signature='o')
    def RequestChannel(self, type, interfaces):
        """
        Request a channel satisfying the specified type and interfaces. May
        return an existing channel object, create a new channel, or fail if the
        request cannot be satisfied. The returned channel must be of the
        requested type, but may not necessarily implement the exact interfaces
        requested. For example, a protocol with no concept of an individual
        channel may instead return a new group channel containing the requested
        user.

        Parameters:
        type - a D-Bus interface name representing base channel type
        interfaces - a dictionary mapping D-Bus interface names to a boxed variant
        containing the arguments for those interfaces

        Returns:
        the D-Bus object path for the channel created or retrieved
        """
        raise IOError('Unknown channel type %s' % type)

class ConnectionManager(dbus.service.Object):
    """
    A D-Bus service which allows connections to be created. The manager
    processes are intended to be started by D-Bus service activation.  The
    names of these services, the protocols they support, and the parameters
    understood by that protocol are intended to be discovered by reading files
    on disk which are provided along with the connection manager. These are
    documented elsewhere.

    Once a connection manager service has been activated, the object
    path of the manager object implementing this interface is always:
     /org/freedesktop/Telepathy/ConnectionManager/name
    Where name is the identifier for the connection manager.

    It is not required that a connection manager be able to support multiple
    protocols, or even multiple connections. When a connection is made, a
    service name where the connection object can be found is returned. The
    connection manager may then remove itself from its well-known bus name,
    causing a new connection manager to be activated when somebody attempts to
    make a new connection.
    """
    def __init__(self, name):
        """
        Initialise the connection manager. The service will appear as the
        service org.freedesktop.Telepathy.ConnectionManager.name, and publish
        an object called as /org/freedesktop/Telepathy/ConnectionManager/name.
        """
        self.bus_name = dbus.service.BusName(CONN_MGR_SERVICE+'.'+name, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, self.bus_name, CONN_MGR_OBJECT+'/'+name)

        self.connections = set()
        self.protos = {}

    def __del__(self):
        print str(self.bus_name), "deleted"
        dbus.service.Object.__del__(self)

    def disconnected(self, conn):
        """
        Remove a connection from the list of connections.
        """
        self.connections.remove(conn)
        del conn

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='', out_signature='as')
    def ListProtocols(self):
        """
        Get a list of protocol identifiers that are implemented by this
        connection manager. The following well-known values should be used
        when applicable:
         aim - AOL Instant Messenger
         gadugadu - Gadu-Gadu
         groupwise - Novell Groupwise
         icq - ICQ
         irc - Internet Relay Chat
         jabber - Jabber (XMPP)
         msn - MSN Messenger
         napster - Napster
         silc - SILC
         trepia - Trepia
         yahoo - Yahoo! Messenger
         zephyr - Zephyr

        Returns:
        a list of string protocol identifiers supported by this manager
        """
        return self.protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='s', out_signature='a{sg}')
    def GetProtocolParameters(self, proto):
        """
        Get a list of the parameter names and types which are understood
        by the connection manager for a given protocol.

        Parameters:
        proto - the protocol identifier

        Returns:
        an dictionary mapping parameter identifiers to type signatures
        """
        pass

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='ssa{sv}', out_signature='so')
    def Connect(self, proto, account, parameters):
        """
        Connect to a given account on a given protocol with the given
        parameters. The parameters accepted by a protocol are specified
        in a file shipped by the connection manager, and can be retrieved
        at run-time with the GetProtocolParameters method. The client
        must have prior knowledge of the meaning of these parameters,
        so the following well-known names and types should be used where
        relevant:

        s:server - a fully qualified domain name or numeric IPv4 or IPv6
        address. Using the fully-qualified domain name form is RECOMMENDED
        whenever possible. If this paramter is specified and the account
        for that protocol also specifies a server, this parameter should
        override that in the user id.

        q:port - a TCP or UDP port number. If this paramter is specified
        and the account for that protocol also specifies a port, this
        parameter should override that in the account.

        s:password - A password associated with the account.

        s:proxy-server - A URI for a proxy server to use for this connection.

        b:require-encryption - Require encryption for this connection. A
        connection should fail to connect if require-encryption is set
        and an encrypted connection is not possible.

        Parameters:
        proto - the protocol identifier
        account - the user's account on this protocol
        parameters - a dictionary mapping parameter name to the variant boxed value

        Returns:
        a D-Bus service name where the new Connection object can be found
        the D-Bus object path to the Connection on this service
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
        Emitted when a new Connection object is created.

        Parameters:
        service_name - the D-Bus service where the connection object can be found
        object_path - the object path of the Connection object on this service
        proto - the identifier for the protocol this connection uses
        account - the identifier for the user's account on this protocol
        """
        pass
