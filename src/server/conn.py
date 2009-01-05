# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005, 2006 Collabora Limited
# Copyright (C) 2005, 2006 Nokia Corporation
# Copyright (C) 2006 INdT
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import dbus
import dbus.service
import re
import weakref

from telepathy.constants import (CONNECTION_STATUS_DISCONNECTED,
                                 CONNECTION_STATUS_CONNECTED,
                                 HANDLE_TYPE_NONE,
                                 LAST_HANDLE_TYPE)
from telepathy.errors import (Disconnected, InvalidArgument,
                              InvalidHandle, NotAvailable)
from telepathy.interfaces import (CONN_INTERFACE,
                                  CONN_INTERFACE_ALIASING,
                                  CONN_INTERFACE_AVATARS,
                                  CONN_INTERFACE_CAPABILITIES,
                                  CONN_INTERFACE_PRESENCE,
                                  CONN_INTERFACE_RENAMING)
from telepathy.server.handle import Handle
from telepathy.server.properties import DBusProperties

from telepathy._generated.Connection import Connection as _Connection

_BAD = re.compile(r'(?:^[0-9])|(?:[^A-Za-z0-9])')

def _escape_as_identifier(name):
    if isinstance(name, unicode):
        name = name.encode('utf-8')
    if not name:
        return '_'
    return _BAD.sub(lambda match: '_%02x' % ord(match.group(0)), name)

class Connection(_Connection, DBusProperties):

    _optional_parameters = {}
    _mandatory_parameters = {}

    def __init__(self, proto, account, manager=None):
        """
        Parameters:
        proto - the name of the protcol this conection should be handling.
        account - a protocol-specific account name
        manager - the name of the connection manager
        """

        if manager is None:
            import warnings
            warnings.warn('The manager parameter to Connection.__init__ '
                          'should be supplied', DeprecationWarning)
            manager = 'python'

        clean_account = _escape_as_identifier(account)
        bus_name = u'org.freedesktop.Telepathy.Connection.%s.%s.%s' % \
                (manager, proto, clean_account)
        bus_name = dbus.service.BusName(bus_name)

        object_path = '/org/freedesktop/Telepathy/Connection/%s/%s/%s' % \
                (manager, proto, clean_account)
        _Connection.__init__(self, bus_name, object_path)

        # monitor clients dying so we can release handles
        dbus.SessionBus().add_signal_receiver(self.name_owner_changed_callback,
                                              'NameOwnerChanged',
                                              'org.freedesktop.DBus',
                                              'org.freedesktop.DBus',
                                              '/org/freedesktop/DBus')

        self._interfaces = set()

        DBusProperties.__init__(self)
        self._implement_property_get(CONN_INTERFACE,
                {'SelfHandle': lambda: dbus.UInt32(self.GetSelfHandle())})

        self._proto = proto

        self._status = CONNECTION_STATUS_DISCONNECTED

        self._handles = weakref.WeakValueDictionary()
        self._next_handle_id = 1
        self._client_handles = {}

        self._channels = set()
        self._next_channel_id = 0

    def check_parameters(self, parameters):
        """
        Uses the values of self._mandatory_parameters and
        self._optional_parameters to validate and type check all of the
        provided parameters, and check all mandatory parameters are present.
        Sets defaults according to the defaults if the client has not
        provided any.
        """
        for (parm, value) in parameters.iteritems():
            if parm in self._mandatory_parameters.keys():
                sig = self._mandatory_parameters[parm]
            elif parm in self._optional_parameters.keys():
                sig = self._optional_parameters[parm]
            else:
                raise InvalidArgument('unknown parameter name %s' % parm)

            # we currently support strings, (u)int16/32 and booleans
            if sig == 's':
                if not isinstance(value, unicode):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected a string' % (parm, type(value)))
            elif sig in 'iunq':
                if not isinstance(value, (int, long)):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an int' % (parm, type(value)))
            elif sig == 'b':
                if not isinstance(value, bool):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an boolean' % (parm, type(value)))
            else:
                raise TypeError('unknown type signature %s in protocol parameters' % type)

        for (parm, value) in self._parameter_defaults.iteritems():
            if parm not in parameters:
                parameters[parm] = value

        missing = set(self._mandatory_parameters.keys()).difference(parameters.keys())
        if missing:
            raise InvalidArgument('required parameters %s not given' % missing)

    def check_connected(self):
        if self._status != CONNECTION_STATUS_CONNECTED:
            raise Disconnected('method cannot be called unless status is CONNECTION_STATUS_CONNECTED')

    def check_handle(self, handle_type, handle):
        if (handle_type, handle) not in self._handles:
            print "Connection.check_handle", handle, handle_type, self._handles.keys()
            print str(list( [ self._handles[x] for x in self._handles.keys() ] ) )
            raise InvalidHandle('handle number %d not valid for type %d' %
                (handle, handle_type))

    def check_handle_type(self, type):
        if (type <= HANDLE_TYPE_NONE or type > LAST_HANDLE_TYPE):
            raise InvalidArgument('handle type %s not known' % type)

    def get_handle_id(self):
        id = self._next_handle_id
        self._next_handle_id += 1
        return id

    def add_client_handle(self, handle, sender):
        if sender in self._client_handles:
            self._client_handles[sender].add((handle.get_type(), handle))
        else:
            self._client_handles[sender] = set([(handle.get_type(), handle)])

    def name_owner_changed_callback(self, name, old_owner, new_owner):
        # when name and old_owner are the same, and new_owner is
        # blank, it is the client itself releasing its name... aka exiting
        if (name == old_owner and new_owner == "" and name in self._client_handles):
            print "deleting handles for", name
            del self._client_handles[name]

    def set_self_handle(self, handle):
        self._self_handle = handle

    def get_channel_path(self):
        ret = '%s/channel%d' % (self._object_path, self._next_channel_id)
        self._next_channel_id += 1
        return ret

    def add_channel(self, channel, handle, suppress_handler):
        """ add a new channel and signal its creation""" 
        self._channels.add(channel)
        self.NewChannel(channel._object_path, channel._type, handle.get_type(), handle.get_id(), suppress_handler)

    def remove_channel(self, channel):
        self._channels.remove(channel)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        self.check_connected()
        return self._interfaces

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        return self._proto

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='as')
    def InspectHandles(self, handle_type, handles):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)

        ret = []
        for handle in handles:
            ret.append(self._handles[handle_type, handle].get_name())

        return ret

    @dbus.service.method(CONN_INTERFACE, in_signature='uas', out_signature='au', sender_keyword='sender')
    def RequestHandles(self, handle_type, names, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        ret = []
        for name in names:
            handle = None
            for candidate in self._handles.values():
                if candidate.get_name() == name:
                    handle = candidate
                    break

            if not handle:
                id = self.get_handle_id()
                handle = Handle(id, handle_type, name)
                self._handles[handle_type, id] = handle

            self.add_client_handle(handle, sender)
            ret.append(handle.get_id())

        return ret

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='', sender_keyword='sender')
    def HoldHandles(self, handle_type, handles, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)

        for handle in handles:
            hand = self._handles[handle_type, handle]
            self.add_client_handle(hand, sender)

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='', sender_keyword='sender')
    def ReleaseHandles(self, handle_type, handles, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)
            hand = self._handles[handle_type, handle]
            if sender in self._client_handles:
                if (handle_type, hand) not in self._client_handles[sender]:
                    raise NotAvailable('client is not holding handle %s of type %s' % (handle, handle_type))
            else:
                raise NotAvailable('client does not hold any handles')

        for handle in handles:
            hand = self._handles[handle_type, handle]
            self._client_handles[sender].remove((handle_type, hand))

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetSelfHandle(self):
        self.check_connected()
        return self._self_handle

    @dbus.service.signal(CONN_INTERFACE, signature='uu')
    def StatusChanged(self, status, reason):
        self._status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetStatus(self):
        return self._status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='a(osuu)')
    def ListChannels(self):
        self.check_connected()
        ret = []
        for channel in self._channels:
            chan = (channel._object_path, channel._type, channel._handle.get_type(), channel._handle)
            ret.append(chan)
        return ret


