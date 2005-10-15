import ConfigParser, os
import dircache
import dbus

def ManagerRegistry:
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
        all_services.append(dircache.listdir("/usr/share/telepathy/services/"))
        all_services.append(dircache.listdir(os.path.expanduser("~/.telepathy"))
        for service in all_services:
            config.read(service)
            connection_manager =config.items("ConnectionManager")
            self.services[name]=connection_manager
            for section in config.sections - ["ConnectionManager"]:
                if section[:6]="Proto ":
                    self.services[name][section[6:]]=config.items(section)
                

    def GetProtos(self):
        """
        returns a list of protocols supported on this system
        """
        protos=[]
        for service in self.services.keys():
            protos.append(self.servcices[service].keys())
        return protos
       
    def GetManagers(self, proto):
        """
        Returns names of managers that can handle the given protocol.
        """
        managers = []
        for service in self.services.keys():
            if self.services[service][proto]:
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
                    params[name]=(type, dbus.Variant(default,signature=type)
                else:
                    params[name]=(type, None)
            ret.append(params)
        
        return ret

