import ConfigParser, os
import dircache
import dbus

class ManagerRegistry:
    def __init__(self):
        self.services = {}

    def LoadManagers(self):
        """
        Searches local and system wide configurations
    
        Can raise all ConfigParser errors. Generally filename member will be
        set to the name of the erronous file.
        """
        config = ConfigParser.SafeConfigParser()
        all_services=[]
        if os.path.exists("/usr/share/telepathy/services/"):
            all_services += dircache.listdir("/usr/share/telepathy/services/")
        if os.path.exists(os.path.expanduser("~/.telepathy")):
            all_services += dircache.listdir(os.path.expanduser("~/.telepathy"))
        for service in all_services:
            config.read(service)
            connection_manager =dict(config.items("ConnectionManager"))
            if "name" not in connection_manager.keys():
                raise ConfigParser.NoOptionError("name","ConnectionManager")
            self.services[connection_manager["name"]]=connection_manager
            for section in set(config.sections()) - set(["ConnectionManager"]):
                if section[:6]=="Proto ":
                    self.services[connection_manager["name"]]["protos"]={section[6:]:dict(config.items(section))}
                

    def GetProtos(self):
        """
        returns a list of protocols supported on this system
        """
        protos=[]
        for service in self.services.keys():
            if self.services[service].has_key("protos"):
                protos.extend(self.services[service]["protos"].keys())
        return protos
       
    def GetManagers(self, proto):
        """
        Returns names of managers that can handle the given protocol.
        """
        managers = []
        for service in self.services.keys():
            if self.services[service].has_key("protos"):
                if self.services[service]["protos"][proto]:
                    managers.append(service)
        return managers
                    
    def GetParams(self, manager, proto):
        """
        Returns two dicts of paramters for the given proto on the given manager.
        One dict of mandatory parameters, one of optional.
        The keys will be the parameters names, and the values a tuple of 
        (dbus type, default value). If no default value is specified, the second
        item in the tuple will be None.
        """
        ret=()
       
        for field in ["MandatoryParams","OptionalParams"]:
            params={}
            for item in split(self.services[manager][proto][field],','):
                type, name = split(strip(item),':')
                default=None
                for key in self.services[manager][proto].keys():
                    strip(key)
                    if key=="Default-"+name:
                        default=key[8:]
                        break
                if default:
                    params[name]=(type, dbus.Variant(default,signature=type))
                else:
                    params[name]=(type, None)
            ret.append(params)
        
        return ret

