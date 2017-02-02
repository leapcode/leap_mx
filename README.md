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

### Stalled emails

In case of problems with couchdb and other unknown sources emails can get
stalled in the spool. There is a bouncing mechanism for long stalled emails,
after 5 days the email will get bounced. The timestamp of stalled emails is
hold in memory, restarting leap-mx will erase all timestamps and the stalled
timeout will be reset.

## Hacking

Please see the doc/DESIGN docs.

Our bugtracker is [here](https://leap.se/code/projects/mx).

Please use that for bug reports and feature requests instead of github's
tracker. We're using github for code commenting and review between
collaborators.

### Running Tests

You need tox to run the tests. If you don't have it in your system yet::

~~~
$ pip install tox
~~~

And then run all the tests::

~~~
$ tox
~~~

## Issues

* see the [Changelog](./CHANGELOG) for details of all major changes in the different versions

### 0.6.1

* Bouncing messages can get into a bouncing loop (#6858)

### 0.6.0

* leap-mx needs to get restarted after the first incoming mail is delivered (#6687)
