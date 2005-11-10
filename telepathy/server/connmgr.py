#!/usr/bin/env python

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
    service name where the connection object can be found is returned. The
    connection manager may then remove itself from its well-known bus name,
    causing a new connection manager to be activated when somebody attempts to
    make a new connection.
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
        self.NewConnection(conn._name.get_name(), conn._object_path, conn._proto, conn._account)

    def disconnected(self, conn):
        """
        Remove a connection from the list of connections.
        """
        self._connections.remove(conn)
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
         sip - Session Initiation Protocol (SIP)
         trepia - Trepia
         yahoo - Yahoo! Messenger
         zephyr - Zephyr

        Returns:
        a list of string protocol identifiers supported by this manager
        """
        return self._protos.keys()

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='s', out_signature='a{ss}')
    def GetProtocolParameters(self, proto):
        """
        Get a list of the parameter names and types which are understood
        by the connection manager for a given protocol.

        Parameters:
        proto - the protocol identifier

        Returns:
        an dictionary mapping parameter identifiers to type signatures

        Potential Errors:
        NotImplemented (the requested protocol is not supported by this manager)
        """
        if proto in self._protos:
            if getattr(self._protos[proto], '_protocol_parameters', None):
                return self._protos[proto]._protocol_parameters
            else:
                return {}
        else:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

    @dbus.service.method(CONN_MGR_INTERFACE, in_signature='ssa{sv}', out_signature='so')
    def Connect(self, proto, account, parameters):
        """
        Connect to a given account on a given protocol with the given
        parameters. The method returns the bus name and the object path
        where the new Connection object can be found, which should
        be in the 'connecting' state.

        The parameters accepted by a protocol are specified
        in a file shipped by the connection manager, and can be retrieved
        at run-time with the GetProtocolParameters method. The client
        must have prior knowledge of the meaning of these parameters,
        so the following well-known names and types should be used where
        relevant:

        s:server - a fully qualified domain name or numeric IPv4 or IPv6
        address. Using the fully-qualified domain name form is recommended
        whenever possible. If this parameter is specified and the account
        for that protocol also specifies a server, this parameter should
        override that in the user id.

        q:port - a TCP or UDP port number. If this parameter is specified
        and the account for that protocol also specifies a port, this
        parameter should override that in the account.

        s:password - A password associated with the account.

        s:proxy-server - A URI for a proxy server to use for this connection.

        b:require-encryption - Require encryption for this connection. A
        connection should fail to connect if require-encryption is set
        and an encrypted connection is not possible.

        b:register - This account should be created on the server if it
        does not already exist.

        s:ident - The local username to report to the server if
        necessary, such as in IRC.

        s:fullname - The user's full name if the service requires this
        when authenticating or registering.

        s:authentication-realm - A string identifier for your authentication
        realm, if necessary.

        s:authentication-username - A username to use for authentication, if 
        necessary.

        s:authentication-type - A string representation of authentication type,
        such as 'Digest'.

        Parameters:
        proto - the protocol identifier
        account - the user's account on this protocol
        parameters - a dictionary mapping parameter name to the variant boxed value

        Returns:
        a D-Bus service name where the new Connection object can be found
        the D-Bus object path to the Connection on this service

        Potential Errors:
        NetworkError, NotImplemented (unknown protocol), InvalidArgument (unrecognised connection parameters)
        """
        if proto in self._protos:
            conn = self._protos[proto](self, account, parameters)
            self.connected(conn)
            return (conn._name.get_name(), conn._object_path)
        else:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

    @dbus.service.signal(CONN_MGR_INTERFACE, signature='soss')
    def NewConnection(self, bus_name, object_path, proto, account):
        """
        Emitted when a new Connection object is created.

        Parameters:
        bus_name - the D-Bus service where the connection object can be found
        object_path - the object path of the Connection object on this service
        proto - the identifier for the protocol this connection uses
        account - the identifier for the user's account on this protocol
        """
        pass
