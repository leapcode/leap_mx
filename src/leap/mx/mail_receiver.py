import os
import pyinotify
import logging
import argparse
import ConfigParser

from email import message_from_string

logger = logging.getLogger(name='leap_mx')


def _get_uuid(uid, user, password, server):
    # TODO: implement!
    return ""


def _get_pubkey(uuid, user, password, server):
    # TODO: implent!
    return ""

def _encrypt_message(pubkey, message):
    # TODO: implement!
    return message


def _export_message(uuid, message, user, password, server):
    # TODO: Implement!
    return True

# <Event dir=False mask=0x100 maskname=IN_CREATE name=1366132684.P9922.delloise path=Maildir/tmp pathname=Maildir/tmp/1366132684.P9922.delloise wd=2 >
# <Event dir=False mask=0x20 maskname=IN_OPEN name=1366132684.P9922.delloise path=Maildir/tmp pathname=Maildir/tmp/1366132684.P9922.delloise wd=2 >
# <Event dir=False mask=0x2 maskname=IN_MODIFY name=1366132684.P9922.delloise path=Maildir/tmp pathname=Maildir/tmp/1366132684.P9922.delloise wd=2 >
# <Event dir=False mask=0x8 maskname=IN_CLOSE_WRITE name=1366132684.P9922.delloise path=Maildir/tmp pathname=Maildir/tmp/1366132684.P9922.delloise wd=2 >
# <Event dir=False mask=0x100 maskname=IN_CREATE name=1366132684.V14I40088dM542424.delloise path=Maildir/new pathname=Maildir/new/1366132684.V14I40088dM542424.delloise wd=4 >
# <Event dir=False mask=0x200 maskname=IN_DELETE name=1366132684.P9922.delloise path=Maildir/tmp pathname=Maildir/tmp/1366132684.P9922.delloise wd=2 >

class EventHandler(pyinotify.ProcessEvent):
    def __init__(self, user, password, server, *args, **kwargs):
        pyinotify.ProcessEvent.__init__(self, *args, **kwargs)
        self._user = user
        self._password = password
        self._server = server

    def process_IN_CREATE(self, event):
        if os.path.split(event.path)[-1]  == "new":
            logger.debug("Processing new mail at %s" % (event.pathname,))
            with open(event.pathname, "r") as f:
                mail_data = f.read()
                mail = message_from_string(mail_data)
                owner = mail["Delivered-To"]
                logger.debug("%s received a new mail" % (owner,))
                # get user uuid
                uuid = _get_uuid(owner, self._user, self._password, self._server)
                # get the pubkey for uuid
                pubkey = _get_pubkey(uuid, self._user, self._password, self._server)
                # if the message isn't encrypted already:
                #     encrypt the message to the pubkey
                encrypted = _encrypt_message(pubkey, mail_data)
                # save the message in a couchdb
                if _export_message(uuid, encrypted, self._user, self._password, self._server):
                    # remove the original mail
                    try:
                        os.remove(event.pathname)
                    except Exception as e:
                        # TODO: better handle exceptions
                        logger.error(e.message())

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
        config_file = "mail_receiver.cfg"

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

    user = config.get("couchdb", "user")
    password = config.get("couchdb", "password")
    server = config.get("couchdb", "server")

    wm = pyinotify.WatchManager()
    mask = pyinotify.IN_CREATE
    handler = EventHandler(user, password, server)
    notifier = pyinotify.Notifier(wm, handler)

    for section in config.sections():
        if section in ("couchdb"):
            continue
        to_watch = config.get(section, "path")
        recursive = config.getboolean(section, "recursive")
        logger.debug("Watching %s --- Recursive: %s" % (to_watch, recursive))
        wm.add_watch(to_watch, mask, rec=recursive)

    notifier.loop()

if __name__ == "__main__":
    main()
