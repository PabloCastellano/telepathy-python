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

"""
The registry of managers takes the form of any number of .manager files, which
are searched for in /usr/share/telepathy/services or in ~/.telepathy.

.manager files should have an initial stanza of the form:

[ConnectionManager]
Name = value
BusName = value
ObjectPath = value


where:
'Name' field sets the name of connection manager.
'BusName' sets the D-Bus bus name of this connection manager.
'ObjectPath' sets the D-Bus object path to the ConnectionManager object under this service.

Then any number of proctol support declarators of the form:

[Protocol (name of supported protocol)]
param-(parameter name) = signature flags
default-(paramater name) = value

Where:
'signature' is a single complete DBus type signature.
'flags' is a space-delimited list of flags; valid flags are 'required' and
'register'.
default-(paramater name) sets the default value for that parameter. e.g.
default-port=522 sets te default value of the 'port' parameter to 522.
 
All connection managers should register as activatable dbus services. They
should also close themselves down after an idle time with no open connections.

Clients should use the Protocol sections to query the user for necessary
information.

Telepathy defines a common subset of paramter names to facilitate GUI design.

s:server - a fully qualified domain name or numeric IPv4 or IPv6 address.
Using the fully-qualified domain name form is RECOMMENDED whenever possible.
If this paramter is specified and the user id for that service also specifies
a server, this parameter should override that in the user id.

q:port - a TCP or UDP port number. If this paramter is specified and the user
id for that service also specifies a port, this parameter should override that
in the user id.

s:password - A password associated with the user.

s:proxy-server - a uri for a proxyserver to use for this connection

b:require-encryption - require encryption for this connection. A connection
should fail if require-encryption is set and encryption is not possible.

UIs should display any default values, but should *not* store them.
"""

import ConfigParser, os
import dircache
import dbus

class ManagerRegistry:
    def __init__(self):
        self.services = {}

    def LoadManager(self, path):
        config = ConfigParser.SafeConfigParser()
        config.read(path)
        connection_manager = dict(config.items("ConnectionManager"))

        if "name" not in connection_manager.keys():
            raise ConfigParser.NoOptionError("name", "ConnectionManager")

        cm_name = connection_manager["name"]
        self.services[cm_name] = connection_manager
        protocols = {}

        for section in set(config.sections()) - set(["ConnectionManager"]):
            if section.startswith('Protocol '):
                proto_name = section[len('Protocol '):]
                protocols[proto_name] = dict(config.items(section))

        if not protocols:
            raise ConfigParser.NoSectionError("no protocols found (%s)" % path)

        self.services[cm_name]["protos"] = protocols

    def LoadManagers(self):
        """
        Searches local and system wide configurations

        Can raise all ConfigParser errors. Generally filename member will be
        set to the name of the erronous file.
        """

        all_paths = (
            '/usr/share/telepathy/managers/',
            '/usr/local/share/telepathy/managers/',
            os.path.expanduser('~/.telepathy'),
            )

        for path in all_paths:
            if os.path.exists(path):
                for name in dircache.listdir(path):
                    if name.endswith('.manager'):
                        self.LoadManager(os.path.join(path, name))

    def GetProtos(self):
        """
        returns a list of protocols supported on this system
        """
        protos=set()
        for service in self.services.keys():
            if self.services[service].has_key("protos"):
                protos.update(self.services[service]["protos"].keys())
        return list(protos)

    def GetManagers(self, proto):
        """
        Returns names of managers that can handle the given protocol.
        """
        managers = []
        for service in self.services.keys():
            if "protos" in self.services[service]:
                if self.services[service]["protos"].has_key(proto):
                    managers.append(service)
        return managers

    def GetBusName(self, manager):
        assert(manager in self.services)
        assert('busname' in self.services[manager])
        return self.services[manager]['busname']

    def GetObjectPath(self, manager):
        assert(manager in self.services)
        assert('objectpath' in self.services[manager])
        return self.services[manager]['objectpath']

    def GetParams(self, manager, proto):
        """
        Returns two dicts of paramters for the given proto on the given manager.
        One dict of mandatory parameters, one of optional.
        The keys will be the parameters names, and the values a tuple of 
        (dbus type, default value). If no default value is specified, the second
        item in the tuple will be None.
        """
        params={}
        for key, val in self.services[manager]["protos"][proto].items():
            if key.startswith("default-"):
                continue
                
            values = val.split(" ")
            type = values[0]
            flags = FLAG_NONE
            if "register" in values:
                flags = flags|FLAG_REGISTER
            if "required" in values:
                flags = flags|FLAG_REQUIRED
            name = key[6:]
            default=None
            for key, val in self.services[manager]["protos"][proto].items():
                if key.strip().startswith("default-"+name):
                    default = val.strip()

            if default:
               params[name]=(type, dbus.Variant(default,signature=type), flags)
            else:
               params[name]=(type, None, flags)

        return params
