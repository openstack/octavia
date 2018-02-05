..
  This work is licensed under a Creative Commons Attribution 3.0 Unported
  License.

  http://creativecommons.org/licenses/by/3.0/legalcode


=================================
Active-Active, N+1 Amphorae Setup
=================================

https://blueprints.launchpad.net/octavia/+spec/active-active-topology

Problem description
===================

This blueprint describes how Octavia implements an *active-active*
loadbalancer (LB) solution that is highly-available through redundant
Amphorae. It presents the high-level service topology and suggests
high-level code changes to the current code base to realize this scenario.
In a nutshell, an *Amphora Cluster* of two or more active Amphorae
collectively provide the loadbalancing service.

The Amphora Cluster shall be managed by an *Amphora Cluster Manager* (ACM).
The ACM shall provide an abstraction that allows different types of
active-active features (e.g., failure recovery, elasticity, etc.). The
initial implementation shall not rely on external services, but the
abstraction shall allow for interaction with external ACMs (to be developed
later).

This blueprint uses terminology defined in Octavia glossary when available,
and defines new terms to describe new components and features as necessary.

.. _P2:

  **Note:** Items marked with [`P2`_] refer to lower priority features to be
  designed / implemented only after initial release.


Proposed change
===============

A tenant should be able to start a highly-available, loadbalancer for the
tenant's backend services as follows:

* The operator should be able to configure an active-active topology
  through an Octavia configuration file or [`P2`_] through a Neutron flavor,
  which the loadbalancer shall support. Octavia shall support active-active
  topologies in addition to the topologies that it currently supports.

* In an active-active topology, a cluster of two or more amphorae shall
  host a replicated configuration of the load-balancing services. Octavia
  will manage this *Amphora Cluster* as a highly-available service using a
  pool of active resources.

* The Amphora Cluster shall provide the load-balancing services and support
  the configurations that are supported by a single Amphora topology,
  including L7 load-balancing, SSL termination, etc.

* The active-active topology shall support various Amphora types and
  implementations; including, virtual machines, [`P2`_] containers, and
  bare-metal servers.

* The operator should be able to configure the high-availability
  requirements for the active-active load-balancing services. The operator
  shall be able to specify the number of healthy Amphorae that must exist
  in the load-balancing Amphora Cluster. If the number of healthy Amphorae
  drops under the desired number, Octavia shall automatically and
  seamlessly create and configure a new Amphora and add it to the Amphora
  Cluster. [`P2`_] The operator should be further able to define that the
  Amphora Cluster shall be allocated on separate physical resources.

* An Amphora Cluster will collectively act to serve as a single logical
  loadbalancer as defined in the Octavia glossary. Octavia will seamlessly
  distribute incoming external traffic among the Amphorae in the Amphora
  Cluster. To that end, Octavia will employ a *Distributor* component that
  will forward external traffic towards the managed amphora instances.
  Conceptually, the Distributor provides an extra level of load-balancing
  for an active-active Octavia application, albeit a simplified one.
  Octavia should be able to support several Distributor implementations
  (e.g., software-based and hardware-based) and different affinity models
  (at minimum, flow-affinity should be supported to allow TCP connectivity
  between clients and Amphorae).

