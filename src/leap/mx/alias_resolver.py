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
    o We should probably use twisted.mail.alias somehow.
"""


from twisted.protocols import postfix

from leap.mx.tcp_map import LEAPostfixTCPMapServerFactory
from leap.mx.tcp_map import TCP_MAP_CODE_SUCCESS
from leap.mx.tcp_map import TCP_MAP_CODE_TEMPORARY_FAILURE
from leap.mx.tcp_map import TCP_MAP_CODE_PERMANENT_FAILURE


class LEAPPostfixTCPMapAliasServer(postfix.PostfixTCPMapServer):
    """
    A postfix tcp map alias resolver server.
    """

    def _cbGot(self, value):
        """
        Return a code and message depending on the result of the factory's
        get().

        :param value: The uuid and public key.
        :type value: list
        """
        uuid, pubkey = value
        if uuid is None:
            self.sendCode(
                TCP_MAP_CODE_PERMANENT_FAILURE,
                postfix.quote("NOT FOUND SRY"))
        elif pubkey is None:
            self.sendCode(
                TCP_MAP_CODE_TEMPORARY_FAILURE,
                postfix.quote("4.7.13 USER ACCOUNT DISABLED"))
        else:
            self.sendCode(
                TCP_MAP_CODE_SUCCESS,
                postfix.quote(uuid))


class AliasResolverFactory(LEAPostfixTCPMapServerFactory):
    """
    A factory for postfix tcp map alias resolver servers.
    """

    protocol = LEAPPostfixTCPMapAliasServer
