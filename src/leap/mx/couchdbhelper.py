# -*- encoding: utf-8 -*-
# couchdb.py
# Copyright (C) 2013 LEAP
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


"""
Classes for working with CouchDB or BigCouch instances which store email alias
maps, user UUIDs, and GPG keyIDs.
"""


from paisley import client
from twisted.python import log


class ConnectedCouchDB(client.CouchDB):
    """
    Connect to a CouchDB instance.

    CouchDB document for testing is '_design', and the view is simply
    a preconfigured set of mapped responses.
    """

    def __init__(self, host, port=5984, dbName=None, username=None,
                 password=None, *args, **kwargs):
        """
        Connect to a CouchDB instance.

        :param host: A hostname string for the CouchDB server.
        :type host: str
        :param port: The port of the CouchDB server.
        :type port: int
        :param dbName: (optional) The default database to bind queries to.
        :type dbName: str
        :param username: (optional) The username for authorization.
        :type username: str
        :param str password: (optional) The password for authorization.
        :type password: str
        """
        client.CouchDB.__init__(self,
                                host,
                                port=port,
                                dbName=dbName,
                                username=username,
                                password=password,
                                *args, **kwargs)
        self._cache = {}

    def createDB(self, dbName):
        """
        Overrides ``paisley.client.CouchDB.createDB``.
        """
        pass

    def deleteDB(self, dbName):
        """
        Overrides ``paisley.client.CouchDB.deleteDB``.
        """
        pass

    def queryByAddress(self, address):
        """
        Check to see if a particular email or alias exists.

        :param address: A string representing the email or alias to check.
        :type address: str
        :return: a deferred for this query
        :rtype twisted.defer.Deferred
        """
        # TODO: Cache results
        d = self.openView(docId="Identity",
                          viewId="by_address/",
                          key=address,
                          reduce=True,
                          include_docs=False)

        def _callback(result):
            if len(result["rows"]):
                return address
            return None

        d.addCallbacks(_callback, log.err)

        return d

    def getPubKey(self, address):
        """
        Returns a deferred that will fire with the pubkey for the address.

        :param address: email address to query
        :type address: str

        :rtype: Deferred
        """
        d = self.openView(docId="Identity",
                          viewId="pgp_key_by_email/",
                          key=address,
                          reduce=False,
                          include_docs=False)

        def _callback(result):
            if not result["rows"]:
                log.msg("No PGP public key found for %s." % address)
                return None
            if len(result["rows"]) > 1:
                log.msg("More than one PGP public key found for %s, "
                        "will pick the first one found." % address)
            row = result["rows"].pop(0)
            return row["value"]

        d.addCallbacks(_callback, log.err)

        return d