* The detailed design of the Distributor component will be described in a
  separate document (see "Distributor for Active-Active, N+1 Amphorae
  Setup", active-active-distributor.rst).


High-level Topology Description
-------------------------------

Single Tenant
~~~~~~~~~~~~~

* The following diagram illustrates the active-active topology:

::

                     Front-End                  Back-End
  Internet            Network                   Network
  (world)             (tenant)                  (tenant)
    ║                    ║                         ║
  ┌─╨────┐ floating IP   ║                         ║  ┌────────┐
  │Router│  to LB VIP    ║  ┌────┬─────────┬────┐  ║  │ Tenant │
  │  GW  ├──────────────►╫◄─┤ IP │ Amphora │ IP ├─►╫◄─┤Service │
  └──────┘               ║  └┬───┤   (1)   │back│  ║  │  (1)   │
                         ║   │VIP├─┬──────┬┴────┘  ║  └────────┘
                         ║   └───┘ │ MGMT │        ║  ┌────────┐
    ╓◄───────────────────║─────────┤  IP  │        ║  │ Tenant │
    ║   ┌─────────┬────┐ ║         └──────┘        ╟◄─┤Service │
    ║   │ Distri- │  IP├►╢                         ║  │  (2)   │
    ║   │  butor  ├───┬┘ ║  ┌────┬─────────┬────┐  ║  └────────┘
    ║   └─┬──────┬┤VIP│  ╟◄─┤ IP │ Amphora │ IP ├─►╢  ┌────────┐
    ║     │ MGMT │└─┬─┘  ║  └┬───┤   (2)   │back│  ║  │ Tenant │
    ╟◄────┤  IP  │  └arp►╢   │VIP├─┬──────┬┴────┘  ╟◄─┤Service │
    ║     └──────┘       ║   └───┘ │ MGMT │        ║  │  (3)   │
    ╟◄───────────────────║─────────┤  IP  │        ║  └────────┘
    ║  ┌───────────────┐ ║         └──────┘        ║
    ║  │ Octavia LBaaS │ ║           •••           ║      •
    ╟◄─┤  Controller   │ ║  ┌────┬─────────┬────┐  ║      •
    ║  └┬─────────────┬┘ ╙◄─┤ IP │ Amphora │ IP ├─►╢
    ║   │   Amphora   │     └┬───┤   (k)   │back│  ║  ┌────────┐
    ║   │ Cluster Mgr.│      │VIP├─┬──────┬┴────┘  ║  │ Tenant │
    ║   └─────────────┘      └───┘ │ MGMT │        ╙◄─┤Service │
    ╟◄─────────────────────────────┤  IP  │           │  (m)   │
    ║                              └──────┘           └────────┘
    ║
  Management                    Amphora Cluster    Back-end Pool
  Network                           1..k                1..m

* An example of high-level data-flow:

  1. Internet clients access a tenant service through an externally visible
     floating-IP (IPv4 or IPv6).

  2. If IPv4, a gateway router maps the floating IP into a loadbalancer's
     internal VIP on the tenant's front-end network.

  3. The (multi-tenant) Distributor receives incoming requests to the
     loadbalancer's VIP. It acts as a one-legged direct return LB,
     answering ``arp`` requests for the loadbalancer's VIP (see Distributor
     spec.).

  4. The Distributor distributes incoming connections over the tenant's
     Amphora Cluster, by forwarding each new connection opened with a
     loadbalancer's VIP to a front-end MAC address of an Amphora in the
     Amphora Cluster (layer-2 forwarding). *Note*: the Distributor may
     implement other forwarding schemes to support more complex routing
     mechanisms, such as DVR (see Distributor spec.).

  5. An Amphora receives the connection and accepts traffic addressed to
     the loadbalancer's VIP. The front-end IPs of the Amphorae are
     allocated on the tenant's front-end network. Each Amphora accepts VIP
     traffic, but does not answer ``arp`` request for the VIP address.

  6. The Amphora load-balances the incoming connections to the back-end
     pool of tenant servers, by forwarding each external request to a
     member on the tenant network. The Amphora also performs SSL
     termination if configured.

  7. Outgoing traffic traverses from the back-end pool members, through
     the Amphora and directly to the gateway (i.e., not through the
     Distributor).

Multi-tenant Support
~~~~~~~~~~~~~~~~~~~~

* The following diagram illustrates the active-active topology with
  multiple tenants:

::

                      Front-End                   Back-End
  Internet             Networks                   Networks
  (world)              (tenant)                   (tenant)
    ║                    B  A                         A
    ║      floating IP   ║  ║                         ║  ┌────────┐
  ┌─╨────┐ to LB VIP A   ║  ║  ┌────┬─────────┬────┐  ║  │Tenant A│
  │Router├───────────────║─►╫◄─┤A IP│ Amphora │A IP├─►╫◄─┤Service │
  │  GW  ├──────────────►╢  ║  └┬───┤   (1)   │back│  ║  │  (1)   │
  └──────┘ floating IP   ║  ║   │VIP├─┬──────┬┴────┘  ║  └────────┘
           to LB VIP B   ║  ║   └───┘ │ MGMT │        ║  ┌────────┐
    ╓◄───────────────────║──║─────────┤  IP  │        ║  │Tenant A│
    ║                    ║  ║         └──────┘        ╟◄─┤Service │
    M                    B  A  ┌────┬─────────┬────┐  ║  │  (2)   │
    ║                    ║  ╟◄─┤A IP│ Amphora │A IP├─►╢  └────────┘
    ║                    ║  ║  └┬───┤   (2)   │back│  ║  ┌────────┐
    ║                    ║  ║   │VIP├─┬──────┬┴────┘  ║  │Tenant A│
    ║                    ║  ║   └───┘ │ MGMT │        ╟◄─┤Service │
    ╟◄───────────────────║──║─────────┤  IP  │        ║  │  (3)   │
    ║                    ║  ║         └──────┘        ║  └────────┘
    ║                    B  A           •••           B      •
    ║   ┌─────────┬────┐ ║  ║  ┌────┬─────────┬────┐  ║      •
    ║   │         │IP A├─╢─►╫◄─┤A IP│ Amphora │A IP├─►╢  ┌────────┐
    ║   │         ├───┬┘ ║  ║  └┬───┤   (k)   │back│  ║  │Tenant A│
    ║   │ Distri- │VIP├─arp►╜   │VIP├─┬──────┬┴────┘  ╙◄─┤Service │
    ║   │  butor  ├───┘  ║      └───┘ │ MGMT │           │  (m)   │
    ╟◄─ │         │ ─────║────────────┤  IP  │           └────────┘
    ║   │         ├────┐ ║            └──────┘
    ║   │         │IP B├►╢                                tenant A
    ║   │         ├───┬┘ ║  = = = = = = = = = = = = = = = = = = = = =
    ║   │         │VIP│  ║     ┌────┬─────────┬────┐  B   tenant B
    ║   └─┬──────┬┴─┬─┘  ╟◄────┤B IP│ Amphora │B IP├─►╢  ┌────────┐
    ║     │ MGMT │  └arp►╢     └┬───┤   (1)   │back│  ║  │Tenant B│
    ╟◄────┤  IP  │       ║      │VIP├─┬──────┬┴────┘  ╟◄─┤Service │
    ║     └──────┘       ║      └───┘ │ MGMT │        ║  │  (1)   │
    ╟◄───────────────────║────────────┤  IP  │        ║  └────────┘
    ║  ┌───────────────┐ ║            └──────┘        ║
    M  │ Octavia LBaaS │ B              •••           B      •
    ╟◄─┤  Controller   │ ║     ┌────┬─────────┬────┐  ║      •
    ║  └┬─────────────┬┘ ╙◄────┤B IP│ Amphora │B IP├─►╢
    ║   │   Amphora   │        └┬───┤   (q)   │back│  ║  ┌────────┐
    ║   │ Cluster Mgr.│         │VIP├─┬──────┬┴────┘  ║  │Tenant B│
    ║   └─────────────┘         └───┘ │ MGMT │        ╙◄─┤Service │
    ╟◄────────────────────────────────┤  IP  │           │  (r)   │
    ║                                 └──────┘           └────────┘
    ║
  Management                      Amphora Clusters      Back-end Pool
  Network                         A(1..k), B(1..q)    A(1..m),B(1..r)


* Both tenants A and B share the Distributor, but each has a different
  front-end network. The Distributor listens on both loadbalancers' VIPs
  and forwards to either A's or B's Amphorae.

* The Amphorae and the back-end (tenant) networks are not shared between
  tenants.


Problem Details
---------------

* Octavia should support different Distributor implementations, similar
  to its support for different Amphora types. The operator should be able
  to configure different types of algorithms for the Distributor. All
  algorithms should provide flow-affinity to allow TLS termination at the
  amphora. See :doc:`active-active-distributor` for details.

* Octavia controller shall seamlessly configure any newly created Amphora
  ([`P2`_] including peer state synchronization, such as sticky-tables, if
  needed) and shall reconfigure the other solution components (e.g.,
  Neutron) as needed. The  controller shall further manage all Amphora
  life-cycle events.

* Since it is impractical at scale for peer state synchronization to occur
  between all Amphorae part of a single load balancer, Amphorae that are all
  part of a single load balancer configuration need to be divided into smaller
  peer groups (consisting of 2 or 3 Amphorae) with which they should
  synchronize state information.


