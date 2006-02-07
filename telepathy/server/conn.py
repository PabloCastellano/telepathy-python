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
import re
import weakref

from telepathy import *
from handle import Handle

class Connection(dbus.service.Object):
    """
    This models a connection to a single user account on a communication
    service. Its basic capability is to provide the facility to request and
    receive channels of differing types (such as text channels or streaming
    media channels) which are used to carry out further communication.

    A Connection object should always endeavour to remain connected to the
    server until instructed to the contrary with the Disconnect method.

    As well as the methods and signatures below, arbitrary interfaces may be
    provided by the Connection object to represent extra connection-wide
    functionality, such as the Connection.Interface.Presence for receiving and
    reporting presence information, and Connection.Interface.Aliasing for
    connections where contacts may set and change an alias for themselves.
    These interfaces can be discovered using GetInterfaces after the
    connection, has been established and must not change subsequently at
    runtime.

    Contacts, rooms, and server-stored lists (such as subscribed contacts,
    block lists, or allow lists) on a service are all represented by
    immutable handles, which are unsigned non-zero integers which are valid
    only for the lifetime of the connection object, and are used throughout the
    protocol where these entities are represented, allowing simple testing of
    equality within clients. Connection manager implementations should
    reference count these handles to determine if they are in use either by any
    active clients or any open channels, and may deallocate them when this
    ceases to be true. Clients may request handles of a given type and name
    with the RequestHandle method, inspect the entity name of a handle
    with the InspectHandle method, keep a given handle from being released
    with HoldHandle, and notify that they are no longer storing a handle with
    ReleaseHandle.
    """
    def __init__(self, proto, account):
        """
        Parameters:
        proto - the name of the protcol this conection should be handling.
        account - a protocol-specific account name
        account - a unique identifier for this account which is used to identify this connection
        """
        clean_account = re.sub('[^a-zA-Z0-9_]', '_', account)
        bus_name = dbus.service.BusName('org.freedesktop.Telepathy.Connection.' + clean_account)
        object_path = '/org/freedesktop/Telepathy/Connection/' + clean_account
        dbus.service.Object.__init__(self, bus_name, object_path)

        # monitor clients dying so we can release handles
        self._bus.add_signal_receiver(self.name_owner_changed_callback,
                                      'NameOwnerChanged',
                                      'org.freedesktop.DBus',
                                      'org.freedesktop.DBus',
                                      '/org/freedesktop/DBus')

        self._proto = proto

        self._status = CONNECTION_STATUS_CONNECTING
        self._interfaces = set()

        self._handles = weakref.WeakValueDictionary()
        self._next_handle_id = 1
        self._client_handles = {}

        self._channels = set()
        self._next_channel_id = 0

    def check_parameters(self, parameters):
        """
        Uses the values of self._mandatory_parameters and
        self._optional_parameters to validate and type check all of the
        provided parameters, and check all mandatory parameters are present.
        Sets defaults according to the defaults if the client has not
        provided any.
        """
        for (parm, value) in parameters.iteritems():
            if parm in self._mandatory_parameters.keys():
                sig = self._mandatory_parameters[parm]
            elif parm in self._optional_parameters.keys():
                sig = self._optional_parameters[parm]
            else:
                raise InvalidArgument('unknown parameter name %s' % parm)

            if sig == 's':
                if not isinstance(value, unicode):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected a string' % (parm, type(value)))
            elif sig == 'q':
                if not isinstance(value, int):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an int' % (parm, type(value)))
            elif sig == 'b':
                if not isinstance(value, bool):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an boolean' % (parm, type(value)))
            else:
                raise TypeError('unknown type signature %s in protocol parameters' % type)

        for (parm, value) in self._parameter_defaults.iteritems():
            if parm not in parameters:
                parameters[parm] = value

        missing = set(self._mandatory_parameters.keys()).difference(parameters.keys())
        if missing:
            raise InvalidArgument('required parameters %s not given' % missing)

    def check_connected(self):
        if self._status != CONNECTION_STATUS_CONNECTED:
            raise Disconnected('method cannot be called unless status is CONNECTION_STATUS_CONNECTED')

    def check_handle(self, handle_type, handle):
        if (handle_type, handle) not in self._handles:
            print "Connection.check_handle", handle, handle_type, self._handles.keys()
            print str(list( [ self._handles[x] for x in self._handles.keys() ] ) )
            raise InvalidHandle('handle number %s not valid' % handle)

    def check_handle_type(self, type):
        if (type < CONNECTION_HANDLE_TYPE_CONTACT or
            type > CONNECTION_HANDLE_TYPE_LIST):
            raise InvalidArgument('handle type %s not known' % type)

    def get_handle_id(self):
        id = self._next_handle_id
        self._next_handle_id += 1
        return id

    def add_client_handle(self, handle, sender):
        if sender in self._client_handles:
            self._client_handles[sender].add((handle.get_type(), handle))
        else:
            self._client_handles[sender] = set([(handle.get_type(), handle)])

    def name_owner_changed_callback(self, name, old_owner, new_owner):
        # when name and old_owner are the same, and new_owner is
        # blank, it is the client itself releasing its name... aka exiting
        if (name == old_owner and new_owner == "" and name in self._client_handles):
            print "deleting handles for", name
            del self._client_handles[name]

    def set_self_handle(self, handle):
        self._self_handle = handle

    def get_channel_path(self):
        ret = '%s/channel%d' % (self._object_path, self._next_channel_id)
        self._next_channel_id += 1
        return ret

    def add_channel(self, channel, handle, suppress_handler):
        """ add a new channel and signal its creation""" 
        self._channels.add(channel)
        self.NewChannel(channel._object_path, channel._type, handle.get_type(), handle.get_id(), suppress_handler)

    def remove_channel(self, channel):
        self._channels.remove(channel)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        """
        Get the optional interfaces supported by the connection. Not valid
        until the connection has been established (GetState returns
        CONNECTION_STATE_CONNECTED).

        Returns:
        an array of D-Bus interface names

        Potential Errors:
        Disconnected
        """
        self.check_connected()
        return self._interfaces

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        """
        Get the protocol this connection is using.

        Returns:
        a string identifier for the protocol

        Potential Errors:
        Disconnected
        """
        return self._proto

    @dbus.service.method(CONN_INTERFACE, in_signature='uu', out_signature='s')
    def InspectHandle(self, handle_type, handle):
        """
        For a given handle representing a contact, room or list entity on
        this connection, return a string representation of the entity name.

        Parameters:
        handle_type - an integer handle type (as defined in RequestHandle)
        handle - an integer handle number

        Returns:
        a string entity name

        Potential Errors:
        Disconnected, InvalidArgument (the given type is not valid),
        InvalidHandle (the given handle is not valid on this connection)
        """
        self.check_connected()
        self.check_handle_type(handle_type)
        self.check_handle(handle_type, handle)
        hand = self._handles[handle_type, handle]
        return hand.get_name()

    @dbus.service.method(CONN_INTERFACE, in_signature='us', out_signature='u', sender_keyword='sender')
    def RequestHandle(self, handle_type, name, sender):
        """
        Request a handle from the connection manager which represents a
        contact, room or server-stored list on the service. The connection
        manager should record that this handle is in use by the client who
        invokes this method, and must not deallocate the handle until the
        client disconnects from the bus or calls the ReleaseHandle method.
        Where the name refers to an entity that already has a handle in this
        connection manager, this handle should be returned instead. The handle
        number 0 must not be returned by the connection manager.

        The type value may be one of the following:
        0 - CONNECTION_HANDLE_TYPE_NONE
        1 - CONNECTION_HANDLE_TYPE_CONTACT
        2 - CONNECTION_HANDLE_TYPE_ROOM
        3 - CONNECTION_HANDLE_TYPE_LIST

        Parameters:
        type - an integer handle type
        name - the name of the entity to request a handle for

        Returns:
        a non-zero integer handle number

        Potential Errors:
        Disconnected, InvalidArgument (the given type is not valid), NotAvailable (the given name is not a valid entity of the given type)
        """
        self.check_connected()
        self.check_handle_type(handle_type)

        id = self.get_handle_id()
        handle = Handle(id, handle_type, name)
        self._handles[handle_type, id] = handle
        self.add_client_handle(handle, sender)

        return id

    @dbus.service.method(CONN_INTERFACE, in_signature='uu', out_signature='', sender_keyword='sender')
    def HoldHandle(self, handle_type, handle, sender):
        """
        Notify the connection manger that your client is holding a copy
        of a handle which may not be in use in any existing channel or
        list, and was not obtained by using the RequestHandle method. For
        example, a handle observed in an emitted signal, or displayed
        somewhere in the UI that is not associated with a channel. The
        connection manager must not deallocate a handle where any clients
        have used this method to indicate it is in use until the ReleaseHandle
        method is called, or the clients disappear from the bus.

        Parameters:
        handle_type - an integer representing the handle type
        handle - an integer handle to hold

        Potential Errors:
        Disconnected, InvalidArgument (the handle type is invalid),
        InvalidHandle (the given handle is not valid)
        """
        self.check_connected()
        self.check_handle_type(handle_type)
        self.check_handle(handle_type, handle)

        hand = self._handles[handle_type, handle]
        self.add_client_handle(hand, sender)

    @dbus.service.method(CONN_INTERFACE, in_signature='uu', out_signature='')
    def ReleaseHandle(self, handle_type, handle):
        """
        Explicitly notify the connection manager that your client is no
        longer holding any references to the given handle, and that it
        may be deallocated if it is not held by any other clients or
        referenced by any existing channels.

        Parameters:
        handle_type 
        handle - an integer handle being held by the client

        Potential Errors:
        Disconnected, InvalidArgument (the given handle type is invalid),
        InvalidHandle (the given handle is not valid), NotAvailable (the given
        handle is not held by this client)
        """
        self.check_connected()
        self.check_handle_type(handle_type)
        self.check_handle(handle_type, handle)

        hand = self._handles[handle_type, handle]
        if sender in self._client_handles:
            if hand in self._client_handles[sender]:
                self._client_handles[sender].remove(hand)
            else:
                raise NotAvailable('client is not holding handle %s' % handle)
        else:
            raise NotAvailable('client does not hold any handles')

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetSelfHandle(self):
        """
        Get the handle which represents the user on this connection, which will
        remain valid for the lifetime of this connection or until the user's
        identifier changes. This is always a CONTACT type handle.

        Returns:
        an integer handle representing the user

        Potential Errors:
        Disconnected
        """
        self.check_connected()
        return self._self_handle

    @dbus.service.signal(CONN_INTERFACE, signature='uu')
    def StatusChanged(self, status, reason):
        """
        Emitted when the status of the connection changes.  All states and
        reasons have numerical values, as defined here:

        0 - CONNECTION_STATUS_CONNECTED
            The connection is alive and all methods are available.

        1 - CONNECTION_STATUS_CONNECTING
            The connection has not yet been established, or has been
            severed and reconnection is being attempted. Some methods may fail
            until the connection has been established.

        2 - CONNECTION_STATUS_DISCONNECTED
            The connection has been severed and no method calls are
            valid. The object may be removed from the bus at any time.

        The reason should be one of the following:

        0 - CONNECTION_STATUS_REASON_NONE_SPECIFIED
            There is no reason set for this state change.

        1 - CONNECTION_STATUS_REASON_REQUESTED
            The change is in response to a user request.

        2 - CONNECTION_STATUS_REASON_NETWORK_ERROR
            There was an error sending or receiving on the network socket.

        3 - CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
            The username or password was invalid.

        4 - CONNECTION_STATUS_REASON_ENCRYPTION_ERROR
            There was an error negotiating SSL on this connection, or
            encryption was unavailable and require-encryption was set when the
            connection was created.

        5 - CONNECTION_STATUS_REASON_NAME_IN_USE
            Someone is already connected to the server using the name
            you are trying to connect with.

        Parameters:
        status - an integer indicating the new status
        reason - an integer indicating the reason for the status change
        """
        self._status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetStatus(self):
        """
        Get the current status as defined in the StatusChanged signal.

        Returns:
        an integer representing the current status
        """
        return self._status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='')
    def Disconnect(self):
        """
        Request that the connection be closed.

        Potential Errors:
        Disconnected
        """
        self.check_connected()

    @dbus.service.signal(CONN_INTERFACE, signature='osuub')
    def NewChannel(self, object_path, channel_type, handle_type, handle, suppress_handler):
        """
        Emitted when a new Channel object is created, either through user
        request or incoming information from the service. The suppress_handler
        boolean indicates if the channel was requested by an existing client,
        or is an incoming communication and needs to have a handler launched.

        Parameters:
        object_path - a D-Bus object path for the channel object on this service
        channel_type - a D-Bus interface name representing the channel type
        handle_type - an integer representing the type of handle this channel communicates with, which is zero if no handle is specified
        handle - a handle indicating the specific contact, room or list this channel communicates with, or zero if it is an anonymous channel
        suppress_handler - a boolean indicating that the channel was requested by a client that intends to display it to the user, so no handler needs to be launched
        """
        pass

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='a(osuu)')
    def ListChannels(self):
        """
        List all the channels which currently exist on this connection.

        Returns:
        an array of structs containing:
            a D-Bus object path for the channel object on this service
            a D-Bus interface name representing the channel type
            an integer representing the handle type this channel communicates with, or zero
            an integer handle representing the contact, room or list this channel communicates with, or zero

        Potential Errors:
        Disconnected
        """
        self.check_connected()
        ret = []
        for channel in self._channels:
            chan = (channel._object_path, channel._type, channel._handle.get_type(), channel._handle)
            ret.append(chan)
        return ret

    @dbus.service.method(CONN_INTERFACE, in_signature='suub', out_signature='o')
    def RequestChannel(self, type, handle_type, handle, suppress_handler):
        """
        Request a channel satisfying the specified type and communicating with
        the contact, room or list indicated by the given handle. The handle may
        be zero to request the creation of a new, empty channel, which may or
        may not be available depending on the protocol and channel type. May
        return an existing channel object, create a new channel, or fail if the
        request cannot be satisfied.

        Parameters:
        type - a D-Bus interface name representing base channel type
        handle_type - an integer representing the handle type, or zero if no handle is being specified
        handle - an integer handle representing a contact, room or list, or zero
        suppress_handler - a boolean indicating that the requesting client intends to take responsibility for displaying the channel to the user, so that no other handler needs to be launched

        Returns:
        the D-Bus object path for the channel created or retrieved

        Possible Errors:
        Disconnected, NetworkError, NotImplemented (unknown channel type), InvalidHandle (the given handle does not exist), NotAvailable (the requested channel type cannot be created with the given handle)
        """
        self.check_connected()
        raise NotImplemented('unknown channel type %s' % type)


