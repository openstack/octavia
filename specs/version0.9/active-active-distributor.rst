..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================================================
Distributor for Active-Active, N+1 Amphorae Setup
=================================================

.. attention::
  Please review the active-active topology blueprint first (
  :doc:`active-active-topology` )

https://blueprints.launchpad.net/octavia/+spec/active-active-topology

Problem description
===================

This blueprint describes how Octavia implements a *Distributor* to support the
*active-active* loadbalancer (LB) solution, as described in the blueprint
linked above. It presents the high-level Distributor design and suggests
high-level code changes to the current code base to realize this design.

In a nutshell, in an *active-active* topology, an *Amphora Cluster* of two
or more active Amphorae collectively provide the loadbalancing service.
It is designed as a 2-step loadbalancing process; first, a lightweight
*distribution* of VIP traffic over an Amphora Cluster; then, full-featured
loadbalancing of traffic over the back-end members. Since a single
loadbalancing service, which is addressable by a single VIP address, is
served by several Amphorae at the same time, there is a need to distribute
incoming requests among these Amphorae -- that is the role of the
*Distributor*.

This blueprint uses terminology defined in the Octavia glossary when available,
and defines new terms to describe new components and features as necessary.

.. _P2:

  **Note:** Items marked with [`P2`_] refer to lower priority features to be
  designed / implemented only after initial release.


Proposed change
===============

* Octavia shall implement a Distributor to support the active-active
  topology.

* The operator should be able to select and configure the Distributor
  (e.g., through an Octavia configuration file or [`P2`_] through a flavor
  framework).

* Octavia shall support a pluggable design for the Distributor, allowing
  different implementations. In particular, the Distributor shall be
  abstracted through a *driver*, similarly to the current support of
  Amphora implementations.

* Octavia shall support different provisioning types for the Distributor;
  including VM-based (the default, similar to current Amphorae),
  [`P2`_] container-based, and [`P2`_] external (vendor-specific) hardware.

* The operator shall be able to configure the distribution policies,
  including affinity and availability (see below for details).


Architecture
------------

High-level Topology Description
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The following diagram illustrates the Distributor's role in an active-active
  topology:

::


                          Front-End                               Back-End
  Internet                Networks                                Networks
  (world)                 (tenants)                               (tenants)
     ║                A       B       C                             A B C
  ┌──╨───┐floating IP ║       ║       ║  ┌────────┬──────────┬────┐ ║ ║ ║
  │      ├─ to VIP ──►╢◄──────║───────║──┤f.e. IPs│ Amphorae │b.e.├►╜ ║ ║
  │      │   LB A     ║       ║       ║  └──┬─────┤    of    │ IPs│   ║ ║
  │      │            ║       ║       ║     │VIP A│ Tenant A ├────┘   ║ ║
  │  GW  │            ║       ║       ║     └─────┴──────────┘        ║ ║
  │Router│floating IP ║       ║       ║  ┌────────┬──────────┬────┐   ║ ║
  │      ├─ to VIP ───║──────►╟◄──────║──┤f.e. IPs│ Amphorae │b.e.├──►╜ ║
  │      │   LB B     ║       ║       ║  └──┬─────┤    of    │ IPs│     ║
  │      │            ║       ║       ║     │VIP B│ Tenant B ├────┘     ║
  │      │            ║       ║       ║     └─────┴──────────┘          ║
  │      │floating IP ║       ║       ║  ┌────────┬──────────┬────┐     ║
  │      ├─ to VIP ───║───────║──────►╢◄─┤f.e. IPs│ Amphorae │b.e.├────►╜
  └──────┘   LB C     ║       ║       ║  └──┬─────┤    of    │ IPs│
                      ║       ║       ║     │VIP C│ Tenant C ├────┘
                 arp─►╢  arp─►╢  arp─►╢     └─────┴──────────┘
               ┌─┴─┐  ║┌─┴─┐  ║┌─┴─┐  ║
               │VIP│┌►╜│VIP│┌►╜│VIP│┌►╜
               ├───┴┴┐ ├───┴┴┐ ├───┴┴┐
               │IP A │ │IP B │ │IP C │
              ┌┴─────┴─┴─────┴─┴─────┴┐
              │                       │
              │      Distributor      │
              │     (multi-tenant)    │
              └───────────────────────┘


