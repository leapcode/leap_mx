# -*- encoding: utf-8 -*-
# soledadhelper.py
# Copyright (C) 2017 LEAP
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
Classes for working with Soledad Incoming API.
See: http://soledad.readthedocs.io/en/latest/incoming_box.html
"""


import base64
import treq
from io import BytesIO
from twisted.internet import defer

try:
    from six import raise_from
except ImportError:
    def raise_from(value, from_value):
        raise value


class UnavailableIncomingAPIException(Exception):
    pass


class SoledadIncomingAPI:
    """
    Delivers messages using Soledad Incoming API.
    """

    def __init__(self, host, port, token):
        """
        Creates a SoledadIncomingAPI helper to deliver messages into user's
        database.

        :param host: A hostname string for the Soledad incoming service host.
            This will usually be localhost, unless served over stunnel.
        :type host: str
        :param port: The port of the Soledad incoming service host.
        :type port: int
        :param token: Incoming service authentication token as configured in
            Soledad.
        :type token: str
        """
        self._incoming_url = "http://%s:%s/incoming/" % (host, port)
        b64_token = base64.b64encode(token)
        self._auth_header = {'Authorization': ['Token %s' % b64_token]}

    @defer.inlineCallbacks
    def put_doc(self, uuid, doc_id, content):
        """
        Make a PUT request to Soledad's incoming API, delivering a message into
        user's database.

        :param uuid: The uuid of a user
        :type uuid: str
        :param content: Message content.
        :type content: str

        :return: A deferred which fires after the HTTP request is complete, or
                 which fails with the correspondent exception if there was any
                 error.
        """
        url = self._incoming_url + "user-%s/%s" % (uuid, doc_id)
        try:
            response = yield treq.put(
                url,
                BytesIO(str(content)),
                headers=self._auth_header,
                persistent=False)
        except Exception as original_exception:
            error_message = "Server unreacheable or unknown error: %s"
            error_message %= (original_exception.message)
            our_exception = UnavailableIncomingAPIException(error_message)
            raise_from(our_exception, original_exception)
        if not response.code == 200:
            error_message = '%s returned status %s instead of 200'
            error_message %= (url, response.code)
            raise UnavailableIncomingAPIException(error_message)
