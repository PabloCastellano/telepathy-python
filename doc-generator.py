#!/usr/bin/python2.4
import sys
import os
import inspect
import dbus

inspectmod=__import__(sys.argv[1],[],[],[])

doc={}

for (cname,val) in inspectmod.__dict__.items():
    if inspect.isclass(val):
        if val.__dict__.has_key("_dbus_interfaces"):
            iname=val._dbus_interfaces[val.__name__]
            doc[iname]={}
            doc[iname]["maintext"]=val.__doc__.replace('\n\n','<p>')
            doc[iname]["methods"]={}
        for (mname, mval) in val.__dict__.items():
            if inspect.isfunction(mval) and mval.__dict__.has_key("_dbus_is_method"):
                iname=mval.__dict__["_dbus_interface"]
                if not doc.has_key(iname):
                    doc[iname]={}
                    doc[iname]["maintext"]=val.__doc__.replace('\n\n','<p>')
                    doc[iname]["methods"]={}
                doc[iname]["methods"][mname]={}
                sigin=dbus.Signature(mval.__dict__["_dbus_in_signature"])
                argspec=inspect.getargspec(mval)
                args=', '.join(map(lambda tup: str(tup[0])+": "+tup[1], zip(sigin,argspec[0][1:]))) #chop off self
                doc[iname]["methods"][mname]["in_sig"]=args
                if mval.__dict__["_dbus_out_signature"] == "":
                    doc[iname]["methods"][mname]["out_sig"]="None"
                else:
                    doc[iname]["methods"][mname]["out_sig"]=mval.__dict__["_dbus_out_signature"]
                doc[iname]["methods"][mname]["text"]= mval.__doc__.replace('\n\n','<p>')


if sys.argv[2][:17]== "--generate-order=":
    order=file(sys.argv[2][17:],'w')
    order.write('\n'.join(doc.keys()))
    sys.exit(0)
else: 
    print '<html>'
    print '<head>'
    print '<title>Documentation for dbus interfaces defined in',inspectmod.__name__,'</title>'
    print '<link rel="stylesheet" type="text/css" media="screen" href="style.css" />'
    print '</head>'
    print '<body>'
    print '<div class="topbox">Telepathy</div>'
    #print '<div class="sidebar">'
    #
    #for name in doc.keys():
    #    for method in doc[name]["methods"].keys(): 
    #        print '  <a href="#%s">%s</a>' % (method,method)
    #print '</div>'

    order=file(sys.argv[2])
    for name in order:
        name=name[:-1]
        name.strip()
        print "<h1>"+name+"</h1>"
        print doc[name]["maintext"]
        print '<ul>'
        for method in doc[name]["methods"].keys(): 
            print '<li></a><div class="method" name="%s">' % method
            print '<h2>%s ( %s ) -> %s</h2>' % (method,doc[name]["methods"][method]["in_sig"], doc[name]["methods"][method]["out_sig"])

            print doc[name]["methods"][method]["text"]
            print '</div></li>'
        print '</ul>'
        print '<br>'
    print '</body></html>'

    sys.exit(0)
