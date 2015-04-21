#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# bounce.py
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
Everything you need to correctly bounce a message!

This is built from the following RFCs:

  * The Multipart/Report Media Type for the Reporting of Mail System
    Administrative Messages
    https://tools.ietf.org/html/rfc6522

  * Recommendations for Automatic Responses to Electronic Mail
    https://tools.ietf.org/html/rfc3834

  * An Extensible Message Format for Delivery Status Notifications
    https://tools.ietf.org/html/rfc3464
"""


import re
import socket

from StringIO import StringIO
from textwrap import wrap

from email.errors import MessageError
from email.message import Message
from email.utils import formatdate
from email.utils import parseaddr
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.generator import Generator
from email.generator import NL

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.error import ProcessDone
from twisted.python import log


EMAIL_ADDRESS_REGEXP = re.compile("[^@]+@[^@]+\.[^@]+")
HOSTNAME = socket.gethostbyaddr(socket.gethostname())[0]


def _valid_address(address):
    """
    Return whether address is a valid email address.

    :param address: An email address candidate.
    :type address: str

    :return: Whether address is valid.
    :rtype: bool
    """
    return bool(EMAIL_ADDRESS_REGEXP.match(address))


def bounce_message(bounce_from, bounce_subject, orig_msg, reason):
    """
    Bounce a message.

    :param bounce_from: The sender of the bounce message.
    :type bounce_from: str
    :param bounce_subject: The subject of the bounce message.
    :type bounce_subject: str
    :param orig_msg: The original message that will be bounced.
    :type orig_msg: email.message.Message
    :param reason: The reason for bouncing the message.
    :type reason: str

    :return: A deferred that will fire with the output of the sendmail process
             if it was successful or with a failure containing the reason for
             the end of the process if it failed.
    :rtype: Deferred
    """
    orig_rpath = orig_msg.get("Return-Path")

    # do not bounce if sender address is invalid
    _, addr = parseaddr(orig_rpath)
    if not _valid_address(addr):
        log.msg(
            "Will not send a bounce message to an invalid address: %s"
            % orig_rpath)
        return

    msg = _build_bounce_message(
        bounce_from, bounce_subject, orig_msg, reason)
    return _async_check_output(["/usr/sbin/sendmail", "-t"], msg.as_string())


def _check_valid_return_path(return_path):
    """
    Check if a certain return path is valid.

    From RFC 3834:

      Responders MUST NOT generate any response for which the
      destination of that response would be a null address (e.g., an
      address for which SMTP MAIL FROM or Return-Path is <>), since the
      response would not be delivered to a useful destination.
      Responders MAY refuse to generate responses for addresses commonly
      used as return addresses by responders - e.g., those with local-
      parts matching "owner-*", "*-request", "MAILER-DAEMON", etc.
      Responders are encouraged to check the destination address for
      validity before generating the response, to avoid generating
      responses that cannot be delivered or are unlikely to be useful.

    :return: Whether the return_path is valid.
    :rtype: bool
    """
    _, addr = parseaddr(return_path)

    # check null address
    if not addr:
        return False

    # check addresses commonly used as return addresses by responders
    local, _ = addr.split("@", 1)
    if local.startswith("owner-") \
            or local.endswith("-request") \
            or local.startswith("MAILER-DAEMON"):
        return False

    return True


class DeliveryStatusNotificationMessage(MIMEBase):
    """
    A delivery status message, as per RFC 3464.
    """

    def __init__(self, orig_msg):
        """
        Initialize the DSN.
        """
        MIMEBase.__init__(self, "message", "delivery-status")
        self.__delitem__("MIME-Version")
        self._build_dsn(orig_msg)

    def _build_dsn(self, orig_msg):
        """
        Build an RFC 3464 compliant delivery status message.

        :param orig_msg: The original bouncing message.
        :type orig_msg: email.message.Message
        """
        content = []

        # Per-Message DSN fields
        # ======================

        # Original-Envelope-Id (optional)
        envelope_id = orig_msg.get("Envelope-Id")
        if envelope_id:
            content.append("Original-Envelope-Id: %s" % envelope_id)

        # Reporting-MTA (required)
        content.append("Reporting-MTA: dns; %s" % HOSTNAME)

        # XXX add Arrival-Date DSN field? (optional).

        content.append("")

        # Per-Recipient DSN fields
        # ========================

        # Original-Recipient (optional)
        orig_to = orig_msg.get("X-Original-To")  # added by postfix
        _, orig_addr = parseaddr(orig_to)
        if orig_addr:
            content.append("Original-Recipient: rfc822; %s" % orig_addr)

        # Final-Recipient (required)
        delivered_to = orig_msg.get("Delivered-To")
        content.append("Final-Recipient: rfc822; %s" % delivered_to)

        # Action (required)
        content.append("Action: failed")

        # Status (required)
        content.append("Status: 5.0.0")  # permanent failure

        # XXX add other optional fields? (Remote-MTA, Diagnostic-Code,
        #     Last-Attempt-Date, Final-Log-ID, Will-Retry-Until)

        # return a "message/delivery-status" message
        msg = Message()
        msg.set_payload("\n".join(content))
        self.attach(msg)


class RFC822Headers(MIMEText):
    """
    A text/rfc822-headers mime message as defined in RFC 6522.
    """

    def __init__(self, _text, **kwargs):
        """
        Initialize the message.

        :param _text: The contents of the message.
        :type _text: str
        """
        MIMEText.__init__(
            self, _text,
            # set "text/rfc822-headers" mime type
            _subtype='rfc822-headers',
            **kwargs)


BOUNCE_TEMPLATE = """
This is the mail system at {0}.

