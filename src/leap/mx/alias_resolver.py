#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
alias_resolver.py
=================
Classes for resolving postfix aliases.

@authors: Isis Agora Lovecruft
@version: 0.0.1-beta
@license: see included LICENSE file
@copyright: copyright 2013 Isis Agora Lovecruft
'''

import os
import uuid

try:
    from twisted.internet  import address, defer, reactor
    from twisted.mail      import maildir, alias
    from twisted.protocols import postfix
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."

from leap.mx import net, log ## xxx implement log


def createID(alias):
    """
    Creates Universal Unique ID by taking the SHA-1 HASH of an email alias:

        >>> uuid.uuid5(uuid.NAMESPACE_URL, "isis@leap.se")
        UUID('7194878e-4aea-563f-85a4-4f58519f3c4f')

    @param alias: An email address alias.
    @returns: A :class:`uuid.UUID` containing attributes specifying the UUID.
    """
    return uuid.uuid5(uuid.NAMESPACE_URL, str(alias))

class StatusCodes(object):
    """
    The Postfix manual states:

        The request completion status is one of OK, RETRY, NOKEY (lookup
        failed because the key was not found), BAD (malformed request) or DENY
        (the table is not approved for proxy read or update access).

    Other SMTP codes: http://www.greenend.org.uk/rjk/tech/smtpreplies.html
    """
    OK    = "OK Others might say 'HELLA AWESOME'...but we're not convinced."
    RETRY = "RETRY Server is busy plotting revolution; requests might take a while."
    BAD   = "BAD bad Leroy Brown, baddest man in the whole...er. Malformed request."
    NOKEY = "NOKEY Couldn't find your keys, sorry. Did you check in the sofa?"
    DEFER = "DEFER_IF_LOCAL xxx fill me in"
    DENY  = "DENY no gurlz aloud in teh tree house."
    FAIL  = "FAIL xxx fill me in"

    fakeSMTPCodes = { '250': OK,
                      '300': RETRY,
                      '500': BAD,
                      '550': NOKEY,
                      '552': DEFER,
                      '553': DENY,
                      '554': FAIL, }

    def __init__(self, status_code=None):
        """xxx fill me in"""
        if status_code:
            self.get(status_code)

    def get(self, status_code=None)
        """xxx fill me in"""
        if status_code:
            if isinstance(status_code, str):
                return status_code, getattr(self, status_code.upper(), None)
            elif isinstance(status_code, int):
                for k, v in self.fake_smtp_codes.items():
                    ## we want to return None if it's 550
                    if k == str(status_code) and k != '550':
                        return status_code, v
                log.debug("%s" % self.NOKEY)
                return None, ''


class AliasResolver(postfix.PostfixTCPMapServer):
    """
    Resolve postfix aliases, similarly to using "$ postmap -q <alias>".

    This class starts a simple LineReceiver server which listens for a string
    specifying an alias to look up, :param:`key`, and which will be used to
    query the local Postfix server. You can test it with:

        $ ./alias_resolver.py &
        $ /usr/bin/postmap -q <key> tcp:localhost:4242

    """
    def __init__(self, *args, **kwargs):
        """
        Create a local LineReceiver server which listens for Postfix aliases
        to resolve.
        """
        super(postfix.PostfixTCPMapServer, self).__init__(*args, **kwargs)


class PostfixAliasResolverFactory(postfix.PostfixTCPMapDeferringDictServerFactory):
    """
    A Factory for creating PostfixAliasResolver servers, which handles inputs
    and outputs, and keeps an in-memory mapping of Postfix aliases in the form
    of a dict.

    xxx fill me in

    """
    protocol = PostfixAliasResolver

    def __init__(self, addr='127.0.0.1', port=4242, timeout=120, data=None):
        """
        Create a Factory which returns :class:`PostfixAliasResolver` servers.

        @param addr:
            (optional) A string giving the IP address of the Postfix server.
            Default: '127.0.0.1'
        @param port:
            (optional) An integer that specifies the port number of the
            Postfix server. Default: 4242
        @param timeout:
            (optional) An integer specifying the number of seconds to wait
            until we should time out. Default: 120
        @param data:
            (optional) A dict to use to initialise or update the alias
            mapping.
        """
        super(postfix.PostfixTCPMapDeferringDictServerFactory, 
              self).__init__(data=data)
        self.timeout = timeout
        ## xxx get config value, should be something like verbose = no
        self.noisy = False

        try:
            assert isinstance(port, int), "Port number must be an integer"
            assert isinstance(timeout, int), "Timeout must be an integer"
        except AssertionError, ae:
            raise SystemExit(ae.message)

        if net.checkIPaddress(addr):
            self.addr = address._IPAddress('TCP', addr, int(port))
        else:
            log.debug("Using default address for Postfix: 127.0.0.1:%s" % port)
            self.addr = address._IPAddress('TCP', '127.0.0.1', int(port))

    def buildProtocol(self):
        """
        Create an instance of the :class:`PostfixAliasResolver` server.
        """
        proto = self.protocol()
        proto.timeout = self.timeout
        proto.factory = self
        return proto


if __name__ == "__main__":

    print "To test alias_resolver.py, please use /test/test_alias_resolver.py"
