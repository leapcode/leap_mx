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

from twisted.internet import defer
from twisted.trial    import runner, reporter, unittest
from twisted.python   import usage

from leap.mx.util import log, version


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


class TestRunner(runner.TrialRunner):
    """
    This class handles loading unittests from a directory, module, file,
    class, method, or anything really, and running any unittests found with
    twisted.trial.

    @param options: A subclass of :class:twisted.python.usage.Options.
    @param test: (optional) The thing to load tests from.
    """
    def __init__(self, options, test_location=None, *args, **kwargs):
        """
        Create a runner for handling unittest runs.
        
        @param options: An the dictionary :ivar:`opts` from the parsed options
             of a :class:`twisted.python.usage.Options`.
        @param test_location: The path to a directory or filename containing
             unittests to run, or the path to a file prefixed with 'test_', or
             a subclass of :class:`twisted.trial.unittest.TestCase`, or a
             function/method prefixed with 'test_'.
        """
        log.debug("Creating TestRunner: %s" % self.__repr__())

        if isinstance(options, dict):
            log.debug("TestRunner loaded options class")
            self.options = options
        else:
            self.options = None
            raise usage.UsageError(
                "TestRunner expected t.p.u.Options subclass, got %s"
                % options)

        self.loader = runner.TestLoader()
        self._parse_options()

        self.test_location = test_location
        self.tests_loaded  = self.loadUnittests()
        self.test_list     = self.runUnittests()
        self.results       = defer.DeferredList(self.test_list)

    def _parse_options(self):
        """
        Parse the :class:`twisted.python.usage.Options` for flags pertaining
        to running unittests.
        """
        if not self.options is None:
            if self.options['debug']:
                log.debug("Enabled debugging on test runner.")
                self.DEBUG = True
            if self.options['force-gc']:
                ## not sure if we need to call it or assign it...
                log.debug("Forcing garbage collection between unittest runs.")
                self.loader.forceGarbageCollection(True)
            if self.options['all-tests']:
                repo = version.getRepoDir()
                test_directory = ospath.join(repo, 'src/leap/mx/tests')
                self.test_location = test_directory
        else:
            log.warn("TestRunner: got None for t.p.u.Options class!")

    def loadUnittests(self):
        """
        Load all tests. Tests may be a module or directory, the path to a
        filename in the form 'test_*.py", a subclass of
        :class:`twisted.trial.unittest.TestCase` or
        :class:`twisted.trial.unittest.TestSuite`, or a any function/method
        which is prefixed with 'test_'.

        @returns: An instance of :class:`twisted.trial.unittest.TestCase` or
                  :class:`twisted.trial.unittest.TestSuite`.
        """
        log.msg("Attempting to load unittests...")

        tests_loaded = None

        if self.test_location:
            log.msg("Loading unittests from %s" % self.test_location)
            if ospath.isdir(self.test_location):
                log.msg("Found test directory: %s" % test)
                tests_loaded = self.loader.loadAnything(self.test_location,
                                                        recurse=True)
            else:
                log.msg("Found test file: %s" % self.test_location)
                tests_loaded = self.loader.loadAnything(self.test_location)
        else:
            log.warn("Test location %s seems to be None!" % self.test_location)

        return tests_loaded

    def runUnittests(self):
        """xxx fill me in"""
        results = []
        if not self.tests_loaded is None:
            if isinstance(self.tests_loaded, unittest.TestCase):
                log.msg("Test case loaded.")
                classes = self.loader.findTestClasses(self.tests_loaded)
                for cls in classes:
                    test_instance = cls()
                    test_instance.setUp() ## xxx does TestRunner handle this?
                    d = defer.maybeDeferred(test_instance.run())
                    self.results.append(d)
            elif isinstance(self.tests, unittest.TestSuite):
                classes = None ## xxx call each TestCase in TestSuite
                test_suite = self.tests()
                self.results.append(test_suite.visit())
                log.msg("Test suite loaded: %d tests to run"
                        % test_suite.countTestCases)
        return results

    #return runner.TrialRunner(reporter.TreeReporter, mode=mode, 
    #                          profile=profile, logfile=logfile, 
    #                          tbformat, rterrors, unclean_warnings, 
    #                          temp-directory, force-gc)
