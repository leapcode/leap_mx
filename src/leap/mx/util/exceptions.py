#! -*- encoding: utf-8 -*-
"""
Custom exceptions for leap_mx.

@authors: Isis Lovecruft, <isis@leap.se> 0x2cdb8b35
@version: 0.0.1
@license: see included LICENSE file
"""


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

class UnsupportedOS(Exception):
    """Raised when we're not *nix or *BSD."""
