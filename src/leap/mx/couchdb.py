# -*- encoding: utf-8 -*-
'''
couchdb.py
==========
Classes for working with CouchDB or BigCouch instances which store email alias
maps, user UUIDs, and GPG keyIDs.

@authors: Isis Agora Lovecruft
@version: 0.0.1-beta
@license: see included LICENSE file
'''

try:
    from paisley import client
except ImportError:
    print "This software requires paisley. Please see the README file"
    print "for instructions on getting required dependencies."

try:
    from twisted.internet import defer
except ImportError:
    print "This software requires Twisted. Please see the README file"
    print "for instructions on getting required dependencies."

from leap.mx.util import log


class ConnectedCouchDB(client.CouchDB):
    """Connect to a CouchDB instance.

    CouchDB document for testing is '_design', and the view is simply
    a preconfigured set of mapped responses.
    """
    def __init__(self, host, port=5984, dbName=None, username=None,
                 password=None, *args, **kwargs):
        """
        Connect to a CouchDB instance.

        :param str host: A hostname string for the CouchDB server.
        :param int port: The port of the CouchDB server.
        :param str dbName: (optional) The default database to bind queries to.
        :param str username: (optional) The username for authorization.
        :param str password: (optional) The password for authorization.
        :returns: A :class:`twisted.internet.defer.Deferred` representing the
                  the client connection to the CouchDB instance.
        """
        super(client.CouchDB, self).__init__(host,
                                             port=port,
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
