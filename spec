The mission control library reads files on disk to determine available
connection managers, and the protocols they support, listed as activatable
service names of the form:
 org.freedesktop.ipcf.connectionmanager.{manager specific identifier}

Once activated, the connection manager provides an object implementing the
interface:
 org.freedesktop.ipcf.connectionmanager
Named:
 /org/freedesktop/ipcf/connectionmanager/{manager id}
Which provides methods to query available protocols, and create a connection.

When a connection is created, the manager appears as a service of the form:
 org.freedesktop.ipcf.connection.{protocol}.{protocol specific account identifier}
A manager which is only capable of managing a single connection would then
deregister its org.freedesktop.ipcf.connectionmanager.* identifier, causing
another instance to be activated when another connection is required.

The connection service provides an object implementing the interface:
 org.freedesktop.ipcf.connection
Named:
 /org/freedesktop/ipcf/connection/{protocol}/{account id}
Which provides methods to query the channels that the connection currently
has open, create channels, query available contacts, add/remove contacts,
disconnect, etc, and emits signals for changes in these entities.



Galago
Person -> list of Accounts


