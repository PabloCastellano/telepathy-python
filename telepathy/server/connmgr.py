# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005, 2006 Collabora Limited
# Copyright (C) 2005, 2006 Nokia Corporation
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

from telepathy.errors import NotImplemented
from telepathy.interfaces import CONN_MGR_INTERFACE

from telepathy._generated.Connection_Manager \
        import ConnectionManager as _ConnectionManager

class ConnectionManager(_ConnectionManager):
    def __init__(self, name):
        """
        Initialise the connection manager.
        """
        bus_name = 'org.freedesktop.Telepathy.ConnectionManager.%s' % name
        object_path = '/org/freedesktop/Telepathy/ConnectionManager/%s' % name
        _ConnectionManager.__init__(self, dbus.service.BusName(bus_name), object_path)

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
        return self._protos.keys()

    def RequestConnection(self, proto, parameters):
        if proto in self._protos:
            conn = self._protos[proto](self, parameters)
            self.connected(conn)
            return (conn._name.get_name(), conn._object_path)
        else:
            raise NotImplemented('unknown protocol %s' % proto)
