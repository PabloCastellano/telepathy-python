#!/usr/bin/env python

import dbus.service

from telepathy import *

class Channel(dbus.service.Object):
    """
    All communication in the Telepathy framework is carried out via channel
    objects which are created and managed by connections. This interface must
    be implemented by all channel objects, along with one single channel type,
    such as Channel.Type.ContactList which represents a list of people (such
    as a buddy list) or a Channel.Type.Text which represents a channel over
    which textual messages are sent and received.

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
    def __init__(self, connection, type):
        """
        Initialise the base channel object.

        Parameters:
        connection - the parent Connection object
        type - interface name for the type of this channel
        """
        self._conn = connection
        object_path = self._conn.get_channel_path()
        dbus.service.Object.__init__(self, self._conn._name, object_path)

        self._type = type
        self._interfaces = set()
        self._members = set()

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='')
    def Close(self):
        """
        Request that the channel be closed. This is not the case until
        the Closed signal has been emitted, and depending on the connection
        manager this may simply remove you from the channel on the server,
        rather than causing it to stop existing entirely.

        Possible Errors:
        Disconnected, NetworkError
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
        pass

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='s')
    def GetChannelType(self):
        """ Returns the interface name for the type of this channel. """
        return self._type

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """
        Get the optional interfaces implemented by the channel.

        Returns:
        an array of the D-Bus interface names
        """
        return self._interfaces

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetMembers(self):
        """
        Returns an array of identifiers for the members of this channel.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._members


class ChannelTypeContactSearch(Channel):
    """
    A channel type for searching server-stored user directories. A new channel
    should be requested by a client for each search attempt, and it should be
    closed when the search is completed or the required result has been found.
    The search can be cancelled at any time by calling the channel Close
    method, although depending upon the protocol the connection manager may not
    be able to prevent the server from sending further results.

    Before searching, the GetSearchKeys method should be used to discover any
    instructions sent by the server, and the valid search keys which can be
    provided to the Search method. A search request is then started by
    providing some of these terms to the Search method, and the search status
    will be set to 'during'. When results are returned by the server, the
    SearchResultReceived signal is emitted for each contact found, and when the
    search is complete, the search status will be set to 'after'.
    """
    def __init__(self, connection):
        """
        Initialise the contact search channel.
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_CONTACT_SEARCH)
        self.search_state = 'before'
        self.search_results = {}

    @dbus.service.method(CHANNEL_TYPE_CONTACT_SEARCH, in_signature='', out_signature='sa{s(bg)}')
    def GetSearchKeys(self):
        """
        Returns any instructions from the server along with a dictionary of
        search key names to their types, and a boolean indicating if the key is
        mandatory. The following well-known search key names should be used
        where appropriate:
         s:first - the desired contact's given name
         s:last - the desired contact's family name
         s:nick - the desired contact's nickname
         s:email - the e-mail address of the desired contact

        Returns:
        a string with any instructions from the server
        a dictionary mapping string search key names to an array of:
            booleans indicating if the search key is mandatory
            type signature of the value for this search key

        Possible Errors:
        Disconnected, NetworkError, NotAvailable
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_CONTACT_SEARCH, in_signature='a{sv}', out_signature='')
    def Search(self, terms):
        """
        Send a request to start a search for contacts on this connection. A
        valid search request will cause the SearchStateChanged signal to be
        emitted with the status 'during'.

        Parameters:
        a dictionary mapping search key names to the desired values

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_CONTACT_SEARCH, in_signature='', out_signature='s')
    def GetSearchState(self):
        """
        Returns the current state of this search channel object. One of the following
        values:
         before - the search has not started
         during - the search is in progress
         after - the search has been completed

        Returns:
        a string representing the search state
        """
        return self.search_state

    @dbus.service.signal(CHANNEL_TYPE_CONTACT_SEARCH, signature='s')
    def SearchStateChanged(self, state):
        """
        Emitted when the search state (as returned by the GetSearchState method) changes.

        Parameters:
        state - a string representing the search state
        """
        self.search_state = state

    @dbus.service.signal(CHANNEL_TYPE_CONTACT_SEARCH, signature='sa{sv}')
    def SearchResultReceived(self, contact, values):
        """
        Emitted when a search result is received from the server.

        Parameters:
        a string contact identifier
        a dictionary mapping search key names to values for this contact
        """
        self.search_results[contact] = values


