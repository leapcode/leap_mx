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
    # from twisted.mail      import alias
    from twisted.protocols import postfix
    from twisted.python import log
    from twisted.internet import defer
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."


class LEAPPostFixTCPMapserver(postfix.PostfixTCPMapServer):
    def _cbGot(self, value):
        if value is None:
            self.sendCode(500, postfix.quote("NOT FOUND SRY"))
        else:
            self.sendCode(200, postfix.quote(value))


class AliasResolverFactory(postfix.PostfixTCPMapDeferringDictServerFactory):

    protocol = LEAPPostFixTCPMapserver

    def __init__(self, couchdb, *args, **kwargs):
        postfix.PostfixTCPMapDeferringDictServerFactory.__init__(
            self, *args, **kwargs)
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

    def spit_result(self, result):
        """
        Formats the return codes in a postfix friendly format.
        """
        if result is None:
            return None
        else:
            return defer.succeed(result)

    def get(self, key):
        """
        Looks up the passed key, but only up to the username id of the key.

        At some point we will have to consider the domain part too.
        """
        try:
            log.msg("Query key: %s" % (key,))
            d = self._cdb.queryByAddress(key)

            d.addCallback(self._to_str)
            d.addCallback(self.spit_result)
            d.addErrback(log.err)
            return d
        except Exception as e:
            log.err('exception in get: %r' % e)
