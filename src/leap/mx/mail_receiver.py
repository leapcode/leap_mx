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
from twisted.internet import inotify, defer, task
from twisted.python import filepath, log

from leap.common.mail import get_email_charset
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
        self._processing_skipped = False

    def startService(self):
        """
        Starts the MailReceiver service
        """
        Service.startService(self)
        self.wm = inotify.INotify()
        self.wm.startReading()

        mask = inotify.IN_CREATE

        for directory, recursive in self._directories:
            log.msg("Watching %r --- Recursive: %r" % (directory, recursive))
            self.wm.watch(filepath.FilePath(directory), mask,
                          callbacks=[self._process_incoming_email],
                          recursive=recursive)

        self._lcall = task.LoopingCall(self._process_skipped)
        # Run once every half an hour, but don't start right now
        self._lcall.start(interval=60*30, now=False)

    def _encrypt_message(self, pubkey, message):
        """
        Given a public key and a message, it encrypts the message to
        that public key.
        The address is needed in order to build the OpenPGPKey object.

        :param pubkey: public key for the owner of the message
        :type pubkey: str
        :param message: message contents
        :type message: str

        :return: doc to sync with Soledad or None, None if something
                 went wrong.
        :rtype: SoledadDocument
        """
        if pubkey is None or len(pubkey) == 0:
            log.msg("_encrypt_message: Something went wrong, here's all "
                    "I know: %r" % (pubkey,))
            return None

        doc = SoledadDocument(doc_id=str(pyuuid.uuid4()))

        encoding = get_email_charset(message.decode("utf8", "replace"),
                                     default=None)
        if encoding is None:
            result = chardet.detect(message)
            encoding = result["encoding"]

        data = {'incoming': True, 'content': message}

        if pubkey is None or len(pubkey) == 0:
            doc.content = {
                self.INCOMING_KEY: True,
                ENC_SCHEME_KEY: EncryptionSchemes.NONE,
                ENC_JSON_KEY: json.dumps(data, encoding=encoding)
            }
            return doc

        openpgp_key = None
        with openpgp.TempGPGWrapper(gpgbinary='/usr/bin/gpg') as gpg:
            gpg.import_keys(pubkey)
            key = gpg.list_keys().pop()
            # We don't care about the actual address, so we use a
            # dummy one, we just care about the import of the pubkey
            openpgp_key = openpgp._build_key_from_gpg("dummy@mail.com", key, pubkey)

            doc.content = {
                self.INCOMING_KEY: True,
                ENC_SCHEME_KEY: EncryptionSchemes.PUBKEY,
                ENC_JSON_KEY: str(gpg.encrypt(
                    json.dumps(data, encoding=encoding),
                    openpgp_key.fingerprint,
                    symmetric=False))
            }

        return doc

    def _export_message(self, uuid, doc):
        """
        Given a UUID and a SoledadDocument, it saves it directly in the
        couchdb that serves as a backend for Soledad, in a db
        accessible to the recipient of the mail.

        :param uuid: the mail owner's uuid
        :type uuid: str
        :param doc: SoledadDocument that represents the email
        :type doc: SoledadDocument

        :return: True if it's ok to remove the message, False
                 otherwise
        :rtype: bool
        """
        if uuid is None or doc is None:
            log.msg("_export_message: Something went wrong, here's all "
                    "I know: %r | %r" % (uuid, doc))
            return False

        log.msg("Exporting message for %s" % (uuid,))

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
                log.msg("Removing %r" % (filepath.path,))
                filepath.remove()
                log.msg("Done removing")
            except Exception:
                log.err()
        else:
            log.msg("Not removing %r" % (filepath.path,))

    def _get_owner(self, mail):
        """
        Given an email, returns the uuid of the owner.

        :param mail: mail to analyze
        :type mail: email.message.Message

        :returns: uuid
        :rtype: str or None
        """
        uuid = None

        delivereds = mail.get_all("Delivered-To")
        if delivereds is None:
            return None
        for to in delivereds:
            name, addr = email.utils.parseaddr(to)
            parts = addr.split("@")
            if len(parts) > 1 and parts[1] == self._domain:
                uuid = parts[0]
                break

        return uuid

    def sleep(self, secs):
        """
        Async sleep for a defer. Use this when you want to wait for
        another (non atomic) defer to finish.

        :param secs: seconds to wait (not really accurate, it depends
                     on the event queue)
        :type secs: int

        :rtype: twisted.internet.defer.Deferred
        """
        from twisted.internet import reactor
        d = defer.Deferred()
        reactor.callLater(secs, d.callback, None)
        return d

    @defer.inlineCallbacks
    def _process_skipped(self):
        """
        Recursively or not (depending on the configuration) process
        all the watched directories for unprocessed mail and try to
        process it.
        """
        if self._processing_skipped:
            defer.returnValue(None)

        self._processing_skipped = True
        log.msg("Starting processing skipped mail...")
        log.msg("-"*50)

        for directory, recursive in self._directories:
            for root, dirs, files in os.walk(directory):
                for fname in files:
                    fullpath = os.path.join(root, fname)
                    fpath = filepath.FilePath(fullpath)
                    yield self._step_process_mail_backend(fpath)

                if not recursive:
                    break

        self._processing_skipped = False
        log.msg("+"*50)
        log.msg("Done processing skipped mail")

    @defer.inlineCallbacks
    def _step_process_mail_backend(self, filepath):
        """
        Processes the email pointed by filepath in an async
        fashion. yield this method in another inlineCallbacks method
        or return it for it to be run.

        :param filepath: Path of the file that changed
        :type filepath: twisted.python.filepath.FilePath
        """
        log.msg("Processing new mail at %r" % (filepath.path,))
        with filepath.open("r") as f:
            mail_data = f.read()
            mail = message_from_string(mail_data)
            uuid = self._get_owner(mail)
            if uuid is None:
                log.msg("Don't know how to deliver mail %r, skipping..." %
                        (filepath.path,))
                defer.returnValue(None)
            log.msg("Mail owner: %s" % (uuid,))

            if uuid is None:
                log.msg("BUG: There was no uuid!")
                defer.returnValue(None)

            pubkey = yield self._users_cdb.getPubKey(uuid)
            if pubkey is None or len(pubkey):
                log.msg("No public key, stopping the processing chain")
                defer.returnValue(None)

            log.msg("Encrypting message to %s's pubkey" % (uuid,))
            doc = yield self._encrypt_message(pubkey, mail_data)

            do_remove = yield self._export_message(uuid, doc)
            yield self._conditional_remove(do_remove, filepath)

    @defer.inlineCallbacks
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
            while self._processing_skipped:
                log.msg("Waiting for the process of skipped mail to be done...")
                yield self.sleep(10)  # NO-OP
            if os.path.split(filepath.dirname())[-1]  == "new":
                yield self._step_process_mail_backend(filepath)
        except Exception as e:
            log.msg("Something went wrong while processing {0!r}: {1!r}"
                    .format(filepath, e))
