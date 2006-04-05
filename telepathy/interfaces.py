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

CONN_MGR_INTERFACE = 'org.freedesktop.Telepathy.ConnectionManager'

CONN_INTERFACE = 'org.freedesktop.Telepathy.Connection'

CONN_INTERFACE_ALIASING = 'org.freedesktop.Telepathy.Connection.Interface.Aliasing'
CONN_INTERFACE_CAPABILITIES = 'org.freedesktop.Telepathy.Connection.Interface.Capabilities'
CONN_INTERFACE_CONTACT_INFO = 'org.freedesktop.Telepathy.Connection.Interface.ContactInfo'
CONN_INTERFACE_FORWARDING = 'org.freedesktop.Telepathy.Connection.Interface.Forwarding'
CONN_INTERFACE_PRESENCE = 'org.freedesktop.Telepathy.Connection.Interface.Presence'
CONN_INTERFACE_PRIVACY = 'org.freedesktop.Telepathy.Connection.Interface.Privacy'
CONN_INTERFACE_RENAMING = 'org.freedesktop.Telepathy.Connection.Interface.Renaming'

CHANNEL_INTERFACE = 'org.freedesktop.Telepathy.Channel'
CHANNEL_TYPE_CONTACT_LIST = 'org.freedesktop.Telepathy.Channel.Type.ContactList'
CHANNEL_TYPE_CONTACT_SEARCH = 'org.freedesktop.Telepathy.Channel.Type.ContactSearch'
CHANNEL_TYPE_TEXT = 'org.freedesktop.Telepathy.Channel.Type.Text'
CHANNEL_TYPE_ROOM_LIST = 'org.freedesktop.Telepathy.Channel.Type.RoomList'
CHANNEL_TYPE_STREAMED_MEDIA = 'org.freedesktop.Telepathy.Channel.Type.StreamedMedia'

CHANNEL_INTERFACE_DTMF = 'org.freedesktop.Telepathy.Channel.Interface.DTMF'
CHANNEL_INTERFACE_GROUP = 'org.freedesktop.Telepathy.Channel.Interface.Group'
CHANNEL_INTERFACE_HOLD = 'org.freedesktop.Telepathy.Channel.Interface.Hold'
CHANNEL_INTERFACE_PASSWORD = 'org.freedesktop.Telepathy.Channel.Interface.Password'
CHANNEL_INTERFACE_ROOM_PROPERTIES = 'org.freedesktop.Telepathy.Channel.Interface.RoomProperties'
CHANNEL_INTERFACE_TRANSFER = 'org.freedesktop.Telepathy.Channel.Interface.Transfer'

MEDIA_SESSION_HANDLER = 'org.freedesktop.Telepathy.Media.SessionHandler'
MEDIA_STREAM_HANDLER = 'org.freedesktop.Telepathy.Media.StreamHandler'

