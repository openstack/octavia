..
      Copyright (c) 2016 IBM

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

================
Layer 7 Cookbook
================

Introduction
============
This document gives several examples of common L7 load balancer usage. For a
description of L7 load balancing see: :doc:`l7`

For the purposes of this guide we assume that the OpenStack Client command-line
interface is going to be used to configure all features of Octavia with the
Octavia driver back-end. Also, in order to keep these examples short, we assume
that many non-L7 configuration tasks (such as deploying loadbalancers,
listeners, pools, members, healthmonitors, etc.) have already been
accomplished. A description of the starting conditions is given in each example
below.


Examples
========

.. _redirect-http-to-https:

Redirect *http://www.example.com/* to *https://www.example.com/*
----------------------------------------------------------------
**Scenario description**:

* Load balancer *lb1* has been set up with ``TERMINATED_HTTPS`` listener
  *tls_listener* on TCP port 443.
* *tls_listener* has been populated with a default pool, members, etc.
* *tls_listener* is available under the DNS name *https://www.example.com/*
* We want any regular HTTP requests to TCP port 80 on *lb1* to be redirected
  to *tls_listener* on TCP port 443.

**Solution**:

1. Create listener *http_listener* as an HTTP listener on *lb1* port 80.
2. Set up an L7 Policy *policy1* on *http_listener* with action
   ``REDIRECT_TO_URL`` pointed at the URL *https://www.example.com/*
3. Add an L7 Rule to *policy1* which matches all requests.


**CLI commands**:

.. code-block:: bash

    openstack loadbalancer listener create --name http_listener --protocol HTTP --protocol-port 80 lb1
    openstack loadbalancer l7policy create --action REDIRECT_PREFIX --redirect-prefix https://www.example.com/ --name policy1 http_listener
    openstack loadbalancer l7rule create --compare-type STARTS_WITH --type PATH --value / policy1


.. _send-requests-to-static-pool:

Send requests starting with /js or /images to *static_pool*
-----------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is set up to send all requests to
  its default_pool *pool1*.
* We are introducing static content servers 10.0.0.10 and 10.0.0.11 on subnet
  *private-subnet*, and want any HTTP requests with a URL that starts with
  either "/js" or "/images" to be sent to those two servers instead of *pool1*.

**Solution**:

1. Create pool *static_pool* on *lb1*.
2. Populate *static_pool* with the new back-end members.
3. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *static_pool*.
4. Create an L7 Rule on *policy1* which looks for "/js" at the start of
   the request path.
5. Create L7 Policy *policy2* with action ``REDIRECT_TO_POOL`` pointed at
   *static_pool*.
6. Create an L7 Rule on *policy2* which looks for "/images" at the start
   of the request path.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name static_pool --protocol HTTP
    openstack loadbalancer member create --address 10.0.0.10 --protocol-port 80 --subnet-id private-subnet static_pool
    openstack loadbalancer member create --address 10.0.0.11 --protocol-port 80 --subnet-id private-subnet static_pool
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool static_pool --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type STARTS_WITH --type PATH --value /js policy1
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool static_pool --name policy2 listener1
    openstack loadbalancer l7rule create --compare-type STARTS_WITH --type PATH --value /images policy2

**Alternate solution** (using regular expressions):

1. Create pool *static_pool* on *lb1*.
2. Populate *static_pool* with the new back-end members.
3. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *static_pool*.
4. Create an L7 Rule on *policy1* which uses a regular expression to match
   either "/js" or "/images" at the start of the request path.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name static_pool --protocol HTTP
    openstack loadbalancer member create --address 10.0.0.10 --protocol-port 80 --subnet-id private-subnet static_pool
    openstack loadbalancer member create --address 10.0.0.11 --protocol-port 80 --subnet-id private-subnet static_pool
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool static_pool --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type REGEX --type PATH --value '^/(js|images)' policy1


Send requests for *http://www2.example.com/* to *pool2*
-------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is set up to send all requests to
  its default_pool *pool1*.
* We have set up a new pool *pool2* on *lb1* and want any requests using the
  HTTP/1.1 hostname *www2.example.com* to be sent to *pool2* instead.

