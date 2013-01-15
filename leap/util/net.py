#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
net.py
-------
Utilities for networking.

@authors: Isis Agora Lovecruft, <isis@leap.se> 0x2cdb8b35
@license: see included LICENSE file
@copyright: 2013 Isis Agora Lovecruft
'''

import ipaddr
import sys
import socket

from random import randint

from leap.mx.utils import log


PLATFORMS = {'LINUX': sys.platform.startswith("linux"),
             'OPENBSD': sys.platform.startswith("openbsd"),
             'FREEBSD': sys.platform.startswith("freebsd"),
             'NETBSD': sys.platform.startswith("netbsd"),
             'DARWIN': sys.platform.startswith("darwin"),
             'SOLARIS': sys.platform.startswith("sunos"),
             'WINDOWS': sys.platform.startswith("win32")}


class UnsupportedPlatform(Exception):
    """Support for this platform is not currently available."""

class IfaceError(Exception):
    """Could not find default network interface."""

class PermissionsError(SystemExit):
    """This test requires admin or root privileges to run. Exiting..."""


def getClientPlatform(platform_name=None):
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name, test

def getPosixIfaces():
    from twisted.internet.test import _posixifaces
    log.msg("Attempting to discover network interfaces...")
    ifaces = _posixifaces._interfaces()
    return ifaces

def getWindowsIfaces():
    from twisted.internet.test import _win32ifaces
    log.msg("Attempting to discover network interfaces...")
    ifaces = _win32ifaces._interfaces()
    return ifaces

def getIfaces(platform_name=None):
    client, test = getClientPlatform(platform_name)
    if client:
        if client == ('LINUX' or 'DARWIN') or client[-3:] == 'BSD':
            return getPosixIfaces()
        elif client == 'WINDOWS':
            return getWindowsIfaces()
        ## XXX fixme figure out how to get iface for Solaris
        else:
            raise UnsupportedPlatform
    else:
        raise UnsupportedPlatform

def getRandomUnusedPort(addr=None):
    free = False
    while not free:
        port = randint(1024, 65535)
        s = socket.socket()
        try:
            s.bind((addr, port))
            free = True
        except:
            pass
        s.close()
    return port

def getNonLoopbackIfaces(platform_name=None):
    try:
        ifaces = getIfaces(platform_name)
    except UnsupportedPlatform, up:
        log.err(up)

    if not ifaces:
        log.msg("Unable to discover network interfaces...")
        return None
    else:
        found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
        log.debug("Found non-loopback interfaces: %s" % found)
        for iface in ifaces:
            try:
                interface = checkInterfaces(found)
            except IfaceError, ie:
                log.err(ie)
                return None
            else:
                return interfaces


def getLocalAddress():
    default_iface = getDefaultIface()
    return default_iface.ipaddr
