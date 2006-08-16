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
import gobject

from telepathy.client.interfacefactory import InterfaceFactory
from telepathy.interfaces import CHANNEL_INTERFACE

class Channel(InterfaceFactory):
    def __init__(self, service_name, object_path, bus=None):
        if not bus:
            bus = dbus.Bus()

        object = bus.get_object(service_name, object_path)
        InterfaceFactory.__init__(self, object)
        self.get_valid_interfaces().add(CHANNEL_INTERFACE)
        self[CHANNEL_INTERFACE].GetInterfaces(reply_handler=self.get_interfaces_reply_cb, error_handler=self.error_cb)

    def error_cb(self, exception):
        print "Exception received from asynchronous method call:"
        print exception

    def get_interfaces_reply_cb(self, interfaces):
        self.get_valid_interfaces().update(interfaces)
        gobject.idle_add(self.got_interfaces)

    def got_interfaces(self):
        pass
