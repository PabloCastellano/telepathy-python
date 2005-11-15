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
                raise KeyError

            self._interfaces[name] = dbus.Interface(self._dbus_object, name)

        return self._interfaces[name]