class ChannelTypeContactList(Channel):
    """
    A channel type for representing a list of people on the server which is
    not used for communication. This is intended for use with the interface
    Channel.Interface.Group for managing buddy lists and privacy lists
    on the server. This channel type has no methods because all of the
    functionality it represents is available via the group interface.

    The following named singleton instances (obtained by specifying as an
    argument to Channel.Interface.Named) of this channel type should be
    created by the connection manager at connection time if the list
    exists on the server:
     subscribe - the group of contacts for whom you wish to receive presence
     publish - the group of contacts who may receive your presence
     hide - a group of contacts who are on the publish list but are temporarily disallowed from receiving your presence
     allow - a group of contacts who may send you messages
     deny - a group of contacts who may not send you messages
    """
    _dbus_interfaces = [CHANNEL_TYPE_CONTACT_LIST]

    def __init__(self):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_CONTACT_LIST)


class ChannelTypeStreamedMedia(Channel):
    """
    A channel that can send and receive streamed media such as audio or video.
    All communication on this channel takes the form of messages exchanged in
    SDP (see IETF RFC 2327). This interface is designed so that the connection
    manager will use the 'user' media parameters set on the connection with the
    Connection.Interface.StreamedMedia, and carry out negotiations on behalf of
    the user according to IETF RFC 3264, "An Offer/Answer Model with the
    Session Description Protocol".

    When the negotiations are completed, the ReceivedMediaParameters signal is
    emitted, containing the 'local' media parameters, which contain the SDP
    information for the local user's media streams, and the 'remote' media
    parameters which contains the same information for the remote user's
    streams.
    """
    def __init__(self, connection):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_STREAMED_MEDIA)
        self._media_parameters = {}

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='ss', out_signature='')
    def SendMediaParameters(self, recipient, parameters):
        """
        Send an message to a member of this channel proposing a new
        set of codecs to use. This is used for case-by case overrides
        of the per-connection 'user' media parameters which are set with
        the Connection.Interface.StreamedMedia.

        Parameters:
        recipient - a string the member to send the parameters to
        parameters - a string of SDP with the new media parameters to propose

        Possible Errors:
        Disconnected, NetworkError, UnknownContact, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='sss')
    def ReceivedMediaParameters(self, member, local, remote):
        """
        Signals that an message has been received from a member of this
        channel containing the negotiated local and remote media parameters
        to use for the streams with this member.

        Parameters:
        member - a string indicating the member the parameters were sent by
        local - a string of SDP describing the local media parameters
        remote - a string of SDP describing the remote media parameters
        """
        self._media_parameters[member] = (local, remote)

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='s', out_signature='s')
    def GetMediaParameters(self, member):
        """
        Retrieve the last received media parameters for a given member
        of this channel.

        Parameters:
        contact - a channel member to retrieve the parameters for

        Returns:
        a string of SDP containing the local media parameters
        a string of SDP containing the remote media parameters

        Possible Errors:
        Disconnected, UnknownContact, NotAvailable (if the contact has sent nothing to us on this channel)
        """
        if CHANNEL_INTERFACE_GROUP in self._interfaces:
            if (contact not in self.local_pending and
                contact not in self.remote_pending and
                contact not in self._members):
                raise telepathy.UnknownContact
        else:
            if contact not in self._members:
                raise telepathy.UnknownContact

        if contact in self._media_parameters:
            return self._media_parameters[contact]
        else:
            raise telepathy.NotAvailable


class ChannelTypeRoomList(Channel):
    """
    A channel type for listing named channels available on the server. Once the
    ListRooms method is called, it emits signals for rooms present on the
    server, until you Close this channel. In some cases, it may not be possible
    to stop the deluge of information from the server.

    This channel type may be implemented as a singleton on some protocols, so
    clients should be prepared for the eventuality that they are given a
    channel that is already in the middle of listing channels. The ListingRooms
    signal, or GetListingRooms method, can be used to check this.
    """
    def __init__(self, connection):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_ROOM_LIST)
        self.listing_rooms = False
        self.rooms = {}

    @dbus.service.method(CHANNEL_TYPE_ROOM_LIST, in_signature='', out_signature='')
    def ListRooms(self):
        """
        Request the list of rooms from the server. The ListingRooms signal
        should be emitted when this request is being processed, GotRooms when
        any room information is received, and ListingRooms when the request
        is complete.

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_ROOM_LIST, in_signature='', out_signature='b')
    def GetListingRooms(self):
        """
        Check to see if there is already a room list request in progress
        on this channel.

        Returns:
        a boolean indicating if room listing is in progress
        """
        return self.listing_rooms

    @dbus.service.signal(CHANNEL_TYPE_ROOM_LIST, signature='b')
    def ListingRooms(self, listing):
        """
        Emitted to indicate whether or not room listing request is currently
        in progress.

        Parameters:
        listing - a boolean indicating if room listing is in progress
        """
        self.listing_rooms = listing

    @dbus.service.signal(CHANNEL_TYPE_ROOM_LIST, signature='a(ssa{sv})')
    def GotRooms(self, rooms):
        """
        Emitted when information about rooms on the server becomes available.
        The array contains the room name (as can be passed to the Named channel
        interface when requesting a room), the channel type, and a dictionary
        containing further information about the room as available. The
        following well-known keys and types are recommended for use where
        appropriate:
         s:subject - the subject of the room
         u:members - the number of members of the room
         b:password - true if the room requires a password to enter

        Parameters:
        rooms - an array of structs containing:
            a string room identifier
            a string channel type
            an dictionary mapping string keys to variant boxed information
        """
        for (room, type, details) in rooms:
            self.rooms[room] = (type, details)


