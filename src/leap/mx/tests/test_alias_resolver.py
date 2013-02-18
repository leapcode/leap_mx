#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
test_alias_resolver.py
======================
Unittests for /leap/mx/alias_resolver.py.

@authors: Isis Agora Lovecruft
@license: see included LICENSE file
@copyright: copyright 2013 Isis Agora Lovecruft
'''

import os
import socket
import stat

from twisted.internet  import address, defer, reactor
from twisted.mail      import maildir, alias
from twisted.protocols import postfix
from twisted.trial     import unittest

from leap.mx      import alias_resolver
from leap.mx.util import config, log, net


config.filename = 'mx.conf.private'
config.loadConfig()

user = config.couch.user
pswd = config.couch.passwd
host = config.couch.host
port = config.couch.port

## xxx dbName should be a config setting
connection = alias_resolver.ConnectedCouchDB(host, port, 
                                             dbName="users",
                                             username=user,
                                             password=pswd)
connection.listDB()
print connection

class TestAliasResolverServer(unittest.TestCase):
    def setUp(self, *args, **kwargs):
        self.factory = alias_resolver.AliasResolverFactory(
            data={'isis@leap.se': '0x2cdbb35'})
        self.protocol = self.factory.buildProtocol()

        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if (os.path.exists(client_socket) and
            os.stat(socket).st_mode & (
                stat.S_IRGP | stat.S_IRUSR | stat.S_IROTH)):
            self.client_connection = (reactor, client_socket)
            self.client = UnixClientEndpoint(self.client_connection)
    

if __name__ == "__main__":

    tars = TestAliasResolverServer()
