#!/usr/bin/env python

import dbus.service

from telepathy import *

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
    def __init__(self, proto, account, name_parts):
        """
        Parameters:
        proto - the name of the protcol this conection should be handling.
        account - a protocol-specific account name
        name_parts - a list of strings with which to form the service and
        object names
        """
        bus_name = dbus.service.BusName('org.freedesktop.Telepathy.Connection.' + '.'.join(name_parts))
        object_path = '/org/freedesktop/Telepathy/Connection/' + '/'.join(name_parts)
        print bus_name, object_path
        dbus.service.Object.__init__(self, bus_name, object_path)

        self._proto = proto
        self._account = account

        self._status = 'connecting'
        self._interfaces = set()
        self._channels = set()

    def addChannel(self, channel):
        """ add a new channel and signal its creation""" 
        self._channels.add(channel)
        self.NewChannel(channel.type, channel.object_path, channel.requested)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """
        Get the optional interfaces supported by the connection. Not valid
        until the connection has been established (GetState returns
        'connected').

        Returns:
        an array of D-Bus interface names

        Potential Errors:
        Disconnected
        """
        return self._interfaces

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        """
        Get the protocol this connection is using.

        Returns:
        a string identifier for the protocol
        """
        return self._proto

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetAccount(self):
        """
        Get the identifier for this connection's account.

        Returns:
        a string identifier for the user
        """
        return self._account

    @dbus.service.signal(CONN_INTERFACE, signature='ss')
    def StatusChanged(self, status, reason):
        """
        Emitted when the status of the connection changes. The currently
        defined states are:

        connected - The connection is alive and all methods are available.

        connecting - The connection has not yet been established, or has been
        severed and reconnection is being attempted. Some methods may fail
        until the connection has been established.

        disconnected - The connection has been severed and no method calls are
        valid. The object may be removed from the bus at any time.

        The reason should be one of the following:

        requested - The change is in response to a user request.

        network-error - There was an error sending or receiving on the
        network socket.

        authentication-failed - The username or password was invalid.

        encryption-error - There was an error negotiating SSL on this
        connection, or encryption was unavailable and require-encryption was
        set when the connection was created.

        Parameters:
        status - a string indicating the new status
        """
        print 'service_name: %s object_path: %s signal: StatusChanged %s' % (self.service_name, self.object_path, status)
        self._status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetStatus(self):
        """
        Get the current status as defined in the StatusChanged signal.

        Returns:
        a string representing the current status
        """
        return self._status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='')
    def Disconnect(self):
        """
        Request that the connection be closed.
        """
        pass

    @dbus.service.signal(CONN_INTERFACE, signature='sob')
    def NewChannel(self, type, object_path, requested):
        """
        Emitted when a new Channel object is created, either through user
        request or incoming information from the service. The requested boolean
        indicates if the channel was requested by an existing client, or is an
        incoming communication and needs to have a handler launched.

        Parameters:
        type - a D-Bus interface name representing the channel type
        object_path - a D-Bus object path for the channel object on this service
        requested - a boolean indicating if the channel was requested or not
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
        for channel in self._channels:
            chan = (channel.type, channel.object_path)
            ret.append(chan)
        return ret

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

        Possible Errors:
        Disconnected, NetworkError, NotImplemented (unknown channel type), InvalidArgument (invalid interface parameters), NotAvailable (requested interfaces unavailable), UnknownContact
        """
        raise IOError('Unknown channel type %s' % type)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetMatchFlags(self):
        """
        A function that returns a list of flags telling the user interface
        which policies to follow when comparing contact IDs from the server.
        In keeping with Galago's service flags, the well-known values
        that should be supported by all client implementations are:
         preserve-case - preserve case during matching
         preserve-spaces - preserve spaces during matching
         strip-slash - strip the last slash and everything following it before matching
        Further flags may be agreed between connection manager and client
        implementations as necessary.

        Returns:
        an array of strings of policy flags to follow when comparing contact IDs
        """
        return []