class ChannelTypeText(Channel):
    """
    A channel type for sending and receiving messages in plain text, with no
    formatting.

    When a message is received, an identifier is assigned and a Received signal
    emitted, and the message placed in a pending queue which can be inspected
    with GetPendingMessages. A client which has handled the message by showing
    it to the user (or equivalent) should acknowledge the receipt using the
    AcknowledgePendingMessage method, and the message will then be removed from
    the pending queue. Numeric identifiers for received messages may be reused
    over the lifetime of the channel.

    Each message has an associated 'type' value, which should be one of the
    following well-known values where appropriate:
     normal - a standard message
     action - an action which might be presented to the user as * <sender> <action>
     notice - an automated message not expecting a reply

    Sending messages can be requested using the Send method, which will return
    and cause the Sent signal to be emitted when the message has been delivered
    to the server.
    """

    def __init__(self, connection):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_TEXT)

        self._pending_messages = {}

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='ss', out_signature='')
    def Send(self, type, text):
        """
        Request that a message be sent on this channel. The Sent signal will be
        emitted when the message has been sent, and this method will return.

        Parameters:
        type - the type of the message (normal, action, notice, etc)
        text - the message to send

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='u', out_signature='')
    def AcknowledgePendingMessage(self, id):
        """
        Inform the channel that you have handled a message by displaying it to
        the user (or equivalent), so it can be removed from the pending queue.

        Parameters:
        id - the message to acknowledge

        Possible Errors:
        InvalidArgument (the given message ID was not found)
        """
        if id in self._pending_messages:
            del self._pending_messages[id]
        else:
            raise telepathy.InvalidArgument("the given message ID was not found")

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='', out_signature='a(uusss)')
    def ListPendingMessages(self):
        """
        List the messages currently in the pending queue.

        Returns:
        an array of structs containing:
            a numeric identifier
            a unix timestamp indicating when the message was received
            a string of the contact who sent the message
            a string of the message type
            a string of the text of the message
        """
        messages = []
        for id in self._pending_messages.keys():
            (timestamp, sender, type, text) = self._pending_messages[id]
            message = (id, timestamp, sender, type, text)
            messages.append(message)
        messages.sort(cmp=lambda x,y:cmp(x[1], y[1]))
        return messages

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uss')
    def Sent(self, timestamp, type, text):
        """
        Signals that a message has been sent on this channel.

        Parameters:
        timestamp - the unix timestamp indicating when the message was sent
        type - the message type (normal, action, normal, etc)
        text - the text of the message
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uusss')
    def Received(self, id, timestamp, sender, type, text):
        """
        Signals that a message with the given id, timestamp, sender, type
        and text has been received on this channel. Applications that catch
        this signal and reliably inform the user of the message should
        acknowledge that they have dealt with the message with the
        AcknowledgePendingMessage method.

        Parameters:
        id - a numeric identifier for acknowledging the message
        timestamp - a unix timestamp indicating when the message was received
        sender - the contact who sent the message
        type - the type of the message (normal, action, notice, etc)
        text - the text of the message
        """
        self._pending_messages[id] = (timestamp, sender, type, text)


