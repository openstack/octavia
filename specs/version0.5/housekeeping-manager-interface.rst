..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Housekeeping Manager Specification
==========================================
https://blueprints.launchpad.net/octavia/+spec/housekeeping-manager

Problem description
===================

The Housekeeping Manager will manage the spare amphora pool and the
teardown of amphorae that are no longer needed. On a configurable
interval the Housekeeping Manager will check the Octavia database to
identify the required cleanup and maintenance actions required. The
amphora-lifecycle-management specification details the Create and
Deactivate amphora sequences the Housekeeping Manager will follow.


Proposed change
===============
The housekeeping manager will run as a daemon process which will
perform the following actions:

* Read the following from the configuration file

  * housekeeping_interval: The time (in seconds) that the
    housekeeping manager will sleep before running its checks
    again.
  * spare_amphora_pool_size: The desired number of spare amphorae.
  * maximum_deploying_amphora_count: The maximum number of amphorae
    that may be deployed simultaneously.
  * maximum_preserved_amphora_count: How many deactivated amphorae to
    preserve.  0 means delete, 1 or greater means keep up to that many
    amphorae for future diagnostics.  Only amphorae in the ERROR and
    PRESERVE states are eligible to be preserved.  TODO: Right now
    there is no PRESERVE state, for this to work we would need to
    define one in the amphora spec.
  * preservation_scheme

    * "keep": keep all preserved amphorae
    * "cycle": maintain a queue of preserved amphorae, deleting the
      oldest one when a new amphora is preserved.

  * preservation_method: Preservation must take into account the
    possibility that amphorae instantiated in the future may reuse MAC
    addresses.

    * "unplug": Disconnect the virtual NICs from the amphora
    * "snapshot":  Take a snapshot of the amphora, then stop it

* Get the spare pool size

  * Log the spare pool size
  * If the spare pool size is less than the spare pool target
    capacity, initiate creation of appropriate number of amphorae.

* Obtain the list of deactivated amphorae and schedule their removal.
  If preservation_count > 0, and there are fewer than that many
  amphorae in the preserved pool, preserve the amphora.  After the
  preserved pool size reaches preservation_count, use
  preservation_scheme to determine whether to keep newly failed
  amphorae.

* Sleep for the time specified by housekeeping_interval.

* Return to the top

Establish a base class to model the desired functionality:

.. code:: python


    class HousekeepingManager(object):

    """ Class to manage the spare amphora pool.  This class should do
    very little actual work, its main job is to monitor the spare pool
    and schedule creation of new amphrae and removal of used amphrae.
    By default, used amphorae will be deleted, but they may optionally
    be preserved for future analysis.
    """

        def get_spare_amphora_size(self):
            """ Return the target capacity of the spare pool """
            raise NotImplementedError

        def get_ready_spare_amphora_count(self):
            """ Return the number of available amphorae in the spare pool
            """
            raise NotImplementedError

        def create_amphora(self, num_to_create = 1):
            """ Schedule the creation of the specified number of amphorae
            to be added to the spare pool."""
            raise NotImplementedError

        def remove_amphora(self, amphora_ids):
            """ Schedule the removal of the amphorae specified by
            amphora_ids."""
            raise NotImplementedError

Exception Model
---------------

The manager is expected to raise or pass along the following
well-defined exceptions:

* NotImplementedError - this functionality is not implemented/not supported
* AmphoraDriverError - a super class for all other exceptions and the catch
    all if no specific exception can be found
    * NotFoundError - this amphora couldn't be found/ was deleted by nova
    * UnauthorizedException - the driver can't access the amphora
    * UnavailableException - the amphora is temporary unavailable
    * DeleteFailed - this load balancer couldn't be deleted

Alternatives
------------

Data model impact
-----------------

Requires the addition of the housekeeping_interval, spare_pool_size,
spare_amphora_pool_size, maximum_preserved_amphora_count,
preservation_scheme, and preservation_method to the config.


REST API impact
---------------

None.

Security impact
---------------

Must follow standard practices for database access.

Notifications impact
--------------------

Other deployer impact
---------------------

Other end user impact
---------------------

There should be no end-user-visible impact.

Performance Impact
------------------

The housekeeping_interval and spare_pool_size parameters will be
adjustable by the operator in order to balance resource usage against
performance.


Developer impact
----------------

Developers of other modules need to be aware that amphorae may be
created, deleted, or saved for diagnosis by this daemon.


Implementation
==============

Assignee(s)
-----------
Al Miller <ajmiller>

Work Items
----------
* Write abstract interface
* Write Noop driver
* Write tests


Dependencies
============
Amphora driver
Config manager



Testing
=======
* Unit tests with tox and Noop-Driver
* tempest tests with Noop-Driver


Documentation Impact
====================
None - we won't document the interface for 0.5. If that changes
we need to write an interface documentation so
3rd party drivers know what we expect.


References
==========
