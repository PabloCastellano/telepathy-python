# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005 Collabora Limited
# Copyright (C) 2005 Nokia Corporation
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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

    Each channel may have an immutable handle associated with it, which may
    be any handle type, such as a contact, room or list handle, indicating
    that the channel is for communicating with that handle. If a channel does
    not have a handle, it means that the channel is defined by some other
    terms, such as it may be a transient group defined only by its members
    as visible through the Channel.Interface.Group interface.

    Other optional interfaces can be implemented to indicate other available
    functionality, such as Channel.Interface.Group if the channel contains
    a number of contacts, Channel.Interface.Password to indicate
    that a channel may have a password set to require entry, and
    Channel.Interface.RoomProperties for extra data about channels which
    represent chat rooms. The interfaces implemented may not vary after the
    channel's creation has been signalled to the bus (with the connection's
    NewChannel signal).

    Specific connection manager implementations may implement channel types and
    interfaces which are not contained within this specification in order to
    support further functionality. To aid interoperability between client and
    connection manager implementations, the interfaces specified here should be
    used wherever applicable, and new interfaces made protocol-independent
    wherever possible. Because of the potential for 3rd party interfaces adding
    methods or signals with conflicting names, the D-Bus interface names should
    always be used to invoke methods and bind signals.
    """
    def __init__(self, connection, type, handle):
        """
        Initialise the base channel object.

        Parameters:
        connection - the parent Connection object
        type - interface name for the type of this channel
        handle - the channels handle if applicable
        """
        self._conn = connection
        object_path = self._conn.get_channel_path()
        dbus.service.Object.__init__(self, self._conn._name, object_path)

        self._type = type
        self._handle = handle
        self._interfaces = set()

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='')
    def Close(self):
        """
        Request that the channel be closed. This is not the case until
        the Closed signal has been emitted, and depending on the connection
        manager this may simply remove you from the channel on the server,
        rather than causing it to stop existing entirely. Some channels
        such as contact list channels may not be closed.

        Possible Errors:
        Disconnected, NetworkError, NotImplemented
        """
        self.Closed()
        self._conn.remove_channel(self)

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

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='uu')
    def GetHandle(self):
        """ Returns the handle type and number if this channel represents a
        communication with a particular contact, room or server-stored list, or
        zero if it is transient and defined only by its contents. """
        if self._handle:
            return self._handle.get_type(), self._handle
        else:
            return (CONNECTION_HANDLE_TYPE_NONE, 0)

    @dbus.service.method(CHANNEL_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """
        Get the optional interfaces implemented by the channel.

        Returns:
        an array of the D-Bus interface names
        """
        return self._interfaces


class ChannelTypeContactSearch(Channel):
    """
    A channel type for searching server-stored user directories. A new channel
    should be requested by a client for each search attempt, and it should be
    closed when the search is completed or the required result has been found
    in order to free unused handles. The search can be cancelled at any time
    by calling the channel Close method, although depending upon the protocol
    the connection manager may not be able to prevent the server from sending
    further results.

    Before searching, the GetSearchKeys method should be used to discover any
    instructions sent by the server, and the valid search keys which can be
    provided to the Search method. A search request is then started by
    providing some of these terms to the Search method, and the search status
    will be set to CHANNEL_CONTACT_SEARCH_STATE_DURING. When results are
    returned by the server, the SearchResultReceived signal is emitted for each
    contact found, and when the search is complete, the search status will be
    set to CHANNEL_SEARCH_STATE_AFTER.
    """
    def __init__(self, connection):
        """
        Initialise the contact search channel.
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_CONTACT_SEARCH)
        self._search_state = CHANNEL_SEARCH_STATE_BEFORE

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
        emitted with the status CHANNEL_CONTACT_SEARCH_STATE_DURING.

        Parameters:
        a dictionary mapping search key names to the desired values

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_CONTACT_SEARCH, in_signature='', out_signature='u')
    def GetSearchState(self):
        """
        Returns the current state of this search channel object. One of the
        following values:
        0 - CHANNEL_CONTACT_SEARCH_STATE_BEFORE
            the search has not started
        1 - CHANNEL_CONTACT_SEARCH_STATE_DURING
            the search is in progress
        2 - CHANNEL_CONTACT_SEARCH_STATE_AFTER
            the search has been completed

        Returns:
        an integer representing the search state
        """
        return self._search_state

    @dbus.service.signal(CHANNEL_TYPE_CONTACT_SEARCH, signature='u')
    def SearchStateChanged(self, state):
        """
        Emitted when the search state (as returned by the GetSearchState
        method) changes.

        Parameters:
        state - an integer representing the new search state
        """
        self._search_state = state

    @dbus.service.signal(CHANNEL_TYPE_CONTACT_SEARCH, signature='ua{sv}')
    def SearchResultReceived(self, contact, values):
        """
        Emitted when a search result is received from the server.

        Parameters:
        an integer handle for the contact
        a dictionary mapping search key names to values for this contact
        """
        pass


