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
how health information or statistics are gathered from the amphora.


Problem description
===================
The controller needs to talk through a driver to the amphora to allow
for custom APIs and custom rendering of configuration data for
different amphora implementations.

The controller will heavily utilize taskflow [2] to accomplish its goals
so it is highly encouraged for drivers to use taskflow to organize their
work, too.


Proposed change
===============
Establish a base class to model the desire functionality:

.. code:: python

    class AmphoraLoadBalancerDriver(object):

        def update(self, listener, vip):
            """updates the amphora with a new configuration

            for the listener on the vip.
            """
            raise NotImplementedError

        def stop(self, listener, vip):
            """stops the listener on the vip."""
            return None

        def start(self, listener, vip):
            """starts the listener on the vip."""
            return None

        def delete(self, listener, vip):
            """deletes the listener on the vip."""
            raise NotImplementedError

        def get_info(self, amphora):
            """Get detailed information about an amphora

            returns information about the amphora, e.g. {"Rest Interface":
            "1.0", "Amphorae": "1.0", "packages":{"ha proxy":"1.5"},
            "network-interfaces": {"eth0":{"ip":...}} some information might
            come from querying the amphora
            """
            raise NotImplementedError

        def get_diagnostics(self, amphora):
            """OPTIONAL - Run diagnostics

            run some expensive self tests to determine if the amphora and the
            lbs are healthy the idea is that those tests are triggered more
            infrequent than the heartbeat
            """
            raise NotImplementedError

        def finalize_amphora(self, amphora):
            """OPTIONAL - called once an amphora has been build but before

            any listeners are configured. This is a hook for drivers who need
            to do additional work before am amphora becomes ready to accept
            listeners. Please keep in mind that amphora might be kept in am
            offline pool after this call.
            """
            pass

        def post_network_plug(self, amphora, port):
            """OPTIONAL - called after adding a compute instance to a network.

            This will perform any necessary actions to allow for connectivity
            for that network on that instance.

            port is an instance of octavia.network.data_models.Port.  It
            contains information about the port, subnet, and network that
            was just plugged.
            """

        def post_vip_plug(self, load_balancer, amphorae_network_config):
            """OPTIONAL - called after plug_vip method of the network driver.

            This is to do any additional work needed on the amphorae to plug
            the vip, such as bring up interfaces.

            amphorae_network_config is a dictionary of objects that include
            network specific information about each amphora's connections.
            """

        def start_health_check(self, health_mixin):
            """start check health

            :param health_mixin: health mixin object
            :type amphora: object

            Start listener process and  calls HealthMixin to update
            databases information.
            """
            pass

        def stop_health_check(self):
            """stop check health

            Stop listener process and  calls HealthMixin to update
            databases information.
            """
            pass

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
    * NetworkConfigException - gathering network information failed
    * UnauthorizedException - the driver can't access the amphora
    * TimeOutException - contacting the amphora timed out
    * UnavailableException - the amphora is temporary unavailable
    * SuspendFaied - this load balancer couldn't be suspended
    * EnableFailed - this load balancer couldn't be enabled
    * DeleteFailed - this load balancer couldn't be deleted
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
            # elements are named to keep it extensible for future versions
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
[1] https://martinfowler.com/bliki/CircuitBreaker.html
[2] https://docs.openstack.org/taskflow/latest/


