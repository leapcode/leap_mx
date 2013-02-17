#! -*- encoding: utf-8 -*-
"""
Config file utilities.

This module has an :attr:`config_filename`, which can be used to set the
filename outside of function calls:

    >>> from leap.mx.util import config
    >>> config.config_filename = "blahblah.yaml"

If not set anywhere, it will default to using the top level repository
directory, i.e. "/.../leap_mx/leap_mx.conf", and will create that file with
the default settings if it does not exist.

The config file can be loaded/created with :func:`config.loadConfig`:

    >>> config.loadConfig()

Once the config file is loaded, this module presents a highly object-oriented
interface, so that sections taken from the config file become attribute of
this module, and the name of their respective settings become attributes of
the section names. Like this:

    >>> print config.basic.postfix_port
    465

@authors: Isis Lovecruft, <isis@leap.se> 0x2cdb8b35
@version: 0.0.1
@license: see included LICENSE file
"""

from os import path as ospath

import sys
import yaml

from leap.mx.util       import version, storage
from leap.mx.exceptions import MissingConfig, UnsupportedOS


filename       = None
config_version = None
basic          = storage.Storage()
couch          = storage.Storage()
advanced       = storage.Storage()

PLATFORMS = {'LINUX': sys.platform.startswith("linux"),
             'OPENBSD': sys.platform.startswith("openbsd"),
             'FREEBSD': sys.platform.startswith("freebsd"),
             'NETBSD': sys.platform.startswith("netbsd"),
             'DARWIN': sys.platform.startswith("darwin"),
             'SOLARIS': sys.platform.startswith("sunos"),
             'WINDOWS': sys.platform.startswith("win32")}

def getClientPlatform(platform_name=None):
    """
    Determine the client's operating system platform. Optionally, if
    :param:`platform_name` is given, check that this is indeed the platform
    we're operating on.

    @param platform_name: A string, upper-, lower-, or mixed case, of one
              of the keys in the :attr:`leap.util.version.PLATFORMS`
              dictionary. E.g.  'Linux' or 'OPENBSD', etc.
    @returns: A string specifying the platform name, and the boolean test
              used to determine it.
    """
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name, test

def _create_config_file(conffile):
    """
    Create the config file if it doesn't exist.

    @param conffile: The full path to the config file to write to.
    """
    with open(conffile, 'w+') as conf:
        conf.write("""
#
# mx.conf
# =======
# Configurable options for the leap_mx encrypting mail exchange.
#
# This file follows YAML markup format: http://yaml.org/spec/1.2/spec.html
# Keep in mind that indentation matters.
#

basic:
    # Whether or not to log to file:
    enable_logfile: True
    # The name of the logfile:
    logfile: mx.log
    # Where is the spoolfile of messages to encrypt?:
    spoolfile: /var/mail/encrypt_me
couch:
    # The couch username for authentication to a CouchDB instance:
    user: admin
    # The couch username's password:
    passwd: passwd
    # The CouchDB hostname or IP address to connect to:
    host: couchdb.example.com
    # The CouchDB port to connect to:
    port: 7001
advanced:
    # Which port on localhost should postfix send check_recipient queries to?:
    check_recipient_access_port: 1347
    # Which port on localhost should postfix ask for UUIDs?:
    virtual_alias_map_port: 1348
    # Enable debugging output in the logger:
    debug: True
    # Print enough things really fast to make you look super 1337:
    noisy: False
config_version: 0.0.2

""")
        conf.flush()
    assert ospath.isfile(conffile), "Config file %s not created!" % conffile

def _get_config_location(config_filename=None,
                         use_dot_config_directory=False):
    """
    Get the full path and filename of the config file.
    """
    platform = getClientPlatform()[0]

    ## If not given, default to the application's name + '.conf'
    if not config_filename:
        if not filename:
            config_filename = "mx.conf"
        else:
            config_filename = filename

    ## Oh hell, it could be said only to beguile:
    ## That windoze users are capable of editing a .conf file.
    ## Also, what maddened wingnut would be so fool
    ## To run a mail exchange on a windoze nodule?
    ## I'm ignoring these loons for now. And pardon if I seem jaded,
    ## But srsly, this and that solaris sh*t should be deprecated.
    if not platform.endswith('LINUX') and not platform.endswith('BSD'):
        raise UnsupportedOS("Sorry, your operating system isn't supported.")

    where = None
    if use_dot_config_directory:
        ## xxx only install/import this in *nix
        from xdg import BaseDirectory

        dot_config_dirs = BaseDirectory.xdg_config_dirs
        for dir in dot_config_dirs:
            our_dir = ospath.join(dir, package_name)
            if ospath.isdir(our_dir):
                if config_filename in os.listdir(our_dir):
                    where = ospath.abspath(our_dir)
    ## Use repo dir instead:
    if not where:
        where = version.getRepoDir()

    conffile = ospath.join(where, config_filename)
    try:
        with open(conffile) as cf: pass
    except IOError:
        _create_config_file(conffile)
    finally:
        return conffile

def loadConfig(file=None):
    """
    Some of this is taken from OONI config code for now, and so this should be
    refacotored, along with the leap_client config code, so that we have
    similarly structured config files. It is perhaps desirable to also use
    soledad as a backend for remote setup and maintainance, and thus this code
    will need to hook into u1db (and potentially "pysqlcipher").

    Excuse the yaml for now, I just wanted something that works.

    @param file: (optional) If provided, use this filename.
    """
    if not file:
         file = _get_config_location()

    if ospath.isfile(file):
        with open(file, 'a+') as conf:
            config_contents = '\n'.join(conf.readlines())
            cfg = yaml.safe_load(config_contents)

            ## These become objects with their keys loaded as attributes:
            ##
            ##     from leap.util import config
            ##     config.basic.foo = bar
            ##
            try: 
                for k, v in cfg['basic'].items(): 
                    basic[k] = v
            except (AttributeError, KeyError): pass

            try: 
                for k, v in cfg['advanced'].items(): 
                    advanced[k] = v
            except (AttributeError, KeyError): pass

            try: 
                for k, v in cfg['couch'].items(): 
                    couch[k] = v
            except (AttributeError, KeyError): pass

            if 'config_version' in cfg:
                config_version = cfg['config_version']
            else:
                config_version = 'unknown'

            return basic, couch, advanced, config_version
    else:
        raise MissingConfig("Could not load config file.")


## This is the name of the config file to use:
## If not set, it defaults to 'leap_mx/leap_mx.conf'
if not filename:
    filename = _get_config_location()
else:
    filename = _get_config_location(config_filename=filename)