class ChannelInterfaceDTMF(dbus.service.Interface):
    """
    An interface that gives a Channel the ability to send or receive DTMF
    signalling tones. This usually only makes sense for channels transporting
    audio.
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_DTMF)

    @dbus.service.method(CHANNEL_INTERFACE_DTMF, in_signature='uu', out_signature='')
    def SendDTMF(self, signal, duration):
        """
        Requests that a DTMF tone is sent.

        Parameters:
        signal - a numeric signal number
        duration - a numeric duration in milliseconds

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, InvalidArgument
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_DTMF, signature='uu')
    def ReceivedDTMF(self, signal, duration):
        """
        Signals that this channel received a DTMF tone.

        Parameters:
        signal - a numeric signal number
        duration - a numeric duration in milliseconds
        """
        pass


class ChannelInterfaceGroup(dbus.service.Interface):
    """
    Interface for channels which have multiple members, and where your
    presence in the channel cannot be presumed by the channel's existence (for
    example, a channel you may request membership of but your request may
    not be granted).

    As well as the basic Channel's member list, this interface implements a
    further two lists: local pending and remote pending members. Contacts on
    the remote pending list have been invited to the channel, but the remote
    user has not accepted the invitation. Contacts on the local pending list
    have requested membership of the channel, but the local user of the
    framework must accept their request before they may join. A single
    contact should never appear on more than one of the three lists. The
    lists are empty when the channel is created, and the MembersChanged
    signal should be emitted when information is retrieved from the
    server, or changes occur.

    Addition of members to the channel may be requested by using AddMembers. If
    remote acknowledgement is required, use of the AddMembers method will cause
    users to appear on the remote pending list. If no acknowledgement is
    required, AddMembers will add contacts to the member list directly.
    If a contact is awaiting authorisation on the local pending list,
    AddMembers will grant their membership request.

    Removal of contacts from the channel may be requested by using
    RemoveMembers.  If a contact is awaiting authorisation on the local pending
    list, RemoveMembers will refuse their membership request. If a contact is
    on the remote pending list but has not yet accepted the invitation,
    RemoveMembers will rescind the request if possible.

    It should not be presumed that the requester of a channel implementing this
    interface is immediately granted membership, or indeed that they are a
    member at all, unless they appear in the list. They may, for instance,
    be placed into the remote pending list until a connection has been
    established or the request acknowledged remotely.

    This interface must never be implemented alongside Channel.Interface.Individual.
    """
 
    def __init__(self, me):
        assert(CHANNEL_INTERFACE_INDIVIDUAL not in self._interfaces)
        self._interfaces.add(CHANNEL_INTERFACE_GROUP)
        self.group_flags = set()
        self.local_pending = set()
        self.remote_pending = set()
        self.me = me

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetGroupFlags(self):
        """
        Returns a list of the flags relevant to this group channel. The user
        interface can use this to present information about which operations
        are currently valid.

        These can be:
         can-add - the AddMembers method can be used to add or invite members who are not already in the local pending list (which is always valid)
         can-remove - the RemoveMembers method can be used to remove channel members (removing those on the pending local list is always valid)
         can-rescind - the RemoveMembers method can be used on people on the remote pending list

        Returns:
        an array of strings of flags

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.group_flags

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='asas')
    def GroupFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetGroupFlags are changed.
        The user interface should be updated as appropriate.

        Parameters:
        added - the flags which have been set
        removed - the flags which are no longer set
        """
        self.group_flags.update(added)
        self.group_flags.difference_update(removed)


    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def AddMembers(self, contacts):
        """
        Invite all the given contacts into the channel, or approve requests
        for channel membership for contacts on the pending local list.

        Parameters:
        contacts - contact IDs to invite to the channel

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied, UnknownContact
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def RemoveMembers(self, contacts):
        """
        Requests the removal of contacts from a channel, refuse their request
        for channel membership on the pending local list, or rescind their
        invitation on the pending remote list.

        Parameters:
        contacts - contact IDs to remove from the channel

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied, UnknownContact
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
    def GetLocalPendingMembers(self):
        """
        Returns an array of identifiers for the contacts requesting
        channel membership and awaiting local approval with AddMembers.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.local_pending

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetRemotePendingMembers(self):
        """
        Returns an array of identifiers for contacts who have been
        invited to the channel and are awaiting remote approval.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.remote_pending

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='sasasasas')
    def MembersChanged(self, message, added, removed, local_pending, remote_pending):
        """
        Emitted when contacts join any of the three lists (members, local
        pending or remote pending).  Contacts are listed in the removed
        list when they leave any of the three lists. There may also be
        a message from the server regarding this change, which may be
        displayed to the user if desired.

        Parameters:
        message - a string message from the server, or blank if not
        added - a list of members added to the channel
        removed - a list of members removed from the channel
        local_pending - a list of members who are pending local approval
        remote_pending - a list of members who are pending remote approval
        """

        self._members.update(added)
        self._members.difference_update(removed)

        self.local_pending.update(local_pending)
        self.local_pending.difference_update(added)
        self.local_pending.difference_update(removed)

        self.remote_pending.update(remote_pending)
        self.remote_pending.difference_update(added)
        self.remote_pending.difference_update(removed)


