# -*- encoding: utf-8 -*-
'''
log.py
------
Logging for leap_mx.

@authors: Isis Agora Lovecruft, <isis@leap.se> 0x2cdb8b35
@licence: see included LICENSE file
@copyright: 2013 Isis Agora Lovecruft
'''

from datetime  import datetime
from functools import wraps

import logging
import os
import sys
import time
import traceback

from twisted.python import log  as txlog
from twisted.python import util as txutil
from twisted.python import logfile as txlogfile
from twisted.python.failure import Failure

from leap.mx.util import version, config


class InvalidTimestampFormat(Exception):
    pass

class UnprefixedLogfile(txlog.FileLogObserver):
    """Logfile with plain messages, without timestamp prefixes."""
    def emit(self, eventDict):
        text = txlog.textFromEventDict(eventDict)
        if text is None:
            return

        txutil.untilConcludes(self.write, "%s\n" % text)
        txutil.untilConcludes(self.flush)


def utcDateNow():
    """The current date for UTC time."""
    return datetime.utcnow()

def utcTimeNow():
    """Seconds since epoch in UTC time, as type float."""
    return time.mktime(time.gmtime())

def dateToTime(date):
    """Convert datetime to seconds since epoch."""
    return time.mktime(date.timetuple())

def prettyDateNow():
    """Pretty string for the local time."""
    return datetime.now().ctime()

def utcPrettyDateNow():
    """Pretty string for UTC."""
    return datetime.utcnow().ctime()

def timeToPrettyDate(time_val):
    """Convert seconds since epoch to date."""
    return time.ctime(time_val)

def start(logfilename=None, logfiledir=None):
    """
    Start logging to stdout, and optionally to a logfile as well.

    @param logfile: The full path of the filename to store logs in.
    """
    txlog.startLoggingWithObserver(UnprefixedLogfile(sys.stdout).emit)

    if logfilename and logfiledir:
        if not os.path.isdir(logfiledir):
            os.makedirs(logfiledir)
        daily_logfile = txlogfile.DailyLogFile(logfilename, logfiledir)
        txlog.addObserver(txlog.FileLogObserver(daily_logfile).emit)

    txlog.msg("Starting %s, version %s, on %s UTC" % (version.getPackageName(),
                                                      version.getVersion(),
                                                      utcPrettyDateNow()))
    txlog.msg("Authors: %s" % version.getAuthors())

def msg(msg, *arg, **kwarg):
    """Log a message at the INFO level."""
    print "[*] %s" % msg

def debug(msg, *arg, **kwarg):
    """Log a message at the DEBUG level."""
    if config.basic.debug:
        print "[d] %s" % msg

def warn(msg, *arg, **kwarg):
    """Log a message at the WARN level."""
    if config.basic.show_warnings:
        txlog.logging.captureWarnings('true')
        print "[#] %s" % msg

def err(msg, *arg, **kwarg):
    """Log a message at the ERROR level."""
    print "[!] %s" % msg

def fail(*failure):
    """Log a message at the CRITICAL level."""
    logging.critical(failure)
    ## xxx should we take steps to exit here?

def exception(error):
    """
    Catch an exception and print only the error message, then continue normal
    program execution.

    @param error: Can be error messages printed to stdout and to the
    logfile, or can be a twisted.python.failure.Failure instance.
    """
    if isinstance(error, Failure):
        error.printTraceback()
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

def catch(func):
    """
    Quick wrapper to add around test methods for debugging purposes,
    catches the given Exception. Use like so:

        >>> @log.catch
            def foo(bar):
                if bar == 'baz':
                    raise Exception("catch me no matter what I am")
        >>> foo("baz")
        [!] catch me no matter what I am

    """
    @wraps(func)
    def _catch(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, exc:
            exception(exc)
    return _catch
