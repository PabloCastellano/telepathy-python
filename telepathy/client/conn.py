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
        self[CONN_INTERFACE].GetInterfaces(reply_handler=self.get_interfaces_reply_cb, error_handler=self.error_cb)

    def error_cb(self, exception):
        print "Exception received from asynchronous method call:"
        print exception

    def get_interfaces_reply_cb(self, interfaces):
        self.get_valid_interfaces().update(interfaces)
        gobject.idle_add(self.got_interfaces)

    def got_interfaces(self):
        pass
