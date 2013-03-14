# -*- coding: utf-8 -*-
# setup.py
# Copyleft (C) 2013 LEAP
"""
setup file for leap.mx
"""
from setuptools import setup, find_packages

requirements = [
    "twisted",
    #...
]

# XXX add classifiers, docs

setup(
    name='leap.mx',
    version='0.0.1',
    url='https://leap.se/',
    license='',
    author="Isis Agora Lovecruft",
    author_email="<isis@leap.se> 0x2cdb8b35",
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
    install_requires=requirements,
)