class ChannelTypeContactList(Channel):
    """
    A channel type for representing a list of people on the server which is
    not used for communication. This is intended for use with the interface
    Channel.Interface.Group for managing buddy lists and privacy lists
    on the server. This channel type has no methods because all of the
    functionality it represents is available via the group interface.

    Singleton instances of this channel type should be created by the
    connection manager at connection time if the list exists on the server, or
    may be requested by using the appropriate handle.  These handles can be
    obtained using RequestHandle with a handle type of
    CONNECTION_HANDLE_TYPE_LIST and one of the following identifiers:
     subscribe - the group of contacts for whom you wish to receive presence
     publish - the group of contacts who may receive your presence
     hide - a group of contacts who are on the publish list but are temporarily disallowed from receiving your presence
     allow - a group of contacts who may send you messages
     deny - a group of contacts who may not send you messages
    """
    _dbus_interfaces = [CHANNEL_TYPE_CONTACT_LIST]

    def __init__(self, connection, handle):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_CONTACT_LIST, handle)


class ChannelTypeStreamedMedia(Channel):
    """
    A channel that can send and receive streamed media such as audio or video.

    A complete negotiation interface is defined, based off that of 
    the Farsight project's.
  
    When the negotiations are completed, the ReceivedMediaParameters signal is
    emitted, containing the 'local' media parameters, which contain the SDP
    information for the local user's media streams, and the 'remote' media
    parameters which contains the same information for the remote user's
    streams.
    """
    def __init__(self, connection, handle):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_STREAMED_MEDIA, handle)
        self._media_parameters = {}

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='uos')

    def NewMediaSessionHandler(self, member, session_handler, type):
        """
        signal that a session handler object has been created for a member
        of this channel
        The client should then service this session handler object to provide
        streaming services.
  
        Parameter:
        member - member that the MediaSessionHandler is created for
        session_handler - object path to MediaSessionHandler object
        type - string indicateing type of session, eg "rtp"
        
        Possible Errors:
        Disconnected, InvalidHandle, NotAvailable (if the contact has sent nothing to us on this channel)
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='', 
                                                      out_signature='a(uos)')
    def GetSessionHandlers(self):
        """
        Returns all currently active session handlers on this channel
        as a list of (member,session_handler_path,type)
        """
        pass

    @dbus.service.method(CHANNEL_TYPE_STREAMED_MEDIA, in_signature='',
                                                      out_signature='a(uuuu)')
    def GetStreams(self):
        """
        Returns an array of structs of contact handles, stream identifiers
        accompanying stream types and the current state of the stream.
        Stream identifiers are unsigned interegers and are unique for 
        each contact.
        Stream types are identified by the following values:
          MEDIA_STREAM_TYPE_AUDIO = 0
          MEDIA_STREAM_TYPE_VIDEO = 1
        Stream states are identified by
          MEDIA_STREAM_STATE_STOPPED =0
          MEDIA_STREAM_STATE_PLAYING = 1
          MEDIA_STREAM_STATE_CONNECTING = 2
          MEDIA_STREAM_STATE_CONNECTED = 3
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_STREAMED_MEDIA, signature='uuu')
    def StreamStateChanged(self, contact_handle, stream_id, stream_state):
        """
        Signal emitted when a memeber's stream's state changes.
        stream_id is as returned in GetStreams
        stream_state is as defined in GetStreams
        """
        pass