class ConnectionInterfaceAliasing(dbus.service.Interface):
    """
    An interface on connections to support protocols where contacts have an
    alias which they can change at will, but their underlying unique identifier
    remains unchanged. Provides a method for the user to set their own alias,
    and a signal which should be emitted when a contact's alias is changed
    or first discovered.
    """

    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_ALIASING)

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

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, UnknownContact
        """
        pass

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='s', out_signature='')
    def SetAlias(self, alias):
        """
        Request that the user's alias be changed. Success will be indicated by
        emitting an AliasUpdate signal.

        Parameters:
        alias - the new alias to set

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument, NotAvailable, PermissionDenied
        """
        pass


class ConnectionInterfaceCapabilities(dbus.service.Interface):
    """
    An interface for connections where it is possible to know what channel
    types may be requested before the request is made to the connection object.
    Each capability represents a commitment by the connection manager that it
    will ordinarily be able to create a channel when given a request with the
    given type and interfaces. The channel created by these requests may still
    implement other interfaces (such as the subject or password interfaces)
    which are not part of the capability.

    Capabilities can be pertaining to a certain contact, representing
    activities such as having a text chat or a voice call with the user, or can
    be on the connection itself, where they represent the ability to create
    channels for chat rooms or activities such as searching and room listing.
    When the group interface is included in a capability on a certain contact,
    this is an indication that the user may be invited into channels of this
    type.

    For example, a capability on a contact indicating you can have a private
    text chat with them would be:
     Type: org.freedesktop.Telepathy.Channel.Type.Text
     Interfaces: org.freedesktop.Telepathy.Channel.Interface.Individual

    A capability indicating that a contact could be invited into a named chat
    room:
     Type: org.freedesktop.Telepathy.Channel.Type.Text
     Interfaces: org.freedesktop.Telepathy.Channel.Interface.Named,
                 org.freedesktop.Telepathy.Channel.Interface.Group
    The same capability on the connection itself would indicate that the
    connection supports named chat rooms at all.

    A capability indicating that a contact can be invited into a multi-person
    audio or video call:
     Type: org.freedesktop.Telepathy.Channel.Type.StreamedMedia
     Interfaces: org.freedesktop.Telepathy.Channel.Interface.Group

    A capability indicating that the connection supports listing the available chat rooms:
     Type: org.freedesktop.Telepathy.Channel.Type.RoomList
    """
    def __init__(self):
        """
        Initialise the capabilities interface.
        """
        self._interfaces.add(CONN_INTERFACE_CAPABILITIES)
        self.caps = set()
        self.contact_caps = {}

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='', out_signature='a(sas)')
    def GetCapabilities(self):
        """
        Returns an array of capabilities for the connection.

        Returns:
        an array of structs containing:
            a string of channel types
            an array of strings of channel interface names

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.caps

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='s', out_signature='a(sas)')
    def GetContactCapabilities(self, contact):
        """
        Return an array of capabilities for a given contact on this connection.

        Returns:
        an array of structs containing:
            a string of channel types
            an array of strings of channel interface names

        Possible Errors:
        Disconnected, NetworkError, UnknownContact
        """
        if contact in self.contact_caps:
            return self.contact_caps[contact]
        else:
            return []

    @dbus.service.signal(CONN_INTERFACE_CAPABILITIES, signature='a(sas)a(sas)')
    def CapabilitiesChanged(self, added, removed):
        """
        Announce the availability or the removal of capabilities on the
        connection.

        Parameters:
        added - an array of structs as returned by GetCapabilities
        removed - an array of structs as returned by GetCapabilities
        """
        self.caps.update(added)
        self.caps.difference_update(removed)

    @dbus.service.signal(CONN_INTERFACE_CAPABILITIES, signature='sa(sas)a(sas)')
    def ContactCapabilitiesChanged(self, contact, added, removed):
        """
        Announce the availability or the removal of capabilities for a given
        contact.

        Parameters:
        contact - the contact in question
        added - an array of structs as returned by GetContactCapabilities
        removed - an array of structs as returned by GetContactCapabilities
        """
        if not contact in self.contact_caps:
            self.contact_caps[contact] = set()

        self.caps.update(added)
        self.caps.difference_update(removed)


