..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
TLS Data Security and Barbican
==============================
Launchpad blueprint:

https://blueprints.launchpad.net/octavia/+spec/tls-data-security

Octavia will have some need of secure storage for TLS related data. This BP is
intended to identify all of the data that needs secure storage, or any other
interaction that will require the use of Barbican or another secure solution.

Problem description
===================
1. Octavia will support TLS Termination (including SNI), which will require us
to store and retrieve certificates and private keys from a secure repository.

2. Octavia will communicate with its Amphorae using TLS, so each Amphora
will need a certificate for the controller to validate.

3. Octavia will need TLS data for exposing its own API via HTTPS.

Proposed change
===============
The initial supported implementation for TLS related functions will be
Barbican, but the interface will be generic such that other implementations
could be created later.

.. seqdiag:: tls-data-security-1.diag

1. Create a CertificateManager interface for storing and retrieving certificate
and private key pairs (and intermediate certs / private key passphrase).
Users will pass their TLS data to Octavia in the form of a certificate_id,
which is a reference to their data in some secure service. Octavia will store
that certificate_id for each Listener/SNI and will retrieve the data when
necessary. (Barbican specific: users will need to add Octavia's user account as
an authorized user on the Container and all Secrets [1] so we catch fetch the
data on their behalf.)

We will need to validate the certificate data (including key and intermediates)
when we initially receive it, and will assume that it remains unchanged for
the lifespan of the LB (in Barbican the data is immutable so this is a safe
assumption, I do not know how well this will work for other services). In the
case of invalid TLS data, we will reject the request with a 400 (if it is an
initial create) or else put the LB into ERROR status (if it is on a failover
event or during some other non-interactive scenario).

.. seqdiag:: tls-data-security-2.diag

2. Create a CertificateGenerator interface to generate certificates from CSRs.
When the controller creates an Amphora, it will generate a private key and a
CSR, generate a signed certificate from the CSR, and include the private key
and signed certificate in a ConfigDrive for the new Amphora. It will also
include a copy of the Controller's certificate on the ConfigDrive. All future
communications with the Amphora will do certificate validation based on these
certificates. For the Amphora, this will be based on our (private) certificate
authority and the CN of the Amphora's cert matching the ID of the Amphora. For
the Controller, the cert should be a complete match with the version provided.

(The CertificateManager and CertificateGenerator interfaces are separate
because while Barbican can perform both functions, future implementations
may need to use two distinct services to achieve both.)

3. The key/cert for the main Octavia API/controller should be maintained
manually by the server operators using whatever configuration management
they choose. We should not need to use a specific external repo for this.
The trusted CA Cert will also need to be retrieved from barbican and manually
loaded in the config.

Alternatives
------------
We could skip the interface and just use Barbican directly, but that would be
diverging from what seems to be the accepted OpenStack model for Secret Store
integration.

We could also store everything locally or in the DB, but that isn't a real
option for production systems because it is incredibly insecure (though there
will be a "dummy driver" that operates this way for development purposes).

Data model impact
-----------------
Nothing new, the models for this should already be in place. Some of the
columns/classes might need to be renamed more generically (currently there is
a tls_container_id column, which would become tls_certificate_id to be more
generic).

REST API impact
---------------
None

Security impact
---------------
Using Barbican is considered secure.

Notifications impact
--------------------
None

Other end user impact
---------------------
None

Performance Impact
------------------
Adding an external touchpoint (a certificate signing service) to the Amphora
spin-up workflow will increase the average time for readying an Amphora. This
shouldn't be a huge problem if the standby-pool size is sufficient for the
particular deployment.

Other deployer impact
---------------------
None

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------
Adam Harwell (adam-harwell)

Work Items
----------
1. Create CertificateManager interface.

2. Create CertificateGenerator interface.

3. Create BarbicanCertificateManager implementation.

4. Create BarbicanCertificateGenerator implementation.

5. Create unit tests!

Dependencies
============
This script will depend on the OpenStack Barbican project, including some
features that are still only at the blueprint stage.

Testing
=======
There will be testing. Yes.

Documentation Impact
====================
Documentation changes will be primarily internal.

References
==========
.. line-block::
    [1] https://review.openstack.org/#/c/127353/
    [2] https://review.openstack.org/#/c/129048/
