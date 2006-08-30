
import telepathy
from telepathy.interfaces import CONN_MGR_INTERFACE
import dbus

def parse_account(s):
    lines = s.splitlines()
    pairs = []
    manager = None
    protocol = None

    for line in lines:
        k, v = line.split(':', 1)
        k = k.strip()
        v = v.strip()

        if k == 'manager':
            manager = v
        elif k == 'protocol':
            protocol = v
        else:
            if k not in ("account", "password"):
                if v.lower() in ("false", "true"):
                    v = bool(v)
                else:
                    try:
                        v = dbus.UInt32(int(v))
                    except:
                        pass
            pairs.append((k, v))

    assert manager
    assert protocol
    return manager, protocol, dict(pairs)

def read_account(path):
    return parse_account(file(path).read())

def connect(manager, protocol, account):
    reg = telepathy.client.ManagerRegistry()
    reg.LoadManagers()

    mgr = reg.GetManager(manager)
    conn_bus_name, conn_object_path = mgr[CONN_MGR_INTERFACE].RequestConnection(protocol, account)
    return telepathy.client.Connection(conn_bus_name, conn_object_path)


