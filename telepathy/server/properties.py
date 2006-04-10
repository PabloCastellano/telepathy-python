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

import dbus.service

from telepathy import *

class PropertiesInterface(dbus.service.Interface):
    """
    Interface for channels and other objects, to allow querying and setting
    properties. ListProperties returns which properties are valid for
    the given channel, including their type, and an integer handle used to
    refer to them in GetProperties, SetProperties, and the PropertiesChanged
    signal. The values are represented by D-Bus variant types, and are
    accompanied by flags indicating whether or not the property is readable or
    writable.

    When applied to channels such as chat rooms, the following property
    types and names should be used where appropriate, but implementations may
    add extra properties to communicate data with particular clients:
      b:invite-only
        true if people may not join the channel until they have been invited
      u:limit
        the limit to the number of members, if limited is true
      b:limited
        true if there is a limit to the number of channel members
      b:moderated
        true if channel membership is not sufficient to allow participation
      s:name
        a human-visible name for the channel, if it differs to the handle
      s:password
        the password required to enter the channel if password-required is true
      b:password-required
        true if a password must be provided to enter the channel
      b:private
        true if the channel is not visible to non-members
      s:subject
        a human-readable description of the channel
      u:subject-timestamp
        a unix timestamp indicating when the subject was last modified
      u:subject-contact
        a contact handle representing who last modified the subject

    Each property also has a flags value to indicate what methods are
    available. This is a bitwise OR of the following values:
        1 - PROPERTY_FLAG_READ
            the property can be read
        2 - PROPERTY_FLAG_WRITE
            the property can be written
    """
    def __init__(self):
        self._interfaces.add(PROPERTIES_INTERFACE)

    @dbus.service.method(PROPERTIES_INTERFACE, in_signature='',
                                               out_signature='a(ussu)')
    def ListProperties(self):
        """
        Returns a dictionary of the properties available on this channel.

        Returns:
        an array of structs containing:
            integer identifiers
            a string property name
            a string representing the D-Bus signature of this property
            a bitwise OR of the flags applicable to this property
        """
        pass

    @dbus.service.method(PROPERTIES_INTERFACE, in_signature='au',
                                               out_signature='a(uv)')
    def GetProperties(self, properties):
        """
        Returns a dictionary of variants containing the current values of the
        given properties.

        If any given property identifiers are invalid, InvalidArgument will be
        returned. All properties must have the PROPERTY_FLAG_READ flag, or
        PermissionDenied will be returned.

        Parameters:
        properties - an array of property identifiers

        Returns:
        an array of structs containing:
            integer identifiers
            variant boxed values

        Potential Errors:
        Disconnected, InvalidArgument, PermissionDenied
        """
        pass

    @dbus.service.method(PROPERTIES_INTERFACE, in_signature='a(uv)',
                                               out_signature='')
    def SetProperties(self, properties):
        """
        Takes a dictionary of variants containing desired values to set the given
        properties. In the case of any errors, no properties will be changed.
        When the changes have been acknowledged by the server, the
        PropertiesChanged signal will be emitted.

        All properties given must have the PROPERTY_FLAG_WRITE flag, or
        PermissionDenied will be returned. If any variants are of the wrong
        type, NotAvailable will be returned.  If any given property identifiers
        are invalid, InvalidArgument will be returned.

        Parameters:
        properties - a dictionary mapping integer identifiers to:
            variant boxed values

        Potential Errors:
        Disconnected, InvalidArgument, NotAvailable, PermissionDenied, NetworkError
        """
        pass

    @dbus.service.signal(PROPERTIES_INTERFACE, signature='a(uv)')
    def PropertiesChanged(self, properties):
        """
        Emitted when the value of readable properties has changed.

        Parameters:
        properties - an array of structs containing:
            integer identifiers
            variant boxed values
        """
        pass

    @dbus.service.signal(PROPERTIES_INTERFACE, signature='a(uu)')
    def PropertyFlagsChanged(self, properties):
        """
        Emitted when the flags of some room properties have changed.

        Parameters:
        properties - an array of structs containing:
            integer identifiers
            a bitwise OR of the current flags
        """
        pass
