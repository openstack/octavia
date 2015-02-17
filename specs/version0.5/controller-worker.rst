..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================
Controller Worker (deploy-worker)
==================================

Launchpad blueprint:

https://blueprints.launchpad.net/octavia/+spec/controller-worker

Octavia is an operator-grade reference implementation for Load Balancing as a
Service (LBaaS) for OpenStack.  The component of Octavia that does the load
balancing is known as Amphora.

The component of Octavia that provides command and control of the Amphora is
the Octavia controller.

Problem description
===================

Components of the Octavia controller require a shared library that provides
the orchestration of create/update/delete actions for Octavia objects such as
load balancers and listeners.

It is expected that this library will be used by the Queue Consumer to service
API requests, by the Housekeeping Manager to manage the spare Amphora pool,
and by the Health Manager to fail over failed objects.

Proposed change
===============

The Controller Worker will be implemented as a class that provides methods to
facilitate the create/update/delete actions.  This class will be responsible
for managing the number of simultaneous operations being executed by
coordinating through the Octavia database.

The Controller Worker will provide a base class that sets up and initilizes
the TaskFlow engines required to complete the action.  Users of the library
will then call the appropriate method for the action.  These methods setup
and launch the appropriate flow.  Each flow will be contained in a seperate
class for code reuse and supportability.

The Controller Worker library will provide the following methods:

.. code:: python

    def create_amphora(self):
        """
            Creates an Amphora.

            :returns: amphora_id
        """
        raise NotImplementedError

    def delete_amphora(self, amphora_id):
        """
            Deletes an existing Amphora.

            :returns: None
            :raises AmphoraNotFound: The referenced Amphora was not found
        """
        raise NotImplementedError

    def create_load_balancer(self, load_balancer_id):
        """
            Creates a load balancer by allocating Amphorae.

            :returns: None
            :raises NoSuitableAmphora: Unable to allocate an Amphora.
        """
        raise NotImplementedError

    def update_load_balancer(self, load_balancer_updates, load_balancer_id):
        """
            Updates a load balancer.

            :returns: None
            :raises LBNotFound: The referenced load balancer was not found
        """
        raise NotImplementedError

    def delete_load_balancer(self, load_balancer_id):
        """
            Deletes a load balancer by de-allocating Amphorae.

            :returns: None
            :raises LBNotFound: The referenced load balancer was not found
        """
        raise NotImplementedError

    def create_listener(self, listener_id):
        """
            Creates a listener.

            :returns: None
            :raises NoSuitableLB: Unable to find the load balancer
        """
        raise NotImplementedError

    def update_listener(self, listener_updates, listener_id):
        """
            Updates a listener.

            :returns: None
            :raises ListenerNotFound: The referenced listener was not found
        """
        raise NotImplementedError

    def delete_listener(self, listener_id):
        """
            Deletes a listener.

            :returns: None
            :raises ListenerNotFound: The referenced listener was not found
        """
        raise NotImplementedError

    def create_pool(self, pool_id):
        """
            Creates a node pool.

            :returns: None
            :raises NoSuitableLB: Unable to find the load balancer
        """
        raise NotImplementedError

    def update_pool(self, pool_updates, pool_id):
        """
            Updates a node pool.

            :returns: None
            :raises PoolNotFound: The referenced pool was not found
        """
        raise NotImplementedError

    def delete_pool(self, pool_id):
        """
            Deletes a node pool.

            :returns: None
            :raises PoolNotFound: The referenced pool was not found
        """
        raise NotImplementedError

    def create_health_monitor(self, health_monitor_id):
        """
            Creates a health monitor.

            :returns: None
            :raises NoSuitablePool: Unable to find the node pool
        """
        raise NotImplementedError

    def update_health_monitor(self, health_monitor_updates, health_monitor_id):
        """
            Updates a health monitor.

            :returns: None
            :raises HMNotFound: The referenced health monitor was not found
        """
        raise NotImplementedError

    def delete_health_monitor(self, health_monitor_id):
        """
            Deletes a health monitor.

            :returns: None
            :raises HMNotFound: The referenced health monitor was not found
        """
        raise NotImplementedError

    def create_member(self, member_id):
        """
            Creates a pool member.

            :returns: None
            :raises NoSuitablePool: Unable to find the node pool
        """
        raise NotImplementedError

    def update_member(self, member_updates, member_id):
        """
            Updates a pool member.

            :returns: None
            :raises MemberNotFound: The referenced member was not found
        """
        raise NotImplementedError

    def delete_member(self, member_id):
        """
            Deletes a pool member.

            :returns: None
            :raises MemberNotFound: The referenced member was not found
        """
        raise NotImplementedError

Alternatives
------------
This code could be included in the Queue Consumer component of the controller.
However this would not allow the library to be shared with other components of
the controller, such as the Health Manager

Data model impact
-----------------


REST API impact
---------------
None

Security impact
---------------


Notifications impact
--------------------


Other end user impact
---------------------


Performance Impact
------------------


Other deployer impact
---------------------


Developer impact
----------------


Implementation
==============

Assignee(s)
-----------
Michael Johnson <johnsom>

Work Items
----------


Dependencies
============
https://blueprints.launchpad.net/octavia/+spec/amphora-driver-interface
https://blueprints.launchpad.net/octavia/+spec/neutron-network-driver
https://blueprints.launchpad.net/octavia/+spec/nova-compute-driver

Testing
=======
Unit tests

Documentation Impact
====================
None

References
==========
https://blueprints.launchpad.net/octavia/+spec/health-manager
https://blueprints.launchpad.net/octavia/+spec/housekeeping-manager
https://blueprints.launchpad.net/octavia/+spec/queue-consumer
