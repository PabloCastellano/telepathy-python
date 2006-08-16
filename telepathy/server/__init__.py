"""
telepathy-python - Base classes defining the interfaces of the Telepathy framework

Copyright (C) 2005, 2006 Collabora Limited
Copyright (C) 2005, 2006 Nokia Corporation
Copyright (C) 2006 INdT

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Library General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

from telepathy.server.connmgr import *
from telepathy.server.conn import *
from telepathy.server.channel import *
from telepathy.server.handle import *
from telepathy.server.properties import *

from telepathy import version, __version__