class MediaSessionHandler(dbus.service.Object):
    """
    A media session handler is an object that handles a number of synchonised
    media streams.
    """

    def __init__(self, bus_name, object_path):
        dbus.service.Object.__init__(self,bus_name, object_path);

    @dbus.service.method(MEDIA_SESSION_HANDLER, in_signature='', 
                                                out_signature='')
    def Ready(self):
        """
        Inform the connection manager that a client is ready to handle
        this SessionHandler
        """
        print "ready called on base class"
        pass;

    @dbus.service.method(MEDIA_SESSION_HANDLER, in_signature='us', 
                                                out_signature='')
    def Error(self, errno, message):
        """
        Inform the connection manager that an error occured in this session.
        """
        pass

    @dbus.service.signal(MEDIA_SESSION_HANDLER, signature='ouu')
    def NewMediaStreamHandler(self, stream_handler, media_type, direction):
        """
        Emitted when a new media stream handler has been created for this
        session.
  
        Parameters:
        stream_handler - an object path to a new MediaStreamHandler
        media_type - enum for type of media that this stream should handle
          MEDIA_STREAM_TYPE_AUDIO = 0
          MEDIA_STREAM_TYPE_VIDEO = 1
        direction - enum for direction of this stream
          MEDIA_STREAM_DIRECTION_NONE = 0
          MEDIA_STREAM_DIRECTION_SEND = 1
          MEDIA_STREAM_DIRECTION_RECEIVE = 2
          MEDIA_STREAM_DIRECTION_BIDIRECTIONAL = 3
        """
        pass

