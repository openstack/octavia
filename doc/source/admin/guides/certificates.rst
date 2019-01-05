..
      Copyright 2018 Rackspace, US Inc.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain a
      copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=======================================
Octavia Certificate Configuration Guide
=======================================

This document is intended for Octavia administrators setting up certificate
authorities for the two-way TLS authentication used in Octavia for command
and control of :term:`Amphora`.

This guide does not apply to the configuration of `TERMINATED_TLS` listeners
on load balancers. See the `Load Balancing Cookbook`_ for instructions on
creating `TERMINATED_TLS` listeners.

.. _Load Balancing Cookbook: ../../user/guides/basic-cookbook.html#deploy-a-tls-terminated-https-load-balancer

Two-way TLS Authentication in Octavia
=====================================

The Octavia controller processes communicate with the Amphora over
a TLS connection much like an HTTPS connection to a website. However, Octavia
validates that both sides are trusted by doing a two-way TLS authentication.

.. note::

    This is a simplification of the full TLS handshake process. See the
    `TLS 1.3 RFC 8446 <https://tools.ietf.org/html/rfc8446>`_ for the full
    handshake.

Phase One
---------

When a controller process, such as the Octavia worker process, connects to
an Amphora, the Amphora will present its `server` certificate
to the controller. The controller will then validate it against the `server`
Certificate Authority (CA) certificate stored on the controller. If the
presented certificate is validated against the `server` CA certificate, the
connection goes into phase two of the two-way TLS authentication.

Phase Two
---------

Once phase one is complete, the controller will present its `client`
certificate to the Amphora. The Amphora will then validate the
certificate against the `client` CA certificate stored inside the Amphora.
If this certificate is successfully validated, the rest of the TLS handshake
will continue to establish the secure communication channel between the
controller and the Amphora.

Certificate Lifecycles
----------------------

The `server` certificates are uniquely generated for each amphora by the
controller using the `server` certificate authority certificates and keys.
These `server` certificates are automatically rotated by the Octavia
housekeeping controller process as they near expiration.

The `client` certificates are used for the Octavia controller processes.
These are managed by the operator and due to their use on the control plane
of the cloud, typically have a long lifetime.

See the `Operator Maintenance Guide <operator-maintenance.html#rotating-cryptographic-certificates>`_ for more
information about the certificate lifecycles.

Creating the Certificate Authorities
====================================

As discussed above, this configuration uses two certificate authorities; one
for the `server` certificates, and one for the `client` certificates.

.. note::

    Technically Octavia can be run using just one certificate authority by
    using it to issue certificates for both roles. However, this weakens the
    security as a `server` certificate from an amphora could be used to
    impersonate a controller. We recommend you use two certificate authorities
    for all deployments outside of testing.

For this document we are going to setup simple OpenSSL based certificate
authorities. However, any standards compliant certificate authority software
can be used to create the required certificates.

1. Create a working directory for the certificate authorities. Make sure to
   set the proper permissions on this directory such that others cannot
   access the private keys, random bits, etc. being generated here.

   .. code-block:: bash

       $ mkdir certs
       $ chmod 700 certs
       $ cd certs

2. Create the OpenSSL configuration file. This can be shared between the
   two certificate authorities.

   .. code-block:: bash

       $ vi openssl.cnf

   .. literalinclude:: sample-configs/openssl.cnf
      :language: ini

3. Make any locally required configuration changes to the openssl.cnf. Some
   settings to consider are:

   * The default certificate lifetime is 10 years.
   * The default bit length is 2048.

4. Make directories for the two certificate authorities.

   .. code-block:: bash

       $ mkdir client_ca
       $ mkdir server_ca

5. Starting with the `server` certificate authority, prepare the CA.

   .. code-block:: bash

       $ cd server_ca
       $ mkdir certs crl newcerts private
       $ chmod 700 private
       $ touch index.txt
       $ echo 1000 > serial

6. Create the `server` CA key.

   * You will need to specify a passphrase to protect the key file.

   .. code-block:: bash

       $ openssl genrsa -aes256 -out private/ca.key.pem 4096
       $ chmod 400 private/ca.key.pem

7. Create the `server` CA certificate.

   * You will need to specify the passphrase used in step 6.
   * You will also be asked to provide details for the certificate. These are
     up to you and should be appropriate for your organization.
   * You may want to mention this is the `server` CA in the common name field.
   * Since this is the CA certificate, you might want to give it a very long
     lifetime, such as twenty years shown in this example command.

   .. code-block:: bash

       $ openssl req -config ../openssl.cnf -key private/ca.key.pem -new -x509 -days 7300 -sha256 -extensions v3_ca -out certs/ca.cert.pem

8. Moving to the `client` certificate authority, prepare the CA.

   .. code-block:: bash

       $ cd ../client_ca
       $ mkdir certs crl csr newcerts private
       $ chmod 700 private
       $ touch index.txt
       $ echo 1000 > serial

