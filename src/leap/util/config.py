#! -*- encoding: utf-8 -*-
"""
xxx fill me in
"""
import os
import yaml

from leap.util import log, version

config_filename = 'mx.conf'

class MissingConfig(Exception):
    """Raised when the config file cannot be found."""
    def __init__(self, message=None, config_file=None):
        if message:
            return
        else:
            self.message  = "Cannot locate config file"
            if config_file:
                self.message += " %s" % config_file
            self.message += "."

def getConfigFilename(dir=None, file=None):
    """
    xxx fill me in
    """
    if not dir:
        dir = version.getRepoDir()
    if not file:
        file = config_filename
    return os.path.join(dir, file)

def createConfigFile(config_file=None):
    """
    xxx fill me in
    """
    if not config_file:
        config_file = getConfigFilename()

    if not os.path.isfile(config_file):
        with open(config_file, 'w+') as conf:
            conf.write("""
#
# mx.conf
# =======
# Configurable options for the leap_mx encrypting mail exchange.
#
""")
            conf.flush()
    else:
        log.debug("Config file %s already present." % config_file)

def loadConfigFile(config_file=None):
    """
    xxx fill me in
    """
    if not config_file:
        config_file = getConfigFilename()

    if os.path.isfile(config_file):
        with open(config_file, 'a+') as conf:
            config_contents = '\n'.join(conf.readlines())
            configuration = yaml.safe_load(config_contents)
    else:
        createConfigFile(config_file)

    ## xxx finish load config
    ## ask kali if we're using yaml or json or what?
    ## xxx kali says json, so ixnay on the amlya bits