class ConnectionInterfaceAliasing(dbus.service.Interface):
    """
    An interface on connections to support protocols where contacts have an
    alias which they can change at will, but their underlying unique identifier
    remains unchanged. Provides a method for the user to set their own alias,
    and a signal which should be emitted when a contact's alias is changed
    or first discovered.

    On connections where the user is allowed to set aliases for contacts and
    store them on the server, the GetAliasFlags method will have the
    CONNECTION_ALIAS_FLAG_USER_SET flag set, and the SetAlias method
    may be called on contact handles other than the user themselves.
    """

    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_ALIASING)

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='', out_signature='u')
    def GetAliasFlags(self):
        """
        Return a logical OR of flags detailing the behaviour of aliases on this
        server. Valid flags are:
        1 - CONNECTION_ALIAS_FLAG_USER_SET
            The aliases of contacts on this server are specified by the user
            of the service, not the contacts themselves. This is the case on
            eg Jabber.

        Returns:
        a integer with a logical OR of flags as defined above

        Potential Errors:
        Disconnected
        """
        return 0

    @dbus.service.signal(CONN_INTERFACE_ALIASING, signature='us')
    def AliasUpdate(self, contact, alias):
        """
        Signal emitted when a contact's alias (or that of the user) is changed.

        Parameters:
        contact - the handle representing the contact
        alias - the new alias
        """
        pass

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='u', out_signature='s')
    def RequestAlias(self, contact):
        """
        Request the value of a contact's alias (or that of the user themselves).

        Parameters:
        contact - the handle representing a contact

        Returns:
        a string representing the contact's alias

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, InvalidHandle
        """
        pass

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='us', out_signature='')
    def SetAlias(self, contact, alias):
        """
        Request that the alias of the given contact be changed. Success will be
        indicated by emitting an AliasUpdate signal. On connections where the
        CONNECTION_ALIAS_FLAG_USER_SET flag is not set, this method will only
        ever succeed if contact is the user's own handle (as returned by
        GetSelfHandle on the Connection interface).

        Parameters:
        contact - the handle of the contact whose alias to set
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
    given type and handle.

    Capabilities can be pertaining to a certain contact handle, representing
    activities such as having a text chat or a voice call with the user, or can
    be on the connection itself (where the handle will be zero), where they
    represent the ability to create channels for chat rooms or activities
    such as searching and room listing.

    The following capability types are defined:
    0 - CONNECTION_CAPABILITY_TYPE_CREATE
        The given channel type and handle can be given to RequestChannel to
        create a new channel of this type.
    1 - CONNECTION_CAPABILITY_TYPE_INVITE
        The given contact can be invited to an existing channel of this type.

    This interface also provides for user interfaces notifying the connection
    manager of what capabilities to advertise for the user. This is done by
    using the AdvertiseCapabilities method, and deals only with the interface
    names of channel types which are implemented by available client processes.
    """
    def __init__(self):
        """
        Initialise the capabilities interface.
        """
        self._interfaces.add(CONN_INTERFACE_CAPABILITIES)
        self._own_caps = set()
        self._caps = {}

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='u', out_signature='a(su)')
    def GetCapabilities(self, handle):
        """
        Returns an array of capabilities for the given contact handle, or
        the connection itself (where handle is zero).

        Parameters:
        handle - a contact handle for this connection, or zero for channel types available on the connection itself

        Returns:
        an array of structs containing:
            a D-Bus interface name representing the channel type
            an integer indicating the capability type

        Possible Errors:
        Disconnected, NetworkError, InvalidHandle (the handle does not represent a contact), PermissionDenied
        """
        if (handle != 0 and handle not in self._handles):
            raise InvalidHandle
        elif handle in self._caps:
            return self._caps[handle]
        else:
            return []

    @dbus.service.signal(CONN_INTERFACE_CAPABILITIES, signature='ua(su)a(su)')
    def CapabilitiesChanged(self, handle, added, removed):
        """
        Announce the availability or the removal of capabilities on the
        given handle, or on the connection itself if the handle is zero.

        Parameters:
        handle - the handle of the contact with these capabilities, or zero if the capability is on the connection itself
        added - an array of structs as returned by GetCapabilities
        removed - an array of structs as returned by GetCapabilities
        """
        if handle not in self._caps:
            self._caps[handle] = set()

        self._caps[handle].update(added)
        self._caps[handle].difference_update(removed)

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='asas', out_signature='')
    def AdvertiseCapabilities(self, add, remove):
        """
        Used by user interfaces to indicate which channel types they are able
        to handle on this connection. Because these may be provided by
        different client processes, this method accepts channel types to add
        and remove from the set already advertised on this connection. The type
        of advertised capabilities (create versus invite) is protocol-dependent
        and hence cannot be set by the this method.

        Upon a successful invocation of this method, the CapabilitiesChanged
        signal will be emitted for the user's own handle (as returned by
        GetSelfHandle) the by the connection manager to indicate the changes
        that have been made.  This signal should also be monitored to ensure
        that the set is kept accurate - for example, a client may remove
        capabilities when it exits which are still provided by another client.

        Parameters:
        add - an array of D-Bus interface names of channel types to add
        remove - an array of D-Bus interface names of channel types to remove

        Potential Errors:
        NetworkError, Disconnected
        """
        # no-op implementation
        self.AdvertisedCapabilitiesChanged(self._self_handle, add, remove)


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

    @dbus.service.method(CONN_INTERFACE_CONTACT_INFO, in_signature='u', out_signature='')
    def RequestContactInfo(self, contact):
        """
        Request information for a given contact. The function will return
        after a GotContactInfo signal has been emitted for the contact, or
        an error returned.

        Parameters:
        contact - an integer handle for the contact to request info for

        Possible Errors:
        Disconnected, NetworkError, InvalidHandle, PermissionDenied, NotAvailable
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_CONTACT_INFO, signature='us')
    def GotContactInfo(self, contact, vcard):
        """
        Emitted when information has been received from the server with
        the details of a particular contact.

        Parameters:
        contact - an integer handle of the contact ID on the server
        vcard - the XML string containing their vcard information
        """
        pass


class ConnectionInterfaceForwarding(dbus.service.Interface):
    """
    A connection interface for services which can signal to contacts
    that they should instead contact a different user ID, effectively
    forwarding all incoming communication channels to another contact on
    the service.
    """
    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_FORWARDING)
        self._forwarding_handle = 0

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='', out_signature='u')
    def GetForwardingHandle(self):
        """
        Returns the current forwarding contact handle, or zero if none is set.

        Returns:
        an integer contact handle to whom incoming communication is forwarded

        Possible Errors:
        Disconnected, NetworkError, NotAvailable
        """
        return self._forwarding_handle

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='u', out_signature='')
    def SetForwardingHandle(self, forward_to):
        """
        Set a contact handle to forward incoming communications to. A zero
        handle disables forwarding.

        Parameters:
        forward_to - an integer contact handle to forward incoming communications to

        Possible Errors:
        Disconnected, NetworkError, PermissionDenied, NotAvailable, InvalidHandle
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_FORWARDING, signature='u')
    def ForwardingChanged(self, forward_to):
        """
        Emitted when the forwarding contact handle for this connection has been
        changed. An zero handle indicates forwarding is disabled.

        Parameters:
        forward_to - an integer contact handle to forward communication to
        """
        self._forwarding_handle = forward_to


