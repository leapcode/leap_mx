#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# check_recipient_access.py
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
Classes for resolving postfix recipient access
"""

import logging

try:
    from twisted.protocols import postfix
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."

logger = logging.getLogger(__name__)


class CheckRecipientAccess(postfix.PostfixTCPMapServer):
    def _cbGot(self, value):
        if value is None:
            self.sendCode(500)
        else:
            self.sendCode(200)


class CheckRecipientAccessFactory(postfix.PostfixTCPMapDeferringDictServerFactory):

    protocol = CheckRecipientAccess

    def __init__(self, couchdb, *args, **kwargs):
        postfix.PostfixTCPMapDeferringDictServerFactory.__init__(self, *args, **kwargs)
        self._cdb = couchdb

    def get(self, key):
        orig_key = key
        try:
            key = key.split("@")[0]
            key = key.split("+")[0]
        except Exception as e:
            key = orig_key
            logger.exception("%s" % (e,))
        d = self._cdb.queryByLoginOrAlias(key)
        return d
