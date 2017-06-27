0.10.0 - xxx
+++++++++++++++++++++++++++++++

Bugfixes
~~~~~~~~
- `#8663 <https://leap.se/code/issues/8663`_: check if key is expired

Features
~~~~~~~~
- Use pgpy instead of python-gnupg


0.9.1 - 16 Feb, 2016 
+++++++++++++++++++++++++++++++

Bugfixes
~~~~~~~~
- Returns doc as None if we have some error during the encryption

Misc
~~~~~~~~
- Packaging changes: add systemd script.


0.8.1 - 13 May, 2016 
+++++++++++++++++++++++++++++++

Bugfixes
~~~~~~~~
- `#7961 <https://leap.se/code/issues/7961>`_: Deleted account crashes leap-mx

0.8.0 - 18 Apr, 2016 
+++++++++++++++++++++++++++++++

Features
~~~~~~~~
- `#4285 <https://leap.se/code/issues/4285>`_: Add postfix lookup against couchdb for client smtp fingerprint
- `#5959 <https://leap.se/code/issues/5959>`_: Make alias resolver to return *uuid@deliver.local*
- `#7998 <https://leap.se/code/issues/7998>`_: Bounce stalled emails after a timeout.

Bugfixes
~~~~~~~~
- `#7253 <https://leap.se/code/issues/7253>`_: Use the original message for encryption.
- `#7961 <https://leap.se/code/issues/7961>`_: Check if the account is enabled.

Misc
~~~~
- `#7271 <https://leap.se/code/issues/7271>`_: Document the return codes of the TCP maps.
