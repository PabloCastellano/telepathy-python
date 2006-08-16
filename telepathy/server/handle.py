# telepathy-python - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005-6 Collabora Limited
# Copyright (C) 2005-6 Nokia Corporation
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

class Handle(object):
    def __init__(self, id, handle_type, name):
        self._id = id
        self._type = handle_type
        self._name = name

    def get_id(self):
        return self._id
    __int__ = get_id

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name

    def __eq__(self, other):
        return (int(self) == int(other) and self.get_type() == other.get_type())

    def __ne__(self, other):
        return not self.__eq__(other)
