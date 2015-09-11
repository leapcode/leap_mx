import ConfigParser
import sys
import os

from twisted.internet import reactor, defer
from twisted.python import filepath, log

from leap.mx import couchdbhelper
from leap.mx.mail_receiver import MailReceiver

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    fullpath = os.path.realpath(sys.argv[1])

    log.msg("Starting test for %s..." % (fullpath,))

    config_file = "/etc/leap/mx.conf"

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    user = config.get("couchdb", "user")
    password = config.get("couchdb", "password")

    server = config.get("couchdb", "server")
    port = config.get("couchdb", "port")

    cdb = couchdbhelper.ConnectedCouchDB(server,
                                         port=port,
                                         dbName="identities",
                                         username=user,
                                         password=password)

    # Mail receiver
    mail_couch_url_prefix = "http://%s:%s@%s:%s" % (user,
                                                    password,
                                                    server,
                                                    port)

    mr = MailReceiver(mail_couch_url_prefix, cdb, [])
    fpath = filepath.FilePath(fullpath)

    d = mr._process_incoming_email(None, fpath, 0)
    d.addCallback(lambda x: reactor.stop())

    reactor.run()
