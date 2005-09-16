#!/usr/bin/env python

from getpass import getpass
from sys import argv
from xmpp import *

class Jabber:
    def __init__(self, jid, pw):
        self.reply = None
        self.run = True
        self.client = Client(jid.getDomain())

        if not self.client.connect():
            raise IOError('Connection failed')
        if not self.client.auth(jid.getNode(), pw, jid.getResource()):
            raise IOError('Authentication failed')

        self.client.RegisterHandler('message', self.messageHandler)
        self.client.sendInitPresence()
        self.go()
        self.client.disconnect()

    def go(self):
        while self.run:
            self.client.Process(0.01)
            cmd = raw_input('? ')
            if cmd=='q':
                self.run = False
            elif cmd=='m':
                to = raw_input('     To: ')
                msg = raw_input('Message: ')
                self.client.send(Message(to, msg))
            elif cmd=='r':
                if self.reply != None:
                    self.reply.setBody(raw_input('Reply: '))
                    self.client.send(self.reply)
                else:
                    print 'No message to reply to.'

    def messageHandler(self, conn, node):
        print '   From:', node.getFrom()
        print 'Message:', node.getBody()
        self.reply = node.buildReply()

if __name__ == '__main__':
    if len(argv) > 1:
        jid = JID(argv[1])
    else:
        jid = JID(raw_input("     JID: "))

    if len(argv) > 2:
        pw = argv[2]
    else:
        pw = getpass.getpass()

    jab = Jabber(jid, pw)