* In the above diagram, several tenants (A, B, C, ...) share the
  Distributor, yet the Amphorae, and the front- and back-end (tenant)
  networks are not shared between tenants. (See also "Distributor Sharing"
  below.) Note that in the initial code implementing the distributor, the
  distributor will not be shared between tenants, until tests verifying the
  security of a shared distributor can be implemented.

* The Distributor acts as a (one-legged) router, listening on each
  load balancer's VIP and forwarding to one of its Amphorae.

* Each load balancer's VIP is advertised and answered by the Distributor.
  An ``arp`` request for any of the VIP addresses is answered by the
  Distributor, hence any traffic sent for each VIP is received by the
  Distributor (and forwarded to an appropriate Amphora).

* ARP is disabled on all the Amphorae for the VIP interface.

* The Distributor distributes the traffic of each VIP to an Amphora in the
  corresponding load balancer Cluster.

* An example of high-level data flow:

  1. Internet clients access a tenant service through an externally visible
     floating-IP (IPv4 or IPv6).

  2. The GW router maps the floating IP into a loadbalancer's internal VIP on
     the tenant's front-end network.

  3. (1st packet to VIP only) the GW send an ``arp`` request on VIP
     (tenant front-end) network. The Distributor answers the ``arp`` request
     with its own MAC address on this network (all the Amphorae on the network
     can serve the VIP, but do not answer the ``arp``).

  4. The GW router forwards the client request to the Distributor.

  5. The Distributor forwards the packet to one of the Amphorae on the
     tenant's front-end network (distributed according to some policy,
     as described below), without changing the destination IP (i.e., still
     using the VIP).

  6. The Amphora accepts the packet and continues the flow on the tenant's
     back-end network as for other Octavia loadbalancer topologies (non
     active-active).

  7. The outgoing response packets from the Amphora are forwarded directly
     to the GW router (that is, it does not pass through the Distributor).

Affinity of Flows to Amphorae
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Affinity is required to make sure related packets are forwarded to the
  same Amphora. At minimum, since TCP connections are terminated at the
  Amphora, all packets that belong to the same flow must be sent to the
  same Amphora. Enhanced affinity levels can be used to make sure that flows
  with similar attributes are always sent to the same Amphora; this may be
  desired to achieve better performance (see discussion below).

- [`P2`_] The Distributor shall support different modes of client-to-Amphora
  affinity. The operator should be able to select and configure the desired
  affinity level.

- Since the Distributor is L3 and the "heavy lifting" is expected to be
  done by the Amphorae, this specification proposes implementing two
  practical affinity alternatives. Other affinity alternatives may be
  implemented at a later time.

  *Source IP and source port*
    In this mode, the Distributor must always send packets from the same
    combination of Source IP and Source port to the same Amphora. Since
    the Target IP and Target Port are fixed per Listener, this mode implies
    that all packets from the same TCP flow are sent to the same Amphora.
    This is the minimal affinity mode, as without it TCP connections will
    break.

    *Note*: related flows (e.g., parallel client calls from the same HTML
    page) will typically be distributed to different Amphorae; however,
    these should still be routed to the same back-end. This could be
    guaranteed by using cookies and/or by synchronizing the stick-tables.
    Also, the Amphorae in the Cluster could be configured to use the same
    hashing parameters (avoid any random seed) to ensure all make similar
    decisions.

  *Source IP* (default)
    In this mode, the Distributor must always send packets from the same
    source IP to the same Amphora, regardless of port. This mode allows TLS
    session reuse (e.g., through session ids), where an abbreviated
    handshake can be used to improve latency and computation time.

    The main disadvantage of sending all traffic from the same source IP to
    the same Amphora is that it might lead to poor load distribution for
    large workloads that have the same source IP (e.g., workload behind a
    single nat or proxy).

    **Note on TLS implications**:
      In some (typical) TLS sessions, the additional load incurred for each new
      session is significantly larger than the load incurred for each new
      request or connection on the same session; namely, the total load on each
      Amphora will be more affected by the number of different source IPs it
      serves than by the number of connections. Moreover, since the total load
      on the Cluster incurred by all the connections depends on the level of
      session reuse, spreading a single source IP over multiple Amphorae
      *increases* the overall load on the Cluster. Thus, a Distributor that
      uniformly spreads traffic without affinity per source IP (e.g., uses
      per-flow affinity only) might cause an increase in overall load on the
      Cluster that is proportional to the number of Amphorae. For example, in a
      scale-out scenario (where a new Amphora is spawned to share the total
      load), moving some flows to the new Amphora might increase the overall
      Cluster load, negating the benefit of scaling-out.

      Session reuse helps with the certificate exchange phase. Improvements
      in performance with the certificate exchange depend on the type of keys
      used, and is greatest with RSA. Session reuse may be less important with
      other schemes; shared TLS session tickets are another mechanism that may
      circumvent the problem; also, upcoming versions of HA-Proxy may be able
      to obviate this problem by synchronizing TLS state between Amphorae
      (similar to stick-table protocol).

