#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
log.py
------
Logging for leap_mx.

@authors: Isis Agora Lovecruft, <isis@leap.se> 0x2cdb8b35
@licence: see included LICENSE file
@copyright: 2013 Isis Agora Lovecruft
'''

from functools import wraps

import logging
import os
import sys
import traceback

from twisted.python import log  as txlog
from twisted.python import util as txutil
from twisted.python.logfile import DailyLogFile
from twisted.python.failure import Failure

from leap.util import version, config


class UnprefixedLogfile(txlog.FileLogObserver):
    def emit(self, eventDict):
        text = txlog.textFromEventDict(eventDict)
        if text is None:
            return

        txutil.untilConcludes(self.write, "%s\n" % text)
        txutil.untilConcludes(self.flush)


def start(logfile=None, application_name=None):
    if not application_name:
        application_name = version.name
    print "application name: %s" % application_name

    daily_logfile = None

    if not logfile:
        logfile = config.basic.logfile

    repo_dir = version.getRepoDir()
    logfile_dir = os.path.join(repo_dir, 'log')
    logfile_name = logfile

    daily_logfile = DailyLogFile(logfile_name, logfile_dir)

    txlog.startLoggingWithObserver(UnprefixedLogfile(sys.stdout).emit)
    txlog.addObserver(txlog.FileLogObserver(daily_logfile).emit)
    txlog.msg("Starting %s on %s (%s UTC)" % (application_name, 
                                              prettyDateNow(),
                                              utcPrettyDateNow()))
    ## xxx need these functions! ^^

def msg(msg, *arg, **kwarg):
    print "[*] %s" % msg

def debug(msg *arg, **kwarg):
    if config.basic.debug:
        print "[d] %s" % msg

def warn(msg, *arg, **kwarg):
    if config.basic.show_warnings:
        txlog.logging.captureWarnings('true')
        print "[#] %s" % msg

def err(msg, *arg, **kwarg):
    print "[!] %s" % msg

def fail(*failure):
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
