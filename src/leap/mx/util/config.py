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

## xxx only install/import this in *nix
from xdg import BaseDirectory

from leap.util import log, version, Storage
from leap.util.exceptions import MissingConfig, UnsupportedOS


def _create_config_file(file):
    """
    xxx fill me in
    """
    with open(file, 'w+') as conf:
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
    # Where is the spoolfile of messages to encrypt?:
    spoolfile: /var/mail/encrypt_me
advanced:
    # Which port on localhost should postfix send check_recipient queries to?:
    check_recipient_access_port: 1347
    # Which port on localhost should postfix ask for UUIDs?:
    virtual_alias_map_port: 1348
    # Enable debugging output in the logger:
    debug: true
    # Print enough things really fast to make you look super 1337:
    noisy: false

""")
        conf.flush()
    try:
        assert os.path.isfile(file), "Config file %s not created!" % file
    except AssertionError, ae:
        raise SystemExit(ae.message)
    else:
        return file

def _get_config_filename(filename=None, use_dot_config_directory=False):
    """
    Get the full path and filename of the config file.
    """
    platform = version.getClientPlatform()[0]
    resource = version.name

    ## Oh hell, it could be said only to beguile:
    ## That windoze users are capable of editing a .conf file.
    ## Also, what maddened wingnut would be so fool
    ## To run a mail exchange on a windoze nodule?
    ## I'm ignoring these loons for now. And pardon if I seem jaded,
    ## But srsly, this and that solaris sh*t should be deprecated.
    if not platform.endswith('LINUX') and not platform.endswith('BSD'):
        raise UnsupportedOS("Sorry, your operating system isn't supported.")

    ## If not given, default to the application's name + '.conf'
    if not filename:
        filename = resource + ".conf"

    where = None
    if not use_dot_config_directory:
        repo_dir = version.getRepoDir()
        where = os.path.abspath(repo_dir)
    ## Use ~/.config/ instead:
    else:
        dot_config_dirs = BaseDirectory.xdg_config_dirs
        for dir in dot_config_dirs:
            our_dir = os.path.join(dir, resource)
            if os.path.isdir(our_dir):
                if filename in os.listdir(our_dir):
                    where = os.path.abspath(our_dir)
        if not where:
            where = BaseDirectory.save_config_path(resource)

    conffile = os.path.join(where, filename)
    try:
        with open(conffile) as cf: pass
    except IOError:
        conffile = _create_config_file(conffile)
    finally:
        return conffile

def loadConfig(filename=config_filename):
    """
    Some of this is taken from OONI config code for now, and so this should be
    refacotored, along with the leap_client config code, so that we have
    similarly structured config files. It is perhaps desirable to also use
    soledad as a backend for remote setup and maintainance, and thus this code
    will need to hook into u1db (and potentially "pysqlcipher").

    Excuse the yaml for now, I just wanted something that works.

    @param filename: (optional) If provided, use this filename.
    """
    if not filename:
         filename = _get_config_filename()

    if os.path.isfile(filename):
        with open(filename, 'a+') as conf:
            config_contents = '\n'.join(conf.readlines())
            configuration = yaml.safe_load(config_contents)

            ## These become objects with their keys loaded as attributes:
            ##
            ##     from leap.util import config
            ##     config.basic.foo = bar
            ##
            basic = Storage()
            try:
                for k, v in configuration['basic'].items():
                    basic[k] = v
            except AttributeError:
                pass

            advanced = Storage()
            try:
                for k, v in configuration['advanced'].items():
                    advanced[k] = v
            except AttributeError:
                pass

            return basic, advanced
    else:
        raise MissingConfig("Could not load config file.")


## This is the name of the config file to use:
## If not set, it defaults to 'leap_mx/leap_mx.conf'
if not config_filename:
    config_filename = _get_config_filename()
else:
    config_filename = _get_config_filename(filename=config_filename)

