leap_mx
=======

**Note:** Currently in development. Feel free to test, and please [report bugs](mailto:isis@leap.se).

An asynchronous, transparently-encrypting remailer for the LEAP platform, using BigCouch/CouchDB and PGP/GnuPG, written in Twisted Python.

## [install](#install) {#install} ##
=========================

**tl;dr:** To get started quickly do:

 # pip install -r requirements.txt

Although, **it is advised** to install inside a python virtualenv. To install python, virtualenv, and get started, do:

~~~
$ sudo apt-get install python2.7 python-pip python-virtualenv python-dev
$ pip install virtualenvwrapper
$ cd
$ git clone https://github.com/isislovecruft/leap_mx.git leap_mx
$ export WORKON_LEAPMX=~/leap_mx
$ source /usr/local/bin/virtualenvwrapper.sh
$ mkvirtualenv -a $WORKON_LEAPMX -r ${WORKON_LEAPMX}/requirements.txt \
      --no-site-packages --setuptools --unzip-setuptools leap_mx
~~~

## [running](#running) {#running} ##
=========================

Hold your horses, boy. This isn't ready yet -- check back later!
