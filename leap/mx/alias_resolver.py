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

from twisted.internet  import address
from twisted.mail      import maildir, alias
from twisted.protocols import postfix

from leap.mx import net, log ## xxx implement log


def checkIPaddress(addr):
    """
    Check that a given string is a valid IPv4 or IPv6 address.

    @param addr:
        Any string defining an IP address, i.e. '0.0.0.0', '::1', or '1.2.3.4'.
    @returns:
        True if :param:`addr` defines a valid IPAddress, False otherwise.
    """
    import ipaddr

    try:
        check = ipaddr.IPAddress(addr)
    except ValueError, ve:
        log.warn(ve.message)
        return False
    else:
        return True

def query_couch(file_desc):
    if not os.path.isfile (file_desc):


class PostfixAliasResolver(postfix.PostfixTCPMapServer):
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

        if checkIPaddress(addr):
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
