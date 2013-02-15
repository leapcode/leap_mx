#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
   ____
  | mx |
  |____|_______________________
     |                         |
     | An encrypting remailer. |
     |_________________________|

@author Isis Agora Lovecruft <isis@leap.se>, 0x2cdb8b35
@version 0.0.1

"""

import os, sys


package_source   = "/src"
application_name = "leap_mx"

def __get_repo_dir__():
    """Get the absolute path of the top-level repository directory."""
    here = os.getcwd()
    repo = here.rsplit(package_source, 1)[0]
    leap = os.path.join(repo, package_source)
    this = os.path.join(leap, application_name.replace('_', '/'))
    return repo, leap, this

## Set the $PYTHONPATH:
repo, leap, this = __get_repo_dir__()
srcdir = os.path.join(repo, 'src/')
sys.path[:] = map(os.path.abspath, sys.path)
sys.path.insert(0, leap)

## Now we should be able to import ourselves without installation:
try:
    from leap.mx      import runner
    from leap.mx.util import log, version
except ImportError, ie:
    print "%s\nExiting..." % ie.message
    sys.exit(1)


class CheckRequirements(ImportError):
    """
    Raised when we're missing something from requirements.pip.
    """
    def __init__(self, message=None, missing=None, pipfile=None):
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

        self.pipfile = pipfile

        if isinstance(missing, str):
            missing = [missing]
        else:
            missing = []
            dependencies = self.__read_pip_requirements__()
            for package, version in dependencies:
                pkg = package.lower() if package == "Twisted" else package
                try:
                    __import__(pkg)
                except ImportError:
                    missing.append(package)

        self.message = application_name + " requires "
        if len(missing) > 1:
            for missed in missing[:-1]:
                self.message += missed + ", "
            self.message += "and "
        if len(missing) == 1:
            self.message += missing[0] + "."
            self.message += "\nPlease see %s for ".format(pipfile)
            self.message += "instruction on installing dependencies."
            raise self
        elif len(missing) <= 0:
            return

    def __read_pip_requirements__(self, file=None):
        """
        Check the pip requirements file to determine our dependencies.

        @param file: The name of the pip requirements.txt file.
        @returns: A list of tuple(package_name, package_version).
        """
        import re

        if not file:
            file = self.pipfile

        filepath     = os.path.join(__get_repo_dir__(), file)
        requirement  = re.compile('[^0-9=><]+')
        dependencies = []

        print filepath
        assert os.path.isfile(filepath), \
            "Couldn't find requirements.pip file!"

        with open(filepath) as pipfile:
            for line in pipfile.readlines():
                shortened       = line.strip()
                matched         = requirement.match(shortened)
                package_name    = matched.group()
                package_version = shortened.split(package_name, 1)[1]
                dependencies.append((package_name, package_version))

        return dependencies

dependency_check = CheckRequirements(pipfile='pkg/mx-requirements.pip')

try:
    from twisted.python   import usage, runtime
    from twisted.internet import reactor
except ImportError, ie:
    print "CheckRequirements class is broken!:", ie.message


if __name__ == "__main__":

    log.start()
    log.debug("Running %s, with Python %s" % (application_name,
                                              runtime.shortPythonVersion()))
    log.debug("Platform: %s" % runtime.platform.getType())
    log.debug("Thread support: %s" % str(runtime.platform.supportsThreads()))

    mx_options = MXOptions()
    mx_options.parseOptions(sys.argv)

    if len(sys.argv) <= 0:
        print mx_options.getUsage()
        sys.exit(0)
    else:
        options = mx_options

    if options['verbose']:
        config.basic.debug = True

    if options['test']:
        from leap.mx import tests ## xxx this needs an __init__.py
        tests.run()               ## xxx need /leap/mx/tests.py
    elif options['conf'] and os.path.isfile(options['conf']):
        config.parse() ## xxx need /leap/mx/config.py 
        runner.run()   ## xxx need /leap/mx/runner.py
    else:
        mx_options.getUsage()
        sys.exit(1)
