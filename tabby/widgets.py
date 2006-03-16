#
# Copyright (C) 2006 Collabora Limited
# Copyright (C) 2006 Nokia Corporation
#   @author Ole Andre Vadla Ravnaas <ole.andre.ravnaas@collabora.co.uk>
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
#

import gtk

class EntryDialog(gtk.Dialog):
    def __init__(self, parent, title, text, password=False):
        gtk.Dialog.__init__(self, title, parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))

        label = gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        self.vbox.pack_start(label, False)
        self._label = label

        entry = gtk.Entry()
        entry.set_visibility(not password)
        self.vbox.pack_start(entry, False, True, 5)
        self._entry = entry

        self.show_all()

    def get_text(self):
        return self._entry.get_text()
