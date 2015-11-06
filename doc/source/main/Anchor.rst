======
Anchor
======
Anchor (see https://wiki.openstack.org/wiki/Security/Projects/Anchor) is
an ephemeral PKI system built to enable cryptographic trust in OpenStack
services. In the context of Octavia it can be used to sign the certificates
which secure the amphora - controller communication.

Basic Setup
-----------
# Download/Install/Start Anchor from  https://github.com/openstack/anchor
# Change the listening port in config.py to 9999
# I found it useful to run anchor in an additional devstack screen
# Set in octavia.conf
## [controller_worker] cert_generator to anchor
## [haproxy_amphora] server_ca = /opt/stack/anchor/CA/root-ca.crt (Anchor CA)
# Restart o-cw o-hm o-hk

Benefit
-------
In bigger cloud installations Anchor can be a gateway to a more secure
certificate management system than our default local signing.
