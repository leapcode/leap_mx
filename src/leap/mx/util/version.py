#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
version.py
----------
Version information for leap_mx.

@authors: Isis Agora Lovecruft, <isis@leap.se> 0x2cdb8b35
@licence: see included LICENSE file
@copyright: 2013 Isis Agora Lovecruft
'''

from os import getcwd
from os import path as ospath

import sys


class Version(object):
    def __init__(self):
        self.name    = 'leap_mx'
        self.version = '0.0.2'
        self.pipfile = ospath.join(self.getRepoDir(),
                                   'pkg/mx-requirements.pip')
        self.authors = [
            ('Isis Agora Lovecruft', '<isis@leap.se>', '0x2cdb8b35'),
            ]
        self.git_url = 'https://github.com/isislovecruft/leap_mx/'
        self.website = 'https://leap.se'

    def getPackageName(self):
        """Returns the application name."""
        return self.name

    def getPipfile(self):
        """Returns the full path of the pip requirements.txt file."""
        return self.pipfile

    def getVersion(self):
        """Returns a version the application name and version number."""
        return self.version

    def getAuthors(self):
        credits = str()
        for author in self.authors:
            credits += " ".join(author)
        return credits

    def getRepoDir(self):
        """Get the top-level repository directory."""
        here = getcwd()
        base = here.rsplit(self.name, 1)[0]
        repo = ospath.join(base, self.name)
        return repo

    def __make_text__(self, extra_text=None):
        splitr = "-" * len(self.version.__str__())
        header = ["\n%s\n" % self.version.__str__(),
                  "%s\n" % splitr]
        footer = ["Website: \t%s\n" % self.website,
                  "Github: \t%s\n" % self.git_url,
                  "\n"]
        contacts = ["\t%s, %s %s\n"
                    % (a[0], a[1], a[2]) for a in self.authors]
        contacts.insert(0, "Authors: ")

        with_contacts = header + contacts

        if extra_text is not None:
            if isinstance(extra_text, iter):
                with_contacts.extend((e for e in extra_text))
            elif isinstance(extra_text, str):
                with_contacts.append(extra_text)
            else:
                print "Couldn't add extra text..."

        text = with_contacts + footer
        return text

    def __update_version__(self):
        repo = self.getRepoDir()
        self.version_file = ospath.join(repo, 'VERSION')
        version_text = self.__make_text__()

        with open(self.version_file, 'w+') as fh:
            fh.writelines((line for line in version_text))
            fh.flush()
            fh.truncate()


if __name__ == "__main__":
    print "Generating new VERSION file..."
    vrsn = Version()
    vrsn.__update_version__()
    print "Done."
