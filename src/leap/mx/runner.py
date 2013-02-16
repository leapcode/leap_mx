#-*- coding: utf-8 -*-
"""
runner
------
A module containing application and daemon process utilities.

@author Isis Agora Lovecruft <isis@leap.se>, 0x2cdb8b35
@version 0.0.1

"""

from os import path as ospath

import re


class CheckRequirements(ImportError):
    """
    Raised when we're missing something from requirements.pip.
    """
    def __init__(self, package_name, pipfile, message=None):
        """
        Display an error message with instructions for obtaining missing
        dependencies.

        @param message: A string describing the error.
        @param missing: A string indicating which dependency is missing.
        @param pipfile: The path and filename of the pip requirements file,
            relative to the top-level repository directory.
        """
        if message:
            self.message = message
            return self

        self.package_name = package_name
        self.pipfile      = pipfile
        self.dependencies = self.__read_pip_requirements__()
        self.missing      = []

        for package, version in self.dependencies:
            pkg = package.lower() if package == "Twisted" else package
            try:
                __import__(pkg)
            except ImportError:
                self.missing.append(package)

        if len(self.missing) > 0:
            self.message = self.package_name + " requires "
        elif len(self.missing) <= 0:
            return None

        if len(self.missing) >= 1:
            for missed in self.missing[:-1]:
                self.message += missed + ", "
            self.message += "and "

        if len(self.missing) == 1:
            self.message += self.missing[0] + "."
            self.message += "\nPlease see %s for ".format(self.pipfile)
            self.message += "instruction on installing dependencies."
            raise self(self.message)

    def __read_pip_requirements__(self, file=None):
        """
        Check the pip requirements file to determine our dependencies.

        @param file: The full path of the pip requirements.txt file.
        @returns: A list of tuple(package_name, package_version).
        """
        if not file:
            file = self.pipfile

        requirement  = re.compile('[^0-9=><]+')
        dependencies = []

        with open(file) as pipfile:
            for line in pipfile.readlines():
                shortened       = line.strip()
                matched         = requirement.match(shortened)
                package_name    = matched.group()
                package_version = shortened.split(package_name, 1)[1]
                dependencies.append((package_name, package_version))
        return dependencies