I'm sorry to have to inform you that your message could not
be delivered to one or more recipients. It's attached below.

For further assistance, please send mail to postmaster.

If you do so, please include this problem report. You can
delete your own text from the attached returned message.

                   The mail system

{1}
""".strip()


class InvalidReturnPathError(MessageError):
    """
    Exception raised when the return path is invalid.
    """


def _build_bounce_message(bounce_from, bounce_subject, orig_msg, reason):
    """
    Build a bounce message.

    :param bounce_from: The sender address of the bounce message.
    :type bounce_from: str
    :param bounce_subject: The subject of the bounce message.
    :type bounce_subject: str
    :param orig_msg: The original bouncing message.
    :type orig_msg: email.message.Message
    :param reason: The reason for the bounce.
    :type reason: str

    :return: The bounce message.
    :rtype: MIMEMultipartReport

    :raise InvalidReturnPathError: Raised when the "Return-Path" header of the
                                   original message is invalid for creating a
                                   bounce message.
    """
    # abort creation if "Return-Path" header is invalid
    orig_rpath = orig_msg.get("Return-Path")
    if not _check_valid_return_path(orig_rpath):
        raise InvalidReturnPathError

    msg = MIMEMultipartReport()
    msg['From'] = bounce_from
    msg['To'] = orig_rpath
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = bounce_subject
    msg['Return-Path'] = "<>"  # prevent bounce message loop, see RFC 3834

    # create and attach first required part
    orig_to = orig_msg.get("X-Original-To")  # added by postfix
    wrapped_reason = wrap(("<%s>: " % orig_to) + reason, 74)
    for i in xrange(1, len(wrapped_reason)):
        wrapped_reason[i] = "    " + wrapped_reason[i]
    wrapped_reason = "\n".join(wrapped_reason)
    text = BOUNCE_TEMPLATE.format(HOSTNAME, wrapped_reason)
    msg.attach(MIMEText(text))

    # create and attach second required part
    msg.attach(DeliveryStatusNotificationMessage(orig_msg))

    # attach third (optional) part.
    #
    # XXX From RFC 6522:
    #
    #       When 8-bit or binary data not encoded in a 7-bit form is to be
    #       returned, and the return path is not guaranteed to be 8-bit or
    #       binary capable, two options are available. The original message
    #       MAY be re-encoded into a legal 7-bit MIME message or the
    #       text/rfc822-headers media type MAY be used to return only the
    #       original message headers.
    #
    #     This is not implemented yet, we should detect if content is 7bit and
    #     use the class RFC822Headers if it is not.
#     try:
#        payload = orig_msg.get_payload()
#        payload.encode("ascii")
#    except UnicodeError:
#        headers = []
#        for k in orig_msg.keys():
#            headers.append("%s: %s" % (k, orig_msg[k]))
#        orig_msg = RFC822Headers("\n".join(headers))
    msg.attach(orig_msg)

    return msg


class BouncerSubprocessProtocol(protocol.ProcessProtocol):
    """
    Bouncer subprocess protocol that will feed the msg contents to be
    bounced through stdin
    """

    def __init__(self, msg):
        """
        Constructor for the BouncerSubprocessProtocol

        :param msg: Message to send to stdin when the process has
                    launched
        :type msg: str
        """
        self._msg = msg
        self._outBuffer = ""
        self._errBuffer = ""
        self._d = defer.Deferred()

    @property
    def deferred(self):
        return self._d

    def connectionMade(self):
        self.transport.write(self._msg)
        self.transport.closeStdin()

    def outReceived(self, data):
        self._outBuffer += data

    def errReceived(self, data):
        self._errBuffer += data

    def processEnded(self, reason):
        if reason.check(ProcessDone):
            self._d.callback(self._outBuffer)
        else:
            self._d.errback(reason)


def _async_check_output(args, msg):
    """
    Async spawn a process and return a defer to be able to check the
    output with a callback/errback

    :param args: the command to execute along with the params for it
    :type args: list of str
    :param msg: string that will be send to stdin of the process once
                it's spawned
    :type msg: str

    :rtype: defer.Deferred
    """
    pprotocol = BouncerSubprocessProtocol(msg)
    reactor.spawnProcess(pprotocol, args[0], args)
    return pprotocol.deferred


class DSNGenerator(Generator):
    """
    A slightly modified generator to correctly parse delivery status
    notifications.
    """

    def _handle_message_delivery_status(self, msg):
        """
        Handle a message of type "message/delivery-status".

        This is modified from upstream version in that it also removes empty
        lines in the beginning of each part.

        :param msg: The message to be handled.
        :type msg: Message
        """
        # We can't just write the headers directly to self's file object
        # because this will leave an extra newline between the last header
        # block and the boundary.  Sigh.
        blocks = []
        for part in msg.get_payload():
            s = StringIO()
            g = self.clone(s)
            g.flatten(part, unixfrom=False)
            text = s.getvalue()
            lines = text.split('\n')
            # Strip off the unnecessary trailing empty line
            if lines:
                if lines[0] == '':
                    lines.pop(0)
                if lines[-1] == '':
                    lines.pop()
                blocks.append(NL.join(lines))
            else:
                blocks.append(text)
        # Now join all the blocks with an empty line.  This has the lovely
        # effect of separating each block with an empty line, but not adding
        # an extra one after the last one.
        self._fp.write(NL.join(blocks))


class MIMEMultipartReport(MIMEMultipart):
    """
    Implement multipart/report MIME type as defined in RFC 6522.

    The syntax of multipart/report is identical to the multipart/mixed
    content type defined in https://tools.ietf.org/html/rfc2045.

    The multipart/report media type contains either two or three sub-
    parts, in the following order:

      1. (REQUIRED) A human-readable message.
      2. (REQUIRED) A machine-parsable body part containing an account of
         the reported message handling event.
      3. (OPTIONAL) A body part containing the returned message or a
         portion thereof.
    """

    def __init__(
            self, report_type="message/delivery-status", boundary=None,
            _subparts=None):
        """
        Initialize the message.

        As per RFC 6522, boundary and report_type are required parameters.

        :param report_type: The type of report. This is set as a
                            "Content-Type" parameter, and should match the
                            MIME subtype of the second body part.
        :type report_type: str

        """
        MIMEMultipart.__init__(
            self,
            # set mime type to "multipart/report"
            _subtype="report",
            boundary=boundary,
            _subparts=_subparts,
            # add "report-type" as a "Content-Type" parameter
            report_type=report_type)
        self._report_type = report_type

    def attach(self, payload):
        """
        Add the given payload to the current payload, but first verify if it's
        valid according to RFC6522.

        :param payload: The payload to be attached.
        :type payload: Message

        :raise MessageError: Raised if the payload is invalid.
        """
        idx = len(self.get_payload()) + 1
        self._check_valid_payload(idx, payload)
        MIMEMultipart.attach(self, payload)

    def _check_valid_payload(self, idx, payload):
        """
        Check that an attachment is valid according to RFC6522.

        :param payload: The payload to be attached.
        :type payload: Message

        :raise MessageError: Raised if the payload is invalid.
        """
        if idx == 1:
            # The text in the first section can use any IANA-registered MIME
            # media type, charset, or language.
            cond = lambda payload: isinstance(payload, MIMEBase)
            error_msg = "The first attachment must be a MIME message."
        elif idx == 2:
            # RFC 6522 requires that the report-type parameter is equal to the
            # MIME subtype of the second body type of the multipart/report.
            cond = lambda payload: \
                payload.get_content_type() == self._report_type
            error_msg = "The second attachment's subtype must be %s." \
                        % self._report_type
        elif idx == 3:
            # A body part containing the returned message or a portion thereof.
            cond = lambda payload: isinstance(payload, Message)
            error_msg = "The third attachment must be a message."
        else:
            # The multipart/report media type contains either two or three sub-
            # parts.
            cond = lambda _: False
            error_msg = "The multipart/report media type contains either " \
                        "two or three sub-parts."
        if not cond(payload):
            raise MessageError("Invalid attachment: %s" % error_msg)

    def as_string(self, unixfrom=False):
        """
        Return the entire formatted message as string.

        This is modified from upstream to use our own generator.

        :param as_string: Whether to include the Unix From envelope heder.
        :type as_string: bool

        :return: The entire formatted message.
        :rtype: str
        """
        fp = StringIO()
        g = DSNGenerator(fp)
        g.flatten(self, unixfrom=unixfrom)
        return fp.getvalue()