class ConnectionInterfacePresence(dbus.service.Interface):
    """
    This interface is for services which have a concept of presence which can
    be published for yourself and monitored on your contacts. Telepathy's
    definition of presence based on that used by the Galago project
    (see http://www.galago-project.org/).

    Presence on an individual (yourself or one of your contacts) is modelled as
    an last activity time along with a set of zero or more statuses, each of
    which may have arbitrary key/value parameters. Valid statuses are defined
    per connection, and a list of them can be obtained with the GetStatuses
    method.

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
    numerical type value which can be used by the client to classify even
    unknown statuses into different fundamental types:
    1 - CONNECTION_PRESENCE_TYPE_OFFLINE
    2 - CONNECTION_PRESENCE_TYPE_AVAILABLE
    3 - CONNECTION_PRESENCE_TYPE_AWAY
    4 - CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY
    5 - CONNECTION_PRESENCE_TYPE_HIDDEN

    These numerical types exist so that even if a client does not understand
    the string identifier being used, and hence cannot present the presence to
    the user to set on themselves, it may display an approximation of the
    presence if it is set on a contact.

    The dictionary of variant types allows the connection manager to exchange
    further protocol-specific information with the client. It is recommended
    that the string (s) argument 'message' be interpreted as an optional
    message which can be associated with a presence status.

    If the connection has a 'subscribe' contact list, PresenceUpdate signals
    should be emitted to indicate changes of contacts on this list, and should
    also be emitted for changes in your own presence. Depending on the
    protocol, the signal may also be emitted for others such as people with
    whom you are communicating, and any user interface should be updated
    accordingly.

    On some protocols, RequestPresence may only succeed on contacts on your
    'subscribe' list, and other contacts will cause a PermissionDenied error.
    On protocols where there is no 'subscribe' list, and RequestPresence
    succeeds, a client may poll the server intermittently to update any display
    of presence information.
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

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='au', out_signature='')
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
        Disconnected, NetworkError, InvalidHandle, PermissionDenied, NotAvailable (if the presence of the requested contacts is not reported to this connection)
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_PRESENCE, signature='a{u(ua{sa{sv}})}')
    def PresenceUpdate(self, presence):
        """
        This signal should be emitted when your own presence has been changed,
        or the presence of the member of any of the connection's channels has
        been changed, or when the presence requested by RequestPresence is available.

        Parameters:
        a dictionary of contact handles mapped to a struct containing:
        - a UNIX timestamp of the last activity time (in UTC)
        - a dictionary mapping the contact's current status identifiers to:
          a dictionary of optional parameter names mapped to their 
          variant-boxed values
        """
        pass

    @dbus.service.method(CONN_INTERFACE_PRESENCE, in_signature='u', out_signature='')
    def SetLastActivityTime(self, time):
        """
        Request that the recorded last activity time for the user be updated on
        the server.

        Parameters:
        time - a UNIX timestamp of the user's last activity time (in UTC)

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
        user. Changes will be indicated by PresenceUpdate signals being
        emitted. As with ClearStatus, removing a status may actually result in
        it being replaced by a default available status.

        Parameters:
        status - the string identifier of the status not to publish anymore for the user

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
        self._privacy_mode = ''
        self._privacy_modes = modes

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
        return self._privacy_modes

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
        return self._privacy_mode

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
        self._privacy_mode = mode


class ConnectionInterfaceRenaming(dbus.service.Interface):
    """
    An interface on connections to support protocols where the unique
    identifiers of contacts can change. Because handles are immutable,
    this is represented by a pair of handles, that representing the
    old name, and that representing the new one.
    """
    def __init__(self):
        self._interfaces.add(CONN_INTERFACE_RENAMING)

    @dbus.service.method(CONN_INTERFACE_RENAMING, in_signature='s', out_signature='')
    def RequestRename(self, name):
        """
        Request that the users own identifier is changed on the server. Success
        is indicated by a Renamed signal being emitted. A new handle will be
        allocated for the user's new identifier, and remain valid for the
        lifetime of the connection.

        Parameters:
        name - a string of the desired identifier

        Possible Errors:
        Disconnected, NetworkError, NotAvailable, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.signal(CONN_INTERFACE_RENAMING, signature='uu')
    def Renamed(self, original, new):
        """
        Emitted when the unique identifier of a contact on the server changes.

        Parameters:
        original - the handle of the original identifier
        new - the handle of the new identifier
        """
        pass

