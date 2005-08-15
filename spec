The mission control library reads files on disk to determine available
connection managers, and the protocols they support, listed as activatable
service names of the form:
 org.freedesktop.ipcf.connectionmanager.{manager specific identifier}

Once activated, the connection manager provides an object implementing the
interface:
 org.freedesktop.ipcf.connectionmanager

Named:
 /org/freedesktop/ipcf/connectionmanager/{manager specufic identifier}
Which provides methods to query available protocols, and create a connection.

When a connection is created, the manager appears as a service of the form:
 org.freedesktop.ipcf.connection.{protocol}.{protocol specific connection identifier}
A manager which is only capable of managing a single connection would then
deregister its org.freedesktop.ipcf.connectionmanager.* identifier, causing
another instance to be activated when another connection is required.

The connection service provides an object implementing the interface:
 org.freedesktop.ipcf.connection
Named:
 /org/freedesktop/ipcf/connection/{protocol}/{protocol specific conection identifier}
Which provides methods to query the channels that the connection currently
has open, create channels, query available contacts, add/remove contacts,
disconnect, etc, and emits signals for changes in these entities.

objects implementing org.freedesktop.ipcf.connection open communication channels 
on request. communication channels shoudl implement interfaces that implement the
capabilities with which they were created.

Galago
Person -> list of Accounts


Interface Specifications:

org.freedesktop.ipcf.connectionmanager:
        make_connection(s:proto,s:account, a{ss}:connect_info)
           proto: protocol name
           account: account name
           connect_info: the rest of how to connect to the server
               e.g. {server:jabber.org, port:55555, password:s3cr1t}
           return (s:protocol specific account identifier)


org.freedesktop.ipcf.connection:
        create_channel(s:contact_account, as:caps)
                contact_account: contacts account name
                caps: capabilities you would like the channel to have
                
                returns: (s:channel identifier, as: caps actually implemented)
                
                