**Solution**:

1. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *pool2*.
2. Create an L7 Rule on *policy1* which matches the hostname
   *www2.example.com*.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool pool2 --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type EQUAL_TO --type HOST_NAME --value www2.example.com policy1


Send requests for *\*.example.com* to *pool2*
---------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is set up to send all requests to
  its default_pool *pool1*.
* We have set up a new pool *pool2* on *lb1* and want any requests using any
  HTTP/1.1 hostname like *\*.example.com* to be sent to *pool2* instead.

**Solution**:

1. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *pool2*.
2. Create an L7 Rule on *policy1* which matches any hostname that ends with
   *example.com*.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool pool2 --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type ENDS_WITH --type HOST_NAME --value example.com policy1


Send unauthenticated users to *login_pool* (scenario 1)
-------------------------------------------------------
**Scenario description**:

* ``TERMINATED_HTTPS`` listener *listener1* on load balancer *lb1* is set up
  to send all requests to its default_pool *pool1*.
* The site behind *listener1* requires all web users to authenticate, after
  which a browser cookie *auth_token* will be set.
* When web users log out, or if the *auth_token* is invalid, the application
  servers in *pool1* clear the *auth_token*.
* We want to introduce new secure authentication server 10.0.1.10 on Neutron
  subnet *secure_subnet* (a different Neutron subnet from the default
  application servers) which handles authenticating web users and sets the
  *auth_token*.

*Note:* Obviously, to have a more secure authentication system that is less
vulnerable to attacks like XSS, the new secure authentication server will need
to set session variables to which the default_pool servers will have access
outside the data path with the web client. There may be other security concerns
as well. This example is not meant to address how these are to be
accomplished--it's mainly meant to show how L7 application routing can be done
based on a browser cookie.

**Solution**:

1. Create pool *login_pool* on *lb1*.
2. Add member 10.0.1.10 on *secure_subnet* to *login_pool*.
3. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *login_pool*.
4. Create an L7 Rule on *policy1* which looks for browser cookie *auth_token*
   (with any value) and matches if it is *NOT* present.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name login_pool --protocol HTTP
    openstack loadbalancer member create --address 10.0.1.10 --protocol-port 80 --subnet-id secure_subnet login_pool
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool login_pool --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type REGEX --key auth_token --type COOKIE --value '.*' --invert policy1


Send unauthenticated users to *login_pool* (scenario 2)
--------------------------------------------------------
**Scenario description**:

* ``TERMINATED_HTTPS`` listener *listener1* on load balancer *lb1* is set up
  to send all requests to its default_pool *pool1*.
* The site behind *listener1* requires all web users to authenticate, after
  which a browser cookie *auth_token* will be set.
* When web users log out, or if the *auth_token* is invalid, the application
  servers in *pool1* set *auth_token* to the literal string "INVALID".
* We want to introduce new secure authentication server 10.0.1.10 on Neutron
  subnet *secure_subnet* (a different Neutron subnet from the default
  application servers) which handles authenticating web users and sets the
  *auth_token*.

*Note:* Obviously, to have a more secure authentication system that is less
vulnerable to attacks like XSS, the new secure authentication server will need
to set session variables to which the default_pool servers will have access
outside the data path with the web client. There may be other security concerns
as well. This example is not meant to address how these are to be
accomplished-- it's mainly meant to show how L7 application routing can be done
based on a browser cookie.

**Solution**:

1. Create pool *login_pool* on *lb1*.
2. Add member 10.0.1.10 on *secure_subnet* to *login_pool*.
3. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *login_pool*.
4. Create an L7 Rule on *policy1* which looks for browser cookie *auth_token*
   (with any value) and matches if it is *NOT* present.
5. Create L7 Policy *policy2* with action ``REDIRECT_TO_POOL`` pointed at
   *login_pool*.
6. Create an L7 Rule on *policy2* which looks for browser cookie *auth_token*
   and matches if it is equal to the literal string "INVALID".

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name login_pool --protocol HTTP
    openstack loadbalancer member create --address 10.0.1.10 --protocol-port 80 --subnet-id secure_subnet login_pool
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool login_pool --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type REGEX --key auth_token --type COOKIE --value '.*' --invert policy1
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool login_pool --name policy2 listener1
    openstack loadbalancer l7rule create --compare-type EQUAL_TO --key auth_token --type COOKIE --value INVALID policy2