class ChannelInterfaceIndividual(dbus.service.Interface):
    """
    An interface for channels which can only ever contain the owner of the
    connection and a single other individual, and if either party leaves, the
    channel closes. If there is the potential for other members to join, be
    invited, or request to join, the group channel interface should be used.
    When requesting channels, this interface accepts the parameter of a
    contact to communicate with, with D-Bus type 's'.

    This interface has no methods so that if an individual channel is
    requested, and a group channel containing that individual is provided
    instead, the client will still operate correctly even if it doesn't
    implement the group channel interface.

    This interface must never be implemented alongside Channel.Interface.Group.
    """
    _dbus_interfaces = [CHANNEL_INTERFACE_INDIVIDUAL]

    def __init__(self, recipient):
        """
        Initialise the individual channel interface.

        Parameters:
        recipient - the identifier for the other member of the channel
        """
        assert(CHANNEL_INTERFACE_GROUP not in self._interfaces)
        self._interfaces.add(CHANNEL_INTERFACE_INDIVIDUAL)
        self._members.add(recipient)


class ChannelInterfaceNamed(dbus.service.Interface):
    """
    Interface for channels which have an immutable name. When requesting
    channels, this interface accepts the parameter of a name to obtain,
    with D-Bus type 's'.
    """
    def __init__(self, name):
        """ Initialise the interface.

        Parameters:
        name - the immutable name of this channel
        """
        self._interfaces.add(CHANNEL_INTERFACE_NAMED)
        self.name = name

    @dbus.service.method(CHANNEL_INTERFACE_NAMED, in_signature='', out_signature='s')
    def GetName(self):
        """ Get the immutable name of this channel. """
        return self.name


