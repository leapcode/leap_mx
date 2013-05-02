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

TODO:
    o Look into using twisted.protocols.postfix.policies classes for
      controlling concurrent connections and throttling resource consumption.
"""

try:
    # TODO: we should probably use the system alias somehow
    # from twisted.mail      import alias
    from twisted.protocols import postfix
    from twisted.python import log
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."


class AliasResolverFactory(postfix.PostfixTCPMapDeferringDictServerFactory):
    def __init__(self, couchdb, *args, **kwargs):
        postfix.PostfixTCPMapDeferringDictServerFactory.__init__(self, *args, **kwargs)
        self._cdb = couchdb

    def _to_str(self, result):
        if isinstance(result, unicode):
            result = result.encode("utf8")
        if result is None:
            log.msg("Result not found")
        return result

    def get(self, key):
        try:
            log.msg("Processing key: %s" % (key,))
            if key.find("@") == -1:
                log.msg("Ignoring key since it's not an email address")
                return None

            key = key.split("@")[0]
            key = key.split("+")[0]
            log.msg("Final key to query: %s" % (key,))
            d = self._cdb.queryByLoginOrAlias(key)
            d.addCallback(self._to_str)
            d.addErrback(log.err)
            return d
        except:
            log.err()

        return None
