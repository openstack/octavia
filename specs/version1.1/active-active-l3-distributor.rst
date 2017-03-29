..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Distributor for L3 Active-Active, N+1 Amphora Setup
===================================================
.. attention::
  Please review the active-active topology blueprint first (
  :doc:`../version0.9/active-active-topology` )

https://blueprints.launchpad.net/octavia/+spec/l3-active-active

Problem description
===================

This blueprint describes a *L3 active-active* distributor implementation to
support the Octavia *active-active-topology*. The *L3 active-active*
distributor will leverage the capabilities of a layer 3 Clos network fabric in
order to distribute traffic to an *Amphora Cluster* of 1 or more amphoras.
Specifically, the *L3 active-active* distributor design will leverage Equal
Cost Multipath Load Sharing (ECMP) with anycast routing to achieve traffic
distribution across the *Amphora Cluster*.  In this reference implementation,
the BGP routing protocol will be used to inject anycast routes into the L3
fabric.

In order to scale a single VIP address across multiple active amphoras it is
required to have a *distributor* to balance the traffic. By leveraging the
existing capabilities of a modern L3 network, we can use the network itself as
the *distributor*. This approach has several advantages, which include:

* Traffic will be routed via the best path to the destination amphora. There is
  no need to add an additional hop (*distributor*) between the network and the
  amphora.

* The *distributor* is not in the data path and simply becomes a function of
  the L3 network.

* The performance and scale of the *distributor* is the same as the L3 network.

* Native support for both IPv4 and IPv6, without customized logic for each
  address family.

.. _P2:

  **Note:** Items marked with [`P2`_] refer to lower priority features to be
  designed / implemented only after initial release.

Proposed change
===============

* Octavia shall implement the *L3 active-active* distributor through a
  pluggable driver.

* The distributor control plane function (*bgp speaker*) will run inside the
  amphora and leverage the existing amphora lifecycle manager.

* Each amphora will run a *bgp speaker* in the default namespace in order to
  announce the anycast VIP into the L3 fabric. BGP peering and announcements
  will occur over the lb-mgmt-net network. The anycast VIP will get advertised
  as a /32 or /128 route with a next-hop of the front-end IP assigned to the
  amphora instance. The front-end network IPs must be directly routable from
  the L3 fabric, such as in the provider networking model.

* Octavia shall implement the ability to specify an anycast VIP/subnet and
  front-end subnet (provider network) when creating a new load balancer. The
  amphora will have ports on three networks (anycast, front-end, management).
  The anycast VIP will get configured on the loopback interface inside the
  *amphora-haproxy* network namespace.

* The operator shall be able to define a *bgp peer profile*, which includes the
  required metadata for the amphora to establish a bgp peering session with
  the L3 fabric. The bgp peering information will be passed into the
  amphora-agent configuration file via config drive during boot. The amphora
  will use the bgp peering information to establish a BGP peer and announce its
  anycast VIP.

* [`P2`_] Add the option to allow the *bgp speaker* to run on a dedicated
  amphora instance that is not running the software load balancer (HAProxy). In
  this model a dedicated *bgp speaker* could advertise anycast VIPs for one or
  more amphoras. Each BGP speaker (peer) can only announce a single next-hop
  route for an anycast VIP. In order to perform ECMP load sharing, multiple
  dedicated amphoras running bgp speakers will be required, each of them would
  then announce a different next-hop address for the anycast VIP. Each next-hop
  address is the front-end (provider network) IP of an amphora instance running
  the software load balancer.

* [`P2`_] The *Amphora Cluster* will provide resilient flow handling in order
  to handle ECMP group flow remapping events and support amphora connection
  draining.

* [`P2`_] Support Floating IPs (FIPs). In order to support FIPs the existing
  Neutron *floatingips* API would need to be extended. This will be described
  in more detail in a separate spec in the Neutron project.

Architecture
------------

High-level Topology Description
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The below diagram shows the interaction between 2 .. n amphora instances from
each tenant and how they interact with the L3 network distributor.

