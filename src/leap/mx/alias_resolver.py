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

try:
    from paisley import client
except ImportError:
    print "This software requires paisley. Please see the README file"
    print "for instructions on getting required dependencies."

try:
    from twisted.internet  import address, defer, reactor
    from twisted.mail      import maildir, alias
    from twisted.protocols import postfix
except ImportError:
    print "This software requires paisley. Please see the README file"
    print "for instructions on getting required dependencies."

from leap.mx import net, log ## xxx implement log


class ConnectedCouchDB(client.CouchDB):
    """
    Connect to a CouchDB instance.

    ## xxx will we need to open CouchDB documents and views?
    ## yes, these are in a _design document
    ## 
    
    """
    def __init__(self, host, port, dbName=None, 
                 username=None, password=None, *args, **kwargs):
        """
        Connect to a CouchDB instance.

        @param host: A hostname string for the CouchDB server.
        @param port: The port of the CouchDB server, as an integer.
        @param dbName: (optional) The default database to connect to.
        @param username: (optional) The username for authorization.
        @param password: (optional) The password for authorization.
        @returns: A :class:`twisted.internet.defer.Deferred` representing the
                  the client connection to the CouchDB instance.
        """
        super(client.CouchDB, self).__init__(host, port,
                                             dbName=dbName,
                                             username=username,
                                             password=password,
                                             *args, **kwargs)
        if dbName:
            self.bindToDB(dbName)
        else:
            databases = self.listDB()
            log.msg("Available databases: %s" % databases)

    def queryByEmailOrAlias(self, alias, dbDoc="User",
                            view="by_email_or_alias"):
        """
        Check to see if a particular email or alias exists.

        @param alias: A string representing the email or alias to check.
        @param dbDoc: The CouchDB document to open.
        @param view: The view of the CouchDB document to use.
        """
        assert isinstance(alias, str), "Email or alias queries must be string"

        ## Prepend a forward slash, in case we forgot it:
        if not alias.startswith('/'):
            alias = '/' + alias

        d = self.openDoc(dbDoc)
        d.addCallbacks(self.openView, log.err, (view))
        d.addCallbacks(self.get, log.err, (alias))
        d.addCallbacks(self.parseResult, log.err)

        @d.addCallback
        def show_answer(result):
            log.msg("Query: %s" % alias)
            log.msg("Answer: %s" % alias)

        return d

    def query(self, uri):
        """
        Query a CouchDB instance that we are connected to.
        """
        try:
            self.checkURI(uri) ## xxx write checkURI()
            ## xxx we might be able to use self._parseURI()
        except SchemeNotSupported, sns: ## xxx where in paisley is this?
            log.exception(sns) ## xxx need log.exception()

        d = self.get(uri)
        @d.addCallback
        def parse_answer(answer):
            return answer

        return answer

    @defer.inlineCallbacks
    def listUsersAndEmails(self, limit=1000, reverse=False):
        """
        List all users and email addresses, up to the given limit.
        """
        query = "/users/_design/User/_view/by_email_or_alias/?reduce=false"
        answer = yield self.query(query, limit=limit, reverse=reverse)
        
        if answer:
            parsed = yield self.parseResult(answer)
            if parsed:
                log.msg("%s" % parsed)
            else:
                log.msg("No answer from database, perhaps there are no users.")
        else:
            log.msg("Problem querying CouchDB instance...")
            log.debug("Host: %s" % host)
            log.debug("Port: %d" % port)

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
