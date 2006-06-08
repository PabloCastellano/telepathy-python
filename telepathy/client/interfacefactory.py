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

class InterfaceFactory(object):
    def __init__(self, dbus_object):
        self._dbus_object = dbus_object
        self._interfaces = {}
        self._valid_interfaces = set()

    def get_valid_interfaces(self):
        return self._valid_interfaces

    def __getitem__(self, name):
        if name not in self._interfaces:
            if name not in self._valid_interfaces:
                raise KeyError(name)

            self._interfaces[name] = dbus.Interface(self._dbus_object, name)

        return self._interfaces[name]
