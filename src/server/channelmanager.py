# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2009 Collabora Limited
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

from telepathy.errors import NotImplemented

from telepathy.interfaces import (CHANNEL_INTERFACE,
                                 CHANNEL_TYPE_CONTACT_LIST,
                                 CHANNEL_TYPE_TEXT)

class ChannelManager(object):

    def __init__(self, connection):
        self._conn = connection

        self._requestable_channel_classes = dict()
        self._channels = dict()
        self._fixed_properties = dict()
        self._available_properties = dict()

    def close(self):
        for channel_type in self._requestable_channel_classes:
            for channel in self._channels[channel_type].values():
                if channel._type == CHANNEL_TYPE_CONTACT_LIST:
                    channel.remove_from_connection()
                else:
                    channel.Close()

    def remove_channel(self, channel):
        for channel_type in self._requestable_channel_classes:
            for handle, chan in self._channels[channel_type].items():
                if channel == chan:
                    del self._channels[channel_type][handle]

    def _get_type_requested_handle(self, props):
        type = props[CHANNEL_INTERFACE + '.ChannelType']
        requested = props[CHANNEL_INTERFACE + '.Requested']
        target_handle = props[CHANNEL_INTERFACE + '.TargetHandle']
        target_handle_type = props[CHANNEL_INTERFACE + '.TargetHandleType']

        handle = self._conn._handles[target_handle_type, target_handle]

        return (type, requested, handle)

    def channel_exists(self, props):
        type, _, handle = self._get_type_requested_handle(props)

        if type in self._channels:
            if handle in self._channels[type]:
                return True

        return False

    def channel_for_props(self, props, signal=True, **args):
        type, _, handle = self._get_type_requested_handle(props)

        if type not in self._requestable_channel_classes:
            raise NotImplemented('Unknown channel type "%s"' % type)

        if self.channel_exists(props):
            return self._channels[type][handle]

        channel = self._requestable_channel_classes[type](
            props, **args)

        self._conn.add_channels([channel], signal=signal)
        self._channels[type][handle] = channel

        return channel

    def _implement_channel_class(self, type, make_channel, fixed, available):
        self._requestable_channel_classes[type] = make_channel
        self._channels.setdefault(type, {})

        self._fixed_properties[type] = fixed
        self._available_properties[type] = available

    def get_requestable_channel_classes(self):
        retval = []

        for channel_type in self._requestable_channel_classes:
            retval.append((self._fixed_properties[channel_type],
                self._available_properties[channel_type]))

        return retval