::

                   Management                                        Front-End
  Internet         Network                                           Networks
  (World)                ║                                           (provider)
     ║                   ║            ┌─────────────────────────────┐    ║
     ║                   ║            │     Amphora of Tenant A     │    ║
  ┌──╨──────────┐        ║      ┌────┬┴──────────┬──────────────────┴┬───╨┐
  │             │        ╠══════╡MGMT│ns: default│ns: amphora-haproxy│f.e.│
  │             │        ║      │ IP ├-----------┼-------------------┤ IP │
  │             │        ║      └────┤    BGP    │    Anycast VIP    ├───╥┘
  │             │        ║           │   Speaker │    (loopback)     │   ║
  │             │        ║           └───────────┴──────────────╥────┘   ║
  │             │        ║                  |                   ║        ║
  │             │        ║                  |                   ║        ║
  │             │   Peering Session   1..*  |                   ║        ║
  │             │---------------------------+                   ║        ║
  │             │   {anycast VIP}/32 next-hop {f.e. IP}         ║        ║
  │             │        ║                                      ║        ║
  │             │        ║            ┌─────────────────────────╨───┐    ║
  │             │        ║            │     Amphora of Tenant B     │    ║
  │             │        ║      ┌────┬┴──────────┬──────────────────┴┬───╨┐
  │             ╞════════╬══════╡MGMT│ns: default│ns: amphora-haproxy│f.e.│
  │             │        ║      │ IP ├-----------┼-------------------┤ IP │
  │             │        ║      └────┤    BGP    │    Anycast VIP    ├───╥┘
  │             │        ║           │   Speaker │    (loopback)     │   ║
  │             │        ║           └───────────┴──────────────╥────┘   ║
  │ Distributor │        ║                  |                   ║        ║
  │ (L3 Network)│        ║                  |                   ║        ║
  │             │   Peering Session   1..*  |                   ║        ║
  │             │---------------------------+                   ║        ║
  │             │   {anycast VIP}/32 next-hop {f.e. IP}         ║        ║
  │             │        ║                                      ║        ║
  │             │        ║            ┌─────────────────────────╨───┐    ║
  │             │        ║            │     Amphora of Tenant C     │    ║
  │             │        ║      ┌────┬┴──────────┬──────────────────┴┬───╨┐
  │             │        ╚══════╡MGMT│ns: default│ns: amphora-haproxy│f.e.│
  │             │               │ IP ├-----------┼-------------------┤ IP │
  │             │               └────┤    BGP    │    Anycast VIP    ├────┘
  │             │                    │   Speaker │    (loopback)     │
  │             │                    └───────────┴──────────────╥────┘
  │             │                           |                   ║
  │             │                           |                   ║
  │             │   Peering Session   1..*  |                   ║
  │             │---------------------------+                   ║
  │             │   {anycast VIP}/32 next-hop {f.e. IP}         ║
  │             │                                               ║
  │             ╞═══════════════════════════════════════════════Anycast
  └─────────────┘                     1..*                      Network

* Whenever a new active-active amphora is instantiated it will create BGP
  peering session(s) over the lb-mgmt-net to the L3 fabric. The BGP peer will
  need to have a neighbor definition in order to allow the peering sessions
  from the amphoras. In order to ease configuration, a neighbor statement
  allowing peers from the entire lb-mgmt-net IP prefix range can be defined:
  ``neighbor 10.10.10.0/24``

* The BGP peer IP can either be a route reflector (RR) or any other network
  device that will redistribute routes learned from the amphora BGP speaker.
  In order to help scaling, it is possible to peer with the ToR switch based on
  the rack the amphora instance is provisioned in. The configuration can be
  simplified by creating an ``anycast loopback interface`` on each ToR switch,
  which will provide a consistent BGP peer IP regardless of which rack or
  hypervisor is hosting the amphora instance.

* Once a peering session is established between an amphora and the L3 fabric,
  the amphora will need to announce its anycast VIP with a next-hop address of
  its front-end network IP. The front-end network IP (provider) must be
  routable and reachable from the L3 network in order to be used.

