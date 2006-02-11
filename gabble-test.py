#!/usr/bin/env python

import dbus
import dbus.glib
import gtk

from telepathy import *
import telepathy.client

from pygtkconsole import GTKInterpreterConsole

class MainWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        
        self.connect("destroy", gtk.main_quit)

        vbox = gtk.VBox()
        
        btn = gtk.Button("Frobble the bloody badger")
        btn.connect("clicked", self._on_btn_clicked)
        vbox.pack_start(btn, expand=False)

        con = GTKInterpreterConsole()
        con.set_size_request(320, 200)
        vbox.pack_start(con, expand=True)

        self.add(vbox)

    def _on_btn_clicked(self, button):
        mgr_bus_name = "org.freedesktop.Telepathy.ConnectionManager.gabble"
        mgr_object_path = "/org/freedesktop/Telepathy/ConnectionManager/gabble"
        
        mgr = telepathy.client.ConnectionManager(mgr_bus_name, mgr_object_path)

        mgr[CONN_MGR_INTERFACE].Connect("google-talk", { "account": "tryggve.tryggvason@gmail.com",
                                                         "password": "badger" })


win = MainWindow()
win.show_all()

gtk.main()

