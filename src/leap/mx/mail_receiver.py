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
MailReceiver service definition. This service monitors the incoming mail and
process it.

The MailReceiver service is configured to process incoming any skipped mail
every half an hour, and also on service start. It can be forced to start
processing by sending SIGUSR1 to the process.

If there's a user facing problem when processing an email, it will be
bounced back to the sender.

User facing problems could be:
- Unknown user (missing uuid)
- Public key not found

Any other problem is a bug, which will be logged. Until the bug is
fixed, the email will stay in there waiting.
"""
import os
import uuid as pyuuid
import signal

import json
import email.utils
import socket

from email import message_from_string
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Utils import formatdate
from email.header import decode_header

from twisted.application.service import Service, IService
from twisted.internet import inotify, defer, task, reactor
from twisted.python import filepath, log

from zope.interface import implements

from leap.soledad.common.crypto import (
    EncryptionSchemes,
    ENC_JSON_KEY,
    ENC_SCHEME_KEY,
)
from leap.soledad.common.couch import CouchDatabase, CouchDocument
from leap.keymanager import openpgp

BOUNCE_TEMPLATE = """
Delivery to the following recipient failed:
    {0}

Reasons:
    {1}

Original message:
    {2}
""".strip()


from twisted.internet import protocol
from twisted.internet.error import ProcessDone


class BouncerSubprocessProtocol(protocol.ProcessProtocol):
    """
    Bouncer subprocess protocol that will feed the msg contents to be
    bounced through stdin
    """

    def __init__(self, msg):
        """
        Constructor for the BouncerSubprocessProtocol

        :param msg: Message to send to stdin when the process has
                    launched
        :type msg: str
        """
        self._msg = msg
        self._outBuffer = ""
        self._errBuffer = ""
        self._d = None

    def connectionMade(self):
        self._d = defer.Deferred()

        self.transport.write(self._msg)
        self.transport.closeStdin()

    def outReceived(self, data):
        self._outBuffer += data

    def errReceived(self, data):
        self._errBuffer += data

    def processEnded(self, reason):
        if reason.check(ProcessDone):
            self._d.callback(self._outBuffer)
        else:
            self._d.errback(reason)


def async_check_output(args, msg):
    """
    Async spawn a process and return a defer to be able to check the
    output with a callback/errback

    :param args: the command to execute along with the params for it
    :type args: list of str
    :param msg: string that will be send to stdin of the process once
                it's spawned
    :type msg: str

    :rtype: defer.Deferred
    """
    pprotocol = BouncerSubprocessProtocol(msg)
    reactor.spawnProcess(pprotocol, args[0], args)
    return pprotocol.d


class MailReceiver(Service):
    """
    Service that monitors incoming email and processes it.
    """
    implements(IService)

    INCOMING_KEY = 'incoming'
    ERROR_DECRYPTING_KEY = "errdecr"
    PROCESS_SKIPPED_INTERVAL = 60 * 30  # every half an hour

    """
    If there's a failure when trying to watch a directory for file creation,
    the service will schedule a retry delayed by the following amount of time.
    """
    RETRY_DIR_WATCH_DELAY = 60 * 5  # 5 minutes

    def __init__(self, mail_couch_url, users_cdb, directories, bounce_from,
                 bounce_subject):
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

        :param bounce_from: Email address of the bouncer
        :type bounce_from: str

        :param bounce_subject: Subject line used in the bounced mail
        :type bounce_subject: str
        """
        # IService doesn't define an __init__
        self._mail_couch_url = mail_couch_url
        self._users_cdb = users_cdb
        self._directories = directories
        self._bounce_from = bounce_from
        self._bounce_subject = bounce_subject

        self._domain = socket.gethostbyaddr(socket.gethostname())[0]
        self._processing_skipped = False

    def startService(self):
        """
        Starts the MailReceiver service
        """
        Service.startService(self)
        self.wm = inotify.INotify()
        self.wm.startReading()

        # watch mail directories for new files to trigger processing of
        # incoming mail
        for directory, recursive in self._directories:
            self._start_watching_dir(directory, recursive)

        # schedule a periodic task to process skipped mail, and also run it
        # immediatelly
        self._lcall = task.LoopingCall(self._process_skipped)
        self._lcall.start(interval=self.PROCESS_SKIPPED_INTERVAL, now=True)

        # catch SIGUSR1 to trigger processing of skipped mail
        signal.signal(
            signal.SIGUSR1,
            lambda *_: self._process_skipped())

    def stopService(self):
        """
        Stop the MailReceiver service
        """
        self.wm.stopReading()
        self._lcall.stop()

    def _start_watching_dir(self, dirname, recursive):
        """
        Start watching a directory to trigger processing of newly created
        files.

        Will also add a delayed call to retry when failed for some reason.
        """
        directory = filepath.FilePath(dirname)
        try:
            if not directory.isdir():
                raise OSError("Not a directory: '%s'" % directory.path)
            self.wm.watch(
                directory,
                inotify.IN_CREATE,
                callbacks=[self._process_incoming_email],
                recursive=recursive)
            log.msg("Watching %r --- Recursive: %r" % (directory, recursive))
        except Exception as e:
            log.msg(
                "Failed adding watch to %s, will try again in %s seconds: %s"
                % (directory, self.RETRY_DIR_WATCH_DELAY, e))
            reactor.callLater(
                self.RETRY_DIR_WATCH_DELAY,
                self._start_watching_dir,
                dirname,
                recursive)

    def _encrypt_message(self, pubkey, message):
        """
        Given a public key and a message, it encrypts the message to
        that public key.
        The address is needed in order to build the OpenPGPKey object.

        :param pubkey: public key for the owner of the message
        :type pubkey: str
        :param message: message contents
        :type message: email.message.Message

        :return: doc to sync with Soledad or None, None if something
                 went wrong.
        :rtype: CouchDocument
        """
        if pubkey is None or len(pubkey) == 0:
            log.msg("_encrypt_message: Something went wrong, here's all "
                    "I know: %r" % (pubkey,))
            return None

        # find message's encoding
        message_as_string = message.as_string()

        doc = CouchDocument(doc_id=str(pyuuid.uuid4()))

        # store plain text if pubkey is not available
        data = {'incoming': True, 'content': message_as_string}
        if pubkey is None or len(pubkey) == 0:
            doc.content = {
                self.INCOMING_KEY: True,
                self.ERROR_DECRYPTING_KEY: False,
                ENC_SCHEME_KEY: EncryptionSchemes.NONE,
                ENC_JSON_KEY: json.dumps(data,
                                         ensure_ascii=False)
            }
            return doc

        # otherwise, encrypt
        with openpgp.TempGPGWrapper(gpgbinary='/usr/bin/gpg') as gpg:
            gpg.import_keys(pubkey)
            key = gpg.list_keys().pop()

            # add X-Leap-Provenance header if message is not encrypted
            if message.get_content_type() != 'multipart/encrypted' and \
                    '-----BEGIN PGP MESSAGE-----' not in \
                    message_as_string:
                message.add_header(
                    'X-Leap-Provenance',
                    email.utils.formatdate(),
                    pubkey=key["keyid"])
                data = {'incoming': True, 'content': message.as_string()}
            doc.content = {
                self.INCOMING_KEY: True,
                self.ERROR_DECRYPTING_KEY: False,
                ENC_SCHEME_KEY: EncryptionSchemes.PUBKEY,
                ENC_JSON_KEY: str(gpg.encrypt(
                    json.dumps(data, ensure_ascii=False),
                    key["fingerprint"],
                    symmetric=False))
            }

        return doc

    def _export_message(self, uuid, doc):
        """
        Given a UUID and a CouchDocument, it saves it directly in the
        couchdb that serves as a backend for Soledad, in a db
        accessible to the recipient of the mail.

        :param uuid: the mail owner's uuid
        :type uuid: str
        :param doc: CouchDocument that represents the email
        :type doc: CouchDocument

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

    @defer.inlineCallbacks
    def _bounce_mail(self, orig_msg, filepath, reason):
        """
        Bounces the email contained in orig_msg to it's sender and
        removes it from the queue.

        :param orig_msg: Message that is going to be bounced
        :type orig_msg: email.message.Message
        :param filepath: Path for that message
        :type filepath: twisted.python.filepath.FilePath
        :param reason: Brief explanation about why it's being bounced
        :type reason: str
        """
        to = orig_msg.get("From")

        msg = MIMEMultipart()
        msg['From'] = self._bounce_from
        msg['To'] = to
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = self._bounce_subject

        decoded_to = " ".join([x[0] for x in decode_header(to)])
        text = BOUNCE_TEMPLATE.format(decoded_to,
                                      reason,
                                      orig_msg.as_string())

        msg.attach(MIMEText(text))

        yield async_check_output(["/usr/sbin/sendmail", "-t"], msg.as_string())
        yield self._conditional_remove(True, filepath)

    def sleep(self, secs):
        """
        Async sleep for a defer. Use this when you want to wait for
        another (non atomic) defer to finish.

        :param secs: seconds to wait (not really accurate, it depends
                     on the event queue)
        :type secs: int

        :rtype: twisted.internet.defer.Deferred
        """
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
        try:
            log.msg("Starting processing skipped mail...")
            log.msg("-" * 50)

            for directory, recursive in self._directories:
                for root, dirs, files in os.walk(directory):
                    for fname in files:
                        try:
                            fullpath = os.path.join(root, fname)
                            fpath = filepath.FilePath(fullpath)
                            yield self._step_process_mail_backend(fpath)
                        except Exception:
                            log.msg("Error processing skipped mail: %r" %
                                    (fullpath,))
                            log.err()
                    if not recursive:
                        break
        except Exception:
            log.msg("Error processing skipped mail")
            log.err()
        finally:
            self._processing_skipped = False

        log.msg("+" * 50)
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
            msg = message_from_string(mail_data)
            uuid = self._get_owner(msg)
            if uuid is None:
                log.msg("Don't know how to deliver mail %r, skipping..." %
                        (filepath.path,))
                bounce_reason = "Missing UUID: There was a problem " \
                                "locating the user in our database."
                yield self._bounce_mail(msg, filepath, bounce_reason)
                defer.returnValue(None)
            log.msg("Mail owner: %s" % (uuid,))

            if uuid is None:
                log.msg("BUG: There was no uuid!")
                defer.returnValue(None)

            pubkey = yield self._users_cdb.getPubKey(uuid)
            if pubkey is None or len(pubkey) == 0:
                log.msg("No public key, stopping the processing chain")
                bounce_reason = "Missing PubKey: There was a problem " \
                                "locating the user's public key in our " \
                                "database."
                yield self._bounce_mail(msg, filepath, bounce_reason)
                defer.returnValue(None)

            log.msg("Encrypting message to %s's pubkey" % (uuid,))
            doc = yield self._encrypt_message(pubkey, msg)

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
                log.msg("Waiting for the process of skipped mail to be "
                        "done...")
                yield self.sleep(10)  # NO-OP
            if os.path.split(filepath.dirname())[-1] == "new":
                yield self._step_process_mail_backend(filepath)
        except Exception as e:
            log.msg("Something went wrong while processing {0!r}: {1!r}"
                    .format(filepath, e))
            log.err()