class ChannelInterfacePassword(dbus.service.Interface):
    """
    Interface for channels that may have a password set that users need
    to provide before being able to join, or may be able to view or change
    once they have joined the channel.

    The GetPasswordFlags method and the associated PasswordFlagsChanged
    signal indicate whether the channel has a password, whether the user
    must now provide it to join, and whether it can be viewed or changed
    by the user.
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_PASSWORD)
        self.password_flags = set()
        self.needs_password = False
        self.password = ''

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='', out_signature='as')
    def GetPasswordFlags(self):
        """
        Returns a list of the flags relevant to the password on this channel.
        The user interface can use this to present information about which
        operations are currently valid.

        These can be:
         modifiable - the SetPassword method can be used to change the password
         required - the password is required for users to join this channel
         provide - the ProvidePassword method must be called now for the user to join
         visible - the GetPassword method can be used to retrieve the password

        Returns:
        an array of strings of flags

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.password_flags

    @dbus.service.signal(CHANNEL_INTERFACE_PASSWORD, signature='asas')
    def PasswordFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetPasswordFlags are changed.
        The user interface should be updated as appropriate.

        Parameters:
        added - the flags which have been set
        removed - the flags which are no longer set
        """
        self.password_flags.update(added)
        self.password_flags.difference_update(removed)

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='s', out_signature='b')
    def ProvidePassword(self, password):
        """
        Provide the password so that the channel can be joined. Must be
        called with the correct password in order for channel joining to
        proceed if the 'provide' password flag is set.

        Parameters:
        password - the password

        Returns:
        a boolean indicating whether or not the password was correct

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='', out_signature='s')
    def GetPassword(self):
        """
        Retrieve the password for the channel. Only valid if the 'visible'
        password flag is set (see GetPasswordFlags).

        Returns:
        a string containing the channel's password

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied, NotAvailable
        """
        return self.password

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='s', out_signature='')
    def SetPassword(self, password):
        """
        Change the password of the channel. Only valid if the 'modifiable'
        password flag is set (see GetPasswordFlags).

        Parameters:
        password - the password to set

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument, PermissionDenied
        """
        self.password = password

class ChannelInterfaceSubject(dbus.service.Interface):
    """
    Interface for channels that may have a modifiable subject or topic. A
    SubjectChanged signal should be emitted whenever the subject is changed,
    and once when the subject is initially discovered from the server.
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_SUBJECT)
        self.subject = ''
        self.subject_info = {}
        self.subject_flags = set()

    @dbus.service.method(CHANNEL_INTERFACE_SUBJECT, in_signature='', out_signature='as')
    def GetSubjectFlags(self):
        """
        Returns a list of the flags relevant to the subject of this channel.
        The user interface can use this to present information about which
        operations are currently valid.

        These can be:
         modifiable - the SetSubject method can be used to change the subject
         present - the subject is set and can be obtained with GetSubject

        Returns:
        an array of strings of flags

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.subject_flags

    @dbus.service.signal(CHANNEL_INTERFACE_SUBJECT, signature='asas')
    def SubjectFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetSubjectFlags are changed.
        The user interface should be updated as appropriate.

        Parameters:
        added - the flags which have been set
        removed - the flags which are no longer set
        """
        self.subject_flags.update(added)
        self.subject_flags.difference_update(removed)

    @dbus.service.method(CHANNEL_INTERFACE_SUBJECT, in_signature='', out_signature='sa{sv}')
    def GetSubject(self):
        """
        Get this channel's current subject. Information such as the user
        who set it and the time are represented in a dictionary of keys
        to values so that arbitrary information can be associated with a
        subject. The following well-known values are defined and should
        be used where appropriate:
         u:timestamp - the UNIX timestamp when the subject was set
         s:set-by - the contact ID of the individual who set it
         s:username - the local username of the individual who set it
         s:hostname - the FQDN, IPV4 or IPv6 address of the contact who set it

        Returns:
        the subject text
        a dictionary mapping string attribute names to variant boxed values

        Possible Errors:
        Disconnected, NetworkError, NotAvailable
        """
        return self.subject, self.subject_info

    @dbus.service.method(CHANNEL_INTERFACE_SUBJECT, in_signature='s', out_signature='')
    def SetSubject(self, subject):
        """
        Request that the subject of this channel be changed. Success will be
        indicated by an emission of the SubjectChanged signal.

        Parameters:
        subject - the subject to set

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied, InvalidArgument
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_SUBJECT, signature='sa{sv}')
    def SubjectChanged(self, subject, info):
        """
        Emitted when the subject changes or is initially discovered from the
        server.

        Parameters:
        subject - the new subject string
        info - a dictionary containing named information mapped to boxed values
        """
        self.subject = subject
        self.subject_info = info


class ChannelInterfaceTransfer(dbus.service.Interface):
    """
    An interface for channels where you may request that one of the members
    connects to somewhere else instead.
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_TRANSFER)

    @dbus.service.method(CHANNEL_INTERFACE_TRANSFER, in_signature='ss', out_signature='')
    def Transfer(self, member, destination):
        """
        Request that the given channel member instead connects to a different
        contact ID.

        Parameters:
        member - the member to transfer
        destination - the destination contact ID

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, UnknownContact, PermissionDenied
        """
        pass