* In order to leverage ECMP for distributing traffic across multiple amphoras,
  multiple equal-cost routes must be installed into the network for the anycast
  VIP. This requires the L3 network to have ``Multipath BGP`` enabled, so BGP
  installs multiple paths and does not select a single best path.

* After the amphoras in a cluster are initialized there will be an ECMP group
  with multiple equal-cost routes for the anycast VIP. The data flow for
  traffic is highlighted below:

    1. Traffic will ingress into the L3 network fabric with a destination IP
       address of the anycast VIP.

    2. If this is a new flow, the flow will get hashed to one of the next-hop
       addresses in the ECMP group.

    3. The packet will get sent to the front-end IP address of the amphora
       instance that was selected from the above step.

    4. The amphora will accept the packet and send it to the back-end server
       over the front-end network or a directly attached back-end (tenant)
       network attached to the amphora.

    5. The amphora will receive the response from the back-end server and
       forward it on to the next-hop gateway of front-end (provider) network
       using the anycast VIP as the source IP address.

    6. All subsequent packets belonging to the same flow will get routed
       through the same path.

* Adding or removing members to a L3 active-active amphora cluster will result
  in flow remapping, as different paths will be selected due to rehashing. It
  is recommended to enable the ``resilient hashing`` feature on ECMP groups in
  order to minimize flow remapping.

Distributor (BGP Speaker) Lifecycle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The below diagram shows the interaction between an amphora instance that is
serving as a distributor and the L3 network. In this example we are peering
with the ToR switch in order to disseminate anycast VIP routes into the
L3 network.

::

  +------------------------------------------------+
  |       Initialize Distributor on Amphora        |
  +------------------------------------------------+
  |                                                |
  | +---------------+            +---------------+ |
  | |1              |            |4              | |
  | |    Amphora    |            |   Ready to    | |
  | |    (boot)     |            |   announce    | |
  | |               |            |    VIP(s)     | |
  | +-------+-------+            +-------+-------+ |
  |         |                            ^         |
  |         |                            |         |
  |         |                            |         |
  |         |                            |         |
  |         |                            |         |
  |         v                            |         |
  | +-------+-------+            +-------+-------+ |
  | |2              |            |3  Establish   | |
  | |  Read Config  |            | BGP connection| |
  | |     Drive     +----------->+    to ToR(s)  | |
  | |  (BGP Config) |            | (BGP Speaker) | |
  | +---------------+            +---------------+ |
  |                                                |
  +------------------------------------------------+

  +------------------------------------------------+
  | Register AMP to Distributor or Listener Start  |
  +------------------------------------------------+
  |                                                |
  | +---------------+            +---------------+ |
  | |5              |            |8              | |
  | |    Amphora    |            |    Amphora    | |
  | |  BGP Speaker  |            | (Receives VIP | |
  | |(Announce VIP) |            |   Traffic)    | |
  | +-------+-------+            +-------+-------+ |
  |         |                            ^         |
  |         |                            |         |
  |         |BGP Peering                 |         |
  |         |Session(s)                  |         |
  |         |                            |         |
  |         v                            |         |
  | +-------+-------+            +-------+-------+ |
  | |6              |            |7              | |
  | |    ToR(s)     |            |   L3 Fabric   | |
  | |(Injects Route +----------->+ Accepts Route | |
  | | into Fabric)  |            |    (ECMP)     | |
  | +---------------+            +---------------+ |
  |                                                |
  +------------------------------------------------+

  +------------------------------------------------+
  | Unregister AMP to Distributor or Listener Stop |
  +------------------------------------------------+
  |                                                |
  | +---------------+            +---------------+ |
  | |9              |            |12             | |
  | |    Amphora    |            |    Amphora    | |
  | |  BGP Speaker  |            |(No longer sent| |
  | |(Withdraw VIP) |            | VIP traffic)  | |
  | +-------+-------+            +-------+-------+ |
  |         |                            ^         |
  |         |                            |         |
  |         |BGP Peering                 |         |
  |         |Session(s)                  |         |
  |         |                            |         |
  |         v                            |         |
  | +-------+-------+            +-------+-------+ |
  | |10             |            |11             | |
  | |    ToR(s)     |            |   L3 Fabric   | |
  | |(Removes Route +----------->+ Removes Route | |
  | | from Fabric)  |            |    (ECMP)     | |
  | +---------------+            +---------------+ |
  |                                                |
  +------------------------------------------------+

