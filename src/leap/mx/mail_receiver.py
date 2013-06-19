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

"""
MailReceiver service definition
"""

import os
import uuid as pyuuid

import json

from email import message_from_string

from twisted.application.service import Service
from twisted.internet import inotify
from twisted.python import filepath, log

from leap.soledad.document import SoledadDocument
from leap.soledad.target import EncryptionSchemes
from leap.soledad_server.couch import CouchDatabase
from leap.keymanager import openpgp


class MailReceiver(Service):
    """
    Service that monitors incoming email and processes it
    """

    def __init__(self, mail_couch_url, users_cdb, directories):
        """
        Constructor

        @param mail_couch_url: URL prefix for the couchdb where mail
        should be stored
        @type mail_couch_url: str
        @param users_cdb: CouchDB instance from where to get the uuid
        and pubkey for a user
        @type users_cdb: ConnectedCouchDB
        @param directories: list of directories to monitor
        @type directories: list of tuples (path: str, recursive: bool)
        """
        # Service doesn't define an __init__
        self._mail_couch_url = mail_couch_url
        self._users_cdb = users_cdb
        self._directories = directories

    def startService(self):
        """
        Starts the MailReceiver service
        """
        Service.startService(self)
        wm = inotify.INotify()
        wm.startReading()

        mask = inotify.IN_CREATE

        for directory, recursive in self._directories:
            log.msg("Watching %s --- Recursive: %s" % (directory, recursive))
            wm.watch(filepath.FilePath(directory), mask,
                     callbacks=[self._process_incoming_email],
                     recursive=recursive)

    def _get_pubkey(self, uuid):
        """
        Given a UUID for a user, retrieve its public key

        @param uuid: UUID for a user
        @type uuid: str

        @return: uuid, public key
        @rtype: tuple of (str, str)
        """
        log.msg("Fetching pubkey for %s" % (uuid,))
        return uuid, self._users_cdb.getPubKey(uuid)

    def _encrypt_message(self, uuid_pubkey, address, message):
        """
        Given a UUID, a public key, address and a message, it encrypts
        the message to that public key.
        The address is needed in order to build the OpenPGPKey object.

        @param uuid_pubkey: tuple that holds the uuid and the public
        key as it is returned by the previous call in the chain
        @type uuid_pubkey: tuple (str, str)
        @param address: mail address for this message
        @type address: str
        @param message: message contents
        @type message: str

        @return: uuid, doc to sync with Soledad
        @rtype: tuple(str, SoledadDocument)
        """
        uuid, pubkey = uuid_pubkey
        log.msg("Encrypting message to %s's pubkey" % (uuid,))
        log.msg("Pubkey: %s" % (pubkey,))

        doc = SoledadDocument(doc_id=str(pyuuid.uuid4()))

        data = {'incoming': True, 'content': message}

        if pubkey is None or len(pubkey) == 0:
            doc.content = {
                "_enc_scheme": EncryptionSchemes.NONE,
                "_enc_json": json.dumps(data)
            }
            return uuid, doc

        def _ascii_to_openpgp_cb(gpg):
            key = gpg.list_keys().pop()
            return openpgp._build_key_from_gpg(address, key, pubkey)

        openpgp_key = openpgp._safe_call(_ascii_to_openpgp_cb, pubkey)

        doc.content = {
            "_enc_scheme": EncryptionSchemes.PUBKEY,
            "_enc_json": openpgp.encrypt_asym(json.dumps(data),
                                              openpgp_key)
        }

        return uuid, doc

    def _export_message(self, uuid_doc):
        """
        Given a UUID and a SoledadDocument, it saves it directly in the
        couchdb that serves as a backend for Soledad, in a db
        accessible to the recipient of the mail

        @param uuid_doc: tuple that holds the UUID and SoledadDocument
        @type uuid_doc: tuple(str, SoledadDocument)

        @return: True if it's ok to remove the message, False
        otherwise
        @rtype: bool
        """
        uuid, doc = uuid_doc
        log.msg("Exporting message for %s" % (uuid,))

        if uuid is None:
            uuid = 0

        db = CouchDatabase(self._mail_couch_url, "user-%s" % (uuid,))
        db.put_doc(doc)

        log.msg("Done exporting")

        return True

    def _conditional_remove(self, do_remove, filepath):
        """
        Removes the message if do_remove is True

        @param do_remove: True if the message should be removed, False
        otherwise
        @type do_remove: bool
        @param filepath: path to the mail
        @type filepath: twisted.python.filepath.FilePath
        """
        if do_remove:
            # remove the original mail
            try:
                log.msg("Removing %s" % (filepath.path,))
                filepath.remove()
                log.msg("Done removing")
            except:
                log.err()

    def _process_incoming_email(self, otherself, filepath, mask):
        """
        Callback that processes incoming email

        @param otherself: Watch object for the current callback from
        inotify
        @type otherself: twisted.internet.inotify._Watch
        @param filepath: Path of the file that changed
        @type filepath: twisted.python.filepath.FilePath
        @param mask: identifier for the type of change that triggered
        this callback
        @type mask: int
        """
        if os.path.split(filepath.dirname())[-1]  == "new":
            log.msg("Processing new mail at %s" % (filepath.path,))
            with filepath.open("r") as f:
                mail_data = f.read()
                mail = message_from_string(mail_data)
                owner = mail["To"]
                if owner is None:  # default to Delivered-To
                    owner = mail["Delivered-To"]
                if owner is None:
                    log.err("Malformed mail, neither To: nor "
                            "Delivered-To: field")
                owner = owner.split("@")[0]
                owner = owner.split("+")[0]
                log.msg("Mail owner: %s" % (owner,))

                log.msg("%s received a new mail" % (owner,))
                d = self._users_cdb.queryByLoginOrAlias(owner)
                d.addCallbacks(self._get_pubkey, log.err)
                d.addCallbacks(self._encrypt_message, log.err,
                               (owner, mail_data))
                d.addCallbacks(self._export_message, log.err)
                d.addCallbacks(self._conditional_remove, log.err,
                               (filepath,))
                d.addErrback(log.err)

