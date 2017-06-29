..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

========================================
Align octavia API With Neutron LBaaS API
========================================


Problem description
===================
For the octavia API to truly be standalone, it needs to have capability parity
with Neutron LBaaS's API.  Neutron LBaaS has the luxury of piggy-backing off
of Neutron's API.  This gives Neutron LBaaS's API resources many capabilities
for free.  This document is meant to enumerate those capabilities that the
octavia API does not possess at the time of this writing.

Proposed change
===============
Complete the tasks enumerated in the `Work Items`_ section

Alternatives
------------
* Do nothing and keep the status quo

Data model impact
-----------------
There will be some minor data model changes to octavia in support of this
change.

REST API impact
---------------
This change will have significant impact to the octavia API.

Security impact
---------------
This change will improve octavia security by adding keystone authentication.

Notifications impact
--------------------
No expected change.

Other end user impact
---------------------
Users will be able to use the new octavia API endpoint for LBaaS.

Performance Impact
------------------
This change may slightly improve performance by reducing the number of
software layers requests will traverse before responding to the request.

Other deployer impact
---------------------
Over time the neutron-lbaas package will be deprecated and deployers will
only require octavia for LBaaS.

Developer impact
----------------
This will simplify LBaaS development by reducing the number of databases
as well as repositories that require updating for LBaaS enhancements.

Implementation
==============

Assignee(s)
-----------
blogan
diltram
johnsom
rm_you
dougwig

Work Items
----------
Implement the following API Capabilities:

* Keystone Authentication
* Policy Engine
* Pagination
* Quotas
* Filtering lists by query parameter
* Fields by query parameter
* Add the same root API endpoints as n-lbaas
* Support "provider" option in the API to select a driver to spin up a load
  balancer.
* API Handler layer to become the same as n-lbaas driver layer and allow
  multiple handlers/drivers.
* Neutron LBaaS V2 driver to octavia API Handler shim layer

Implement the following additional features that n-lbaas maintains:

* OSC extension via a new repository 'python-octaviaclient'


Other Features to be Considered:

* Notifications for resource creating, updating, and deleting.
* Flavors
* Agent namespace driver or some lightweight functional driver.
* Testing octavia with all of the above
* REST API Microversioning

Dependencies
============
None

Testing
=======
Api tests from neutron-lbaas will be used to validate the new octavia API.

Documentation Impact
====================
The octavia api reference will need to be updated.

References
==========
