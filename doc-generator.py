#!/usr/bin/python2.4
import sys
import os
import inspect
import dbus

inspectmod=__import__(sys.argv[1],globals(), locals(),['*'])

doc={}
doc['top'] = inspectmod.__doc__
doc['version'] = inspectmod.version

for (cname,val) in inspectmod.__dict__.items():
    if inspect.isclass(val):
        if '_dbus_error_name' in val.__dict__:
            ename = val._dbus_error_name
            doc[ename] = {}
            doc[ename]['maintext'] = val.__doc__
        if val.__dict__.has_key("_dbus_interfaces"):
            for iname in val._dbus_interfaces:
                doc[iname]={}
                doc[iname]["maintext"]=val.__doc__
                doc[iname]["methods"]={}
                doc[iname]["signals"]={}
        for (mname, mval) in val.__dict__.items():
            if inspect.isfunction(mval) and mval.__dict__.has_key("_dbus_is_method"):
                iname=mval.__dict__["_dbus_interface"]
                if not doc.has_key(iname):
                    doc[iname]={}
                    doc[iname]["maintext"]=val.__doc__
                    doc[iname]["methods"]={}
                    doc[iname]["signals"]={}
                doc[iname]["methods"][mname]={}
                sigin=tuple(dbus.Signature(mval.__dict__["_dbus_in_signature"]))
                argspec=inspect.getargspec(mval)
                args=argspec[0][1:] # chop off self
                if len(args) != len(sigin):
                    raise Exception('number of arguments in signature %s differs from number of arguments to method %s in interface %s' % (mval.__dict__["_dbus_in_signature"], mname, iname))
                decorated_args=', '.join(map(lambda tup: str(tup[0])+": "+tup[1], zip(sigin,args)))
                doc[iname]["methods"][mname]["in_sig"]=decorated_args
                if mval.__dict__["_dbus_out_signature"] == "":
                    doc[iname]["methods"][mname]["out_sig"]="None"
                else:
                    doc[iname]["methods"][mname]["out_sig"]=mval.__dict__["_dbus_out_signature"]
                doc[iname]["methods"][mname]["text"]= mval.__doc__
            elif inspect.isfunction(mval) and mval.__dict__.has_key("_dbus_is_signal"):
                iname=mval.__dict__["_dbus_interface"]
                if not doc.has_key(iname):
                    doc[iname]={}
                    doc[iname]["maintext"]=val.__doc__
                    doc[iname]["methods"]={}
                    doc[iname]["signals"]={}
                doc[iname]["signals"][mname]={}
                sig=tuple(dbus.Signature(mval.__dict__["_dbus_signature"]))
                argspec=mval.__dict__["_dbus_args"]
                if len(argspec) != len(sig):
                    raise Exception('number of arguments in signature %s differs from number of arguments to signature %s in interface %s' % (mval.__dict__["_dbus_signature"], mname, iname))
                args=', '.join(map(lambda tup: str(tup[0])+": "+tup[1], zip(sig,argspec)))
                doc[iname]["signals"][mname]["sig"]=args
                doc[iname]["signals"][mname]["text"]= mval.__doc__


if sys.argv[2][:17]== "--generate-order=":
    order=file(sys.argv[2][17:],'w')
    order.write('\n'.join(doc.keys()))
    sys.exit(0)
else:
    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
    print '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">'
    print '<head>'
    print '<title>Telepathy: D-Bus Interface Specification</title>' # inspectmod.__name__,'</title>'
#    print '<link rel="stylesheet" type="text/css" media="screen" href="style.css" />'
    print '<style type="text/css">'
    style = file('style.css')
    for line in style:
        print line.strip()
    del style
    print '</style>'
    print '</head>'
    print '<body>'
    print '<div class="topbox">Telepathy</div>'

#    print '<div class="sidebar">'
#    order = file(sys.argv[2])
#    for name in order:
#        name = name[:-1]
#        name.strip()
#        pretty = name.replace('org.freedesktop.Telepathy', '')
#        print '  <a href="#%s">%s</a><br />' % (name, pretty)
#    print '</div>'

    (major, minor, patch) = doc['version']
    print '<h3>Version %d.%d</h3>' % (major,minor)

    print '<pre>%s</pre>' % doc['top']

    order=file(sys.argv[2])
    for name in order:
        name=name[:-1]
        name.strip()
        print '<a name="%s"></a>' % name
        print '<h1>'+name+'</h1>'
        print '<pre>', doc[name]["maintext"], '</pre>'

        if 'methods' in doc[name]:
            if len(doc[name]["methods"]) > 0:
                print '<h2>Methods:</h2>'
                for method in doc[name]["methods"].keys(): 
                    print '<div class="method">'
                    print '<h2>%s ( %s ) -> %s</h2>' % (method,doc[name]["methods"][method]["in_sig"], doc[name]["methods"][method]["out_sig"])
                    print '<pre>', doc[name]["methods"][method]["text"], '</pre>'
                    print '</div>'
            else:
                print '<p>Interface has no methods.</p>'

        if 'signals' in doc[name]:
            if len(doc[name]["signals"]) > 0:
                print '<h2>Signals:</h2>'
                for signal in doc[name]["signals"].keys(): 
                    print '<div class="signal">'
                    print '<h2>%s ( %s )</h2>' % (signal,doc[name]["signals"][signal]["sig"])
                    print '<pre>', doc[name]["signals"][signal]["text"], '</pre>'
                    print '</div>'
            else:
                print '<p>Interface has no signals.</p>'

    print '</body></html>'

    sys.exit(0)