from telepathy._generated.Connection_Interface_Aliasing \
        import ConnectionInterfaceAliasing


from telepathy._generated.Connection_Interface_Avatars \
        import ConnectionInterfaceAvatars


from telepathy._generated.Connection_Interface_Capabilities \
        import ConnectionInterfaceCapabilities \
        as _ConnectionInterfaceCapabilities

class ConnectionInterfaceCapabilities(_ConnectionInterfaceCapabilities):
    def __init__(self):
        _ConnectionInterfaceCapabilities.__init__(self)
        # { contact handle : { str channel type : [int, int] }}
        # the first int is the generic caps, the second is the type-specific
        self._caps = {}

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='au', out_signature='a(usuu)')
    def GetCapabilities(self, handles):
        ret = []
        for handle in handles:
            if (handle != 0 and handle not in self._handles):
                raise InvalidHandle
            elif handle in self._caps:
                theirs = self._caps[handle]
                for type in theirs:
                    ret.append([handle, type, theirs[0], theirs[1]])

    @dbus.service.signal(CONN_INTERFACE_CAPABILITIES, signature='a(usuuuu)')
    def CapabilitiesChanged(self, caps):
        for handle, ctype, gen_old, gen_new, spec_old, spec_new in caps:
            self._caps.setdefault(handle, {})[ctype] = [gen_new, spec_new]

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES,
                         in_signature='a(su)as', out_signature='a(su)')
    def AdvertiseCapabilities(self, add, remove):
        my_caps = self._caps.setdefault(self._self_handle, {})

        changed = {}
        for ctype, spec_caps in add:
            changed[ctype] = spec_caps
        for ctype in remove:
            changed[ctype] = None

        caps = []
        for ctype, spec_caps in changed.iteritems():
            gen_old, spec_old = my_caps.get(ctype, (0, 0))
            if spec_caps is None:
                # channel type no longer supported (provider has gone away)
                gen_new, spec_new = 0, 0
            else:
                # channel type supports new capabilities
                gen_new, spec_new = gen_old, spec_old | spec_caps
            if spec_old != spec_new or gen_old != gen_new:
                caps.append((self._self_handle, ctype, gen_old, gen_new,
                            spec_old, spec_new))

        self.CapabilitiesChanged(self._self_handle, caps)

        # return all my capabilities
        return [(ctype, caps[1]) for ctype, caps in my_caps.iteritems()]


from telepathy._generated.Connection_Interface_Presence \
        import ConnectionInterfacePresence

from telepathy._generated.Connection_Interface_Simple_Presence \
        import ConnectionInterfaceSimplePresence

from telepathy._generated.Connection_Interface_Contacts \
        import ConnectionInterfaceContacts

from telepathy._generated.Connection_Interface_Requests \
        import ConnectionInterfaceRequests
