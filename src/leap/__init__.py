# -*- encoding: utf-8 -*-

__all__     = ['mx']
__author__  = version.authors
__version__ = version.getVersion()

from leap import mx
from leap.mx import util
from leap.mx.util import version


def _print_authors_nicely():
    if hasattr(version, 'authors'):
        assert isinstance(version.authors, list)
        if len(version.authors) > 0:
            first = version.authors.pop()
            __author__ = (" ".join(first[:2]))
            if len(version.authors) > 0:
                for auth in version.authors:
                    joined = " ".join(auth[:2])
                    __author__ += ("\n%s" % joined)
                    

print "Version: %s" % version.getVersion()
print "Authors: %s" % _print_authors_nicely()