- Per the agreement at the Mitaka mid-cycle, the default affinity shall be
  based on source-IP only and a consistent hashing function (see below)
  shall be used to distribute flows in a predictable manner; however,
  abstraction will be used to allow other implementations at a later time.

Forwarding with OVS and OpenFlow Rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* The reference implementation of the Distributor shall use OVS for
  forwarding and configure the Distributor through OpenFlow rules.

  - OpenFlow rules can be implemented by a software switch (e.g., OVS) that
    can run on a VM. Thus, can be created and managed by Octavia similarly
    to creation and management of Amphora VMs.

  - OpenFlow rules are supported by several HW switches, so the same
    control plane can be used for both SW and HW implementations.

* Outline of Rules

  - A ``group`` with the ``select`` method is used to distribute IP traffic
    over multiple Amphorae. There is one ``bucket`` per Amphora -- adding
    an Amphora adds a new ``bucket`` and deleting and Amphora removes the
    corresponding ``bucket``.

  - The ``select`` method supports (OpenFlow v1.5) hashed-based selection
    of the ``bucket``. The hash can be set up to use different fields,
    including by source IP only (default) and by source IP and source port.

  - All buckets route traffic back on the in-port (i.e., no forwarding
    between ports). This ensures that the same front-end network is used
    (i.e., the Distributor does not route between front-end networks;
    therefore, does not mix traffic of different tenants).

  - The ``bucket`` actions do a re-write of the outgoing packets. It
    supports re-write of the destination MAC to that of the specific
    Amphora and re-write of the source MAC to that of the Distributor
    interface (together these MAC re-writes provide L3 routing functionality).

    *Note:* alternative re-write rules can be used to support other forwarding
    mechanisms.

  - OpenFlow rules are also used to answer ``arp`` requests on the VIP.
    ``arp`` requests for each VIP are captured, re-written as ``arp``
    replies with the MAC address of the particular front-end interface and
    sent back on the in-port. Again, there is no routing between interfaces.

* Handling Amphora failure

  - Initial implementation will assume a fixed size for each cluster (no
    elasticity). The hashing will be "consistent" by virtue of never
    changing the number of ``buckets``. If the cluster size is changed on
    the fly (there should not be an API to do so) then there are no
    guarantees on shuffling.

  - If an Amphora fails then remapping cannot be avoided -- all flows of
    the failed Amphora must be remapped to a different one. Rather than
    mapping these flows to other active Amphorae in the cluster, the reference
    implementation will map all flows to the cluster's *standby* Amphora (i.e.
    the "+1" Amphora in this "N+1" cluster). This ensures that the cluster
    size does not change. The only change in the OpenFlow rules would be to
    replace the MAC of the failed Amphora with that of the standby Amphora.

  - This implementation is very similar to Active-Standby fail-over. There
    will be a standby Amphora that can serve traffic in case of failure.
    The differences from Active-Standby is that a single Amphora acts as a
    standby for multiple ones; fail-over re-routing is handled through the
    Distributor (rather than by VRRP); and a whole cluster of Amphorae is
    active concurrently, to enable support of large workloads.

  - Health Manager will trigger re-creation of a failed Amphora. Once the
    Amphora is ready it becomes the new *standby* (no changes to OpenFlow
    rules).

  - [`P2`_] Handle concurrent failure of more than a single Amphora

* Handling Distributor failover

  - To handle the event of a Distributor failover caused by a catastrophic
    failure of a Distributor, and in order to preserve the client to Amphora
    affinity when the Distributor is replaced, the Amphora registration process
    with the Distributor should preserve positional information. This should
    ensure that when a new Distributor is created, Amphorae will be assigned to
    the same buckets to which they were previously assigned.

  - In the reference implementation, we propose making the Distributor API
    return the complete list of Amphorae MAC addresses with positional
    information each time an Amphora is registered or unregistered.

Specific proposed changes
-------------------------

