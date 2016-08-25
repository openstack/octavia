..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================================
Active-Standby Amphora Setup using VRRP
=======================================

https://blueprints.launchpad.net/octavia/+spec/activepassiveamphora

This blueprint describes how Octavia implements its Active/Standby
solution. It will describe the high level topology and the proposed code
changes from the current supported Single topology to realize the high
availability loadbalancer scenario.

Problem description
===================

A tenant should be able to start high availability loadbalancer(s) for the
tenant's backend services as follows:

* The operator should be able to configure an Active/Standby topology through
  an octavia configuration file, which the loadbalancer shall support. An
  Active/Standby topology shall be supported by Octavia in addition to the
  Single topology that is currently supported.

* In Active/Standby, two Amphorae shall host a replicated configuration of the
  load balancing services. Both amphorae will also deploy a Virtual Router
  Redundancy Protocol (VRRP) implementation [2].

* Upon failure of the master amphora, the backup one shall seamlessly take over
  the load balancing functions. After the master amphora changes to a healthy
  status, the backup amphora shall give up the load balancing functions to the
  master again (see [2] section 3 for details on master election protocol).

* Fail-overs shall be seamless to end-users and fail-over time should be
  minimized.

* The following diagram illustrates the Active/Standby topology.

asciiflow::

 +--------+
 | Tenant |
 |Service |
 |  (1)   |
 +--------+        +-----------+
 | +--------+ +----+  Master   +----+
 | | Tenant | |VIP |  Amphora  |IP1 |
 | |Service | +--+-+-----+-----+-+--+
 | |   (M)  |    | |MGMT |VRRP | |
 | +--------+    | | IP  | IP1 | |
 | |  Tenant     | +--+--++----+ |
 | | Network     |    |   |      |   +-----------------+ Floating +---------+
 v-v-------------^----+---v-^----v-^-+     Router      |    IP    |         |
 ^---------------+----v-^---+------+-+Floating <-> VIP <----------+ Internet|
 |  Management   |      |   |      | |                 |          |         |
 |    (MGMT)     |      |   |      | +-----------------+          +---------+
 |   Network     |   +--+--++----+ |
 |           Paired  |MGMT |VRRP | |
 |               |   | IP  | IP2 | |
 +-----------+   |   +-----+-----+ |
 |  Octavia  |  ++---+  Backup   +-+--+
 |Controller |  |VIP |  Amphora  |IP2 |
 |    (s)    |  +----+-----------+----+
 +-----------+

* The newly introduced VRRP IPs shall communicate on the same tenant network
  (see security impact for more details).

* The existing Haproxy Jinja configuration template shall include "peer"
  setup for state synchronization over the VRRP IP addresses.

* The VRRP IP addresses shall work with both IPv4 and IPv6.

Proposed change
===============

The Active/Standby loadbalancers require the following high level changes:

* Add support of VRRP in the amphora base image through Keepalived.

* Extend the controller worker to be able to spawn N amphorae associated with
  the same loadbalancer on N different compute nodes (This takes into account
  future work on Active/Active topology). The amphorae shall be allowed to
  use the VIP through "allow address pairing". These amphorae shall replicate
  the same listeners, and pools configuration. Note: topology is a property
  of a load balancer and not of one of its amphorae.

* Extend the amphora driver interface, the amphora REST driver, and Jinja
  configuration templates for the newly introduced VRRP service [4].

* Develop a Keepalived driver.

* Extend the network driver to become aware of the different loadbalancer
  topologies and add support of network creation. The network driver shall
  also pair the different amphorae in a given topology to the same VIP address.

* Extend the controller worker to build the right flow/sub-flows according to
  the given topology. The controller worker is also responsible of creating
  the correct stores needed by other flow/sub-flows.

* Extend the Octavia configuration and Operator API to support the
  Active/Standby topology.

