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

from twisted.internet  import address
from twisted.mail      import maildir, alias
from twisted.protocols import postfix

from leap.mx      import alias_resolver
from leap.mx.util import config, log, net


if __name__ == "__main__":
    config.filename = 'mx.conf.private'
    config.loadConfig()

    user = config.couch.user
    pswd = config.couch.passwd
    host = config.couch.host
    port = config.couch.port

    connection = alias_resolver.ConnectedCouchDB(host, port, 
                                                 dbName="users",
                                                 username=user,
                                                 password=pswd)
    connection.listDB()
    print connection