9. Create the `client` CA key.

   * You will need to specify a passphrase to protect the key file.

   .. code-block:: bash

       $ openssl genrsa -aes256 -out private/ca.key.pem 4096
       $ chmod 400 private/ca.key.pem

10. Create the `client` CA certificate.

    * You will need to specify the passphrase used in step 9.
    * You will also be asked to provide details for the certificate. These are
      up to you and should be appropriate for your organization.
    * You may want to mention this is the `client` CA in the common name field.
    * Since this is the CA certificate, you might want to give it a very long
      lifetime, such as twenty years shown in this example command.

    .. code-block:: bash

        $ openssl req -config ../openssl.cnf -key private/ca.key.pem -new -x509 -days 7300 -sha256 -extensions v3_ca -out certs/ca.cert.pem

11. Create a key for the `client` certificate to use.

    * You can create one certificate and key to be used by all of the
      controllers or you can create a unique certificate and key for each
      controller.
    * You will need to specify a passphrase to protect the key file.

    .. code-block:: bash

        $ openssl genrsa -aes256 -out private/client.key.pem 2048

12. Create the certificate request for the `client` certificate used on the
    controllers.

    * You will need to specify the passphrase used in step 11.
    * You will also be asked to provide details for the certificate. These are
      up to you and should be appropriate for your organization.
    * You must fill in the common name field.
    * You may want to mention this is the `client` certificate in the common
      name field, or the individual controller information.

    .. code-block:: bash

        $ openssl req -config ../openssl.cnf -new -sha256 -key private/client.key.pem -out csr/client.csr.pem

13. Sign the `client` certificate request.

    * You will need to specify the CA passphrase used in step 9.
    * Since this certificate is used on the control plane, you might want to
      give it a very long lifetime, such as twenty years shown in this example
      command.

    .. code-block:: bash

        $ openssl ca -config ../openssl.cnf -extensions usr_cert -days 7300 -notext -md sha256 -in csr/client.csr.pem -out certs/client.cert.pem

14. Create a concatenated `client` certificate and key file.

    * You will need to specify the CA passphrase used in step 11.

    .. code-block:: bash

        $ openssl rsa -in private/client.key.pem -out private/client.cert-and-key.pem
        $ cat certs/client.cert.pem >> private/client.cert-and-key.pem


Configuring Octavia
===================

In this section we will configure Octavia to use the certificates and keys
created during the `Creating the Certificate Authorities`_ section.

1. Copy the required files over to your Octavia controllers.

   * Only the Octavia worker, health manager, and housekeeping processes will
     need access to these files.
   * The first command should return you to the "certs" directory created in
     step 1 of the `Creating the Certificate Authorities`_ section.
   * These commands assume you are running the octavia processes under the
     "octavia" user.
   * Note, some of these steps should be run with "sudo" and are indicated by
     the "#" prefix.

   .. code-block:: bash

       $ cd ..
       # mkdir /etc/octavia/certs
       # chmod 700 /etc/octavia/certs
       # cp server_ca/private/ca.key.pem /etc/octavia/certs/server_ca.key.pem
       # chmod 700 /etc/octavia/certs/server_ca.key.pem
       # cp server_ca/certs/ca.cert.pem /etc/octavia/certs/server_ca.cert.pem
       # cp client_ca/certs/ca.cert.pem /etc/octavia/certs/client_ca.cert.pem
       # cp client_ca/private/client.cert-and-key.pem /etc/octavia/certs/client.cert-and-key.pem
       # chmod 700 /etc/octavia/certs/client.cert-and-key.pem
       # chown -R octavia.octavia /etc/octavia/certs

2. Configure the [certificates] section of the octavia.conf file.

   * Only the Octavia worker, health manager, and housekeeping processes will
     need these settings.
   * The "<server CA passphrase>" should be replaced with the passphrase
     that was used in step 6 of the `Creating the Certificate Authorities`_
     section.

   .. code-block:: ini

       [certificates]
       cert_generator = local_cert_generator
       ca_certificate = /etc/octavia/certs/server_ca.cert.pem
       ca_private_key = /etc/octavia/certs/server_ca.key.pem
       ca_private_key_passphrase = <server CA key passphrase>

3. Configure the [controller_worker] section of the octavia.conf file.

   * Only the Octavia worker, health manager, and housekeeping processes will
     need these settings.

   .. code-block:: ini

       [controller_worker]
       client_ca = /etc/octavia/certs/client_ca.cert.pem

4. Configure the [haproxy_amphora] section of the octavia.conf file.

   * Only the Octavia worker, health manager, and housekeeping processes will
     need these settings.

   .. code-block:: ini

       [haproxy_amphora]
       client_cert = /etc/octavia/certs/client.cert-and-key.pem
       server_ca = /etc/octavia/certs/server_ca.cert.pem

5. Start the controller processes.

   .. code-block:: bash

       # systemctl start octavia-worker
       # systemctl start octavia-healthmanager
       # systemctl start octavia-housekeeping
