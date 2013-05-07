leap_mx
=======
**Note:** Currently in development. Feel free to test, and please [report
 bugs on our tracker](https://we.riseup.net/leap/mx) or [by email](mailto:isis@leap.se).

An asynchronous, transparently-encrypting remailer for the LEAP platform,
using BigCouch/CouchDB and PGP/GnuPG, written in Twisted Python.

## [install](#install) ##

### [virtualenv](#virtualenv) ###
=================================
Impatient? Don't like virtualenvs? [tl;dr](#tl;dr)

Virtualenv is somewhat equivalent to fakeroot for python packages, and -- due
to being packaged with copies of pip and python -- can be used to bootstrap
its own install process, allowing pip and python to be used with sudo.

#### installing without sudo ####

To install without using sudo, a bootstrap script to handle the setup process
is provided. It does the following:

 1. Download, over SSL, the latest tarballs for virtualenv and
 virtualenvwrapper from pypi.
 2. Unpack the tarballs, use the system python interpreter to call the
 virtualenv.py script to setup a bootstrap virtual environment.
 3. Use the pip installed in the bootstrap virtualenv to install
 virtualenvwrapper in the bootstrap virtualenv.
 4. Obtain a copy of leap_mx with git clone.
 5. Use ```mkvirtualenv``` included in the virtualenvwrapper inside the
 bootstrap virtualenv to install a project virtualenv for leap_mx.

To use the bootstrap script, do:
~~~
$ wget -O bootstrap https://raw.github.com/isislovecruft/leap_mx/fix/no-suid-for-virtualenv/bootstrap
$ ./bootstrap
$ workon leap_mx
~~~

#### installing in a regular virtualenv ###
To install python, virtualenv, and get started, do:

~~~
$ sudo apt-get install python2.7 python-dev python-virtualenv virtualenvwrapper
$ git clone https://github.com/leapcode/leap_mx.git leap_mx
$ export WORKON_LEAPMX=${PWD}/leap_mx
$ source /usr/local/bin/virtualenvwrapper.sh
$ mkvirtualenv -a $WORKON_LEAPMX -r ${WORKON_LEAPMX}/pkg/mx-requirements.pip \
      --no-site-packages --setuptools --unzip-setuptools leap_mx
~~~

### [tl;dr](#tl;dr) ###
To get started quickly, without virtualenv, do:
~~~
$ sudo apt-get install python git
$ git clone https://github.com/leapcode/leap_mx.git
# pip install -r ./leap_mx/pkg/mx-requirements.pip
~~~
Although, **it is advised** to install inside a python virtualenv.

## [running](#running) ##
=========================

To get running, clone this repo, and (assuming you've already set up your
virtualenv and obtained all the requirements) do:

~~~
$ ./start_mx.py --help
~~~

## [hacking](#hacking) ##
=========================
Please see the HACKING and DESIGN docs.

Our bugtracker is [here](https://leap.se/code/projects/eip_server/issue/new).

Please use that for bug reports and feature requests instead of github's
tracker. We're using github for code commenting and review between
collaborators.

