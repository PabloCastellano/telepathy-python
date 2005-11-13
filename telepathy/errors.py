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
