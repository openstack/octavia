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

==================================================
Layer 7 Cookbook Using Neutron Client (deprecated)
==================================================

.. warning:: The neutron client used in this document is deprecated. We
             strongly encourage you to use the OpenStack Client and Octavia
             OpenStack Client plugin instead. This document is being maintained
             for deployments still using neutron-lbaas and the neutron client.

Introduction
============
This document gives several examples of common L7 load balancer usage. For a
description of L7 load balancing see: :doc:`l7`

For the purposes of this guide we assume that the neutron command-line
interface is going to be used to configure all features of Neutron LBaaS with
an Octavia back-end. Also, in order to keep these examples short, we assume
that many non-L7 configuration tasks (such as deploying loadbalancers,
listeners, pools, members, healthmonitors, etc.) have already been
accomplished. A description of the starting conditions is given in each example
below.


Examples
========

.. _redirect-http-to-https-n:

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

::

    neutron lbaas-listener-create --name http_listener --loadbalancer lb1 --protocol HTTP --protocol-port 80
    neutron lbaas-l7policy-create --action REDIRECT_TO_URL --redirect-url https://www.example.com/ --listener http_listener --name policy1
    neutron lbaas-l7rule-create --type PATH --compare-type STARTS_WITH --value / policy1


.. _send-requests-to-static-pool-n:

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

::

    neutron lbaas-pool-create --name static_pool --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.10 --protocol-port 80 static_pool
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.11 --protocol-port 80 static_pool
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool static_pool --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type PATH --compare-type STARTS_WITH --value /js policy1
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool static_pool --listener listener1 --name policy2
    neutron lbaas-l7rule-create --type PATH --compare-type STARTS_WITH --value /images policy2

**Alternate solution** (using regular expressions):

1. Create pool *static_pool* on *lb1*.
2. Populate *static_pool* with the new back-end members.
3. Create L7 Policy *policy1* with action ``REDIRECT_TO_POOL`` pointed at
   *static_pool*.
4. Create an L7 Rule on *policy1* which uses a regular expression to match
   either "/js" or "/images" at the start of the request path.

**CLI commands**:

::

    neutron lbaas-pool-create --name static_pool --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.10 --protocol-port 80 static_pool
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.11 --protocol-port 80 static_pool
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool static_pool --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type PATH --compare-type REGEX --value '^/(js|images)' policy1


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

::

    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool pool2 --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type HOST_NAME --compare-type EQUAL_TO --value www2.example.com policy1


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

::

    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool pool2 --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type HOST_NAME --compare-type ENDS_WITH --value example.com policy1


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

::

    neutron lbaas-pool-create --name login_pool --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet secure_subnet --address 10.0.1.10 --protocol-port 80 login_pool
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool login_pool --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type COOKIE --key auth_token --compare-type REGEX --value '.*' --invert policy1


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

::

    neutron lbaas-pool-create --name login_pool --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet secure_subnet --address 10.0.1.10 --protocol-port 80 login_pool
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool login_pool --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type COOKIE --key auth_token --compare-type REGEX --value '.*' --invert policy1
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool login_pool --listener listener1 --name policy2
    neutron lbaas-l7rule-create --type COOKIE --key auth_token --compare-type EQUAL_TO --value INVALID policy2


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

::

    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool api_pool --listener listener1 --name policy1
    neutron lbaas-l7rule-create --type HOST_NAME --compare-type EQUAL_TO --value api.example.com policy1
    neutron lbaas-l7rule-create --type PATH --compare-type STARTS_WITH --value /api policy1


Set up A/B testing on an existing production site using a cookie
----------------------------------------------------------------
**Scenario description**:

* Listener *listener1* on load balancer *lb1* is a production site set up as
  described under :ref:`send-requests-to-static-pool-n` (alternate solution)
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

::

    neutron lbaas-pool-create --name pool_B --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.50 --protocol-port 80 pool_B
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.51 --protocol-port 80 pool_B
    neutron lbaas-pool-create --name static_pool_B --lb-algorithm ROUND_ROBIN --loadbalancer lb1 --protocol HTTP
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.100 --protocol-port 80 static_pool_B
    neutron lbaas-member-create --subnet private-subnet --address 10.0.0.101 --protocol-port 80 static_pool_B
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool static_pool_B --listener listener1 --name policy2 --position 1
    neutron lbaas-l7rule-create --type PATH --compare-type REGEX --value '^/(js|images)' policy2
    neutron lbaas-l7rule-create --type COOKIE --key site_version --compare-type EQUAL_TO --value B policy2
    neutron lbaas-l7policy-create --action REDIRECT_TO_POOL --redirect-pool pool_B --listener listener1 --name policy3 --position 2
    neutron lbaas-l7rule-create --type COOKIE --key site_version --compare-type EQUAL_TO --value B policy3
