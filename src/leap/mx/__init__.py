#-*- encoding: utf-8 -*-
"""
leap/mx/__init__.py
-------------------
Module initialization file for leap.mx .
"""
from leap.mx.util import version

__all__ = ['alias_resolver', 'couchdb', 'exceptions', 'runner', 'util']
__author__ = version.getAuthors()
__version__ = version.getVersion()
