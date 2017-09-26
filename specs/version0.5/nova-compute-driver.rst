..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================
Nova Compute Driver
===================

Blueprint: https://blueprints.launchpad.net/octavia/+spec/nova-compute-driver

Octavia needs to interact with nova for creation of VMs for this version.  This
spec will flesh out all the methods described in the compute-driver-interface
with nova VM specific commands.

Problem description
===================
This spec details operations for creating, updating, and modifying amphora that
will hold the actual load balancer.  It will utilize the nova client python api
version 3 for the nova specific requests and commands.

Proposed change
===============
Expose nova operations

- Build:  Will need to build a virtual machine according to configuration
  parameters

  - Will leverage the nova client ServerManager method "create" to build a
    server

- Get:  Will need to retrieve details of the virtual machine from nova

  - Will leverage the nova client ServerManager method "get" to retrieve a
    server, and return an amphora object

- Delete:  Will need to remove a virtual machine

  - Will leverage the nova client ServerManager method "delete" for removal of
    server

- Status:  Will need to retrieve the status of the virtual machine

  - Will leverage the aforementioned get call to retrieve status of the server

Alternatives
------------
None

Data model impact
-----------------
Add fields to existing Amphora object

REST API impact
---------------
None

Security impact
---------------
None

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
Will need a nova service account and necessary credentials stored in config

Implementation
==============

Assignee(s)
-----------
trevor-vardeman

Work Items
----------
Expose nova operations

Dependencies
============
compute-driver-interface

Testing
=======
Unit tests
Functional tests

Documentation Impact
====================
None

References
==========
https://blueprints.launchpad.net/octavia/+spec/nova-compute-driver
https://docs.openstack.org/python-novaclient/latest/reference/api/index.html