1. The amphora gets created and is booted. In this example, the amphora will
   perform both the load balancing (HAProxy) and L3 Distributor function
   (BGP Speaker).

2. The amphora will read in the BGP configuration information from the config
   drive and configure the BGP Speaker to peer with the ToR switch.

3. The BGP Speaker process will start and establish a BGP peering session with
   the ToR switch.

4. Once the BGP peering session is active, the amphora is ready to advertise
   its anycast VIP into the network with a next-hop of its front-end IP
   address.

5. The BGP speaker will communicate using the BGP protocol and send a BGP
   "announce" message to the ToR switch in order to announce a VIP route. If
   the amphora is serving as both a load balancer and distributor the
   announcement will happen on listener start. Otherwise the announce will
   happen on a register amphora request to the distributor.

6. The ToR switch will learn this new route and advertise it into the L3
   fabric. At this point the L3 fabric will know of the new VIP route and how
   to reach it (via the ToR that just announced it).

7. The L3 fabric will create an ECMP group if it has received multiple route
   advertisements for the same anycast VIP. This will result in a single VIP
   address with multiple next-hop addresses.

8. Once the route is accepted by the L3 fabric, traffic will get distributed
   to the recently registered amphora (HAProxy).

9. The BGP speaker will communicate using the BGP protocol and send a BGP
   "withdraw" message to the ToR switch in order to withdraw a VIP route. If
   the amphora is serving as both a load balancer and distributor the
   withdrawal will happen on listener stop. Otherwise the withdraw will happen
   on an unregister amphora request to the distributor.

10. The ToR switch will tell the L3 fabric over BGP that the anycast VIP route
    for the amphora being unregistered is no longer valid.

11. The L3 fabric will remove the VIP address with the next-hop address to the
    amphora (HAProxy) being unregistered. It will keep all other existing VIP
    routes to other amphora (HAProxy) instances until they are explicitly
    unregistered.

12. Once the route is removed the amphora (HAProxy) will no longer receive any
    traffic for the VIP.

Alternatives
------------
TBD

Data model impact
-----------------
Add the following columns to the existing ``vip`` table:

* distributor_id ``(String(36) , nullable=True)``
    ID of the distributor responsible for distributing traffic for the
    corresponding VIP.

Add table ``distributor`` with the following columns:

* id ``(String(36) , nullable=False)``
    ID of Distributor instance.

* distributor_type ``(String(36) , nullable=False)``
    Type of distributor ``L3_BGP``.

* status ``(String(36) , nullable=True)``
    Provisioning status.

Update existing table ``amphora``. An amphora can now serve as a distributor,
lb, or both. The vrrp_* tables will be renamed to frontend_* in order to make
the purpose of this interface more apparent and to better represent other use
cases besides active/standy.

* load_balancer_id ``(String(36) , nullable=True)``
    This will be set to null if this amphora is a dedicated distributor and
    should not run HAProxy.

* service_type ``(String(36) , nullable=True)``
    New field added to the amphora table in order to describe the type of
    amphora. This field is used to describe the function (service) the amphora
    provides. For example, if this is a dedicated distributor the service type
    would be set to "distributor".

* frontend_ip ``(String(64) , nullable=True)``
    New name for former vrrp_ip field. This is the primary IP address inside
    the amphora-haproxy namespace used for L3 communication to back-end
    members.

* frontend_subnet_id ``(String(36) , nullable=True)``
    New field added to the amphora table, which is the neutron subnet id of
    the front-end network connected to the amphora.

* frontend_port_id ``(String(36) , nullable=True)``
    New name for former vrrp_port_id field. This represents the neutron port ID
    of a port attached to the front-end network. It should no longer be assumed
    that the front-end subnet is the same as the VIP subnet.

