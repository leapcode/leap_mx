# design #

## overview #
----------------------
This page pertains to the incoming mail exchange servers of the provider.

General overview of how incoming email will work:

 1. Incoming message is received by provider's MX servers.
 2. The MTA (postfix in our case) does a ton of checks on the message before we
 even check to see if the recipient is valid (this comes from experience
 running the riseup mail infrastructure, where the vast majority of messages
 can be rejected early in the SMTP reception and thus save a ton of processing
 time on the server).
 3. Postfix then queries the database to check if the recipient is valid, if
 they are over quota, if their account is enabled, and to resolve any aliases
 for the account.
 4. The message is then delivered to an on-disk message spool.
 5. A daemon watches for new files in this spool. Each message is encrypted to
 the user's public key, and stored in the user's incoming message queue (stored
 in couchdb), and removed from disk.
 6. When the user next logs in with their client, the user's message queue is
 emptied by the client.
 7. Each message is decrypted by the client, and then stored in the user's
 "inbox" as an unread message.
 8. This local inbox uses soledad for storage
 9. Soledad, in the background, will then re-encrypt this email (now a soledad
 document), and sync to the cloud.

## postfix pipeline ##
---------------------------
incoming mx servers will run postfix, configured in a particular way:

 1. postscreen: before accepting an incoming message, checks RBLs, checks RFC
 validity, checks for spam pipelining.
    (pass) proceed to next step.
    (fail) return SMTP error, which bounces email.
 2. more SMTP checks: valid hostnames, etc.
    (pass) accepted, proceed to next step.
    (fail) return SMTP error, which bounces email.
 3. check_recipient_access -- look up each recipient and ensure they are
 allowed to receive messages.
    (pass) empty result, proceed to next step.
    (fail) return SMTP error code and error comment, bounce message.
 4. milter processessing (spamassassin & clamav)
    (pass) continue
    (fail) bounce message, flag as spam, or silently kill.
 5. virtual_alias_maps -- map user defined aliases and forwards
    (local address) continue if new address is for this mx
    (remote address) continue. normally, postfix would relay to the remote domain, but we don't want that.
 6. deliver message to spool
    (write) save the message to disk on the mx.
 7. postfix's job is done, mail_receiver picks up email from spool directory

Questions:

 * what is the best way to have postfix write a message to a spool directory?
   There is a built-in facility for saving to a maildir, so we could just
   specify a common maildir for everyone. alternately, we could pipe to a
   simple command that was responsible for safely saving the file to disk. a
   third possibility would be to have a local long running daemon that spoke
   lmtp that postfix forward the message on to for delivery.
 * if virtual_alias_maps comes after check_recipient_access, then a user with
   aliases set but who is over quota will not be able to forward email. i think
   this is fine.
 * if we are going to support forwarding, we should ensure that the message
   gets encrypted before getting forwarded. so, postfix should not do any
   forwarding. instead, this should be the job of mail_receiver.

Considerations:

 1. high load should fill queue, not crash pipeline: It is important that the
 pipeline be able to handle massive bursts of email, as often happens with
 email. This means map lookups need to be very fast, and when there is a high
 load of email postfix should not be waiting on the mail receiver but must be
 able to pass the message off quickly and have the slower mail receiver churn
 through the backlog as best it can.
 2. don't lose messages: It is important to not lose any messages when there is
 a problem. So, generally, a copy of an email should always exist in some spool
 somewhere, and that copy should not be deleted until there is confirmation
 that the next stage has succeeded.
 
## alias_resolver ##
------------------------------
The alias_resolver will be a daemon running on MX servers that handles lookups
in the user database of email aliases, forwards, quota, and account status.

