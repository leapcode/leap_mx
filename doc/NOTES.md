
# Questions #
-------------

1. What is the lowest available RAM for a target server running a leap_mx?
       1.a. Do we want to store all id_keys and/or aliases in memory?

2. Asked in discussion section of '''postfix pipeline''' on the [leap_mx wiki
page](https://we.riseup.net/leap/mx) : 

   "What is the best way to have postfix write a message to a spool directory?
    There is a built-in facility for saving to a maildir, so we could just
    specify a common maildir for everyone. alternately, we could pipe to a
    simple command that was responsible for safely saving the file to disk. a
    third possibility would be to have a local long running daemon that spoke
    lmtp that postfix forward the message on to for delivery."

    I think that maildir is fine, but perhaps this will slow things down more
    than monitoring a spool file. I would also imagine that if the server is
    supposed to stand up to high loads, a spool file I/O blocks with every
    email added to the queue.

3. How do get it to go faster? Should we create some mockups and benchmark
them? Could we attempt to learn which aliases are most often resolved and
prioritize keeping those in in-memory mappings? Is
[memcache](http://code.sixapart.com/svn/memcached/trunk/server/doc/protocol.txt)
a viable protocol for this, and how would it interact with CouchDB?

4. What lib should we use for Python + Twisted + GPG/PGP ?
   4.a. It looks like most people are using python-gnupg...