* frontend_interface ``(String(16) , nullable=True)``
    New name for former vrrp_interface field.

* frontend_id ``(Integer , nullable=True)``
    New name for former vrrp_id field.

* frontend_priority ``(Integer , nullable=True)``
    New name for former vrrp_priority field.

Use existing table ``amphora_health`` with the following columns:

* amphora_id ``(String(36) , nullable=False)``
    ID of amphora instance running lb and/or implementing distributor function.

* last_update ``(DateTime , nullable=False)``
    Last time amphora heartbeat was received by a health monitor.

* busy ``(Boolean , nullable=False)``
    Field indicating a create / delete or other action is being conducted on
    the amphora instance (ie. to prevent a race condition when multiple health
    managers are in use).

Add table ``amphora_registration`` with the below columns. This table
determines the role of the amphora. The amphora can be dedicated as a
distributor, load balancer, or perform a combined role of load balancing and
distributor. A distributor amphora can be registered to multiple load
balancers.

* amphora_id ``(String(36) , nullable=False)``
    ID of Amphora instance.

* load_balancer_id ``(String(36) , nullable=False)``
    ID of load balancer.

* distributor_id ``(String(36) , nullable=True)``
    ID of Distributor instance.

Add table ``distributor_l3_bgp_speaker`` with the following columns:

* id ``(String(36) , nullable=False)``
    ID of the BGP Speaker.

* ip_version ``(Integer , nullable=False)``
    Protocol version of the BGP speaker. IP version ``4`` or ``6``.

* local_as ``(Integer , nullable=False)``
    Local AS number for the BGP speaker.

Add table ``distributor_l3_bgp_peer`` with the following columns:

* id ``(String(36) , nullable=False)``
    ID of the BGP peer.

* peer_ip ``(String(64) , nullable=False)``
    The IP address of the BGP neighbor.

* remote_as ``(Integer , nullable=False)``
    Remote AS of the BGP peer.

* auth_type ``(String(16) , nullable=True)``
    Authentication type, such as ``md5``. An additional parameter will need to
    be set in the octavia configuration file by the admin to set the md5
    authentication password that will be used with the md5 auth type.

* ttl_hops ``(Integer , nullable=True)``
    Number of hops between speaker and peer for ttl security ``1-254``.

* hold_time ``(Integer , nullable=True)``
    Amount of time in seconds that can elapse between messages from peer.

* keepalive_interval ``(Integer , nullable=True)``
    How often to send keep alive packets in seconds.

Add table ``distributor_l3_bgp_peer_registration`` with the following columns:

* distributor_l3_bgp_speaker_id ``(String(36) , nullable=False)``
    ID of the BGP Speaker.

* distributor_l3_bgp_peer_id ``(String(36) , nullable=False)``
    ID of the BGP peer.

Add table ``distributor_l3_amphora_bgp_speaker_registration`` with the
following columns:

* distributor_l3_bgp_speaker_id ``(String(36) , nullable=False)``
    ID of the BGP Speaker.

* amphora_id ``(String(36) , nullable=False)``
    ID of amphora instance that the BGP speaker will run on.

Add table ``distributor_l3_amphora_vip_registration`` with the following
columns:

* amphora_id ``(String(36) , nullable=False)``
    ID of the distributor amphora instance.

* load_balancer_id ``(String(36) , nullable=False)``
    The ID of the load balancer. This will be used to get the VIP IP address.

* nexthop_ip ``(String(64) , nullable=False)``
    The amphora front-end network IP used to handle VIP traffic. This is the
    next-hop address that will be advertised for the VIP. This does not have to
    be an IP address of an amphora, as it could be external such as for UDP
    load balancing.

* distributor_l3_bgp_peer_id ``(String(36) , nullable=True)``
    The BGP peer we will announce the anycast VIP to. If not specified, we will
    announce over all peers.

REST API impact
---------------

* Octavia API -- Allow the user to specify a separate VIP/subnet and front-end
  subnet (provider network) when creating a new load balancer. Currently the
  user can only specify the VIP subnet, which results in both the VIP and
  front-end network being on the same subnet.

