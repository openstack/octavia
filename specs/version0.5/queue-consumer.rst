..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
Queue Consumer
==============
https://blueprints.launchpad.net/octavia/+spec/queue-consumer

This blueprint describes how Oslo messages are consumed, processed and
delegated from the API-controller queue to the controller worker component of
Octavia. The component that is responsible for these activities is called the
Queue Consumer.

Problem description
===================
Oslo messages need to be consumed by the controller and delegated to the proper
controller worker. Something needs to interface with the API-controller queue
and spawn the controller workers. That "something" is what we are calling the
Queue Consumer.

Proposed change
===============
The major component of the Queue Consumer will be a class that acts as a
consumer to Oslo messages. It will be responsible for configuring and starting
a server that is then able to receive messages. There will be a one-to-one
mapping between API methods and consumer methods (see code snippet below).
Corresponding controller workers will be spawned depending on which consumer
methods are called.

The threading will be handled by Oslo messaging using the 'eventlet' executor.
Using the 'eventlet' executor will allow for message throttling and removes
the need for the controller workers to manage threads. The benefit of using the
'eventlet' executor is that the Queue Consumer will not have to spawn threads
at all, since every message received will be in its own thread already. This
means that the Queue Consumer doesn't spawn a controller worker, rather it just
starts the execution of the deploy code.

An 'oslo_messaging' configuration section will need to be added to octavia.conf
for Oslo messaging options. For the Queue Consumer, the 'rpc_thread_pool_size'
config option will need to be added. This option will determine how many
consumer threads will be able to read from the queue at any given time (per
consumer instance) and serve as a throttling mechanism for message consumption.
For example, if 'rpc_thread_pool_size' is set to 1 thread then only one
controller worker will be able to conduct work. When that controller worker
completes its task then a new message can be consumed and a new controller
worker flow started.

Below are the planned interface methods for the queue consumer. The Queue
Consumer will be listening on the **OCTAVIA_PROV** (short for octavia
provisioning) topic. The *context* parameter will be supplied along with an
identifier such as a load balancer id, listener id, etc. relevant to the
particular interface method. The *context* parameter is a dictionary and is
reserved for metadata. For example, the Neutron LBaaS agent leverages this
parameter to send additional request information. Additionally, update methods
include a *\*_updates* parameter than includes the changes that need to be
made. Thus, the controller workers responsible for the update actions will
need to query the database to retrieve the old state and combine it with the
updates to provision appropriately. If a rollback or exception occur, then the
controller worker will only need to update the provisioning status to **ERROR**
and will not need to worry about making database changes to attributes of the
object being updated.

.. code:: python

    def create_load_balancer(self, context, load_balancer_id):
        pass

    def update_load_balancer(self, context, load_balancer_updates,
                             load_balancer_id):
        pass

    def delete_load_balancer(self, context, load_balancer_id):
        pass

    def create_listener(self, context, listener_id):
        pass

    def update_listener(self, context, listener_updates, listener_id):
        pass

    def delete_listener(self, context, listener_id):
        pass

    def create_pool(self, context, pool_id):
        pass

    def update_pool(self, context, pool_updates, pool_id):
        pass

    def delete_pool(self, context, pool_id):
        pass

    def create_health_monitor(self, context, health_monitor_id):
        pass

    def update_health_monitor(self, context, health_monitor_updates,
                              health_monitor_id):
        pass

    def delete_health_monitor(self, context, health_monitor_id):
        pass

    def create_member(self, context, member_id):
        pass

    def update_member(self, context, member_updates, member_id):
        pass

    def delete_member(self, context, member_id):
        pass

Alternatives
------------
There are a variety of ways to consume from Oslo messaging. For example,
instead of having a single consumer on the controller we could have multiple
consumers (i.e. one for CREATE messages, one for UPDATE messages, etc.).
However, since we merely need something to pass messages off to controller
workers other options are overkill.

Data model impact
-----------------
While there is no direct data model impact it is worth noting that the API
will not be persisting updates to the database. Rather, delta updates will pass
from the user all the way to the controller worker. Thus, when the controller
worker successfully completes the prescribed action, only then will it persist
the updates to the database. No API changes are necessary for create and update
actions.

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
The only performance related item is queue throttling. This is done by design
so that operators can safely throttle incoming messages dependent on their
specific needs.

Other deployer impact
---------------------
Configuration options will need to be added to ocativa.conf. Please see above
for more details.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------
jorge-miramontes

Work Items
----------
- Implement consumer class
- Add executable queue-consumer.py to bin directory

Dependencies
============
https://blueprints.launchpad.net/octavia/+spec/controller-worker

Testing
=======
Unit tests

Documentation Impact
====================
None

References
==========
None