Send requests for *http://api.example.com/api* to *api_pool*
------------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is set up to send all requests
  to its default_pool *pool1*.
* We have created pool *api_pool* on *lb1*, however, for legacy business logic
  reasons, we only want requests sent to this pool if they match the hostname
  *api.example.com* AND the request path starts with */api*.

**Solution**:

1. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *api_pool*.
2. Create an L7 Rule on *policy1* which matches the hostname *api.example.com*.
3. Create an L7 Rule on *policy1* which matches */api* at the start of the
   request path. (This rule will be logically ANDed with the previous rule.)

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool api_pool --name policy1 listener1
    openstack loadbalancer l7rule create --compare-type EQUAL_TO --type HOST_NAME --value api.example.com policy1
    openstack loadbalancer l7rule create --compare-type STARTS_WITH --type PATH --value /api policy1


Set up A/B testing on an existing production site using a cookie
----------------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is a production site set up as
  described under :ref:`send-requests-to-static-pool` (alternate solution)
  above. Specifically:

  * HTTP requests with a URL that starts with either "/js" or "/images" are
    sent to pool *static_pool*.
  * All other requests are sent to *listener1's* default_pool *pool1*.

* We are introducing a "B" version of the production site, complete with its
  own default_pool and static_pool. We will call these *pool_B* and
  *static_pool_B* respectively.
* The *pool_B* members should be 10.0.0.50 and 10.0.0.51, and the
  *static_pool_B* members should be 10.0.0.100 and 10.0.0.101 on subnet
  *private-subnet*.
* Web clients which should be routed to the "B" version of the site get a
  cookie set by the member servers in *pool1*. This cookie is called
  "site_version" and should have the value "B".

**Solution**:

1. Create pool *pool_B* on *lb1*.
2. Populate *pool_B* with its new back-end members.
3. Create pool *static_pool_B* on *lb1*.
4. Populate *static_pool_B* with its new back-end members.
5. Create L7 Policy *policy2* with action ``REDIRECT_TO_POOL`` pointed at
   *static_pool_B*. This should be inserted at position 1.
6. Create an L7 Rule on *policy2* which uses a regular expression to match
   either "/js" or "/images" at the start of the request path.
7. Create an L7 Rule on *policy2* which matches the cookie "site_version" to
   the exact string "B".
8. Create L7 Policy *policy3* with action ``REDIRECT_TO_POOL`` pointed at
   *pool_B*. This should be inserted at position 2.
9. Create an L7 Rule on *policy3* which matches the cookie "site_version" to
   the exact string "B".

*A word about L7 Policy position*: Since L7 Policies are evaluated in order
according to their position parameter, and since the first L7 Policy whose L7
Rules all evaluate to True is the one whose action is followed, it is important
that L7 Policies with the most specific rules get evaluated first.

For example, in this solution, if *policy3* were to appear in the listener's L7
Policy list before *policy2* (that is, if *policy3* were to have a lower
position number than *policy2*), then if a web client were to request the URL
http://www.example.com/images/a.jpg with the cookie "site_version:B", then
*policy3* would match, and the load balancer would send the request to
*pool_B*. From the scenario description, this request clearly was meant to be
sent to *static_pool_B*, which is why *policy2* needs to be evaluated before
*policy3*.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name pool_B --protocol HTTP
    openstack loadbalancer member create --address 10.0.0.50 --protocol-port 80 --subnet-id private-subnet pool_B
    openstack loadbalancer member create --address 10.0.0.51 --protocol-port 80 --subnet-id private-subnet pool_B
    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name static_pool_B --protocol HTTP
    openstack loadbalancer member create --address 10.0.0.100 --protocol-port 80 --subnet-id private-subnet static_pool_B
    openstack loadbalancer member create --address 10.0.0.101 --protocol-port 80 --subnet-id private-subnet static_pool_B
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool static_pool_B --name policy2 --position 1 listener1
    openstack loadbalancer l7rule create --compare-type REGEX --type PATH --value '^/(js|images)' policy2
    openstack loadbalancer l7rule create --compare-type EQUAL_TO --key site_version --type COOKIE --value B policy2
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool pool_B --name policy3 --position 2 listener1
    openstack loadbalancer l7rule create --compare-type EQUAL_TO --key site_version --type COOKIE --value B policy3