* MINOR: Extend the Health Manager to be aware of the role of the amphora
  (Master/Backup) [9]. If the health manager decided to spawn a new amphora
  to replace an unhealthy one (while a backup amphora is already in service),
  it must replicate the same VRRP priorities, ids, and authentication
  credentials to keep the loadbalancer in its appropriate configuration.
  Listeners associated with this load balancer shall be put in a DEGRADED
  provisioning state.

Alternatives
------------

We could use heartbeats as an alternative to VRRP, which is also a widely
adopted solution. Heartbeats better suit redundant file servers, filesystems,
and databases rather than network services such as routers, firewalls, and
loadbalancers. Willy Tarreau, the creator of Haproxy, provides a detailed
view on the major differences between heartbeats and VRRP in [5].

Data model impact
-----------------

The data model of the Octavia database shall be impacted as follows:

* A new column in the load_balancer table shall indicate its topology. The
  topology field takes values from: SINGLE, or ACTIVE/STANDBY.

* A new column in the amphora table shall indicate an amphora's role in the
  topology. If the topology is SINGLE, the amphora role shall be STANDALONE. If
  the topology is ACTIVE/STANDBY, the amphora role shall be either MASTER or
  BACKUP. This role field will also be of use for the Active/Active topology.

* New value tables for the loadbalancer topology and the amphorae roles.

* New columns in the amphora table shall indicate the VRRP priority, the VRRP
  ID, and the VRRP interface of the amphora.

* A new column in the listener table shall indicate the TCP port used for
  listener internal data synchronization.

* VRRP groups define the common VRRP configurations for all listeners on an
  amphora. A new table shall hold the VRRP groups main configuration
  primitives including at least: VRRP authentication information, role and
  priority advertisement interval. Each Active/Standby loadbalancer defines one
  and only one VRRP group.

REST API impact
---------------

** Changes to amphora API: see [11] **

PUT /listeners/{amphora_id}/{listener_id}/haproxy

PUT /vrrp/upload

PUT /vrrp/{action}

GET /interface/{ip_addr}

** Changes to operator API: see [10] **

POST /loadbalancers
* Successful Status Code - 202
* JSON Request Body Attributes
** vip - another JSON object with one required attribute from the following
*** net_port_id - uuid
*** subnet_id - uuid
*** floating_ip_id - uuid
*** floating_ip_network_id - uuid
** tenant_id - string - optional - default "0" * 36 (for now)
** name - string - optional - default null
** description - string - optional - default null
** enabled - boolean - optional - default true
* JSON Response Body Attributes
** id - uuid
** vip - another JSON object
*** net_port_id - uuid
*** subnet_id - uuid
*** floating_ip_id - uuid
*** floating_ip_network_id - uuid
** tenant_id - string
** name - string
** description - string
** enabled - boolean
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)
** **topology - string enum - (SINGLE, ACTIVE_STANDBY)**

PUT /loadbalancers/{lb_id}
* Successful Status Code - 202
* JSON Request Body Attributes
** name - string
** description - string
** enabled - boolean
* JSON Response Body Attributes
** id - uuid
** vip - another JSON object
*** net_port_id - uuid
*** subnet_id - uuid
*** floating_ip_id - uuid
*** floating_ip_network_id - uuid
** tenant_id - string
** name - string
** description - string
** enabled - boolean
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)
** **topology - string enum - (SINGLE, ACTIVE_STANDBY)**

GET /loadbalancers/{lb_id}
* Successful Status Code - 200
* JSON Response Body Attributes
** id - uuid
** vip - another JSON object
*** net_port_id - uuid
*** subnet_id - uuid
*** floating_ip_id - uuid
*** floating_ip_network_id - uuid
** tenant_id - string
** name - string
** description - string
** enabled - boolean
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)
** **topology - string enum - (SINGLE, ACTIVE_STANDBY)**

Security impact
---------------

* The VRRP driver must automatically add a security group rule to the amphora's
  security group to allow VRRP traffic (Protocol number 112) on the same tenant
  subnet.

