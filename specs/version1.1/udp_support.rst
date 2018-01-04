..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========
UDP Support
===========

https://storyboard.openstack.org/#!/story/1657091

Problem description
===================
Currently, the default driver of Octavia (haproxy) only supports TCP, HTTP,
HTTPS, and TERMINATED_HTTPS. We need support for load balancing UDP.

For some use-cases, UDP load balancing support is useful. One such case are
real-time media streaming applications which are based on RTSP [#foot1]_.

For the Internet of Things (IoT) [#foot2]_, there are many services or
applications that use UDP as their transmission protocol. For example:
CoAP [#foot3]_ (Constrained Application Protocol),
DDS [#foot4]_ (Data Distribution Service) for Real-Time systems, and the
introduction protocol Thread [#foot5]_.

Applications with high demand for real-time (like video chatting) run on
RDUP [#foot6]_ (Reliable User Datagram Protocol),
RTP [#foot7]_ (RealTime Protocol) and UDT [#foot8]_
(UDP-based Data Transfer Protocol). These protocols also are based on UDP.

There isn't any option in the API for these protocols, which Layer 4 UDP would
provide. This means that customers lack a way to support these services which
may be running on VM instances in an OpenStack environment.


Proposed change
===============
This spec extends the LBaaSv2 API to support `UDP` as a protocol in Listener
and Pool resource requests.

It will require a new load balancing engine to support this feature, as the
current haproxy engine only supports TCP based protocols. If users want a load
balancer which supports both TCP and UDP, this need cannot be met by launching
haproxy-based amphora instances. It's the good time to extend octavia to
support more load balancing scenarios. This spec will introduce how
LVS [#foot9]_ can work with haproxy for UDP loadbalancing. The reason for
choosing LVS is that we can easily integrate it with the existing
``keepalived`` service. That means we can configure LVS via ``keepalived``, and
check member health as well.

For the current service VM driver implementation, haproxy runs in the
amphora-haproxy namespace in an amphora instance. So we also need to configure
``keeplived`` in the same namespace for UDP cases even in SINGLE topology.
For ACTIVE_STANDBY, ``keepalived`` will serve two purposes: UDP and VRRP.
So, one instance of ``keepalived`` must be bound in the namespace, along with
the LVS instance it configures.

The main idea is to use ``keepalived`` to configure and manage LVS [#foot10]_
and its configuration. We also need to check the members' statuses with
``keepalived`` instead of ``haproxy``, so there must be a different workflow
in Octavia resources and deployment topologies. The simplest implementation is
LVS within NAT mode, so we will only support this mode to start. If possible
we will add other modes in the future.

Currently, a single ``keepalived`` instance can support multiple virtual server
configurations, but for minimal impact of reconfiguration to the existing
listeners, we'd better not to refresh all the ``keepalived`` configuration
files and restart the instances, because that would cause all listeners traffic
to be blocked if the LVS configuration maintained by ``keepalived`` is removed.
This spec proposes that each listener will have its own ``keepalived`` process,
but that process won't contain a VRRP instance, just the configuration
of virtual server and real servers. That means if the Loadbalancer service is
running with ACTIVE-STANDBY topology, each amphora instance will run multiple
``keepalived`` instances, the count being N+1 (where N is the UDP ``Listener``
count, and +1 is the VRRP instance for HA).  The existing ``keepalived``
will be used, but each "UDP Listener keepalived process" will need to be
controlled by health check of the Main VRRP keepalived process. Then the VIP
could be moved to the BACKUP amphorae instance in ACTIVE/STANDBY topology if
there is any issue with these UDP keepalived processes. The health check will
simply reflect whether the keepalived processes are alive.

The workflow for this feature contains:

1. Add a new ``keepalived`` jinja template to support LVS configuration.
2. Add ``netcat`` into dib-elements for supporting all platforms.
3. Extend the ability of amphora agent to run ``keepalived`` with LVS
   configuration in amphora instances, including the init configuration, such
   as systemd, sysvinit and upstart.
4. Enhance the session persistence to work with UDP and enable/disable the
   "One-Packet-Scheduling" option.
5. Update the database to allow listeners to support both ``tcp`` and ``udp``
   on the same port, add ``udp`` as a valid protocol and
   ``ONE_PACKET_SCHEDULING`` as a valid session_persistence_type in the
   database.
6. Setup validation code for supported features of UDP load balancing (such as
   session persistence, types of health monitors, load balancing algorithms,
   number of L7 policies allowed, etc).
7. Extend the existing LBaaSv2 API in Octavia to allow ``udp`` parameters in
   the ``Listener`` resource.
8. Extend the Loadbalancer/Listener flows to support udp loadbalancer in the
   particular topologies.

Alternatives
------------
Introduce a new UDP driver based on LVS or other Loadbalancer engines. Then
find a way to fix the gap of the current Octavia data models which have a
strong relationship with HTTP which based on TCP.

Provide a new driver provider framework to change the amphorae backend from
haproxy to some other load balancer engines, for example, if we introduce LVS
driver, we may just support the simple L7 functions with LVS, as it's a risk to
change provider from existing haproxy-based amphora instances to LVS ones. If
possible, we need to limit the API to not support fields/resources if the
backend driver is LVS, such as "insert_headers" in Listener, L7Policies,
L7Rules and etc, a series fields/resources that related to L7 layer. The all
things are to match the real ability of backend. That means all the
configuration of L7 resources will be ignored or translate to LVS configuration
if the backend is LVS. For other load balancer engines which support UDP, such
as f5/nginx, we may also need to do this.

Combining the 2 load balancer engines for a simple reference implementation,
LVS would only support the L4 layer LB, and haproxy would provide the L7
LB functionality which is more specific and detailed. For other engines like
f5/nginx, Octavia can directly pass the UDP parameters to backend. This is
very good for the community environment. Then Octavia may support more powerful
and complex LoadBalancing solutions.

Data model impact
-----------------
There may not be any data model changes, this spec just allows a user to
input the ``udp`` protocol to create/update the ``Listener`` and ``Pool``
resources. So here, just extend the ``SUPPORTED_PROTOCOLS`` to add the value
``PROTOCOL_UDP``.

.. code-block:: python

    SUPPORTED_PROTOCOLS = (PROTOCOL_TCP, PROTOCOL_HTTPS, PROTOCOL_HTTP,
                           PROTOCOL_TERMINATED_HTTPS, PROTOCOL_PROXY,
                           PROTOCOL_UDP)

Also add a record into the table ``protocol`` for ``PROTOCOL_UDP``.

As LVS only operates in Layer 4, there are some conflicts with current
Octavia data models. There are some limitation below:

1. No L7 policies allowed.
2. For session persistence, this spec will intro ``persistence_timeout`` (sec)
   and ``persistence_granularity`` (subnet mask) [#foot11]_ in the virtual
   server configuration. The function will be based on the LVS. With no session
   persistence specified, LVS will be configured with a persistence_timeout
   of 0. There are two valid session persistence options for UDP (if session
   persistence is specified), ``SOURCE_IP`` and ``ONE_PACKET_SCHEDULING``.
3. Intro a 'UDP_CONNECT' type for UDP in ``healthmonitor``, for the simple,
   only check the UDP port is open by ``nc`` command. And for current API of
   ``healthmonitor``, we need to make clear the meaning of LVS with the current
   ``healthmonitor`` API like the mapping below

   +---------------------+--------------------------+-------------------------+
   | Option Mapping      |  Healthmonitor           |  Keepalived LVS         |
   | Healthmonitor->LVS  |  Description             |  Description            |
   +=====================+==========================+=========================+
   |                     | Set the time in seconds, | Delay timer for service |
   | delay -> delay_loop | between sending probes   | polling.                |
   |                     | to members.              |                         |
   +---------------------+--------------------------+-------------------------+
   | max_retires_down -> | Set the number of allowed| Number of retries       |
   | retry               | check failure before     | before fail.            |
   |                     | changing the operating   |                         |
   |                     | status of the member to  |                         |
   |                     | ERROR.                   |                         |
   +---------------------+--------------------------+-------------------------+
   | timeout ->          | Set the maximum time, in | delay before retry      |
   | delay_before_retry  | seconds, that a monitor  | (default 1 unless       |
   |                     | waits to connect before  | otherwise specified)    |
   |                     | it times out. This value |                         |
   |                     | must be less than the    |                         |
   |                     | delay value.             |                         |
   +---------------------+--------------------------+-------------------------+

4. For UDP load balancing, we can support the same algorithms at first. Such as
   SOURCE_IP(sh), ROUND_ROBIN(rr) and LEAST_CONNECTIONS(lc).

REST API impact
---------------

* Allow the ``protocol`` fields to accept ``udp``.
* Allow the ``healthmonitor.type`` field to accept UDP type values.
* Add some fields to ``session_persistence`` that are specific to UDP though
  ``SOURCE_IP`` type and a new type ``ONE_PACKET_SCHEDULING``.

Create/Update Listener Request::

    POST/PUT /v2.0/lbaas/listeners
    {
        "listener": {
            "admin_state_up": true,
            "connection_limit": 100,
            "description": "listener one",
            "loadbalancer_id": "a36c20d0-18e9-42ce-88fd-82a35977ee8c",
            "name": "listener1",
            "protocol": "UDP",
            "protocol_port": "18000"
        }
    }

.. note:: It is the same as the current relationships, where one ``listener``
          will have only one default ``pool`` for UDP. A ``loadbalancer`` can
          have multiple ``listeners`` for UDP loadbalancing on different ports.

Create/Update Pool Request

``SOURCE_IP`` type case::

    POST/PUT /v2.0/lbaas/pools

    {
        "pool": {
            "admin_state_up": true,
            "description": "simple pool",
            "lb_algorithm": "ROUND_ROBIN",
            "name": "my-pool",
            "protocol": "UDP",
            "session_persistence": {
                "type": "SOURCE_IP",
                "persistence_timeout": 60,
                "persistence_granularity": "255.255.0.0",
            }
            "listener_id": "39de4d56-d663-46e5-85a1-5b9d5fa17829",
        }
    }

``ONE_PACKET_SCHEDULING`` type case::

    POST/PUT /v2.0/lbaas/pools

    {
        "pool": {
            "admin_state_up": true,
            "description": "simple pool",
            "lb_algorithm": "ROUND_ROBIN",
            "name": "my-pool",
            "protocol": "UDP",
            "session_persistence": {
                "type": "ONE_PACKET_SCHEDULING"
            }
            "listener_id": "39de4d56-d663-46e5-85a1-5b9d5fa17829",
        }
    }

.. note:: The validation part for UDP will just allow to set the specific
          fields which associated with UDP. For example, user can not set the
          ``protocol`` with "udp" and ``insert_headers`` in the same request.

Create/Update Health Monitor Request::

    POST/PUT /v2.0/lbaas/healthmonitors

    {
        "healthmonitor": {
            "name": "Good health monitor"
            "admin_state_up": true,
            "pool_id": "c5e9e801-0473-463b-a017-90c8e5237bb3",
            "delay": 10,
            "max_retries": 4,
            "max_retries_down": 4,
            "timeout": 5,
            "type": "UDP_CONNECT"
        }
    }

.. note:: We don't allow to create a ``healthmonitor`` with any other L7
          parameters, like "http_method", "url_path" and "expected_code" if
          the associated ``pool`` support UDP. But for the positional option
          "max_retries", it's different from API description in keepalived/LVS,
          so the default value is the same as the value of "max_retires_down"
          if user specified. In general, "max_retires_down" should be
          overridden by "max_retries".

Security impact
---------------
The security should be affected by the UDP server, we need to add another
neutron security group rule to the existing security group to support UDP.
Security impact is minimal as the keepalived/LVS will be running in the tenant
traffic network namespace.

Notifications impact
--------------------
No expected change.

Other end user impact
---------------------
Users will be able to pass "UDP" to create/update Listener/Pool resources for
UDP load balancer.

Performance Impact
------------------
* If enabled driver is LVS, it will have a good performance for L4 load
  balancing, but lack the any functionality in L7.
* As this spec introduces LVS and Haproxy working together, if users update the
  ``Listener`` or ``Pool`` resources in a ``LoadBalancer`` instance frequently,
  the loadbalancer functionality may be delayed for a while as the refresh of
  UDP related LVS configuration.
* As we need to add keepalived monitoring process for each UDP listeners, it is
  necessary to consider RAM about amphora VM instances.

Other deployer impact
---------------------
No expected change.

Developer impact
----------------
No expected change.

Implementation
==============

Assignee(s)
-----------
zhaobo


Work Items
----------
* Add/extend startup script templates for keepalived processes, including
  configuration.
* Extend the ability of existing amphora agent and driver to generate and
  control LVS by ``keepalived`` in amphora instances.
* Extend the exist Octavia V2 API to access ``udp`` parameter in ``Listener``
  and ``pools`` resources.
* Extend the Loadbalancer/Listener flows to support udp loadbalancer in the
  particular topologies.
* Extend Octavia V2 API to accept UDP fields.
* Add the specified logic which involved into haproxy agent and the affected
  resource workflow in Octavia.
* Add API validation code to validate the fields of UDP cases.
* Add Unit Tests to Octavia.
* Add API functional tests.
* Add scenario tests into octavia tempest plugin.
* Update CLI and Octavia-dashboard to support UDP fields input.
* Documentation work.

Dependencies
============
None

Testing
=======
Unit tests, Functional tests, API tests and Scenario tests are necessary.

Documentation Impact
====================
The description of Octavia API reference will need to be updated.
The load balancing cookbook should be also updated.
Make it clear the difference of ``healthmonitor`` behaviors in UDP cases.

References
==========

.. [#foot1] https://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol
.. [#foot2] https://en.wikipedia.org/wiki/Internet_of_things
.. [#foot3] https://en.wikipedia.org/wiki/Constrained_Application_Protocol
.. [#foot4] https://en.wikipedia.org/wiki/Data_Distribution_Service
.. [#foot5] https://en.wikipedia.org/wiki/Thread_(network_protocol)
.. [#foot6] https://en.wikipedia.org/wiki/Reliable_User_Datagram_Protocol
.. [#foot7] https://de.wikipedia.org/wiki/Real-Time_Transport_Protocol
.. [#foot8] https://en.wikipedia.org/wiki/UDP-based_Data_Transfer_Protocol
.. [#foot9] http://www.linuxvirtualserver.org/
.. [#foot10] https://github.com/acassen/keepalived/blob/master/doc/keepalived.conf.SYNOPSIS#L559
.. [#foot11] http://www.linuxvirtualserver.org/docs/persistence.html
