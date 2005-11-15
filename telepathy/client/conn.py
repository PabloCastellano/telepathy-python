import dbus

from interfacefactory import InterfaceFactory
from telepathy import *

class Connection(InterfaceFactory):
    def __init__(self, service_name, object_path, bus=None):
        if not bus:
            bus = dbus.Bus()

        object = bus.get_object(service_name, object_path)
        InterfaceFactory.__init__(self, object)
        self.get_valid_interfaces().add(CONN_INTERFACE)