Required changes
----------------

The active-active loadbalancers require the following high-level changes:


Amphora related changes
~~~~~~~~~~~~~~~~~~~~~~~

* Updated Amphora image to support active-active topology. The front-end
  still has both a unique IP (to allow direct addressing on front-end
  network) and a VIP; however, it should not answer ARP requests for the
  VIP address (all Amphorae in a single Amphora Cluster concurrently serve
  the same VIP). Amphorae should continue to have a management IP on the LB
  Network so Octavia can configure them. Amphorae should also generally
  support hot-plugging interfaces into back-end tenant networks as they do
  in the current implementation. [`P2`_] Finally, the Amphora configuration
  may need to be changed to randomize the member list, in order to prevent
  synchronized decisions by all Amphorae in the Amphora Cluster.

* Extend data model to support active-active Amphora. This is somewhat
  similar to active-passive (VRRP) support. Each Amphora needs to store its
  IP and port on its front-end network (similar to ha_ip and ha_port_id
  in the current model) and its role should indicate it is in a cluster.

  The provisioning status should be interpreted as referring to an Amphora
  only and not the load-balancing service. The status of the load balancer
  should correspond to the number of ``ONLINE`` Amphorae in the Cluster.
  If all Amphoae are ``ONLINE``, the load balancer is also ``ONLINE``. If a
  small number of Amphorae are not ``ONLINE``, then the load balancer is
  ``DEGRADED``. If enough Amphorae are not ``ONLINE`` (past a threshold), then
  the load balancer is ``DOWN``.

* Rework some of the controller worker flows to support creation and
  deletion of Amphorae by the ACM in an asynchronous manner. The compute
  node may be created/deleted independently of the corresponding Amphora
  flow, triggered as events by the ACM logic (e.g., node update). The flows
  do not need much change (beyond those implied by the changes in the data
  model), since the post-creation/pre-deletion configuration of each
  Amphora is unchanged. This is also similar to the failure recovery flow,
  where a recovery flow is triggered asynchronously.

* Create a flow (or task) for the controller worker for (de-)registration
  of Amphorae with Distributor. The Distributor has to be aware of the
  current ``ONLINE`` Amphorae, to which it can forward traffic. [`P2`_] The
  Distributor can do very basic monitoring of the Amphorae health (primarily
  to make sure network connectivity between the Distributor and Amphorae is
  working). Monitoring pool member health will remain the purview of the
  pool health monitors.

* All the Amphorae in the Amphora Cluster shall replicate the same
  listeners, pools, and TLS configuration, as they do now. We assume all
  Amphorae in the Amphora Cluster can perform exactly the same
  load-balancing decisions and can be treated as equivalent by the
  Distributor (except for affinity considerations).

* Extend the Amphora (REST) API and/or *Plug VIP* task to allow disabling
  of ``arp`` on the VIP.

* In order to prevent losing session_persistence data in the event of an
  Amphora failure, the Amphorae will need to be configured to share
  session_persistence data (via stick tables) with a subset of other
  Amphorae that are part of the same load balancer configuration (ie. a
  peer group).

Amphora Cluster Manager driver for the active-active topology (*new*)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Add an active-active topology to the topology types.

* Add a new driver to support creation/deletion of an Amphora Cluster via
  an ACM. This will re-use existing controller-worker flows as much as
  possible. The reference ACM will call the existing drivers to create
  compute nodes for the Amphorae and configure them.

* The ACM shall orchestrate creation and deletion of Amphora instances to
  meet the availability requirements. Amphora failover will utilize the
  existing health monitor flows, with hooks to notify the ACM when
  ACTIVE-ACTIVE topology is used. [`P2`_] ACM shall handle graceful amphora
  removal via draining (delay actual removal until existing connections are
  terminated or some timeout has passed).

* Change the flow of LB creation. The ACM driver shall create an Amphora
  Cluster instance for each new loadbalancer. It should maintain the
  desired number of Amphorae in the Cluster and meet the
  high-availability configuration given by the operator. *Note*: a base
  functionality is already supported by the Health Manager; it may be
  enough to support a fixed or dynamic cluster size. In any case, existing
  flows to manage Amphora life cycle will be re-used in the reference ACM
  driver.

