#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# mail_receiver.py
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

import os
import logging
import argparse
import ConfigParser

from email import message_from_string
from functools import partial

from twisted.internet import inotify, reactor
from twisted.python import filepath

from leap.mx import couchdbhelper
from leap.soledad.backends.couch import CouchDatabase

logger = logging.getLogger(__name__)


def _get_pubkey(uuid):
    # TODO: implent!
    logger.debug("Fetching pubkey for %s" % (uuid,))
    return uuid, ""

def _encrypt_message(uuid_pubkey, message):
    # TODO: implement!
    uuid, pubkey = uuid_pubkey
    logger.debug("Encrypting message to %s's pubkey" % (uuid,))
    logger.debug("Pubkey: %s" % (pubkey,))

    if pubkey is None or len(pubkey) == 0:
        # TODO: This is only for testing!! REMOVE!
        return uuid, message

    encrypted = ""

    return uuid, encrypted


def _export_message(uuid_message, couch_url):
    uuid, message = uuid_message
    logger.debug("Exporting message for %s" % (uuid,))

    if uuid is None:
        uuid = 0

    db_url = couch_url + '/user-%s' % uuid
    db = CouchDatabase.open_database(db_url, create=True)
    doc = db.create_doc({'content': str(message)})

    return True


def _conditional_remove(do_remove, filepath):
    if do_remove:
        # remove the original mail
        try:
            logger.debug("Removing %s" % (filepath.path,))
            filepath.remove()
        except Exception as e:
            # TODO: better handle exceptions
            logger.exception("%s" % (e,))


def _process_incoming_email(users_db, mail_couchdb_url_prefix, self, filepath, mask):
    if os.path.split(filepath.dirname())[-1]  == "new":
        logger.debug("Processing new mail at %s" % (filepath.path,))
        with filepath.open("r") as f:
            mail_data = f.read()
            mail = message_from_string(mail_data)
            owner = mail["Delivered-To"]
            logger.debug("%s received a new mail" % (owner,))
            d = users_db.queryByLoginOrAlias(owner)
            d.addCallback(_get_pubkey)
            d.addCallback(_encrypt_message, (mail_data))
            d.addCallback(_export_message, (mail_couchdb_url_prefix))
            d.addCallback(_conditional_remove, (filepath))


def main():
    epilog = "Copyright 2012 The LEAP Encryption Access Project"
    parser = argparse.ArgumentParser(description="""LEAP MX Mail receiver""", epilog=epilog)
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

    debug = opts.debug
    config_file = opts.config

    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    if config_file is None:
        config_file = "leap_mx.cfg"

    logger.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logger.info("    LEAP MX Mail receiver")
    logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    logger.info("Reading configuration from %s" % (config_file,))

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    users_user = config.get("couchdb", "users_user")
    users_password = config.get("couchdb", "users_password")

    mail_user = config.get("couchdb", "mail_user")
    mail_password = config.get("couchdb", "mail_password")

    server = config.get("couchdb", "server")
    port = config.get("couchdb", "port")

    wm = inotify.INotify(reactor)
    wm.startReading()

    mask = inotify.IN_CREATE

    users_db = couchdbhelper.ConnectedCouchDB(server,
                                              port=port,
                                              dbName="users",
                                              username=users_user,
                                              password=users_password)

    mail_couch_url_prefix = "http://%s:%s@localhost:%s" % (mail_user,
                                                           mail_password,
                                                           port)

    incoming_partial = partial(_process_incoming_email, users_db, mail_couch_url_prefix)
    for section in config.sections():
        if section in ("couchdb"):
            continue
        to_watch = config.get(section, "path")
        recursive = config.getboolean(section, "recursive")
        logger.debug("Watching %s --- Recursive: %s" % (to_watch, recursive))
        wm.watch(filepath.FilePath(to_watch), mask, callbacks=[incoming_partial], recursive=recursive)

    reactor.run()

if __name__ == "__main__":
    main()
