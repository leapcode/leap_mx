#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# start_mx.py
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

import argparse
import sys
import ConfigParser
import logging

try:
    from leap.mx import couchdbhelper
    from leap.mx.alias_resolver import AliasResolverFactory
except ImportError, ie:
    print "%s \nExiting... \n" % ie.message
    sys.exit(1)

try:
    from twisted.internet import reactor
    from twisted.internet.endpoints import TCP4ServerEndpoint
except ImportError, ie:
    print "This software requires Twisted>=12.0.2, please see the README for"
    print "help on using virtualenv and pip to obtain requirements."


if __name__ == "__main__":
    epilog = "Copyright 2012 The LEAP Encryption Access Project"
    parser = argparse.ArgumentParser(description="""LEAP MX""",
                                     epilog=epilog)
    parser.add_argument('-d', '--debug', action="store_true",
                        help="Launches the LEAP MX mail receiver with debug output")
    parser.add_argument('-l', '--logfile', metavar="LOG FILE", nargs='?',
                        action="store", dest="log_file",
                        help="Writes the logs to the specified file")
    parser.add_argument('-c', '--config', metavar="CONFIG FILE", nargs='?',
                        action="store", dest="config",
                        help="Where to look for the configuration file. " \
                            "Default: mail_receiver.cfg")

    opts, _ = parser.parse_known_args()

    logger = logging.getLogger(name='leap')

    debug = opts.debug
    config_file = opts.config

    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    if config_file is None:
        config_file = "mx.conf"

    logger.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    logger.info("~~~~~~~~~~~~~~~~~~~")
    logger.info("    LEAP MX")
    logger.info("~~~~~~~~~~~~~~~~~~~")

    logger.info("Reading configuration from %s" % (config_file,))

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    users_user = config.get("couchdb", "users_user")
    users_password = config.get("couchdb", "users_password")

    mail_user = config.get("couchdb", "mail_user")
    mail_password = config.get("couchdb", "mail_password")

    server = config.get("couchdb", "server")
    port = config.get("couchdb", "port")

    cdb = couchdbhelper.ConnectedCouchDB(server,
                                         port=port,
                                         dbName="users",
                                         username=users_user,
                                         password=users_password)

    # TODO: use the couchdb for mail

    # TODO: make the listening ports configurable
    alias_endpoint = TCP4ServerEndpoint(reactor, 4242)
    alias_endpoint.listen(AliasResolverFactory(couchdb=cdb))

    reactor.run()