class MediaStreamHandler(dbus.service.Object):
    """
    Handles ths lifetime of a media stream. A client should provide 
    information to this handler as and when is it ready
    """

    def __init__(self, bus_name, object_path):
        dbus.service.Object.__init__(self, bus_name, object_path);

    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='a(usuuua{ss})', 
                                               out_signature='')
    def Ready(self, codecs):
        """
        Inform the connection manager that a client is ready to handle
        this StreamHandler. Also provide it with info about all supported
        codecs.

        Parameters:
        codecs - as for SupportedCodecs
        """
        pass;

    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='us', 
                                                out_signature='')
    def Error(self, errno, message):
        """
        Inform the connection manager that an error occured in this stream.

        Parameters:
        errno - id of error:
        message - string describing the error
          MEDIA_STREAM_ERROR_UNKNOWN = 0
          MEDIA_STREAM_ERROR_EOS = 1
        """
        pass


    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='sa(usuussduss)', 
                                               out_signature='')
    def NewNativeCandidate(self, candidate_id, transports ):
        """
        Inform this MediaStreamHandler that a new native transport candidate
        has been ascertained.

        Parameters:
        candidate_id - string identifier for this candidate
        transports - array of transports for this candidate with fields:
          component number
          ip (as a string)
          port
          enum for base network protocol 
            MEDIA_STREAM_BASE_PROTO_UDP = 0
            MEDIA_STREAM_BASE_PROTO_TCP = 1
          string specifying proto subtype (e.g RTP )
          string specifying proto profile (e.g AVP)
          our preference value of this transport (double in range 0-1 
          inclusive)
            1 signals most preferred transport
          transport type  
            MEDIA_STREAM_TRANSPORT_TYPE_LOCAL = 0 - a local address      
            MEDIA_STREAM_TRANSPORT_TYPE_DERIVED = 1 - an external address 
                derived by a method such as STUN
            MEDIA_STREAM_TRANSPORT_TYPE_RELAY = 2 - an external stream relay
          username - string to specify a username if authentication 
                     is required 
          password - string to specify a password if authentication 
                     is required 
       """
        pass

    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='', 
                                               out_signature='')
    def NativeCandidatesPrepared(self):
        """
        Informs the connection manager that all possible native candisates
        have been discovered for the moment.
        """
    pass

    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='ss', 
                                               out_signature='')
    def NewActiveCandidatePair(self, native_candidate_id, remote_candidate_id):
        """
        Informs the connection manager that a valid candidate pair
        has been discovered and streaming is in progress
        """
        pass

    @dbus.service.signal(MEDIA_STREAM_HANDLER, signature='ss')
    def SetActiveCandidatePair(self, native_candidate_id, remote_candidate_id):
        """
        used by the connection manager to inform the voip engine that a 
        valid candidate pair has been discovered by the remote end
        and streaming is in progress
        """
        pass


    @dbus.service.signal(MEDIA_STREAM_HANDLER, signature='a(sa(usuussduss))')
    def SetRemoteCandidateList(self, remote_candidates):
        """
        Signal emitted when the connectoin manager wishes to inform the 
        voip engine of all the remotes candidates at once.
        
        Parameters:

        remote_candidates - a list of candidate id and a list of transports
        as defined in NewNativeCandidate
        """
        pass

    @dbus.service.signal(MEDIA_STREAM_HANDLER, signature='sa(usuussduss)')
    def AddRemoteCandidate(self, candidate_id, transports):
        """
        Signal emitted when the connectoin manager wishes to inform the 
        voip engine of new remote candidate
        
        Parameters:

        candidate_id - string identifier for this candidate
        transports - array of transports for this candidate with fields
                     As defined in NewNativeCandidate
        """
        pass

    @dbus.service.signal(MEDIA_STREAM_HANDLER, signature='s')
    def RemoveRemoteCandidate(self, candidate_id):
        """
        Signal emitted when the connectoin manager wishes to inform the 
        voip engine thatthe remote end has dropped a previously usable
        candidate
        
        Parameters:

        candidate_id - string identifier for remote candidate to drop
        """
        pass


    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='u', 
                                               out_signature='')
    def CodecChoice(self, codec_id):
        """
        Informs the connection manaager of the current codec choice
        """
    pass

    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='u', 
                                               out_signature='')
    def StreamState(self, state):
        """
        Informs the connection manaager of the stream's current state
        State is as specified in ChannelTypeStreamedMedia::GetStreams
        """
    pass


    @dbus.service.method(MEDIA_STREAM_HANDLER, in_signature='a(usuuua{ss})', 
                                                out_signature='')
    def SupportedCodecs(self, codecs):
        """
        Inform the connection manager of the supported codecs for this session.
        This is called after the connection manager has emitted SetRemoteCodecs
        to notify what codecs are supported by the peer, and will thus be an
        intersection of all locally supported codecs (passed to Ready)
        and those supported by the peer.
        
        Parameters:
        codecs - list of codec info structures containing
            id of codec
            codec name
            media type
            clock rate of codec
            number of supported channels
            string key-value pairs for supported optional parameters
        """ 
 
    @dbus.service.signal(MEDIA_STREAM_HANDLER, signature='a(usuuua{ss})')
    def SetRemoteCodecs(self, codecs):
        """
        Signal emitted when the connectoin manager wishes to inform the 
        voip engine of the codecs supported by the remote end.
        Parameters:
        codecs - as for SupportedCodecs
        """
        pass

    