Redirect requests with an invalid TLS client authentication certificate
-----------------------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is configured for ``OPTIONAL``
  client_authentication.
* Web clients that do not present a TLS client authentication certificate
  should be redirected to a signup page at *http://www.example.com/signup*.

**Solution**:

1. Create the load balancer *lb1*.
2. Create a listener *listner1* of type ``TERMINATED_TLS`` with a
   client_ca_tls_container_ref and client_authentication ``OPTIONAL``.
3. Create a L7 Policy *policy1* on *listener1* with action ``REDIRECT_TO_URL``
   pointed at the URL *http://www.example.com/signup*.
4. Add an L7 Rule to *policy1* that does not match ``SSL_CONN_HAS_CERT``.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer create --name lb1 --vip-subnet-id public-subnet
    openstack loadbalancer listener create --name listener1 --protocol TERMINATED_HTTPS --client-authentication OPTIONAL --protocol-port 443 --default-tls-container-ref http://192.0.2.15:9311/v1/secrets/697c2a6d-ffbe-40b8-be5e-7629fd636bca --client-ca-tls-container-ref http://192.0.2.15:9311/v1/secrets/dba60b77-8dad-4171-8a96-f21e1ca5fb46 lb1
    openstack loadbalancer l7policy create --action REDIRECT_TO_URL --redirect-url http://www.example.com/signup --name policy1 listener1
    openstack loadbalancer l7rule create --type SSL_CONN_HAS_CERT --invert --compare-type EQUAL_TO --value True policy1


Send users from the finance department to pool2
-----------------------------------------------
**Scenario description**:

* Users from the finance department have client certificates with the OU field
  of the distinguished name set to ``finance``.
* Only users with valid finance department client certificates should be able
  to access ``pool2``. Others will be rejected.

**Solution**:

1. Create the load balancer *lb1*.
2. Create a listener *listner1* of type ``TERMINATED_TLS`` with a
   client_ca_tls_container_ref and client_authentication ``MANDATORY``.
3. Create a pool *pool2* on load balancer *lb1*.
4. Create a L7 Policy *policy1* on *listener1* with action ``REDIRECT_TO_POOL``
   pointed at *pool2*.
5. Add an L7 Rule to *policy1* that matches ``SSL_CONN_HAS_CERT``.
6. Add an L7 Rule to *policy1* that matches ``SSL_VERIFY_RESULT`` with a value
   of 0.
7. Add an L7 Rule to *policy1* of type ``SSL_DN_FIELD`` that looks for
   "finance" in the "OU" field of the client authentication distinguished name.

**CLI commands**:

.. code-block:: bash

    openstack loadbalancer create --name lb1 --vip-subnet-id public-subnet
    openstack loadbalancer listener create --name listener1 --protocol TERMINATED_HTTPS --client-authentication MANDATORY --protocol-port 443 --default-tls-container-ref http://192.0.2.15:9311/v1/secrets/697c2a6d-ffbe-40b8-be5e-7629fd636bca --client-ca-tls-container-ref http://192.0.2.15:9311/v1/secrets/dba60b77-8dad-4171-8a96-f21e1ca5fb46 lb1
    openstack loadbalancer pool create --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --name pool2 --protocol HTTP
    openstack loadbalancer l7policy create --action REDIRECT_TO_POOL --redirect-pool pool2 --name policy1 listener1
    openstack loadbalancer l7rule create --type SSL_CONN_HAS_CERT --compare-type EQUAL_TO --value True policy1
    openstack loadbalancer l7rule create --type SSL_VERIFY_RESULT --compare-type EQUAL_TO --value 0 policy1
    openstack loadbalancer l7rule create --type SSL_DN_FIELD --compare-type EQUAL_TO --key OU --value finance policy1
