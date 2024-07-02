..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Support for traffic rate limiting in Octavia
============================================
Rate limiting is an essential technique for managing
the traffic that is handled by
a load balancer and for ensuring fairness and system stability.

Problem description
===================
Without rate limiting malicious clients and bots
may be able to attack a server by flooding it with traffic or requests.
Rate limiting can help to limit the amount of resources that
single clients can allocate on server side and therefor
can help to mitigate DoS attacks.

Octavia already allows to limit the number of concurrent connections
by using the ``connection_limit`` option when configuring a listener. This
option will continue to exist and will work independently of this new rate
limiting feature.

Proposed change
===============
Both the data model and the REST API need to be extended.
The concept of *rate limit policies* and *rate limit rules* allows to manage
rules for rate limiting and to apply them to listeners. This document
refers to them as policies and rules for simplicity.

A policy consists of one or more rules.
Each policy defines an ``action`` that specifies the rate limiting method
that should be used.
Rules within a policy will be combined using a logical AND operation.
That means all rules within a policy need to be broken before rate limiting
gets applied. Multiple policies on a single listener logically OR
each other.

Rate limiting can be implemented in various ways using different metrics for
different protocols. Hence, this specification tries to be as flexible
as possible while keeping the API simple. Drivers may choose to
implement only a subset of the possible configuration variants,
or even none of them.
The algorithm used for rate limiting is considered an implementation detail
of the driver and out of the scope of this document.

Alternatives
------------
Rate limiting for all request based protocols (HTTP protocols) could be
done by extending the L7 policy API and by managing rules as L7 rules.

Rate limiting for all TCP based protocols could be supported
and configured using the listener API.

Splitting the configuration between two different APIs may confuse users,
however. Using a separate API for rate limiting seems like the cleaner
approach.

Data model impact
-----------------
A new ``RateLimitPolicy`` model class contains data about policies.
Its attributes are:

* ``id`` (string)
* ``name`` (string)
* ``description`` (string)
* ``rules`` (``RateLimitRule``\s)
* ``action`` (string)
* ``listener_id`` (string)
* ``listener`` (string)
* ``enabled`` (boolean)
* ``provisioning_status`` (string)
* ``operating_status`` (string)
* ``project_id`` (string)
* ``created_at`` (DateTime)
* ``updated_at`` (DateTime)
* ``tags`` (string)

The ``rules`` attribute forms a
one-to-many relationship with a new ``RateLimitRule`` model class.
``action`` defines the rate limiting method.
Possible values are
``DENY`` (respond with HTTP 429),
``REJECT`` (close the connection with no response),
``SILENT_DROP`` (like ``REJECT``, but without client notification)
``QUEUE`` (queue new requests, "leaky bucket") using a Python enum.
The existing ``Listener`` model class gets a new
one-to-may relationship with the
``RateLimitPolicy`` model class using a new ``rate_limit_policies``
attribute. That means a listener may have multiple policies, but a policy
can be linked to only one listener.

The new ``RateLimitRule`` model class defines a specific
rate limiting rule. Its attributes are:

* ``id`` (string)
* ``name`` (string)
* ``project_id`` (string)
* ``metric`` (string)
* ``threshold`` (integer)
* ``interval`` (integer, defaults to 30)
* ``urls`` (ScalarListType)
* ``provisioning_status`` (string)
* ``operating_status`` (string)
* ``tags`` (string)

Possible values of ``metric`` are
``REQUESTS`` ``REQUESTS_PER_URL``,
``KBYTES`` and ``PACKETS``.
``interval`` denotes the time interval in seconds in
which the metric gets measured for each client.
``threshold`` defines the threshold at which the rate gets limited.
The ``urls`` field defines the URL paths for the specific rule and is
ignored if ``metric`` is not ``REQUESTS_PER_URL``.

REST API impact
---------------
If not stated otherwise the attributes in the responses match with the
ones in the data model. The relationships will be shown using IDs of
related objects.

Listener
~~~~~~~~
The listener API gets a new ``rate_limit_policies`` (Optional) attribute.
Valid values are ``null`` (the default) or a list of policy IDs.