class ChannelTypeRoomList(Channel):
    """
    A channel type for listing named channels available on the server. Once the
    ListRooms method is called, it emits signals for rooms present on the
    server, until you Close this channel. In some cases, it may not be possible
    to stop the deluge of information from the server. This channel should be
    closed when the room information is no longer being displayed, so that the
    room handles can be freed.

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
        self._listing_rooms = False
        self._rooms = {}

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
        return self._listing_rooms

    @dbus.service.signal(CHANNEL_TYPE_ROOM_LIST, signature='b')
    def ListingRooms(self, listing):
        """
        Emitted to indicate whether or not room listing request is currently
        in progress.

        Parameters:
        listing - a boolean indicating if room listing is in progress
        """
        self._listing_rooms = listing

    @dbus.service.signal(CHANNEL_TYPE_ROOM_LIST, signature='a(usa{sv})')
    def GotRooms(self, rooms):
        """
        Emitted when information about rooms on the server becomes available.
        The array contains the room handle (as can be passed to the
        RequestChannel method with CONNECTION_HANDLE_TYPE_ROOM), the channel
        type, and a dictionary containing further information about the
        room as available. The following well-known keys and types are
        recommended for use where appropriate:
         s:subject - the subject of the room
         u:members - the number of members of the room
         b:password - true if the room requires a password to enter
         b:invite-only - true if you cannot join the room, but must be invited

        Parameters:
        rooms - an array of structs containing:
            an integer room handle
            a string representing the D-Bus interface name of the channel type
            an dictionary mapping string keys to variant boxed information
        """
        pass


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
    following:
    0 - CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        a standard message
    1 - CHANNEL_TEXT_MESSAGE_TYPE_ACTION
        an action which might be presented to the user as * <sender> <action>
    2 - CHANNEL_TEXT_MESSAGE_TYPE_NOTICE
        an automated message not expecting a reply

    Sending messages can be requested using the Send method, which will return
    and cause the Sent signal to be emitted when the message has been delivered
    to the server.
    """

    def __init__(self, connection, handle):
        """
        Initialise the channel.

        Parameters:
        connection - the parent Telepathy Connection object
        """
        Channel.__init__(self, connection, CHANNEL_TYPE_TEXT, handle)

        self._pending_messages = {}

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='us', out_signature='')
    def Send(self, type, text):
        """
        Request that a message be sent on this channel. The Sent signal will be
        emitted when the message has been sent, and this method will return.

        Parameters:
        type - an integer indicating the type of the message
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

    @dbus.service.method(CHANNEL_TYPE_TEXT, in_signature='', out_signature='a(uuuus)')
    def ListPendingMessages(self):
        """
        List the messages currently in the pending queue.

        Returns:
        an array of structs containing:
            a numeric identifier
            a unix timestamp indicating when the message was received
            an integer handle of the contact who sent the message
            an integer of the message type
            a string of the text of the message
        """
        messages = []
        for id in self._pending_messages.keys():
            (timestamp, sender, type, text) = self._pending_messages[id]
            message = (id, timestamp, sender, type, text)
            messages.append(message)
        messages.sort(cmp=lambda x,y:cmp(x[1], y[1]))
        return messages

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uus')
    def Sent(self, timestamp, type, text):
        """
        Signals that a message has been sent on this channel.

        Parameters:
        timestamp - the unix timestamp indicating when the message was sent
        type - the message type (normal, action, notice, etc)
        text - the text of the message
        """
        pass

    @dbus.service.signal(CHANNEL_TYPE_TEXT, signature='uuuus')
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
        sender - the handle of the contact who sent the message
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
    Interface for channels which have multiple members, and where the members
    of the channel can change during its lifetime. Your presence in the channel
    cannot be presumed by the channel's existence (for example, a channel you
    may request membership of but your request may not be granted).

    This interface implements three lists: a list of current members, and two
    lists of local pending and remote pending members. Contacts on the remote
    pending list have been invited to the channel, but the remote user has not
    accepted the invitation. Contacts on the local pending list have requested
    membership of the channel, but the local user of the framework must accept
    their request before they may join. A single contact should never appear on
    more than one of the three lists. The lists are empty when the channel is
    created, and the MembersChanged signal should be emitted when information
    is retrieved from the server, or changes occur.

    Addition of members to the channel may be requested by using AddMembers. If
    remote acknowledgement is required, use of the AddMembers method will cause
    users to appear on the remote pending list. If no acknowledgement is
    required, AddMembers will add contacts to the member list directly.  If a
    contact is awaiting authorisation on the local pending list, AddMembers
    will grant their membership request.

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
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_GROUP)
        self._group_flags = 0
        self._members = set()
        self._local_pending = set()
        self._remote_pending = set()

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='u')
    def GetGroupFlags(self):
        """
        Returns an integer representing the logical or of flags on this
        channel. The user interface can use this to present information about
        which operations are currently valid.

        These can be:
        1 - CHANNEL_GROUP_FLAG_CAN_ADD
            The AddMembers method can be used to add or invite members who are
            not already in the local pending list (which is always valid).
        2 - CHANNEL_GROUP_FLAG_CAN_REMOVE
            The RemoveMembers method can be used to remove channel members
            (removing those on the pending local list is always valid).
        4 - CHANNEL_GROUP_FLAG_CAN_RESCIND
            The RemoveMembers method can be used on people on the remote
            pending list.
        8 - CHANNEL_GROUP_FLAG_MESSAGE_ADD
            A message may be sent to the server when calling AddMembers on
            contacts who are not currently pending members.
        16 - CHANNEL_GROUP_FLAG_MESSAGE_REMOVE
            A message may be sent to the server when calling RemoveMembers on
            contacts who are currently channel members.
        32 - CHANNEL_GROUP_FLAG_MESSAGE_ACCEPT
            A message may be sent to the server when calling AddMembers on
            contacts who are locally pending.
        64 - CHANNEL_GROUP_FLAG_MESSAGE_REJECT
            A message may be sent to the server when calling RemoveMembers on
            contacts who are locally pending.
        128 - CHANNEL_GROUP_FLAG_MESSAGE_RESCIND
            A message may be sent to the server when calling RemoveMembers on
            contacts who are remote pending.

        Returns:
        an integer of flags or'd together

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._group_flags

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='uu')
    def GroupFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetGroupFlags are changed.
        The user interface should be updated as appropriate.

        Parameters:
        added - a logical OR of the flags which have been set
        removed - a logical OR of the flags which have been cleared
        """
        self._group_flags |= added
        self._group_flags &= ~removed

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='aus', out_signature='')
    def AddMembers(self, contacts, message):
        """
        Invite all the given contacts into the channel, or accept requests for
        channel membership for contacts on the pending local list. A message
        may be provided along with the request, which will be sent to the
        server if supported. See the CHANNEL_GROUP_FLAG_MESSAGE_ADD and
        CHANNEL_GROUP_FLAG_MESSAGE_ACCEPT flags to see in which cases this
        message should be provided.

        Parameters:
        contacts - an array of contact handles to invite to the channel
        message - a string message, which can be blank if desired

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied, InvalidHandle
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='aus', out_signature='')
    def RemoveMembers(self, contacts, message):
        """
        Requests the removal of contacts from a channel, reject their request
        for channel membership on the pending local list, or rescind their
        invitation on the pending remote list. A message may be provided along
        with the request, which will be sent to the server if supported. See
        the CHANNEL_GROUP_FLAG_MESSAGE_REMOVE,
        CHANNEL_GROUP_FLAG_MESSAGE_REJECT and
        CHANNEL_GROUP_FLAG_MESSAGE_RESCIND flags to see in which cases this
        message should be provided.


        Parameters:
        contacts - an array of contact handles to remove from the channel
        message - a string message, which can be blank if desired

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, PermissionDenied, InvalidHandle
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='au')
    def GetMembers(self):
        """
        Returns an array of handles for the members of this channel.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._members

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='u')
    def GetSelfHandle(self):
        """
        Returns the handle for the user on this channel if they are a
        member, and 0 if not.

        Possible Errors:
        Disconnected, NetworkError
        """
        self_handle = self._conn.GetSelfHandle()
        if self_handle in self._members:
            return self_handle
        else:
            return 0

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='au')
    def GetLocalPendingMembers(self):
        """
        Returns an array of handles representing contacts requesting
        channel membership and awaiting local approval with AddMembers.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._local_pending

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='au')
    def GetRemotePendingMembers(self):
        """
        Returns an array of handles representing contacts who have been
        invited to the channel and are awaiting remote approval.

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._remote_pending

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='sauauauau')
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

        self._local_pending.update(local_pending)
        self._local_pending.difference_update(added)
        self._local_pending.difference_update(removed)

        self._remote_pending.update(remote_pending)
        self._remote_pending.difference_update(added)
        self._remote_pending.difference_update(removed)


