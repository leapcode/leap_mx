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
import email.utils
import socket

try:
    import cchardet as chardet
except ImportError:
    import chardet

from email import message_from_string

from twisted.application.service import Service
from twisted.internet import inotify
from twisted.python import filepath, log

from leap.soledad.common.document import SoledadDocument
from leap.soledad.common.crypto import (
    EncryptionSchemes,
    ENC_JSON_KEY,
    ENC_SCHEME_KEY,
)
from leap.soledad.common.couch import CouchDatabase
from leap.keymanager import openpgp


class MailReceiver(Service):
    """
    Service that monitors incoming email and processes it
    """

    INCOMING_KEY = 'incoming'

    def __init__(self, mail_couch_url, users_cdb, directories):
        """
        Constructor

        :param mail_couch_url: URL prefix for the couchdb where mail
        should be stored
        :type mail_couch_url: str
        :param users_cdb: CouchDB instance from where to get the uuid
        and pubkey for a user
        :type users_cdb: ConnectedCouchDB
        :param directories: list of directories to monitor
        :type directories: list of tuples (path: str, recursive: bool)
        """
        # Service doesn't define an __init__
        self._mail_couch_url = mail_couch_url
        self._users_cdb = users_cdb
        self._directories = directories
        self._domain = socket.gethostbyaddr(socket.gethostname())[0]

    def startService(self):
        """
        Starts the MailReceiver service
        """
        Service.startService(self)
        self.wm = inotify.INotify()
        self.wm.startReading()

        mask = inotify.IN_CREATE

        for directory, recursive in self._directories:
            log.msg("Watching %s --- Recursive: %s" % (directory, recursive))
            self.wm.watch(filepath.FilePath(directory), mask,
                          callbacks=[self._process_incoming_email],
                          recursive=recursive)

    def _encrypt_message(self, pubkey, uuid, address, message):
        """
        Given a UUID, a public key, address and a message, it encrypts
        the message to that public key.
        The address is needed in order to build the OpenPGPKey object.

        :param uuid_pubkey: tuple that holds the uuid and the public
                            key as it is returned by the previous call in the
                            chain
        :type uuid_pubkey: tuple (str, str)
        :param address: mail address for this message
        :type address: str
        :param message: message contents
        :type message: str

        :return: uuid, doc to sync with Soledad or None, None if
                 something went wrong.
        :rtype: tuple(str, SoledadDocument)
        """
        if uuid is None or pubkey is None or len(pubkey) == 0:
            return None, None

        log.msg("Encrypting message to %s's pubkey" % (uuid,))
        log.msg("Pubkey: %s" % (pubkey,))

        doc = SoledadDocument(doc_id=str(pyuuid.uuid4()))

        result = chardet.detect(message)

        encoding = result["encoding"]

        data = {'incoming': True, 'content': message}

        if pubkey is None or len(pubkey) == 0:
            doc.content = {
                self.INCOMING_KEY: True,
                ENC_SCHEME_KEY: EncryptionSchemes.NONE,
                ENC_JSON_KEY: json.dumps(data, encoding=encoding)
            }
            return uuid, doc

        openpgp_key = None
        with openpgp.TempGPGWrapper(gpgbinary='/usr/bin/gpg') as gpg:
            gpg.import_keys(pubkey)
            key = gpg.list_keys().pop()
            openpgp_key = openpgp._build_key_from_gpg(address, key, pubkey)

            doc.content = {
                self.INCOMING_KEY: True,
                ENC_SCHEME_KEY: EncryptionSchemes.PUBKEY,
                ENC_JSON_KEY: str(gpg.encrypt(
                    json.dumps(data, encoding=encoding),
                    openpgp_key.fingerprint,
                    symmetric=False))
            }

        return uuid, doc

    def _export_message(self, uuid_doc):
        """
        Given a UUID and a SoledadDocument, it saves it directly in the
        couchdb that serves as a backend for Soledad, in a db
        accessible to the recipient of the mail.

        :param uuid_doc: tuple that holds the UUID and SoledadDocument
        :type uuid_doc: tuple(str, SoledadDocument)

        :return: True if it's ok to remove the message, False
                 otherwise
        :rtype: bool
        """
        uuid, doc = uuid_doc
        if uuid is None or doc is None:
            return False

        log.msg("Exporting message for %s" % (uuid,))

        if uuid is None:
            uuid = 0

        db = CouchDatabase(self._mail_couch_url, "user-%s" % (uuid,))
        db.put_doc(doc)

        log.msg("Done exporting")

        return True

    def _conditional_remove(self, do_remove, filepath):
        """
        Removes the message if do_remove is True.

        :param do_remove: True if the message should be removed, False
                          otherwise
        :type do_remove: bool
        :param filepath: path to the mail
        :type filepath: twisted.python.filepath.FilePath
        """
        if do_remove:
            # remove the original mail
            try:
                log.msg("Removing %s" % (filepath.path,))
                filepath.remove()
                log.msg("Done removing")
            except Exception:
                log.err()

    def _get_owner(self, mail):
        """
        Given an email, returns the owner (who's delivered to) and the
        uuid of the owner. In case of a mailing list mail, the owner
        will end up being the mailing list address, but the owner's
        uuid will be correct as long as the user exists in the system.

        :param mail: mail to analyze
        :type mail: email.message.Message

        :returns: a tuple of (owner, uuid)
        :rtype: tuple(str or None, str or None)
        """
        owner = mail["To"]
        uuid = None

        delivereds = mail.get_all("Delivered-To")
        for to in delivereds:
            name, addr = email.utils.parseaddr(to)
            parts = addr.split("@")
            if len(parts) > 1 and parts[1] == self._domain:
                uuid = parts[0]
                break

        if owner is None:  # default to Delivered-To
            owner = mail["Delivered-To"]
        if owner is None:
            log.err("Malformed mail, neither To: nor "
                    "Delivered-To: field")

        return owner, uuid

    def _process_incoming_email(self, otherself, filepath, mask):
        """
        Callback that processes incoming email.

        :param otherself: Watch object for the current callback from
                          inotify.
        :type otherself: twisted.internet.inotify._Watch
        :param filepath: Path of the file that changed
        :type filepath: twisted.python.filepath.FilePath
        :param mask: identifier for the type of change that triggered
                     this callback
        :type mask: int
        """
        try:
            if os.path.split(filepath.dirname())[-1]  == "new":
                log.msg("Processing new mail at %s" % (filepath.path,))
                with filepath.open("r") as f:
                    mail_data = f.read()
                    mail = message_from_string(mail_data)
                    owner, uuid = self._get_owner(mail)
                    if owner is None:
                        # This shouldn't happen, may be a bug in
                        # postfix? But we don't want to drop mail just
                        # because of a bug. Skipping this one...
                        return
                    log.msg("Mail owner: %s %s" % (owner, uuid))

                    if uuid is None:
                        log.msg("BUG: There was no uuid!")
                        return

                    d = self._users_cdb.getPubKey(uuid)
                    d.addCallbacks(self._encrypt_message, log.err,
                                   (uuid, owner, mail_data))
                    d.addCallbacks(self._export_message, log.err)
                    d.addCallbacks(self._conditional_remove, log.err,
                                   (filepath,))
                    d.addErrback(log.err)
        except Exception:
            log.err()