* Extended Amphora API -- The L3 BGP distributor driver will call the extended
  amphora API in order to implement the control plane (BGP) and advertise new
  anycast VIP routes into the network.

The below extended amphora API calls will be implemented for amphoras running
as a dedicated distributor:

1. ``Register Amphora``

   This call will result in the BGP speaker announcing the anycast VIP into the
   L3 network with a next-hop of the front-end IP of the amphora being
   registered. Prior to this call, the load balancing amphora will have to
   configure the anycast VIP on the loopback interface inside the
   amphora-haproxy namespace.

   - amphora_id
       ID of the amphora running the load balancer to register.

   - vip_ip
       The VIP IP address.

   - nexthop_ip
       The amphora's front-end network IP address used to handle anycast VIP
       traffic.

   - peer_id
       ID of the peer that will be used to announce the anycast VIP. If not
       specified, VIP will be announced across all peers.

2. ``Unregister Amphora``

   The BGP speaker will withdraw the anycast VIP route for the specified
   amphora from the L3 network. After the route is withdrawn, the anycast VIP
   IP will be removed from the loopback interface on the load balancing
   amphora.

   - amphora_id
       ID of the amphora running the load balancer to unregister.

   - vip_ip
       The VIP IP address.

   - nexthop_ip
       The amphora's front-end network IP Address used to handle anycast VIP
       traffic.

   - peer_id
       ID of the peer that will be used to withdraw the anycast VIP. If not
       specified, route will be withdrawn from all peers.

3. ``List Amphora``

   Will return a list of all amphora IDs and their anycast VIP routes currently
   being advertised by the BGP speaker.

4. [`P2`_] ``Drain Amphora``

   All new flows will get redirected to other members of the cluster and
   existing flows will be drained. Once the active flows have been drained, the
   BGP speaker will withdraw the anycast VIP route from the L3 network and
   unconfigure the VIP from the lo interface.

5. [`P2`_] ``Register VIP``

   This call will be used for registering anycast routes for non-amphora
   endpoints, such as for UDP load balancing.

   - vip_ip
       The VIP IP address.

   - nexthop_ip
       The nexthop network IP Address used to handle anycast VIP traffic.

   - peer_id
       ID of the peer that will be used to announce the anycast VIP. If not
       specified, route will be announced from all peers.

6. [`P2`_] ``Unregister VIP``

   This call will be used for unregistering anycast routes for non-amphora
   endpoints, such as for UDP load balancing.

   - vip_ip
       The VIP IP address.

   - nexthop_ip
       The nexthop network IP Address used to handle anycast VIP traffic.

   - peer_id
       ID of the peer that will be used to withdraw the anycast VIP. If not
       specified, route will be withdrawn from all peers.

6. [`P2`_] ``List VIP``

   Will return a list of all non-amphora anycast VIP routes currently being
   advertised by the BGP speaker.

Security impact
---------------
The distributor inherently supports multi-tenancy, as it is simply providing
traffic distribution across multiple amphoras. Network isolation on a per
tenant basis is handled by the amphoras themselves, as they service only a
single tenant. Further isolation can be provided by defining separate anycast
network(s) on a per tenant basis. Firewall or ACL policies can then be built
around these prefixes.

To further enhance BGP security, route-maps, prefix-lists, and communities to
control what routes are allowed to be advertised in the L3 network from a
particular BGP peer can be used. MD5 password and GTSM can provide additional
security to limit unauthorized BGP peers to the L3 network.

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

Work Items
----------

Dependencies
============

Testing
=======

* Unit tests with tox.
* Function tests with tox.

Documentation Impact
====================
The API-Ref documentation will need to be updated for load balancer create.
An additional optional parameter frontend_network_id will be added. If set,
this parameter will result in the primary interface inside the amphora-haproxy
namespace getting created on the specified network. Default behavior is to
provision this interface on the VIP subnet.

References
==========
* `Active-Active Topology
  <https://blueprints.launchpad.net/octavia/+spec/active-active-topology/>`_