* The VRRP driver shall automatically add a security group rule to allow
  Authentication Header traffic (Protocol number 51).

* VRRP driver shall support authentication-type MD5.

* The HAProxy driver must be updated to automatically add a security group rule
  that allows multi-peers to synchronize their states.

* Currently HAProxy **does not** support peer authentication, and state sync
  messages are in plaintext.

* At this point, VRRP shall communicate on the same tenant network. The
  rationale is to fail-over based on a similar network interfaces condition
  which the tenant operates experience. Also, VRRP traffic and sync messages
  shall naturally inherit same protections applied to the tenant network.
  This may create fake fail-overs if the tenant network is under unplanned,
  heavy traffic. This is still better than failing over while the master is
  actually serving tenant's traffic or not failing over at all if the master
  has failed services. Additionally, the Keepalived shall check the health of
  the HAproxy service.

* In next steps the following shall be taken into account:
  * Tenant quotas and supported topologies.
  * Protection of VRRP Traffic, HAproxy state sync, Router IDs, and pass
  phrases in both packets and DB.

Notifications impact
--------------------

None.

Other end user impact
---------------------

* The operator shall be able to specify the loadbalancer topology in the
  Octavia configuration file (used by default).

Performance Impact
------------------

The Active/Standby can consume up to twice the resources (storage, network,
compute) as required by the Single Topology. Nevertheless, one single amphora
shall be active (i.e. serving end-user) at any point in time. If the Master
amphora is healthy, the backup one shall remain idle until it receives no
VRRP advertisements from the master.

The VRRP requires executing health checks in the amphorae at fine grain
granularity period. The health checks shall be as lightweight as possible
such that VRRP is able to execute all check scripts within a predefined
interval. If the check scripts failed to run within this predefined interval,
VRRP may become unstable and may alternate the amphorae roles between MASTER
and BACKUP incorrectly.

Other deployer impact
---------------------

* An amphora_topology config option shall be added. The controller worker
  shall change its taskflow behavior according to the requirement of different
  topologies.

* By default, the amphora_topology is SINGLE and the ACTIVE/STANDBY topology
  shall be enabled/requested explicitly by operators.

* The Keepalived version deployed in the amphora image must be newer than
  1.2.8 to support unicast VRRP mode.

Developer impact
----------------

None.


Implementation
==============

Assignee(s)
-----------

Sherif Abdelwahab (abdelwas)

Work Items
----------

* Amphora image update to include Keepalived.

* Data model updates.

* Control Worker extensions.

* Keepalived driver.

* Update Network driver.

* Security rules.

* Update Amphora REST APIs and Jinja Configurations.

* Update Octavia Operator APIs.


Dependencies
============

Keepalived version deployed in the amphora image must be newer than 1.2.8 to
support unicast VRRP mode.


Testing
=======

* Unit tests with tox.
* Function tests with tox.


Documentation Impact
====================

* Description of the different supported topologies: Single, Active/Standby.
* Octavia configuration file changes to enable the Active/Standby topology.
* CLI changes to enable the Active/Standby topology.
* Changes shall be introduced to the amphora APIs: see [11].


References
==========

[1] Implementing High Availability Instances with Neutron using VRRP
http://goo.gl/eP71g7

[2] RFC3768 Virtual Router Redundancy Protocol (VRRP)

[3] https://review.openstack.org/#/c/38230/

[4] http://www.keepalived.org/LVS-NAT-Keepalived-HOWTO.html

[5] http://www.formilux.org/archives/haproxy/1003/3259.html

[6] https://blueprints.launchpad.net/octavia/+spec/base-image

[7] https://blueprints.launchpad.net/octavia/+spec/controller-worker

[8] https://blueprints.launchpad.net/octavia/+spec/amphora-driver-interface

[9] https://blueprints.launchpad.net/octavia/+spec/controller

[10] https://blueprints.launchpad.net/octavia/+spec/operator-api

[11] doc/main/api/haproxy-amphora-api.rst
