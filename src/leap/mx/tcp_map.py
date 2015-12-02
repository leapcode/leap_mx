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


from abc import ABCMeta
from abc import abstractproperty

from twisted.internet.protocol import ServerFactory
from twisted.python import log


# For info on codes, see: http://www.postfix.org/tcp_table.5.html
TCP_MAP_CODE_SUCCESS = 200
TCP_MAP_CODE_TEMPORARY_FAILURE = 400
TCP_MAP_CODE_PERMANENT_FAILURE = 500


# we have to also extend from object here to make the class a new-style class.
# If we don't, we get a TypeError because "new-style classes can't have only
# classic bases". This has to do with the way abc.ABCMeta works and the old
# and new style of python classes.
class LEAPPostfixTCPMapServerFactory(ServerFactory, object):
    """
    A factory for postfix tcp map servers.
    """

    __metaclass__ = ABCMeta

    def __init__(self, couchdb):
        """
        Initialize the factory.

        :param couchdb: A CouchDB client.
        :type couchdb: leap.mx.couchdbhelper.ConnectedCouchDB
        """
        self._cdb = couchdb

    @abstractproperty
    def _query_message(self):
        pass

    def get(self, lookup_key):
        """
        Look up user based on lookup_key.

        :param lookup_key: The lookup key.
        :type lookup_key: str

        :return: A deferred that will be fired with the user's address, uuid
                 and pgp key.
        :rtype: Deferred
        """
        log.msg("%s: %s" % (self._query_message, lookup_key,))
        d = self._cdb.getUuidAndPubkey(lookup_key)
        d.addErrback(log.err)
        return d