class ConnectionInterfaceContactInfo(dbus.service.Interface):
    """
    An interface for requesting information about a contact on a given
    connection. Information is returned as a vCard represented as an XML
    string, in the format defined by JEP-0054: vcard-temp specifiation
    from the Jabber Software Foundation (this is derived from the
    aborted IETF draft draft-dawson-vcard-xml-dtd-01).

    Implementations using PHOTO or SOUND elements should use the URI encoding
    where possible, and not provide base64 encoded data to avoid unnecessary
    bus traffic. Clients should not implement support for these encoded forms.
    A separate interface will be provided for transferring user avatars.

    The following extended element names are also added to represent
    information from other systems which are not based around vCards:
     USERNAME - the username of the contact on their local system (used on IRC for example)
     HOSTNAME - the fully qualified hostname, or IPv4 or IPv6 address of the contact in dotted quad or colon-separated form
    """
    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_CONTACT_INFO)

    @dbus.service.method(CONN_INTERFACE_CONTACT_INFO, in_signature='s', out_signature='')
    def RequestContactInfo(self, contact):
        """
        Request information for a given contact. The function will return
        after a GotContactInfo signal has been emitted for the contact, or
        an error returned.

        Parameters:
        contact - a string identifier for the contact to request info for

        Possible Errors:
        Disconnected, NetworkError, UnknownContact, PermissionDenied, NotAvailable
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_CONTACT_INFO, signature='ss')
    def GotContactInfo(self, contact, vcard):
        """
        Emitted when information has been received from the server with
        the details of a particular contact.

        Parameters:
        contact - a string of the contact ID on the server
        vcard - the XML string containing their vcard information
        """
        pass


class ConnectionInterfaceForwarding(dbus.service.Interface):
    """
    A connection interface for services which can signal to contacts
    that they should instead contact a different user ID, effectively
    forward all incoming communication channels to another contact on
    the service.
    """
    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_FORWARDING)
        self.forwarding = ''

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='', out_signature='s')
    def GetForwarding(self):
        """
        Returns the current forwarding ID, or blank if none is set.

        Returns:
        a string contact ID to whom incoming communication is forwarded

        Possible Errors:
        Disconnected, NetworkError, NotAvailable
        """
        return self.forwarding

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='s', out_signature='')
    def SetForwarding(self, forward_to):
        """
        Set a contact ID to forward incoming communications to. An empty
        string disables forwarding.

        Parameters:
        forward_to - a contact ID to forward incoming communications to

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied, NotAvailable, UnknownContact
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_FORWARDING, signature='s')
    def ForwardingChanged(self, forward_to):
        """
        Emitted when the forwarding contact for this connection has been
        changed. An empty string indicates forwarding is disabled.

        Parameters:
        forward_to - a string contact ID to forward communication to
        """
        self.forwarding = forward_to


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
        self._interfaces.add(CONN_INTERFACE_PRESENCE)

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='', out_signature='a{s(ubba{ss})}')
    def GetStatuses(self):
        """
        Get a dictionary of the valid presence statuses for this connection.

        Returns:
        a dictionary of string identifiers mapped to a struct for each status, containing:
        - a type value from one of the values above
        - a boolean to indicate if this status may be set on yourself
        - a boolean to indicate if this is an exclusive status which you may not set alongside any other
        - a dictionary of valid optional string argument names mapped to their types

        Possible Errors:
        Disconnected, NetworkError
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='as', out_signature='')
    def RequestPresence(self, contacts):
        """
        Request the presence for contacts on this connection. A PresenceUpdate
        signal will be emitted when they are received. This is not the same as
        subscribing to the presence of a contact, which must be done using the
        'subscription' Channel.Type.ContactList, and on some protocols presence
        information may not be available unless a subscription exists.

        Parameters:
        contacts - an array of the contacts whose presence should be obtained

        Possible Errors:
        Disconnected, NetworkError, UnknownContact, PermissionDenied, NotAvailable (if the presence of the requested contacts is not reported to this connection)
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

        Possible Errors:
        Disconnected, NetworkError, NotImplemented (this protocol has no concept of idle time)
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

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument, NotAvailable, PermissionDenied
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='', out_signature='')
    def ClearStatus(self):
        """
        Request that all of a user's presence statuses be removed. Be aware
        that this request may simply result in the statuses being replaced by a
        default available status. Changes will be indicated by PresenceUpdate
        signals being emitted.

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied
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

        Possible Errors:
        Disconnected, NetworkError, InvalidArgument, NotAvailable, PermissionDenied
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='s', out_signature='')
    def RemoveStatus(self, status):
        """
        Request that the given presence status is no longer published for the
        user. Changes will be indicated by PresenceUpdate signals being emitted.

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied
        """
        pass


class ConnectionInterfacePrivacy(dbus.service.Interface):
    """
    An interface to support getting and setting privacy modes to configure
    situations such as not being contactable by people who are not on your
    subscribe list. If this interface is not implemented, the default can be
    presumed to be allow-all (as defined in GetPrivacyModes).
    """
    def __init__(self, modes):
        """
        Initialise privacy interface.

        Parameters:
        modes - a list of privacy modes available on this interface
        """
        self._interfaces.add(CONN_INTERFACE_PRIVACY)
        self.mode = ''
        self.modes = modes

    @dbus.service.method(CONN_INTERFACE_PRIVACY, in_signature='', out_signature='as')
    def GetPrivacyModes(self):
        """
        Returns the privacy modes available on this connection. The following
        well-known names should be used where appropriate:
         allow-all - any contact may initiate communication
         allow-specified - only contacts on your 'allow' list may initiate communication
         allow-subscribed - only contacts on your subscription list may initiate communication

        Returns:
        an array of valid privacy modes for this connection
        """
        return self.modes

    @dbus.service.method(CONN_INTERFACE_PRIVACY, in_signature='', out_signature='s')
    def GetPrivacyMode(self):
        """
        Return the current privacy mode, which must be one of the values
        returned by GetPrivacyModes.

        Returns:
        a string of the current privacy mode

        Possible Errors:
        Disconnected, NetworkError
        """
        return self.mode

    @dbus.service.method(CONN_INTERFACE_PRIVACY, in_signature='s', out_signature='')
    def SetPrivacyMode(self, mode):
        """
        Request that the privacy mode be changed to the given value, which
        must be one of the values returned by GetPrivacyModes. Success is
        indicated by the method returning and the PrivacyModeChanged
        signal being emitted.

        Parameters:
        mode - the desired privacy mode

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied, InvalidArgument
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_PRIVACY, signature='s')
    def PrivacyModeChanged(self, mode):
        """
        Emitted when the privacy mode is changed or the value has been
        initially received from the server.

        Parameters:
        mode - the current privacy mode
        """
        self.mode = mode

class ConnectionInterfaceRenaming(dbus.service.Interface):
    """
    An interface on connections to support protocols where the unique identifiers
    of contacts can change.
    """
    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_RENAMING)

    @dbus.service.method(CONN_INTERFACE_RENAMING, in_signature='s', out_signature='')
    def RequestRename(self, name):
        """
        Request that the users own identifier is changed on the server. Success
        is indicated by a Renamed signal being emitted.

        Parameters:
        name - a string of the desired identifier

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_RENAMING, signature='ss')
    def Renamed(self, original, new):
        """
        Emitted when the unique identifier of a contact on the server changes.

        Parameters:
        original - a string of the original identifier
        new - a string of the new identifier
        """
        pass
