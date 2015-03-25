#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# tcpmap.py
# Copyright (C) 2015 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from twisted.python import log
from twisted.internet import defer
from twisted.internet.protocol import ServerFactory


# For info on codes, see: http://www.postfix.org/tcp_table.5.html
TCP_MAP_CODE_SUCCESS = 200
TCP_MAP_CODE_TEMPORARY_FAILURE = 400
TCP_MAP_CODE_PERMANENT_FAILURE = 500


class LEAPPostfixTCPMapServerFactory(ServerFactory):
    """
    A factory for postfix tcp map servers.
    """

    def __init__(self, couchdb):
        """
        Initialize the factory.

        :param couchdb: A CouchDB client.
        :type couchdb: leap.mx.couchdbhelper.ConnectedCouchDB
        """
        self._cdb = couchdb

    def _getPubKey(self, uuid):
        """
        Look up PGP public key based on user uid.

        :param uuid: The user uid.
        :type uuid: str

        :return: A deferred that is fired with the uuid and the public key, if
                 available.
        :rtype: DeferredList
        """
        if uuid is None:
            return defer.succeed([None, None])
        return defer.gatherResults([
            defer.succeed(uuid),
            self._cdb.getPubKey(uuid),
        ])

    def get(self, key):
        """
        Look up uuid based on key, only up to the username id of the key.

        At some point we will have to consider the domain part too.

        :param key: The lookup key.
        :type key: str
        """
        log.msg("Query key: %s" % (key,))
        d = self._cdb.queryByAddress(key)
        d.addCallback(self._getPubKey)
        d.addErrback(log.err)
        return d
