#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
   ____
  | mx |
  |____|_______________________
     |                         |
     | An encrypting remailer. |
     |_________________________|

@author Isis Agora Lovecruft <isis@leap.se>, 0x2cdb8b35
@version 0.0.1

"""

from os  import getcwd
from os  import path as ospath

import sys

application_name = "leap_mx"

def __get_dirs__():
    """Get the absolute path of the top-level repository directory."""
    here = getcwd()
    base = here.rsplit(application_name, 1)[0]
    repo = ospath.join(base, application_name)
    leap = ospath.join(repo, 'src')
    ours = ospath.join(leap, application_name.replace('_', '/'))
    return repo, leap, ours


if __name__ == "__main__":
    ## Set the $PYTHONPATH:
    repo, leap, ours = __get_dirs__()
    sys.path[:] = map(ospath.abspath, sys.path)
    sys.path.insert(0, leap)

    ## Now we should be able to import ourselves without installation:
    try:
        from leap.mx      import runner
        from leap.mx.util import config, log, version
    except ImportError, ie:
        print "%s\nExiting...\n" % ie.message
        sys.exit(1)

    config.filename = 'mx.conf'
    config.loadConfig()

    ## xxx fixme version requires twisted...
    dependency_check = runner.CheckRequirements(version.getPackageName(),
                                                version.getPipfile())

    from twisted.python   import usage, runtime
    from twisted.internet import reactor

    if config.basic.enable_logfile:
        logfilename = config.basic.logfile
        logfilepath = ospath.join(repo, 'logs')
        log.start(logfilename, logfilepath)
    else:
        log.start()

    log.msg("Testing logging functionality")
    log.debug("Running %s, with Python %s"
              % (application_name, runtime.shortPythonVersion()))
    log.debug("Platform: %s" % runtime.platform.getType())
    log.debug("Thread support: %s" % str(runtime.platform.supportsThreads()))

    mx_options = MXOptions()
    mx_options.parseOptions(sys.argv)

    if len(sys.argv) <= 0:
        print mx_options.getUsage()
        sys.exit(0)
    else:
        options = mx_options

    if options['verbose']:
        config.basic.debug = True

    if options['test']:
        from leap.mx import tests ## xxx this needs an __init__.py
        tests.run()               ## xxx need /leap/mx/tests.py
    elif options['conf'] and os.path.isfile(options['conf']):
        config.parse()
        runner.run()
    else:
        mx_options.getUsage()
        sys.exit(1)
