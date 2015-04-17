Leap MX
=======

**Note:** Currently in development. Feel free to test, and please [report bugs
on our tracker](https://we.riseup.net/leap/mx) or [by
email](mailto:discuss@leap.se).

An asynchronous, transparently-encrypting remailer for the LEAP platform,
using BigCouch/CouchDB and PGP/GnuPG, written in Twisted Python.

## Installing

  * Leap MX is available as a debian package in [Leap
    repository](http://deb.leap.se/repository/).
  * A python package is available in
    [pypi](https://pypi.python.org/pypi/leap.mx). Use ./pkg/requirements.pip
    to install requirements.
  * Source code is available in [github](https://github.com/leapcode/leap_mx).

## Configuring

A sample config file can be found in pkg/mx.conf.sample

## Running

The debian package contains an initscript for the service. If you want to run
from source or from the python package, maybe setup a virtualenv and do:

~~~
# git clone or unzip the python package, change into the dir, and do:
$ python setup.py install
# copy ./pkg/mx.conf.sample to /etc/leap/mx.conf and edit that file, then run:
$ twistd -ny pkg/mx.tac
~~~

## Hacking

Please see the doc/DESIGN docs.

Our bugtracker is [here](https://leap.se/code/projects/mx).

Please use that for bug reports and feature requests instead of github's
tracker. We're using github for code commenting and review between
collaborators.
