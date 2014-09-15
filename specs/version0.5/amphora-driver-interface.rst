..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Amphora Driver Interface
==========================================
https://blueprints.launchpad.net/octavia/+spec/amphora-driver-interface

This blueprint describes how a driver will interface with the controller.
It will describe the base class and other classes required. It will not
describe the REST interface needed to talk to an amphora nor
how health information or statistsics are gathered from the amphora.


Problem description
===================
The controller needs to talk through a driver to the amphora to allow
for custom APIs and custom rendering of configuration data for
different amphora implementations.


Proposed change
===============
Establish a base class to model the desire functionality:

.. code:: python

    class AmphoraLoadBalancerDriver(object):

        def getLogger(self):
            #return the logger to use - this is a way to inject a custom logger for testing, etc

        def update(self, listener, vip):
            #update the amphora with a new configuration for the ;istener on vip
            raise NotImplementedError

        def suspend(self, listener, vip):
            #stop the listener - OPTIONAL
            raise NotImplementedError

        def enable(self, listener, vip):
            #start/enable the listener
            raise NotImplementedError

        def delete(self, listener, vip):
            #delete the listener from the amphora
            raise NotImplementedError

        def info(self, amphora):
            #returns information about the amphora, e.g. {"Rest Interface": "1.0", "Amphorae": "1.0",
            #   "packages":{"ha proxy":"1.5"}}
            #some information might come from querying the amphora
            raise NotImplementedError

        def get_metrics(self, amphora):
            #return ceilometer ready metrics - some amphora might choose to send them
            #straight to ceilometer others might use the mixin
            #support metrics to be compatible with Neutron LBaaS
            raise NotImplementedError

        def get_health(self, amphora):
            #returns map: {"amphora-status":HEALTHY, loadbalancers: {"loadbalancer-id": {"loadbalancer-status": HEALTHY,
            # "listeners":{"listener-id":{"listener-status":HEALTHY, "nodes":{"node-id":HEALTHY, ...}}, ...}, ...}}
            raise NotImplementedError

        def get_diagnostics(self, amphora):
            #run some expensive self tests to determine if the amphora and the lbs are healthy
            #the idea is that those tests are triggered more infrequent than the health
            #gathering
            raise NotImplementedError

The referenced listener is a listener object and vip a vip as described
in our model. The model is detached from the DB so the driver can't write
to the DB. Because our initial goal is to render a whole config no special
methods for adding nodes, health monitors, etc. are supported at this
juncture. This might be added in later versions.

No method for obtaining logs has been added. This will be done in a
future blueprint.


Exception Model
---------------

The driver is expected to raise the following well defined exceptions

* NotImplementedError - this functionality is not implemented/not supported
* AmphoraDriverError - a super class for all other exceptions and the catch
    all if no specific exception can be found
    * NotFoundError - this amphora couldn't be found/ was deleted by nova
    * InfoException - gathering information about this amphora failed
    * MetricsException - gathering metrics failed
    * UnauthorizedException - the driver can't access the amphora
    * StatisticsException - gathering statistics failed
    * TimeOutException - contacting the amphora timed out
    * UnavailableException - the amphora is temporary unavailable
    * DeleteFailed - this load balancer couldn't be deleted
    * SuspendFaied - this load balancer couldn't be suspended
    * EnableFailed - this load balancer couldn't be enabled
    * ArchiveException - couldn't archive the logs

        * TargetException - the target is not accessible
        * QuotaException - the target has no space left
        * UnauthorizedException - unauthorized to write to the target

    * ProvisioningErrors - those are errors which happen during provisioning
        * ListenerProvisioningError - could not provision Listener
        * LoadBalancerProvisoningError - could not provision LoadBalancer
        * HealthMonitorProvisioningError - could not provision HealthMonitor
        * NodeProvisioningError - could not provision Node


Health and Stat Mixin
---------------------
It has been suggested to gather health and statistic information
via UDP packets emitted from the amphora. This requires
each driver
to spin up a thread to listen on a UDP port and then hand the
information to the controller as a mixin to make sense of
it.

Here is the mixin definition:

.. code:: python

    class HealthMixIn(object):
        def update_health(health):
            #map: {"amphora-status":HEALTHY, loadbalancers: {"loadbalancer-id": {"loadbalancer-status": HEALTHY,
            # "listeners":{"listener-id":{"listener-status":HEALTHY, "nodes":{"node-id":HEALTHY, ...}}, ...}, ...}}
            # only items whose health has changed need to be submitted
            # awesome update code
            pass

    class StatsMixIn(object):
        def update_stats(stats):
            #uses map {"loadbalancer-id":{"listener-id": {"bytes-in": 123, "bytes_out":123, "active_connections":123,
            # "total_connections", 123}, ...}
            # elements are named to keep it extsnsible for future versions
            #awesome update code and code to send to ceilometer
            pass

Things a good driver should do:
-------------------------------

 * Non blocking IO - throw an appropriate exception instead
   to wait forever; use timeouts on sockets
 * We might employ a circuit breaker to insulate driver
   problems from controller problems [1]
 * Use appropriate logging
 * Use the preferred threading model

This will be demonstrated in the Noop-driver code.


Alternatives
------------
Require all amphora to implement a common REST interface
and use that as the integration point.


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
German Eichberger

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
None - we won't document the interface for 0.5. If that changes
we need to write an interface documentation so
3rd party drivers know what we expect.


References
==========
[1] http://martinfowler.com/bliki/CircuitBreaker.html