**Note:** These are changes on top of the changes described in the
"Active-Active, N+1 Amphorae Setup" blueprint, (see
https://blueprints.launchpad.net/octavia/+spec/active-active-topology)

* Create flow for the creation of an Amphora cluster with N active Amphora
  and one extra standby Amphora. Set-up the Amphora roles accordingly.

* Support the creation, connection, and configuration of the various
  networks and interfaces as described in `high-level topology` diagram.
  The Distributor shall have a separate interface for each loadbalancer and
  shall not allow any routing between different ports. In particular, when
  a loadbalancer is created the Distributor should:

  - Attach the Distributor to the loadbalancer's front-end network by
    adding a VIP port to the Distributor (the LB VIP Neutron port).

  - Configure OpenFlow rules: create a group with the desired cluster size
    and with the given Amphora MACs; create rules to answer ``arp``
    requests for the VIP address.

  **Notes:**
    [`P2`_] It is desirable that the Distributor be considered as a router by
    Neutron (to handle port security, network forwarding without ``arp``
    spoofing, etc.). This may require changes to Neutron and may also mean
    that Octavia will be a privileged user of Neutron.

    Distributor needs to support IPv6 NDP

    [`P2`_] If the Distributor is implemented as a container then hot-plugging
    a port for each VIP might not be possible.

    If DVR is used then routing rules must be used to forward external
    traffic to the Distributor rather than rely on ``arp``. In particular,
    DVR messes-up ``noarp`` settings.

* Support Amphora failure recovery

  - Modify the HM and failure recovery flows to add tasks to notify the ACM
    when ACTIVE-ACTIVE topology is in use. If an active Amphora fails then
    it needs to be decommissioned on the Distributor and replaced with
    the standby.

  - Failed Amphorae should be recreated as a standby (in the new
    IN_CLUSTER_STANDBY role). The standby Amphora should also be monitored and
    recovered on failure.

* Distributor driver and Distributor image

  - The Distributor should be supported similarly to an amphora; namely, have
    its own abstract driver.

  - Distributor image (for reference implementation) should include OVS
    with a recent version (>1.5) that supports hash-based bucket selection.
    As is done for Amphorae, Distributor image should be installed with
    public keys to allow secure configuration by the Octavia controller.

  - Reference implementation shall spawn a new Distributor VM as needed. It
    shall monitor its health and handle recovery using heartbeats sent to the
    health monitor in a similar fashion to how this is done presently with
    Amphorae. [`P2`_] Spawn a new Distributor if the number VIPs exceeds a
    given limit (to limit the number of Neutron ports attached to one
    Distributor).  [`P2`_] Add configuration options and/or Operator API to
    allow operator to request a dedicated Distributor for a VIP (or per
    tenant).

* Define a REST API for Distributor configuration (no SSH API).
  See below for details.

* Create data-model for Distributor.

Alternatives
------------

TBD

Data model impact
-----------------

Add table ``distributor`` with the following columns:

* id  ``(sa.String(36) , nullable=False)``
    ID of Distributor instance.

* compute_id ``(sa.String(36), nullable=True)``
    ID of compute node running the Distributor.

* lb_network_ip ``(sa.String(64), nullable=True)``
    IP of Distributor on management network.

* status ``(sa.String(36), nullable=True)``
    Provisioning status

* vip_port_ids (list of ``sa.String(36)``)
    List of Neutron port IDs.
    New VIFs may be plugged into the Distributor when a new LB is created. We
    may need to store the Neutron port IDs in order to support
    fail-over from one Distributor instance to another.

Add table ``distributor_health`` with the following columns:

* distributor_id  ``(sa.String(36) , nullable=False)``
    ID of Distributor instance.

* last_update ``(sa.DateTime, nullable=False)``
    Last time distributor heartbeat was received by a health monitor.

* busy ``(sa.Boolean, nullable=False)``
    Field indicating a create / delete or other action is being conducted on
    the distributor instance (ie. to prevent a race condition when multiple
    health managers are in use).

Add table ``amphora_registration`` with the following columns. This describes
which Amphorae are registered with which Distributors and in which order:

* lb_id  ``(sa.String(36) , nullable=False)``
    ID of load balancer.

* distributor_id  ``(sa.String(36) , nullable=False)``
    ID of Distributor instance.

* amphora_id  ``(sa.String(36) , nullable=False)``
    ID of Amphora instance.

* position ``(sa.Integer, nullable=True)``
    Order in which Amphorae are registered with the Distributor.

REST API impact
---------------
Distributor will be running its own rest API server. This API will be secured
using two-way SSL authentication, and use certificate rotation in the same
way this is done with Amphorae today.

Following API calls will be addressed.

1. Post VIP Plug

   Adding a VIP network interface to the Distributor involves tasks which run
   outside the Distributor itself. Once these are complete, the Distributor
   must be configured to use the new interface. This is a REST call, similar
   to what is currently done for Amphorae when connecting to a new member
   network.

   `lb_id`
     An identifier for the particular loadbalancer/VIP. Used for subsequent
     register/unregister of Amphorae.

   `vip_address`
     The IP of the VIP (for which IP to answer ``arp`` requests)

   `subnet_cidr`
     Netmask for the VIP's subnet.

   `gateway`
     Gateway outbound packets from the VIP ip address should use.

   `mac_address`
     MAC address of the new interface corresponding to the VIP.

   `vrrp_ip`
     In the case of HA Distributor, this contains the IP address that will
     be used in setting up the allowed address pairs relationship. (See
     Amphora VIP plugging under the ACTIVE-STANDBY topology for an example
     of how this is used.)

   `host_routes`
     List of routes that should be added when the VIP is plugged.

   `alg_extras`
     Extra arguments related to the algorithm that will be used to distribute
     requests to Amphorae part of this load balancer configuration. This
     consists of an algorithm name and affinity type. In the initial release
     of ACTIVE-ACTIVE, the only valid algorithm will be *hash*, and the
     affinity type may be ``Source_IP`` or [`P2`_] ``Source_IP_AND_port``.

2. Pre VIP unplug

   Removing a VIP network interface will involve several tasks on the
   Distributor to gracefully roll-back OVS configuration and other details
   that were set-up when the VIP was plugged in.

   `lb_id`
     ID of the VIP's loadbalancer that will be unplugged.

3. Register Amphorae

   This adds Amphorae to the configuration for a given load balancer. The
   Distributor should respond with a new list of all Amphorae registered with
   the Distributor with positional information.

   `lb_id`
     ID of the loadbalancer with which the Amphora will be registered

   `amphorae`
     List of Amphorae MAC addresses and (optional) position argument in which
     they should be registered.

4. Unregister Amphorae

   This removes Amphorae from the configuration for a given load balancer. The
   Distributor should respond with a new list of all Amphorae registered with
   the Distributor with positional information.

   `lb_id`
     ID of the loadbalancer with which the Amphora will be registered

   `amphorae`
     List of Amphorae MAC addresses that should be unregistered with the
     Distributor.

Security impact
---------------

The Distributor is designed to be multi-tenant by default. (Note that the first
reference implementation will not be multi-tenant until tests can be developed
to verify the security of a multi-tenant reference distributor.) Although each
tenant has its own front-end network, the Distributor is connected to all,
which might allow leaks between these networks. The rationale is two fold:
First, the Distributor should be considered as a trusted infrastructure
component. Second, all traffic is external traffic before it reaches the
Amphora. Note that the GW router has exactly the same attributes; in other
words, logically, we can consider the Distributor to be an extension to the GW
(or even use the GW HW to implement the Distributor).

This approach might not be considered secure enough for some cases, such as, if
LBaaS is used for internal tier-to-tier communication inside a tenant network.
Some tenants may want their loadbalancer's VIP to remain private and their
front-end network to be isolated. In these cases, in order to accomplish
active-active for this tenant we would need separate dedicated Distributor
instance(s).

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

Further Discussion
------------------

.. Note::
  This section captures some background, ideas, concerns, and remarks that
  were raised by various people. Some of the items here can be considered for
  future/alternative design and some will hopefully make their way into, yet
  to be written, related blueprints (e.g., auto-scaled topology).

[`P2`_] Handling changes in Cluster size (manual or auto-scaled)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The Distributor shall support different mechanism for preserving affinity
  of flows to Amphorae following a *change in the size* of the Amphorae
  Cluster.

- The goal is to minimize shuffling of client-to-Amphora mapping during
  cluster size changes:

  * When an Amphora is removed from the Cluster (e.g., due to failure or
    scale-down action), all its flows are broken; however, flows to other
    Amphorae should not be affected. Also, if a drain method is used to empty
    the Amphora of client flows (in the case of a graceful removal), this
    should prevent disruption.

  * When an Amphora is *added* to the Cluster (e.g., recovery of a failed
    Amphora), some new flows should be distributed to the new Amphora;
    however, most flows should still go to the same Amphora they were
    distributed to before the new Amphora was added. For example, if the
    affinity of flows to Amphorae is per Source IP and a new Amphora was just
    added then the Distributor should forward packets from this IP only one
    of only two Amphorae: either the same Amphora as before or the
    Amphora that was added.

  Using a simple hash to maintain affinity does not meet this goal.

  For example, suppose we maintain affinity (for a fixed cluster size) using
  a hash (for randomizing key distribution) as
  `chosen_amphora_id = hash(sourceIP # port) mod number_of_amphorae`.
  When a new Amphora is added or remove the number of Amphorae changes;
  thus, a different Amphora will be chosen for most flows.

- Below are the couple of ways to tackle this shuffling problem.

  *Consistent Hashing*
    Consistent hashing is a hashing mechanism (regardless if key is based on
    IP or IP/port) that preserves most hash mappings during changes in the
    size of the Amphorae Cluster. In particular, for a cluster with N
    Amphorae that grows to N+1 Amphorae, a consistent hashing function
    ensures that, with high probability, only 1/N of inputs flows will be
    re-hashed (more precisely, K/N keys will be rehashed). Note that, even
    with consistent hashing, some flows will be remapped and there is only
    a statistical bound on the number of remapped flows.

    The "classic" consistent hashing algorithm maps both server IDs and
    keys to hash values and selects for each key the server with the
    closest hash value to the key hash value. Lookup generally requires
    O(log N) to search for the "closest" server. Achieving good
    distribution requires multiple hashes per server (~10s) -- although
    these can be pre-computed there is an ~10s*N memory footprint. Other
    algorithms (e.g., MSFT's Magleb) have better performance, but provide
    weaker guarantees.

    There are several consistent hashing libraries available. None are
    supported in OVS.

    * Ketama https://github.com/RJ/ketama

    * Openstack swift https://docs.openstack.org/swift/latest/ring.html#ring

    * Amazon dynamo
      http://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf

    We should also strongly consider making any consistent hashing algorithm
    we develop available to all OpenStack components by making it part of an
    Oslo library.

  *Rendezvous hashing*
    This method provides similar properties to Consistent Hashing (i.e., a
    hashing function that remaps only 1/N of keys when a cluster with N
    Amphorae grows to N+1 Amphorae.

    For each server ID, the algorithm concatenates the key and server ID and
    computes a hash. The server with the largest hash is chosen. This
    approach requires O(N) for each lookup, but is much simpler to
    implement and has virtually no memory footprint. Through search-tree
    encoding of the server IDs it is possible to achieve O(log N) lookup,
    but implementation is harder and distribution is not as good. Another
    feature is that more than one server can be chosen (e.g., two largest
    values) to handle larger loads -- not directly useful for the
    Distributor use case.

  *Hybrid, Permutation-based approach*
    This is an alternative implementation of consistent hashing that may be
    simpler to implement. Keys are hashed to a set of buckets; each bucket
    is pre-mapped to a random permutation of the server IDs. Lookup is by
    computing a hash of the key to obtain a bucket and then going over the
    permutation selecting the first server. If a server is marked as "down"
    the next server in the list is chosen. This approach is similar to
    Rendezvous hashing if each key is directly pre-mapped to a random
    permutation (and like it allows more than one server selection). If the
    number of failed servers is small then lookup is about O(1); memory is
    O(N * #buckets), where the granularity of distribution is improved by
    increasing the number of buckets. The permutation-based approach is
    useful to support clusters of fixed size that need to handle a few
    nodes going down and then coming back up. If there is an assumption on
    the number of failures then memory can be reduced to O( max_failures *
    #buckets). This approach seems to suit the Distributor Active-Active
    use-case for non-elastic workloads.

- Flow tracking is required, even with the above hash functions, to handle
  the (relatively few) remapped flows. If an existing flow is remapped, its
  TCP connection would break. This is acceptable when an Amphora goes down
  and it flows are mapped to a new one. On the other hand, it may be
  unacceptable when an Amphora is added to the cluster and 1/N of existing
  flows are remapped. The Distributor may support different modes, as follows.

  *None / Stateless*
    In this mode, the Distributor applies its most recent forwarding rules,
    regardless of previous state. Some existing flows might be remapped to a
    different Amphora and would be broken. The client would have to recover
    and establish a connection with the new Amphora (it would still be
    mapped to the same back-end, if possible). Combined with consistent (or
    similar) hashing, this may be good enough for many web applications
    that are built for failure anyway, and can restore their state upon
    reconnect.

  *Full flow Tracking*
    In this mode, the Distributor tracks existing flows to provide full
    affinity, i.e., only new flows can be remapped to different Amphorae.
    The Linux connection tracking may be used (e.g., through IPTables or
    through OpenFlow); however, this might not scale well. Alternatively,
    the Distributor can use an independent mechanism similar to HA-Proxy
    sticky-tables to track the flows. Note that the Distributor only needs to
    track the mapping per source IP and source port (unlike Linux connection
    tracking which follows the TCP state and related connections).

  *Use Ryu*
    Ryu is a well supported and tested python binding for issuing OpenFlow
    commands. Especially since Neutron recently moved to using this for
    many of the things it does, using this in the Distributor might make
    sense for Octavia as well.

Forwarding Data-path Implementation Alternatives
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The current design uses L2 forwarding based only on L3 parameters and uses
Direct Return routing (one-legged). The rational behind this approach is
to keep the Distributor as light as possible and have the Amphorae do the
bulk of the work. This allows one (or a few) Distributor instance(s) to
serve all traffic even for very large workloads. Other approaches are
possible.

2-legged Router
_______________

- Distributor acts as router, being in-path on both directions.

- New network between Distributor and Amphorae -- Only Distributor on VIP
  subnet.

- No need to use MAC forwarding -- use routing rules

LVS
___

Use LVS for Distributor.

DNS
___

Use DNS for the Distributor.

- Use DNS to map to particular Amphorae. Distribution will be of
  domain name rather than VIP.

- No problem with per-flow affinity, as client will use same IP for entire
  TCP connection.

- Need a different public IP for each Amphora (no VIP)

Pure SDN
________

- Implement the OpenFlow rules directly in the network, without a
  Distributor instance.

- If the network infrastructure supports this then the Distributor can
  become more robust and very lightweight, making it practical to have a
  dedicated Distributor per VIP (only the rules will be dedicated as the
  network and SDN controller are shared resources)

Distributor Sharing
^^^^^^^^^^^^^^^^^^^

- The initial implementation of the Distributor will not be shared between
  tenants until tests can be written to verify the security of this solution.

- The implementation should support different Distributor sharing and
  cardinality configurations. This includes single-shared Distributor,
  multiple-dedicated Distributors, and multiple-shared Distributors. In
  particular, an abstraction layer should be used and the data-model should
  include an association between the load balancer and Distributor.

- A shared Distributor uses the least amount of resources, but may not meet
  isolation requirements (performance and/or security) or might become a
  bottleneck.

Distributor High-Availability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The Distributor should be highly-available (as this is one of the
  motivations for the active-active topology). Once the initial active-active
  functionality is delivered, developing a highly available distributor should
  take a high priority.

- A mechanism similar to the VRRP used on ACTIVE-STANDBY topology Amphorae
  can be used.

- Since the Distributor is stateless (for fixed cluster sizes and if no
  connection tracking is used) it is possible to set up an active-active
  configuration and advertise more than one Distributor (e.g, for ECMP).

- As a first step, the initial implementation will use a single Distributor
  instance (i.e., will not be highly-available). Health Manager will monitor
  the Distributor health and initiate recovery if needed.

- The implementation should support plugging-in a hardware-based
  implementation of the Distributor that may have its own high-availability
  support.

- In order to preserve client to Amphora affinity in the case of a failover,
  a VRRP-like HA Distributor has several options. We could potentially push
  Amphora registrations to the standby Distributor with the position
  arguments specified, in order to guarantee the active and standby Distributor
  always have the same configuration. Or, we could invent and utilize a
  synchronization protocol between the active and standby Distributors. This
  will be explored and decided when an HA Distributor specification is
  written and approved.


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


References
==========

https://blueprints.launchpad.net/octavia/+spec/base-image
https://blueprints.launchpad.net/octavia/+spec/controller-worker
https://blueprints.launchpad.net/octavia/+spec/amphora-driver-interface
https://blueprints.launchpad.net/octavia/+spec/controller
https://blueprints.launchpad.net/octavia/+spec/operator-api
:doc:`../../api/haproxy-amphora-api`
https://blueprints.launchpad.net/octavia/+spec/active-active-topology