* The ACM shall be responsible for providing health, performance, and
  life-cycle management at the Cluster-level rather than at Amphora-level.
  Maintaining the loadbalancer status (as described above) by some function
  of the collective status of all Amphorae in the Cluster is one example.
  Other examples include tracking configuration changes, providing Cluster
  statistics, monitoring and maintaining compute nodes for the Cluster,
  etc. The ACM abstraction would also support pluggable ACM implementations
  that may provide more advance capabilities (e.g., elasticity, AZ aware
  availability, etc.). The reference ACM driver will re-use existing
  components and/or code which currently handle health, life-cycle, etc.
  management for other load balancer topologies.

* New data model for an Amphora Cluster which has a one-to-one mapping with
  the loadbalancer. This defines the common properties of the Amphora
  Cluster (e.g., id, min. size, desired size, etc.) and additional
  properties for the specific implementation.

* Add configuration file options to support configuration of an
  active-active Amphora Cluster. Add default configuration. [`P2`_] Add
  Operator API.

* Add or update documentation for new components added and new or changed
  functionality.

* Communication between the ACM and Distributors should be secured using
  two-way SSL certificate authentication much the same way this is accomplished
  between other Octavia controller components and Amphorae today.

Network driver changes
~~~~~~~~~~~~~~~~~~~~~~

* Support the creation, connection, and configuration of the various
  networks and interfaces as described in 'high-level topology' diagram.

* Adding a new loadbalancer requires attaching the Distributor to the
  loadbalancer's front-end network, adding a VIP port to the Distributor,
  and configuring the Distributor to answer ``arp`` requests for the VIP.
  The Distributor shall have a separate interface for each loadbalancer and
  shall not allow any routing between different ports; in particular,
  Amphorae of different tenants must not be able to communicate with each
  other. In the reference implementation, this will be accomplished by using
  separate OVS bridges per load balancer.

* Adding a new Amphora requires attaching it to the front-end and back-end
  networks (similar to current implementation), adding the VIP (but with
  ``arp`` disabled), and registering the Amphora with the Distributor. The
  tenant's front-end and back-end networks must allow attachment of
  dynamically created Amphorae by involving the ACM (e.g., when the health
  monitor replaces a failed Amphora). ([`P2`_] extend the LBaaS API to allow
  specifying an address range for new Amphorae usage, e.g., a subnet pool).


Amphora health-monitoring support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Modify Health Manager to manage the health for an Amphora Cluster through
  the ACM; namely, forward Amphora health change events to the ACM, so it
  can decide when the Amphora Cluster is considered to be in healthy state.
  This should be done in addition to managing the health of each Amphora.
  [`P2`_] Monitor the Amphorae also on their front-end network (i.e., from
  the Distributor).


Distributor support
~~~~~~~~~~~~~~~~~~~

* **Note:** as mentioned above, the detailed design of the Distributor
  component is described in a separate document). Some design
  considerations are highlighted below.

* The Distributor should be supported similarly to an Amphora; namely, have
  its own abstract driver.

* For a reference implementation, add support for a Distributor image.

* Define a REST API for Distributor configuration (no SSH API). The API
  shall support:

  - Add and remove a VIP (loadbalancer) and specify distribution parameters
    (e.g., affinity, algorithm, etc.).

  - Registration and de-registration of Amphorae.

  - Status

  - [`P2`_] Macro-level stats

* Spawn Distributors (if using on demand Distributor compute nodes) and/or
  attach to existing ones as needed. Manage health and life-cycle of the
  Distributor(s). Create, connect, and configure Distributor networks as
  necessary.

* Create data model for the Distributor.

* Add Distributor driver and flows to (re-)configure the Distributor on
  creation/destruction of a new loadbalancer (add/remove loadbalancer VIP)
  and [`P2`_] configure the distribution algorithm for the loadbalancer's
  Amphora Cluster.

* Add flows to Octavia to (re-)configure the Distributor on adding/removing
  Amphorae from the Amphora Cluster.


Packaging
~~~~~~~~~

* Extend Octavia installation scripts to create an image for the Distributor.


Alternatives
------------