Communication with:

 1. postfix:: alias_resolver will be bound to localhost and speak postfix's
 very simple [tcp map protocol -> http://www.postfix.org/tcp_table.5.html].

 2. couchdb:: alias_resolver will make couchdb queries to a local http load
 balancer that connects to a couchdb/bigcouch
 cluster. [directly accessing the couch->https://we.riseup.net/leap+platform/querying-the-couchdb]
 might help getting started.

### Discussion: ###

 1. we want the lookups to be fast. using views in couchdb, these should be
   very fast. when using bigcouch, we can make it faster by specifying a read
   quorum of 1 (instead of the default 2). this will make it so that only a
   single couchdb needs to be queried to find the result. i don't know if this
   would cause problems, but aliases don't change very often.

alias_resolver will be responsible for two map lookups in postfix:

#### check_recipient ####
-------------------------
postfix config:

@check_recipient_access tcp:localhost:1000@

postfix will send "get username@domain.org" and alias_resolver should return an
empty result ("200 \n", i think) if postfix should deliver email to the
user. otherwise, it should return an error. here is example response, verbatim,
that can be used to bounce over quota users:

```
200 DEFER_IF_PERMIT Sorry, your message cannot be delivered because the
recipient's mailbox is full. If you can contact them another way, you may wish
to tell them of this problem.  
```

"DEFER_IF_PERMIT" will let the other MX know that this error is temporary and
that they should try again soon. Typically, an MX will try repeatedly, at
longer and longer intervals, for four days before giving up.

#### virtual alias map ####
---------------------------
postfix config:

@virtual_alias_map tcp:localhost:1001@

postfix will send "get alias-address@domain.org" and alias_resolver should
return "200 id_123456\n", where 123456 is the unique id of the user that has
alias-address@domain.org.

couchdb should have a view that will let us query on an (alias) address and
return the user id.

note: if the result of the alias map (e.g. id_123456) does not have a domain
suffix, i think postfix will use the 'default transport'. if we want it to use
the virtual transport instead, we should append the domain (eg
id_123456@example.org). see
http://www.postfix.org/ADDRESS_REWRITING_README.html#resolve


### Current status: ### 
The current implementation of alias_resolver is in
leap-mx/src/leap/mx/alias_resolver.py.

The class ```alias_resolver.StatusCodes``` deals with creating SMTP-like
response messages for Postfix, speaking Postfix's TCP Map protocol (from item
#1).

As for Discussion item #1: 

It might be possible to use
[python-memcached](https://pypi.python.org/pypi/python-memcached/) as an
interface to a [memcached](http://memcached.org/) instance to speed up database
lookups, by keeping an in memory mapping of recent request/response
pairs. Also, Twisted now (I think as of 12.0.0) ships with a protocol for
handling Memcached servers, this is in ```twisted.protocols.memcache```. This
should be prioritised for later, if it is decided that querying the CouchDB is
too expensive or time-consuming.

Thus far, to speed up alias lookup, an in-memory mapping of alias<->resolution
pairs is created by ```alias_resolver.AliasResolverFactory()```, which can be
optionally seeded with a dictionary of ```{ 'alias': 'resolution' }``` pairs
by doing:
~~~~~~
>>> from leap.mx import alias_resolver
>>> aliasResolverFactory = alias_resolver.AliasResolverFactory(
...      addr='1.2.3.4', port=4242, data={'isis': 'isis@leap.se',
...                                       'drebs': 'drebs@leap.se'})
>>> aliasResolver = aliasResolverFactory.buildProtocol()
>>> aliasResolver.check_recipient_access('isis')
200 OK Others might say 'HELLA AWESOME'...but we're not convinced.
~~~~~~

TODO:
 1. The AliasResolverFactory needs to be connected to the CouchDB. The
 classmethod in which this should occur is ```AliasResolverFactory.get()```.

 2. I am not sure where to get the user's UUID from (Soledad?). Wherever we get
 it from, it will need to be returned in
 ```AliasResolver.virtual_alias_map()```, and if we want Postfix to hear about
 it, then that response will need to be fed into ```AliasResolver.sendCode```.
 
 3. Other than those two things, I think everything is done. The only potential
 other thing I can think of is that the codes in
 ```alias_resolver.StatusCodes``` might need to be urlencoded for Postfix to
 accept them, but this is like two lines of code from urllib.



## mail_receiver ##

the mail_receiver is a daemon that runs on incoming MX servers and is
responsible for encrypting incoming email to the user's public key and saving
the email to an incoming queue database for that user.

communicates with:

 * message spool directory:: mail_reciever sits and waits for new email to be
   written to the spool directory (maybe using this
   https://github.com/seb-m/pyinotify, i think it is better than FAM). when a
   new file is dumped into the spool, mail_receiver reads the file, encrypts
   the entire thing using the public key of the recipient, and saves to
   couchdb.
 * couchdb get:: mail_receiver does a query on user id to get back user's
   public openpgp key. read quorum of 1 is probably ok.
 * couchdb put:: mail_receiver communicates with couchdb for storing encrypted
   email for each user (eventually, mail_receiver will communicate with a local
   http proxy, that communicates with a bigcouch cluster, but the api is
   identical)

discussion:
 * i am not sure if postfix adds a header to indicate to whom a message was
   actually delivered. if not, this is a problem, because then how do we know
   what db to put it in or what public key to use? this is perhaps a good
   reason to not let postfix handle writing the message to disk, but instead
   pipe it to another command (because postfix sets env variables for stuff
   like recipient).

 * should the incoming message queue be a separate database or should it be
   just documents in the user's main database with special flags?

 * whenever possible, we should refer to the user by a fixed id, not their
   username, because we want to support the ability to change usernames. so,
   for example, database names should not be based on usernames.

### Current Status: ###
None of this is done, although having it be a separate daemon sound weird.

You would probably want to use ```twisted.mail.mail.FileMonitoringService``` to
watch the mailbox (is the mailbox virtual or a maildir or mbox or?)
