..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
HAProxy Amphora API
===================

https://blueprints.launchpad.net/octavia/+spec/appliance-api

The reference implementation of Octavia is going to make use of an haproxy-
based amphora. As such, there will be an haproxy reference driver that speaks
a well-defined protocol to the haproxy-based amphora. This document is meant
to be a foundation of this interface, outlining in sufficient detail the
various commands that will definitely be necessary. This design should be
iterated upon as necessary going forward.

Problem description
===================
This API specification is necessary in order to fully develop the haproxy
reference driver, both to ensure this interface is well documented, and so that
different people can work on different parts of bringing Octavia to fruition.

Proposed change
===============
Note that this spec does not yet attempt to define the following, though these
may follow shortly after this initial spec is approved:
* Method for bi-directional authentication between driver and amphora.
* Bootstrapping process of amphora
* Transition process from "spare" to "active" amphora and other amphora
lifecycle transitions

This spec does attempt to provide an initial foundation for the following:
* RESTful interface exposed on amphora management

Alternatives
------------
None

Data model impact
-----------------
None (yet)

REST API impact
---------------
Please note that the proposed changes in this spec do NOT affect either the
publicly-exposed user or operator APIs, nor really anything above the
haproxy reference driver.

Please see doc/main/api/haproxy-amphora-api.rst

Security impact
---------------
None yet, though bi-directional authentication between driver and amphora needs
to be addressed.

Notifications impact
--------------------
None

Other end user impact
---------------------
None

Performance Impact
------------------
None

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
stephen-balukoff
david-lenwell

Work Items
----------

Dependencies
============
haproxy reference driver

Testing
=======
Unit tests

Documentation Impact
====================
None

References
==========
None

