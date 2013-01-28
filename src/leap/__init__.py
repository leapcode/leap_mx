# -*- encoding: utf-8 -*-

from leap import mx
from leap import util
from leap.util import version as mxversion

__all__     = ['mx', 'util']
__author__  = mxversion.authors
__version__ = mxversion.getVersion()

print "Authors: %s" % __author__
print "Version: %s" % __version__
