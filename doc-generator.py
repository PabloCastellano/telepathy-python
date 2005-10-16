#!/usr/bin/python2.4
import sys
import os
import inspect
import dbus

inspectmod=__import__(sys.argv[1],[],[],[])

print '<html>'
print '<head>'
print '<title>Inspecting',inspectmod,'</title>'
print '</head>'
print '<body>'
for (name,val) in inspectmod.__dict__.items():
    if inspect.isclass(val):
        print "<h1>"+name+"</h1>"
        print val.__doc__.replace('\n\n','<p>')
        print '<ul>'
        if val.__dict__.has_key("_dbus_method_vtable"):
            a = set(val.__dict__.keys())
            b = set(val.__dict__["_dbus_method_vtable"].keys())
            for i in (a&b) :
                print '<li><h2>'+i+'</h2>'
                sigin=dbus.Signature(val.__dict__[i].__dict__["_dbus_in_signature"])
                argspec=inspect.getargspec(val.__dict__[i])
                args=', '.join(map(lambda tup: str(tup[0])+":"+tup[1], zip(sigin,argspec[0])))
                print '<h3> DBus in signature ="'+args+'" </h3>'
                print '<h3> DBus out signature="'+val.__dict__[i].__dict__["_dbus_out_signature"]+'"</h3>'
                print val.__dict__[i].__doc__.replace('\n\n','<p>')
                print '</li>'
        print '</ul>'
print '</body></html>'