class ChannelInterfaceHold(dbus.service.Interface):
    """
    Interface for channels where members may put you on hold, or you may put
    members on hold. This usually only makes sense for channels where you are
    streaming media to or from the members. Hold is defined as requesting
    that you are not sent any media streams by another, so these states
    indicate whether or not you are sending and receiving media streams
    to each member of the channel.
    """
    def __init__(self):
        """ Initialise the interface. """
        self._interfaces.add(CHANNEL_INTERFACE_HOLD)

    @dbus.service.method(CHANNEL_INTERFACE_HOLD, in_signature='u', out_signature='u')
    def GetHoldState(self, member):
        """
        Given a member of the channel, return their current hold state. This
        can be one of the following values:
        0 - CHANNEL_HOLD_STATE_NONE
            Neither the local user and the remote member are on hold, and media
            is being sent bidirectionally.
        1 - CHANNEL_HOLD_STATE_SEND_ONLY
            The local user has put the remote member on hold, so is sending
            media but has arranged not to receive any media streams.
        2 - CHANNEL_HOLD_STATE_RECV_ONLY
            The user has been put on hold by the remote member, so is receiving
            media but has arranged not to send any media streams.
        3 - CHANNEL_HOLD_STATE_BOTH
            Both the local user and the remote member have agreed not to send
            any media streams to each other.

        Parameters:
        member - the handle of a member of the channel

        Returns:
        state - an integer representing the hold state, as defined above

        Potential Errors:
        Disconnected, InvalidHandle
        """

    @dbus.service.signal(CHANNEL_INTERFACE_HOLD, signature='uu')
    def HoldStateChanged(self, member, state):
        """
        Emitted to indicate that the hold state (as defined in GetHoldState
        above) has changed for a member of this channel. This may occur as
        a consequence of you requesting a change with RequestHold, or the
        state changing as a result of a request from the remote member
        or another process.

        Parameters:
        member - the integer handle of a member of the channel
        state - an integer representing the new hold state
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_HOLD, in_signature='ub', out_signature='')
    def RequestHold(self, member, hold):
        """
        Request that a certain member be put on hold (be instructed not to send
        any media streams to you) or be taken off hold. Success is indicated
        by the HoldStateChanged signal being emitted.

        Parameters:
        member - the integer handle of a member of the channel
        hold - an boolean indicating whether or not the user should be on hold

        Potential Errors:
        Disconnected, NetworkError, InvalidHandle
        """
        pass


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
        self._password_flags = 0
        self._password = ''

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='', out_signature='u')
    def GetPasswordFlags(self):
        """
        Returns the logical OR of the flags relevant to the password on this
        channel.  The user interface can use this to present information about
        which operations are currently valid.

        These can be:
        8 - CHANNEL_PASSWORD_FLAG_PROVIDE
            the ProvidePassword method must be called now for the user to join the channel

        Returns:
        an integer with the logical OR of all the flags set

        Possible Errors:
        Disconnected, NetworkError
        """
        return self._password_flags

    @dbus.service.signal(CHANNEL_INTERFACE_PASSWORD, signature='uu')
    def PasswordFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetPasswordFlags are changed.
        The user interface should be updated as appropriate.

        Parameters:
        added - a logical OR of the flags which have been set
        removed - a logical OR of the flags which have been cleared
        """
        self._password_flags |= added
        self._password_flags &= ~removed

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


