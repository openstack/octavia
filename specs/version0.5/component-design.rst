..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Octavia v0.5 master component design document
=============================================


Problem description
===================
We need to define the various components that will make up Octavia v0.5.

Proposed change
===============
This is the first functional release of Octavia, incorporating a scalable
service delivery layer, but not yet concerned with a scalable command and
control layer.

See doc/source/design/version0.5 for a detailed description of the v0.5
component design.

Alternatives
------------
We're open to suggestions, but note that later designs already discussed on the
mailing list will incorporate several features of this design.

Data model impact
-----------------
Octavia 0.5 introduces the main data model which will also be used in
subsequent releases.


REST API impact
---------------
None


Security impact
---------------
The only sensitive data used in Octavia 0.5 are the TLS private keys used with
TERMINATED_HTTPS functionality. However, the back-end storage aspect of these
secrets will be handled by Barbican.

Octavia amphorae will also need to keep copies of these secrets locally in
order to facilitate seamless service restarts. These local stores should be
made on a memory filesystem.


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
Operator API and UI may need to be changed as a result of this specification.


Developer impact
----------------
None beyond implementing the spec. :)


Implementation
==============

Assignee(s)
-----------
Lots of us will be working on this!


Work Items
----------
Again, lots of things to be done here.


Dependencies
============
Barbican


Testing
=======
A lot of new tests will need to be written to test the separate components,
their interfaces, and likely failure scenarios.


Documentation Impact
====================
This specification largely defines the documentation of the component design.

Component design is becoming a part of the project standard documentation.


References
==========
Mailing list discussion of similar designs earlier this year
