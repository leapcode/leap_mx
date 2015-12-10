#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# fingerprint_resolver.py
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

"""
Classes for resolve expiration date of certs.

Test this with postmap -v -q "fingerprint" tcp:localhost:2424
"""


from datetime import datetime
from twisted.internet.protocol import ServerFactory
from twisted.protocols import postfix
from twisted.python import log

from leap.mx.tcp_map import TCP_MAP_CODE_SUCCESS
from leap.mx.tcp_map import TCP_MAP_CODE_PERMANENT_FAILURE


class LEAPPostfixTCPMapFingerprintServer(postfix.PostfixTCPMapServer):
    """
    A postfix tcp map fingerprint resolver server.
    """

    def _cbGot(self, res):
        """
        Return a code and message depending on the result of the factory's
        get().

        :param res: The fingerprint and expiration date of the cert
        :type res: (str, str)
        """
        fingerprint, expiry = (None, None)
        if res is not None:
            fingerprint, expiry = res

        if expiry is None:
            code = TCP_MAP_CODE_PERMANENT_FAILURE
            msg = "NOT FOUND SRY"
        elif expiry < datetime.utcnow().strftime("%Y-%m-%d"):
            code = TCP_MAP_CODE_PERMANENT_FAILURE
            msg = "EXPIRED CERT"
        else:
            # properly encode expiry, otherwise twisted complains when replying
            if isinstance(expiry, unicode):
                expiry = expiry.encode("utf8")
            code = TCP_MAP_CODE_SUCCESS
            msg = fingerprint + " " + expiry

        self.sendCode(code, postfix.quote(msg))


class FingerprintResolverFactory(ServerFactory, object):
    """
    A factory for postfix tcp map fingerprint resolver servers.
    """

    protocol = LEAPPostfixTCPMapFingerprintServer

    def __init__(self, couchdb):
        """
        Initialize the factory.

        :param couchdb: A CouchDB client.
        :type couchdb: leap.mx.couchdbhelper.ConnectedCouchDB
        """
        self._cdb = couchdb

    def get(self, fingerprint):
        """
        Look up the cert expiration date based on fingerprint.

        :param fingerprint: The cert fingerprint.
        :type fingerprint: str

        :return: A deferred that will be fired with the expiration date.
        :rtype: Deferred
        """
        log.msg("look up: %s" % (fingerprint,))
        d = self._cdb.getCertExpiry(fingerprint.lower())
        d.addCallback(lambda expiry: (fingerprint, expiry))
        d.addErrback(log.err)
        return d
