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

from telepathy.interfaces import DEBUG
from telepathy.constants import (DEBUG_LEVEL_ERROR,
                                 DEBUG_LEVEL_CRITICAL,
                                 DEBUG_LEVEL_WARNING,
                                 DEBUG_LEVEL_INFO,
                                 DEBUG_LEVEL_DEBUG)

from telepathy._generated.Debug import Debug as _Debug
from telepathy.server.properties import DBusProperties

import dbus.service
import logging

LEVELS = {
        logging.ERROR:   DEBUG_LEVEL_ERROR,
        logging.FATAL:   DEBUG_LEVEL_CRITICAL,
        logging.WARNING: DEBUG_LEVEL_WARNING,
        logging.INFO:    DEBUG_LEVEL_INFO,
        logging.DEBUG:   DEBUG_LEVEL_DEBUG,
        logging.NOTSET:  DEBUG_LEVEL_DEBUG
}

DEBUG_MESSAGE_LIMIT = 800

class Debug(_Debug, DBusProperties, logging.Handler):

    def __init__(self, conn_manager, root=''):
        self.enabled = True
        self._interfaces = set()
        self._messages = []
        object_path = '/org/freedesktop/Telepathy/debug'

        _Debug.__init__(self, conn_manager._name, object_path)
        DBusProperties.__init__(self)
        logging.Handler.__init__(self)

        self._implement_property_get(DEBUG, {'Enabled': lambda: self.enabled})
        logging.getLogger(root).addHandler(self)

    def GetMessages(self):
        return self._messages

    def add_message(self, timestamp, name, level, msg):
        if len(self._messages) >= DEBUG_MESSAGE_LIMIT:
            self._messages.pop()
        self._messages.append((timestamp, name, level, msg))
        if self.enabled:
            self.NewDebugMessage(timestamp, name, level, msg)

    # Handle logging module messages

    def emit(self, record):
        name = self.get_record_name(record)
        level = self.get_record_level(record)
        self.add_message(record.created, name, level, record.msg)

    def get_record_level(self, record):
        return LEVELS[record.levelno]

    def get_record_name(self, record):
        name = record.name
        if name.contains("."):
            domain, category = record.name.split('.', 1)
            name = domain + "/" + category
        return name
