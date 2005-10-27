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
    def GetChannelType(self):
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
    An interface that gives a Channel the ability to send or receive DTMF
    signalling tones. This usually only makes sense for channels transporting
    audio.
    """
    def __init__(self):
        self.interfaces.add(CHANNEL_INTERFACE_DTMF)

    @dbus.service.method(CHANNEL_INTERFACE_DTMF, in_signature='uu', out_signature='')
    def SendDTMF(self, signal, duration):
        """
        Requests that a DTMF tone is sent.

        Parameters:
        signal - a numeric signal number
        duration - a numeric duration in milliseconds
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

    It should not be presumed that the requestor of a channel implementing this
    interface is immediately granted membership, or indeed that they are a
    member at all, unless they appear in the list. They may, for instance,
    be placed into the remote pending list until a connection has been
    established or the request acknowledged remotely.

    This interface must never be implemented alongside Channel.Interface.Individual.
    """
 
    def __init__(self, me):
        assert(CHANNEL_INTERFACE_INDIVIDUAL not in self.interfaces)
        self.interfaces.add(CHANNEL_INTERFACE_GROUP)
        self.local_pending = set()
        self.remote_pending = set()
        self.me = me

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def AddMembers(self, contacts):
        """
        Invite all the given contacts into the channel, or approve requests
        for channel membership for contacts on the pending local list. Calling
        this method with an empty array will do nothing if the user is able
        to invite or add members to this channel, or will fail appropriately
        if they are not allowed to do this. This can be used by user interfaces
        to test whether a particular option should be presented to the user.
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='as', out_signature='')
    def RemoveMembers(self, contacts):
        """
        Requests the removal of contacts from a channel, refuse their request
        for channel membership on the pending local list, or rescind their
        invitation on the pending remote list. Calling this method with an
        empty array will do nothing if the user is able to remove or request
        the removal of members from the channel, or will fail appropriately
        if they are not allowed to do this. This can be used by user interfaces
        to test whether a particular option should be presented to the user.
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
        """
        return dbus.Array(self.local_pending, signature='s')

    @dbus.service.method(CHANNEL_INTERFACE_GROUP, in_signature='', out_signature='as')
    def GetRemotePendingMembers(self):
        """
        Returns an array of identifiers for contacts who have been
        invited to the channel and are awaiting remote approval.
        """
        return dbus.Array(self.remote_pending, signature='s')

    @dbus.service.signal(CHANNEL_INTERFACE_GROUP, signature='asasasas')
    def MembersChanged(self, added, removed, local_pending, remote_pending):
        """
        Emitted when contacts join any of the three lists (members, local
        pending or remote pending).  Contacts are listed in the removed
        list when they leave any of the three lists.
        """

        self.members.update(added)
        self.members.difference_update(removed)

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
        self.interfaces.add(CHANNEL_INTERFACE_PASSWORD)
        self.password_flags = set()
        self.needs_password = False
        self.password = ''

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='', out_signature='')
    def GetPasswordFlags(self):
        """
        Returns a list of the flags relevant to the password on this channel.
        The user interface can use this to present information about which
        operations are currently valid.

        These can be:
         modifiable - the SetPassword method can be used to change the password
         required - the password is required for users to join this channel
         provide - the ProvidePassword method must be called now for the user to join
         visible - the GetPassword method can be used to retreive the password

        Returns:
        an array of strings of flags
        """
        return self.password_flags

    @dbus.service.signal(CHANNEL_INTERFACE_PASSWORD, signature='asas')
    def PasswordFlagsChanged(self, added, removed):
        """
        Emitted when the flags as returned by GetPasswordFlags are changed.
        The user interface should be updated.

        Parameters:
        added - the flags which have been set
        removed - the flags which are no longer set
        """
        self.password_flags.update(added)
        self.password_flags.difference_update(removed)

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='s', out_signature='')
    def ProvidePassword(self, password):
        """
        Provide the password so that the channel can be joined. Must be
        called with the correct password in order for channel joining to
        proceed if the 'provide' password flag is set.

        Parameters:
        password - the password
        """
        pass

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='', out_signature='s')
    def GetPassword(self):
        """
        Retrieve the password for the channel. Only valid if the 'visible'
        password flag is set (see GetPasswordFlags).

        Returns:
        a string containing the channel's password
        """
        return self.password

    @dbus.service.method(CHANNEL_INTERFACE_PASSWORD, in_signature='s', out_signature='')
    def SetPassword(self, password):
        """
        Change the password of the channel. Only valid if the 'modifiable'
        password flag is set (see GetPasswordFlags).

        Parameters:
        password - the password to set
        """
        self.password = password

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

        Parameters:
        subject - the subject to set
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