* Use external services to manage the cluster directly.
    This utilizes functionality that already exists in OpenStack (e.g.,
    like Heat and Ceilometer) rather than replicating it. This approach
    would also benefit from future extensions to these services. On the
    other hand, this adds undesirable dependencies on other projects (and
    their corresponding teams), complicates handling of failures, and
    require defensive coding around service calls. Furthermore, these
    services cannot handle the LB-specific control configuration.

* Implement a nested Octavia
    Use another layer of Octavia to distribute traffic across the Amphora
    Cluster (i.e., the Amphorae in the Cluster are back-end members of
    another Octavia instance). This approach has the potential to provide
    greater flexibility (e.g., provide NAT and/or more complex distribution
    algorithms). It also potentially reuses existing code. However, we do
    not want the Distributor to proxy connections so HA-Proxy cannot be
    used. Furthermore, this approach might significantly increase the
    overhead of the solution.


Data model impact
-----------------

* loadbalancer table

  - `cluster_id`: associated Amphora Cluster (no changes to table, 1-1
    relationship from Cluster data-model)

* lb_topology table

  - new value: ``ACTIVE_ACTIVE``

* amphora_role table

  - new value: ``IN_CLUSTER``

* Distributor table (*new*): Distributor information, similar to Amphora.
  See :doc:`active-active-distributor`

* Cluster table (*new*): an extension to loadbalancer (i.e., one-to-one
  mapping to load-balancer)

  - `id` (primary key)

  - `cluster_name`: identifier of Cluster instance for Amphora Cluster
    Manager

  - `desired_size`: required number of Amphorae in Cluster. Octavia will
    create this many active-active Amphorae in the Amphora Cluster.

  - `min_size`: number of ``ACTIVE`` Amphorae in Cluster must be above this
    number for Amphora Cluster status to be ``ACTIVE``

  - `cooldown`:  cooldown period between successive add/remove Amphora
    operations (to avoid thrashing)

  - `load_balancer_id`: 1:1 relationship to loadbalancer

  - `distributor_id`: N:1 relationship to Distributor. Support multiple
    Distributors

  - `provisioning_status`

  - `operating_status`

  - `enabled`

  - `cluster_type`: type of Amphora Cluster implementation


REST API impact
---------------

* Distributor REST API -- This is a new internal API that will be secured
  via two-way SSL certificate authentication. See
  :doc:`active-active-distributor`

* Amphora REST API -- support configuration of disabling ``arp`` on VIP.

* [`P2`_] LBaaS API -- support configuration of desired availability, perhaps
  by selecting a flavor (e.g., gold is a minimum of 4 Amphorae, platinum is
  a minimum of 10 Amphora).

* Operator API --

  - Topology to use

  - Cluster type

  - Default availability parameters for the Amphora Cluster


Security impact
---------------

* See :doc:`active-active-distributor` for Distributor related security impact.


Notifications impact
--------------------

None.


Other end user impact
---------------------

None.


Performance Impact
------------------

ACTIVE-ACTIVE should be able to deliver significantly higher performance than
SINGLE or ACTIVE-STANDBY topology. It will consume more resources to deliver
this higher performance.


Other deployer impact
---------------------

The reference ACM becomes a new process that is part of the Octavia control
components (like the controller worker, health monitor and housekeeper). If
the reference implementation is used, a new Distributor image will need to be
created and stored in glance much the same way the Amphora image is created
and stored today.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

@TODO


Work Items
----------

@TODO


Dependencies
============

@TODO


Testing
=======

* Unit tests with tox.
* Function tests with tox.
* Scenario tests.


Documentation Impact
====================

Need to document all new APIs and API changes, new ACTIVE-ACTIVE topology
design and features, and new instructions for operators seeking to deploy
Octavia with ACTIVE-ACTIVE topology.


References
==========

https://blueprints.launchpad.net/octavia/+spec/base-image
https://blueprints.launchpad.net/octavia/+spec/controller-worker
https://blueprints.launchpad.net/octavia/+spec/amphora-driver-interface
https://blueprints.launchpad.net/octavia/+spec/controller
https://blueprints.launchpad.net/octavia/+spec/operator-api
:doc:`../../api/haproxy-amphora-api`
https://blueprints.launchpad.net/octavia/+spec/active-active-topology
