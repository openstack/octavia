======
Anchor
======
Anchor (see https://wiki.openstack.org/wiki/Security/Projects/Anchor) is
an ephemeral PKI system built to enable cryptographic trust in OpenStack
services. In the context of Octavia it can be used to sign the certificates
which secure the amphora - controller communication.

Basic Setup
-----------
1. Download/Install/Start Anchor from  https://github.com/openstack/anchor
2. Change the listening port in config.py to 9999
3. I found it useful to run anchor in an additional devstack screen
4. Set in octavia.conf (root-ca.crt here is the Anchor CA)

   a. [controller_worker] cert_generator = anchor
   b. [haproxy_amphora] server_ca = /opt/stack/anchor/CA/root-ca.crt

5. Restart o-cw o-hm o-hk

Benefit
-------
In bigger cloud installations Anchor can be a gateway to a more secure
certificate management system than our default local signing.
