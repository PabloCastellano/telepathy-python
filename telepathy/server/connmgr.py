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

import dbus
import dbus.service

from telepathy import *

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
    service name where the connection object can be found is returned. A
    manager which can only make one connection may then remove itself from its
    well-known bus name, causing a new connection manager to be activated when
    somebody attempts to make a new connection.
    """
    def __init__(self, name):
        """
        Initialise the connection manager.
        """
        bus_name = 'org.freedesktop.Telepathy.ConnectionManager.%s' % name
        object_path = '/org/freedesktop/Telepathy/ConnectionManager/%s' % name
        dbus.service.Object.__init__(self, dbus.service.BusName(bus_name), object_path)

        self._connections = set()
        self._protos = {}

    def __del__(self):
        print str(self._object_path), "deleted"
        dbus.service.Object.__del__(self)

    def connected(self, conn):
        """
        Add a connection to the list of connections, emit the appropriate
        signal.
        """
        self._connections.add(conn)
        self.NewConnection(conn._name.get_name(), conn._object_path, conn._proto)

    def disconnected(self, conn):
        """
        Remove a connection from the list of connections.
        """
        self._connections.remove(conn)
        del conn

        return False # when called in an idle callback

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
         sip - Session Initiation Protocol (SIP)
         trepia - Trepia
         yahoo - Yahoo! Messenger
         zephyr - Zephyr

        Returns:
        an dictionary mapping parameter identifiers to type signatures

        Potential Errors:
        NotImplemented (the requested protocol is not supported by this manager)
        """
        return self._protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='s', out_signature='a(susv)')
    def GetParameters(self, proto):
        """
        Get a list of the parameters which must or may be provided to the
        RequestConnection method when connecting to the given protocol,
        or registering (the boolean "register" parameter is available, and
        set to true).

        Parameters may have the following flags:
        1 - CONN_MGR_PARAM_FLAG_REQUIRED
            This parameter is required for connecting to the server.
        2 - CONN_MGR_PARAM_FLAG_REGISTER
            This parameter is required for registering an account on the
            server.

        Returns:
        an array of structs containing:
            a string parameter name
            a bitwise OR of the parameter flags (as defined above)
            a string D-Bus type signature
            a variant boxed default value

        Potential Errors:
        NotImplemented (the requested protocol is not supported by this manager)
        """
        pass

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='sa{sv}', out_signature='so')
    def RequestConnection(self, proto, parameters):
        """
        Request a Connection object representing a given account on a given
        protocol with the given parameters. The method returns the bus name
        and the object path where the new Connection object can be found, which
        should have the status of CONNECTION_STATUS_DISCONNECTED, to allow
        signal handlers to be attached before connecting is started with the
        Connect method.

        In order to allow Connection objects to be discovered by new clients,
        the bus name and object path must be of the form:
         /org/freedesktop/Telepathy/Connection/manager/proto/account
        And:
         org.freedesktop.Telepathy.Connection.manager.proto.account
        Where manager and proto are the identifiers for this manager and this
        protocol, and account is a series of elements formed such that any
        valid distinct connection instance on this protocol has a distinct
        name. This might be formed by including the server name followed by the
        user name, or on protocols where connecting multiple times is
        permissable, a per-connection identifier is also necessary to ensure
        uniqueness.

        The parameters which must and may be provided in the parameters
        dictionary can be discovered with the GetParameters method. These
        parameters, their types, and their default values may be cached
        in files so that all available connection managers do not need to be
        started to discover which protocols are available.

        To request values for these parameters from the user, a client must
        have prior knowledge of the meaning of the parameter names, so the
        following well-known names and types should be used where appropriate:

        s:account - the identifier for the user's account on the server.

        s:server - a fully qualified domain name or numeric IPv4 or IPv6
        address. Using the fully-qualified domain name form is recommended
        whenever possible. If this parameter is specified and the account
        for that protocol also specifies a server, this parameter should
        override that in the user id.

        q:port - a TCP or UDP port number. If this parameter is specified
        and the account for that protocol also specifies a port, this
        parameter should override that in the account.

        s:password - a password associated with the account.

        b:require-encryption - require encryption for this connection. A
        connection should fail to connect if require-encryption is set
        and an encrypted connection is not possible.

        b:register - this account should be created on the server if it
        does not already exist.

        s:ident - the local username to report to the server if
        necessary, such as in IRC.

        s:fullname - the user's full name if the service requires this
        when authenticating or registering.

        Parameters:
        proto - the protocol identifier
        parameters - a dictionary mapping parameter name to the variant boxed value

        Returns:
        a D-Bus service name where the new Connection object can be found
        the D-Bus object path to the Connection on this service

        Potential Errors:
        NetworkError, NotImplemented (unknown protocol), NotAvailable (the requested connection already appears to exist), InvalidArgument (unrecognised connection parameters)
        """
        if proto in self._protos:
            conn = self._protos[proto](self, parameters)
            self.connected(conn)
            return (conn._name.get_name(), conn._object_path)
        else:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

    @dbus.service.signal(CONN_MGR_INTERFACE, signature='sos')
    def NewConnection(self, bus_name, object_path, proto):
        """
        Emitted when a new Connection object is created.

        Parameters:
        bus_name - the D-Bus service where the connection object can be found
        object_path - the object path of the Connection object on this service
        proto - the identifier for the protocol this connection uses
        """
        pass