Rate Limit Policy
~~~~~~~~~~~~~~~~~
The request of the ``POST /v2/lbaas/ratelimitpolicies``
and ``PUT /v2/lbaas/ratelimitpolicies/{policy_id}`` methods of the
``Rate Limit Policy`` API takes the attributes
``name`` (Optional), ``description`` (Optional), ``listener_id``,
``action``,
``enabled`` (Optional), ``project_id`` (Optional), ``tags`` (Optional).
The response contains all attributes in the data model.
The ``GET /v2/lbaas/ratelimitpolicies`` method supports the attributes
the ``project_id`` (Optional) and ``fields`` (Optional).
The response is a list of policies filtered by the optional ``project_id``
and containing the desired ``fields`` (or all).
The endpoint ``/v2/lbaas/ratelimitpolicies/{policy_id}`` supports the
``GET`` and ``DELETE`` methods.

Rate Limit Rule
~~~~~~~~~~~~~~~
The ``GET /v2/lbaas/ratelimitpolicies/{policy_id}/rules``
method behaves like the GET method for the policy, but for rules.
The ``POST /v2/lbaas/ratelimitpolicies/{policy_id}/rules`` method accepts
the request attributes ``listener_id``,
``project_id`` (Optional),
``metric``, ``threshold``, ``interval`` (Optional), ``urls`` (Optional)
``tags`` (Optional).
The ``GET /v2/lbaas/ratelimitpolicies/{policy_id}/rules/{rule_id}`` request
accepts an optional ``fields`` attribute.
The ``PUT /v2/lbaas/ratelimitpolicies/{policy_id}/rules/{rule_id}``
method accepts
the request attributes `, ``project_id`` (Optional),
``metric``, ``threshold``, ``interval`` (Optional), ``urls`` (Optional),
``tags`` (Optional).
The ``DELETE /v2/lbaas/ratelimitpolicies/{policy_id}/rules/{rule_id}``
method has no response body.

Security impact
---------------
None.

Notifications impact
--------------------
None.

Other end user impact
---------------------
None.

Performance Impact
------------------
Rate limiting is an optional feature and has no performance impact in a
default configuration. Depending on the complexity of the rules and the
implementation, some processing overhead may impact performance. In the
ACTIVE/STANDBY topology some additional network overhead for synchronization
of request statistics (ie. stick tables for Amphorae) is to be expected.

Overall,
however, fairness and performance can improve when using rate limiting.

Other deployer impact
---------------------
Deployers might want to review the RAM setting of the Nova flavor
that is used for the load balancers. Rate limiting will require some
additional memory on Amphorae, depending on the number of rules and
the interval setting.

Developer impact
----------------
Driver developers are impacted by the extended API and data model that allows
them to implement the new feature in future versions.

Implementation
==============
The reference implementation using the Amphora driver will use HAProxy's own
rate limiting capabilities. In addition to limiting the number of
HTTP requests it will also be possible to limit the number of HTTP requests
by URL path [#haproxy-url-path]_.
The sliding window rate limiting algorithm will be
used [#haproxy-four-examples]_.

Rate limiting based on the TCP protocol is not part of the
initial implementation, but might be added in a future version.
This could be done using ``nftables`` rules [#nftables]_.

Assignee(s)
-----------
Primary assignee:
  Tom Weininger

Work Items
----------
#. Adjust API documentation
#. Create user documentation
#. Implement HTTP rate limiting in Amphora driver
#. Implement HTTP by URL rate limiting in Amphora driver
#. Implement unit tests

Dependencies
============
None.

Testing
=======
Testing should focus on API changes, verification and correctness of
generated HAProxy configuration.

Documentation Impact
====================
API and user documentation will need to be extended.

References
==========

.. [#haproxy-four-examples] https://www.haproxy.com/blog/four-examples-of-haproxy-rate-limiting
.. [#nftables] https://wiki.nftables.org/wiki-nftables/index.php/Meters
.. [#haproxy-url-path] https://www.haproxy.com/documentation/haproxy-configuration-tutorials/traffic-policing/#rate-limit-http-requests-by-url-path
