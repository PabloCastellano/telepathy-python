import ConfigParser, os
import dircache
import dbus

"""
The registry of managers takes the form of any number of .manager files, which
are searched for in /usr/share/telepathy/services or in ~/.telepathy.

.manager files should have an initial stanza of the form:

[ConnectionManager]
Name = value
BusName = value
ObjectPath = value


where:
'Name' field sets the name of connection manager.
'BusName' sets the D-Bus bus name of this connection manager.
'ObjectPath' sets the D-Bus object path to the ConnectionManager object under this service.

Then any number of proctol support declarators of the form:

[Proto (name of supported protocol)]
MandatoryParams = list of values
OptionalParams = list of values
default-(paramater name) = value

Where:
MandatoryParams is a comma-seperated list of mandatory parameters that must be passed to Connections created by this ConnectionManager for this protocol. Each should be of the form dbus type signature:name, eg s:password, indicating a paramater called 'password' of type string.
OptionalParams is a comma-separated list of optional params, of same form as MandatoryParams.
default-(paramater name) sets the default value for that parameter. e.g. default-port=522 sets te default value of the 'port' parameter to 522.
 
All connection managers should register as activatable dbus services. They should also close themselves down after an idle time with no open connections.

Clients should use the Proto sections to query the user for necessary informatoin.

Telepathy defines a common subset of paramter names to facilitate GUI design.

s:server - a fully qualified domain name or numeric IPv4 or IPv6 address. Using the fully-qualified domain name form is RECOMMENDED whenever possible. If this paramter is specified and the user id for that service also specifies a server, this parameter should override that in the user id.

q:port - a TCP or UDP port number. If this paramter is specified and the user id for that service also specifies a port, this parameter should override that in the user id.

s:password - A password associated with the user. 

s:proxy-server - a uri for a proxyserver to use for this connection

b:require-encryption - require encryption for this connection. A connection 
should fail if require-encryption is set and encryption is not possible.

UIs should display any default values, but should *not* store them.
"""

class ManagerRegistry:
    def __init__(self):
        self.services = {}

    def LoadManagers(self):
        """
        Searches local and system wide configurations
    
        Can raise all ConfigParser errors. Generally filename member will be
        set to the name of the erronous file.
        """
        all_services=[]
        if os.path.exists("/usr/share/telepathy/services/"):
            all_services += map( lambda dir: "/usr/share/telepathy/services/"+dir, dircache.listdir("/usr/share/telepathy/services/"))
        local_path=os.path.expanduser("~/.telepathy")
        if os.path.exists(local_path):
            all_services += map( lambda dir: local_path +'/'+dir, dircache.listdir(local_path))
        for service in all_services:
            config = ConfigParser.SafeConfigParser()
            config.read(service)
            connection_manager =dict(config.items("ConnectionManager"))
            if "name" not in connection_manager.keys():
                raise ConfigParser.NoOptionError("name","ConnectionManager")
            self.services[connection_manager["name"]]=connection_manager
            for section in set(config.sections()) - set(["ConnectionManager"]):
                if section[:6]=="Proto ":
                    self.services[connection_manager["name"]]["protos"]={section[6:]:dict(config.items(section))}
                    print  self.services[connection_manager["name"]]["protos"]
            del config

    def GetProtos(self):
        """
        returns a list of protocols supported on this system
        """
        protos=set()
        for service in self.services.keys():
            if self.services[service].has_key("protos"):
                protos.update(self.services[service]["protos"].keys())
        return list(protos)

    def GetManagers(self, proto):
        """
        Returns names of managers that can handle the given protocol.
        """
        managers = []
        for service in self.services.keys():
            if "protos" in self.services[service]:
                if self.services[service]["protos"].has_key(proto):
                    managers.append(service)
        return managers

    def GetBusName(self, manager):
        assert(manager in self.services)
        assert('busname' in self.services[manager])
        return self.services[manager]['busname']

    def GetObjectPath(self, manager):
        assert(manager in self.services)
        assert('objectpath' in self.services[manager])
        return self.services[manager]['objectpath']

    def GetParams(self, manager, proto):
        """
        Returns two dicts of paramters for the given proto on the given manager.
        One dict of mandatory parameters, one of optional.
        The keys will be the parameters names, and the values a tuple of 
        (dbus type, default value). If no default value is specified, the second
        item in the tuple will be None.
        """
        ret=[]
       
        for field in ["mandatoryparams","optionalparams"]:
            params={}
            for item in self.services[manager]["protos"][proto][field].split(','):
                if item.strip() != '':
                    type, name = item.strip().split(':')
                    default=None
                    for key in self.services[manager]["protos"][proto].keys():
                        key.strip()
                        if key=="default-"+name:
                            default=key[8:]
                            break
                    if default:
                        params[name]=(type, dbus.Variant(default,signature=type))
                    else:
                        params[name]=(type, None)
            ret.append(params)
        
        return ret