class ChannelInterfaceRoomProperties(dbus.service.Interface):
    """
    Interface for channels which represent a chat room, to allow querying and
    setting properties. ListProperties returns which properties are valid for
    the given channel, including their type, and an integer handle used to
    refer to them in GetProperties, SetProperties, and the PropertiesChanged
    signal. The values are represented by D-Bus variant types, and are
    accompanied by flags indicating whether or not the property is readable or
    writable.

    The following property types and names should be used where appropriate,
    but implementations may add extra properties to communicate data with
    particular clients:
      b:invite-only
        true if people may not join the channel until they have been invited
      u:limit
        the limit to the number of members, if limited is true
      b:limited
        true if there is a limit to the number of channel members
      b:moderated
        true if channel membership is not sufficient to allow participation
      s:name
        a human-visible name for the channel, if it differs to the handle
      s:password
        the password required to enter the channel if password-required is true
      b:password-required
        true if a password must be provided to enter the channel
      b:private
        true if the channel is not visible to non-members
      s:subject
        a human-readable description of the channel
      u:subject-timestamp
        a unix timestamp indicating when the subject was last modified
      u:subject-contact
        a contact handle representing who last modified the subject

    Each property also has a flags value to indicate what methods are
    available. This is a bitwise OR of the following values:
        1 - CHANNEL_ROOM_PROPERTY_FLAG_READ
            the property can be read
        2 - CHANNEL_ROOM_PROPERTY_FLAG_WRITE
            the property can be written
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_ROOM_PROPERTIES)

    @dbus.service.method(CHANNEL_INTERFACE_ROOM_PROPERTIES, in_signature='',
                                                            out_signature='a{u(ssu)}')
    def ListProperties(self):
        """
        Returns a dictionary of the properties available on this channel.

        Returns:
        a dictionary mapping integer identifiers to:
            structs containing:
                a string property name
                a string representing the D-Bus signature of this property
                a bitwise OR of the flags applicable to this property
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_ROOM_PROPERTIES, in_signature='au',
                                                            out_signature='a{uv}')
    def GetProperties(self, properties):
        """
        Returns a dictionary of variants containing the current values of the
        given properties.

        If any given property identifiers are invalid, InvalidArgument will be
        returned. All properties must have the CHANNEL_ROOM_PROPERTY_FLAG_READ
        flag, or PermissionDenied will be returned.

        Parameters:
        properties - an array of property identifiers

        Returns:
        a dictionary mapping integer identifiers to:
            variant boxed values

        Potential Errors:
        Disconnected, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_ROOM_PROPERTIES, in_signature='a{uv}',
                                                            out_signature='')
    def SetProperties(self, properties):
        """
        Takes a dictionary of variants containing desired values to set the given
        properties. In the case of any errors, no properties will be changed.
        When the changes have been acknowledged by the server, the
        PropertiesChanged signal will be emitted.

        All properties given must have the CHANNEL_ROOM_PROPERTY_FLAG_WRITE
        flag, or PermissionDenied will be returned. If any variants are of the
        wrong type, NotAvailable will be returned.  If any given property
        identifiers are invalid, InvalidArgument will be returned.

        Parameters:
        properties - a dictionary mapping integer identifiers to:
            variant boxed values

        Potential Errors:
        Disconnected, InvalidArgument, NotAvailable, PermissionDenied, NetworkError
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_ROOM_PROPERTIES, signature='a{uv}')
    def PropertiesChanged(self, properties):
        """
        Emitted when the value of readable properties has changed.

        Parameters:
        properties - a dictionary mapping integer identifiers to:
            variant boxed values
        """
        pass

    @dbus.service.signal(CHANNEL_INTERFACE_ROOM_PROPERTIES, signature='a{uu}')
    def PropertyFlagsChanged(self, properties):
        """
        Emitted when the flags of some room properties have changed.

        Parameters:
        properties - a dictionary mapping integer identifiers to:
            a bitwise OR of the current flags
        """
        pass


class ChannelInterfaceTransfer(dbus.service.Interface):
    """
    An interface for channels where you may request that one of the members
    connects to somewhere else instead.
    """
    def __init__(self):
        self._interfaces.add(CHANNEL_INTERFACE_TRANSFER)

    @dbus.service.method(CHANNEL_INTERFACE_TRANSFER, in_signature='uu', out_signature='')
    def Transfer(self, member, destination):
        """
        Request that the given channel member instead connects to a different
        contact ID.

        Parameters:
        member - the handle of the member to transfer
        destination - the handle of the destination contact

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, InvalidHandle, PermissionDenied
        """
        pass
