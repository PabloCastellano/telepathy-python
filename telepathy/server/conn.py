#!/usr/bin/env python

import dbus
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


class ConnectionInterfaceContactInfo(dbus.service.Interface):
    """
    An interface for requesting information about a contact on a given
    connection. Information is returned as a vCard represented as an XML
    string, in the format defined by JEP-0054: vcard-temp speficiation
    from the Jabber Software Foundation (this is derived from the
    aborted IETF draft draft-dawson-vcard-xml-dtd-01).

    Implementations using PHOTO or SOUND elements should use the URI encoding
    where possible, and not provide base64 encoded data to avoid unnecessary
    bus traffic. Clients should not implement support for these encoded forms.
    A seperate interface will be provided for transferring user avatars.

    The following extended element names are also added to represent
    information from other systems which are not based around vCards:
     USERNAME - the username of the contact on their local system (used on IRC for example)
     HOSTNAME - the fully qualified hostname, or IPv4 or IPv6 address of the contact in dotted quad or colon-separated form
    """
    def __init__(self):
        self.interfaces.add(CONN_INTERFACE_CONTACT_INFO)

    @dbus.service.method(CONN_INTERFACE_CONTACT_INFO, in_signature='s', out_signature='')
    def RequestContactInfo(self, contact):
        """
        Request information for a given contact. The function will return
        after a GotContactInfo signal has been emitted for the contact, or
        an error returned.

        Parameters:
        contact - a string identifier for the contact to request info for
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
        self.interfaces.add(CONN_INTERFACE_FORWARDING)
        self.forwarding = ''

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='', out_signature='s')
    def GetForwarding(self):
        """
        Returns the current forwarding ID, or blank if none is set.

        Returns:
        a string contact ID to whom incoming communication is forwarded
        """
        return self.forwarding

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='s', out_signature='')
    def SetForwarding(self, forward_to):
        """
        Set a contact ID to forward incoming communications to. An empty
        string disables forwarding.

        Parameters:
        forward_to - a contact ID to forward incoming communications to
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

    @dbus.service.method(CONN_INTERFACE_RENAMING, in_signature='s', out_signature='')
    def RequestRename(self, name):
        """
        Request that the users own identifier is changed on the server. Success
        is indicated by a Renamed signal being emitted.

        Parameters:
        name - a string of the desired identifier
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
