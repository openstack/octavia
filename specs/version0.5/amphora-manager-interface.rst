..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Compute Driver Interface
==========================================
https://blueprints.launchpad.net/octavia/+spec/compute-driver-interface

This blueprint describes how a driver will interface with Nova to
manage the creation and deletion of amphora instances.  It will
describe the base class and other classes required to create, delete,
manage the execution state, and query the status of amphorae.

Problem description
===================
The controller needs to be able to create, delete, and monitor the
status of amphora instances.  The amphorae may be virtual machines,
containers, bare-metal servers, or dedicated hardware load balancers.
This interface should hide the implementation details of the amphorae
from the caller to the maximum extent possible.

This interface will provide means to specify:
 - type (VM, Container, bare metal)
 - flavor (provides means to specify memory and storage capacity)
 - what else?

Proposed change
===============
Establish an abstract base class to model the desired functionality:

.. code:: python

    class AmphoraComputeDriver(object):

        def build(self, amphora_type = VM, amphora_flavor = None,
                  image_id = None, keys = None, sec_groups = None,
                  network_ids = None,config_drive_files = None,user_data=None):

            """ build a new amphora.

            :param amphora_type: The type of amphora to create.  For
            version 0.5, only VM is supported.  In the future this
            may support Container, BareMetal, and HWLoadBalancer.
            :param amphora_flavor: Optionally specify a flavor.  The
            interpretation of this parameter will depend upon the
            amphora type and may not be applicable to all types.
            :param image_id: ID of the base image for a VM amphora
            :param keys: Optionally specify a list of ssh public keys
            :param sec_groups: Optionally specify list of security
            groups
            :param network_ids: A list of network_ids to attach to
            the amphora
            :config_drive_files: A dict of files to overwrite on
            the server upon boot. Keys are file names (i.e. /etc/passwd)
            and values are the file contents (either as a string or as
            a file-like object). A maximum of five entries is allowed,
            and each file must be 10k or less.
            :param user_data: user data to pass to be exposed by the
            metadata server this can be a file type object as well or
            a string

            :returns: The id of the new instance.

            """

            raise NotImplementedError

        def delete(self, amphora_id):
            """  delete the specified amphora
            """

            raise NotImplementedError

        def status(self, amphora_id):

            """ Check whether the specified amphora is up

            :param amphora_id: the ID of the desired amphora
            :returns: the nova response from the amphora
            """
            raise NotImplementedError

        def get_amphora(self, amphora_name = None, amphora_id = None):
            """ Try to find an amphora given its name or id

            :param amphora_name: the name of the desired amphora
            :param amphora_id: the id of the desired amphora
            :returns: the amphora object
            """
            raise NotImplementedError

Exception Model
---------------

The driver is expected to raise the following well defined exceptions:

* NotImplementedError - this functionality is not implemented/not supported
* AmphoraComputeError - a super class for all other exceptions and the catch
    all if no specific exception can be found

    * AmphoraBuildError - An amphora of the specified type could
      not be built
    * DeleteFailed - this amphora couldn't be deleted

* InstanceNotFoundError - an instance matching the desired criteria
  could not be found
* NotSuspendedError - resume() attempted on an instance that was not suspended



Things a good driver should do:
-------------------------------

 * Non blocking operations - If an operation will take a long time to execute,
   perform it asynchronously.  The definition of "a long time" is open to
   interpretation, but a common UX guideline is 200 ms
 * We might employ a circuit breaker to insulate driver
   problems from controller problems [1]
 * Use appropriate logging
 * Use the preferred threading model

This will be demonstrated in the Noop-driver code.


Alternatives
------------


Data model impact
-----------------
None


REST API impact
---------------
None


Security impact
---------------
None


Notifications impact
--------------------
None - since initial version


Other end user impact
---------------------
None


Performance Impact
------------------
Minimal


Other deployer impact
---------------------
Deployers need to make sure to bundle the compatible
versions of amphora, driver, controller --


Developer impact
----------------
Need to write towards this clean interface.


Implementation
==============

Assignee(s)
-----------
Al Miller

Work Items
----------
* Write abstract interface
* Write Noop driver
* Write tests


Dependencies
============
None


Testing
=======
* Unit tests with tox and Noop-Driver
* tempest tests with Noop-Driver


Documentation Impact
====================
None - this is an internal interface and need not be externally
documented.


References
==========
[1] http://martinfowler.com/bliki/CircuitBreaker.html
