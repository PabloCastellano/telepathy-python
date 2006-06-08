
import sys

import dbus
import dbus.glib

import telepathy

bus = dbus.Bus()

def get_names():
    bus_obj = bus.get_object('org.freedesktop.DBus', '/')
    iface = dbus.Interface(bus_obj, 'org.freedesktop.DBus')
    return iface.ListNames()

def get_managers():
    return [
        name[len(telepathy.CONN_MGR_INTERFACE) + 1:]
        for name in get_names()
        if name.startswith(telepathy.CONN_MGR_INTERFACE)]

def get_parameters(name):
    full_name = '%s.%s' % (telepathy.CONN_MGR_INTERFACE, name)
    path = '/org/freedesktop/Telepathy/ConnectionManager/%s' % name
    bus_obj = bus.get_object(full_name, path)
    iface = dbus.Interface(bus_obj, telepathy.CONN_MGR_INTERFACE)

    stanzas = []
    stanza = []
    stanza.append('[ConnectionManager]')
    stanza.append('Name = %s' % name)
    stanza.append('BusName = %s' % full_name)
    stanza.append('ObjectPath = %s' % path)
    stanzas.append(stanza)

    for protocol in iface.ListProtocols():
        stanza = []
        stanza.append('[Protocol %s]' % protocol)

        for name, flags, sig, default in iface.GetParameters(protocol):
            decl = [sig]

            if flags & telepathy.CONN_MGR_PARAM_FLAG_REQUIRED:
                decl.append('required')

            if flags & telepathy.CONN_MGR_PARAM_FLAG_REGISTER:
                decl.append('register')

            stanza.append('param-%s = %s' % (name, ' '.join(decl)))

        stanzas.append(stanza)

    return '\n'.join(
        ''.join(line + '\n' for line in stanza)
        for stanza in stanzas)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        name = sys.argv[1]
        full_name = '%s.%s' % (telepathy.CONN_MGR_INTERFACE, name)

        if full_name not in get_names():
            raise RuntimeError("connection manager '%s' not found on the bus"
                % name)

        print get_parameters(name),
    else:
        managers = get_managers()

        if managers:
            print 'Found connection managers:'

            for manager in managers:
                print '  %s' % manager
        else:
            print 'No connection managers found'

