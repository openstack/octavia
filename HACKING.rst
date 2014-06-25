Octavia Style Commandments
=======================
This project was ultimately spawned from work done on the Neutron project.
As such, we tend to follow Neutron conventions regarding coding style.

- We follow the OpenStack Style Commandments:
  http://docs.openstack.org/developer/hacking/

Octavia Specific Commandments
--------------------------

- [N320] Validate that LOG messages, except debug ones, have translations

Creating Unit Tests
-------------------
For every new feature, unit tests should be created that both test and
(implicitly) document the usage of said feature. If submitting a patch for a
bug that had no unit test, a new passing unit test should be added. If a
submitted bug fix does have a unit test, be sure to add a new one that fails
without the patch and passes with the patch.
