# -*- coding: utf-8 -*-
# setup.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
setup file for leap.mx
"""
import os
from setuptools import setup, find_packages

import versioneer
versioneer.versionfile_source = 'src/leap/mx/_version.py'
versioneer.versionfile_build = 'leap/mx/_version.py'
versioneer.tag_prefix = ''  # tags are like 1.2.0
versioneer.parentdir_prefix = 'leap.mx-'

from pkg.utils.reqs import parse_requirements

trove_classifiers = [
    'Development Status :: 3 - Alpha',
    'Environment :: No Input/Output (Daemon)',
    'Framework :: Twisted',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Affero General Public License v3'
    ' or later (AGPLv3+)',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Topic :: Communications :: Email',
    'Topic :: Security :: Cryptography',
]

if os.environ.get("VIRTUAL_ENV", None):
    data_files = None
else:
    # XXX use a script entrypoint for mx instead, it will
    # be automatically
    # placed by distutils, using whatever interpreter is
    # available.
    data_files = [("/usr/local/bin/", ["pkg/mx.tac"]),
                  ("/etc/init.d/", ["pkg/leap_mx"])]
setup(
    name='leap.mx',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url="http://github.com/leapcode/leap_mx",
    license='AGPLv3+',
    author='The LEAP Encryption Access Project',
    author_email='info@leap.se',
    description=("An asynchronous, transparently-encrypting remailer "
                 "for the LEAP platform"),
    long_description=(
        "An asynchronous, transparently-encrypting remailer "
        "using BigCouch/CouchDB and PGP/GnuPG, written in Twisted Python."
    ),
    namespace_packages=["leap"],
    package_dir={'': 'src'},
    packages=find_packages('src'),
    #test_suite='leap.mx.tests',
    install_requires=parse_requirements(),
    classifiers=trove_classifiers,
    data_files=data_files
)
