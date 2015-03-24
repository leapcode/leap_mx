#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# alias_resolver.py
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
Classes for resolving postfix aliases.

Test this with postmap -v -q "foo" tcp:localhost:4242

TODO:
    o Look into using twisted.protocols.postfix.policies classes for
      controlling concurrent connections and throttling resource consumption.
"""

try:
    # TODO: we should probably use the system alias somehow
    # from twisted.mail import alias
    from twisted.protocols import postfix
    from twisted.python import log
    from twisted.internet import defer
    from twisted.internet.protocol import ServerFactory
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."


class LEAPPostFixTCPMapserver(postfix.PostfixTCPMapServer):
    def _cbGot(self, value):
        uuid, pubkey = value
        if uuid is None:
            self.sendCode(500, postfix.quote("NOT FOUND SRY"))
        elif pubkey is None:
            self.sendCode(400, postfix.quote("4.7.13 USER ACCOUNT DISABLED"))
        else:
            self.sendCode(200, postfix.quote(value))


class AliasResolverFactory(ServerFactory):

    protocol = LEAPPostFixTCPMapserver

    def __init__(self, couchdb):
        self._cdb = couchdb

    def _to_str(self, result):
        """
        Properly encodes the result string if any.
        """
        if isinstance(result, unicode):
            result = result.encode("utf8")
        if result is None:
            log.msg("Result not found")
        return result

    def _getPubKey(self, uuid):
        if uuid is None:
            return defer.succeed([None, None])
        d = defer.gatherResults([
            self._to_str(uuid),
            self._cdb.getPubKey(uuid),
        ])
        return d

    def get(self, key):
        """
        Looks up the passed key, but only up to the username id of the key.

        At some point we will have to consider the domain part too.
        """
        log.msg("Query key: %s" % (key,))
        d = self._cdb.queryByAddress(key)
        d.addCallback(self._getPubKey)
        d.addErrback(log.err)
        return d
