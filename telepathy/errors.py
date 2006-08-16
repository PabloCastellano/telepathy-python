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

_TELEPATHY_ERROR_IFACE = 'org.freedesktop.Telepathy.Error'

class NetworkError(dbus.DBusException):
    """
    Raised when there is an error reading from or writing to the network.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.NetworkError'

class NotImplemented(dbus.DBusException):
    """
    Raised when the requested method, channel, etc is not available on this connection.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.NotImplemented'

class InvalidArgument(dbus.DBusException):
    """
    Raised when one of the provided arguments is invalid.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.InvalidArgument'

class NotAvailable(dbus.DBusException):
    """
    Raised when the requested functionality is temporarily unavailable.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.NotAvailable'

class PermissionDenied(dbus.DBusException):
    """
    The user is not permitted to perform the requested operation.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.PermissionDenied'

class Disconnected(dbus.DBusException):
    """
    The connection is not currently connected and cannot be used.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.Disconnected'

class InvalidHandle(dbus.DBusException):
    """
    The contact name specified is unknown on this channel or connection.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.InvalidHandle'

class ChannelBanned(dbus.DBusException):
    """
    You are banned from the channel.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.Channel.Banned'

class ChannelFull(dbus.DBusException):
    """
    The channel is full.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE +'.Channel.Full'

class ChannelInviteOnly(dbus.DBusException):
    """
    The requested channel is invite only.
    """
    _dbus_error_name = _TELEPATHY_ERROR_IFACE + '.Channel.InviteOnly'
