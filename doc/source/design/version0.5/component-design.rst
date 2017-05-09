=============================
Octavia v0.5 Component Design
=============================
Please refer to the following diagram of the Octavia v0.5 components:

.. graphviz:: v0.5-component-design.dot

This milestone release of Octavia concentrates on making the service delivery
scalable (though individual listeners are not horizontally scalable at this
stage), getting API and other interfaces between major components correct,
without worrying about making the command and control layer scalable.

Note that this design is not yet "operator grade" but is a good first step to
achieving operator grade (which will occur with version 1 of Octavia).

================
LBaaS Components
================
The entities in this section describe components that are part of the Neutron
LBaaS project, with which Octavia interfaces to deliver load balancing
services.

USER API HANDLER
----------------
This is the front-end that users (and user GUIs or what have you) talk to to
manipulate load balancing services.

**Notes:**

* All implementation details are hidden from the user in this interface

* Performs a few simple sanity checks on user-supplied data, but otherwise
  looks to a driver provide more detail around whether what the user is asking
  for is possible on the driver's implementation.

* Any functionality that the user asks for that their back-end flavor / driver
  doesn't support will be met with an error when the user attempts to configure
  services this way. (There may be multiple kinds of errors: "incomplete
  configuration" would be non-fatal and allow DB objects to be created /
  altered. "incompatible configuration" would be fatal and disallow DB objects
  from being created / associations made.)  Examples of this include: UDP
  protocol for a listener on a driver/flavor that uses only haproxy as its
  back-end.

* Drivers should also be able to return 'out of resources' or 'some other
  error occurred' errors (hopefully with helpful error messages).

* This interface is stateless, though drivers may keep state information in a
  database. In any case, this interface should be highly scalable.

* Talks some "intermediate driver interface" with the driver. This takes the
  form of python objects passed directly within the python code to the driver.

=========================
LBaaS / Octavia Crossover
=========================
The entities in this section are "glue" components which allow Octavia to
interface with other services in the OpenStack environment. The idea here is
that we want Octavia to be as loosely-coupled as possible with those services
with which it must interact in order to keep these interfaces as clean as
possible.

Initially, all the components in this section will be entirely under the
purview of the Octavia project. Over time some of these components might be
eliminated entirely, or reduced in scope as these third-party services
evolve and increase in cleanly-consumable functionality.

DRIVER
------
This is the part of the load balancing service that actually interfaces between
the (sanitized) user and operator configuration and the back-end load balancing
appliances or other "service providing entity."

**Notes:**

* Configuration of the driver is handled via service profile definitions in
  association with the Neutron flavor framework. Specifically, a given flavor
  has service profiles associated with it, and service profiles which
  specify the Octavia driver will include meta-data (in the form of JSON
  configuration) which is used by the driver to define implementation
  specifics (for example, HA configuration and other details).

* Driver will be loaded by the daemon that does the user API and operator API.
  It is not, in and of itself, its own daemon, though a given vendor's back-end
  may contain its own daemons or other services that the driver interfaces
  with.

* It is thought that the driver front-end should be stateless in order to make
  it horizontally scalable and to preserves the statelessness of the user and
  operator API handlers. Note that the driver may interface with back-end
  components which need not be stateless.

* It is also possible for multiple instances of the driver will talk to the
  same amphora at the same time. Emphasis on the idempotency of the update
  algorithms used should help minimize the issues this can potentially cause.

NETWORK DRIVER
--------------
In order to keep Octavia's design more clean as a pure consumer of network
services, yet still be able to develop Octavia at a time when it is impossible
to provide the kind of load balancing services we need to provide without
"going around" the existing Neutron API, we have decided to write a "network
driver" component which does those dirty back-end configuration commands via
an API we write, until these can become a standard part of Neutron. This
component should be as loosely coupled with Octavia as Octavia will be with
Neutron and present a standard interface to Octavia for accomplishing network
configuration tasks (some of which will simply be a direct correlation with
existing Neutron API commands).

**Notes:**

* This is a daemon or "unofficial extension", presumably living on a Neutron
  network node which should have "back door" access to all things Neutron and
  exposes an API that should only be used by Octavia.

* Exactly what API will be provided by this driver will be defined as we
  continue to build out the reference implementation for Octavia.

* Obviously, as we discover missing functionality in the Neutron API, we should
  work with the Neutron core devs to get these added to the API in a timely
  fashion: We want the Network driver to be as lightweight as possible.


==================
Octavia Components
==================
Everything from here down are entities that have to do with the Octavia driver
and load balancing system. Other vendor drivers are unlikely to have the same
components and internal structure. It is planned that Octavia will become the
new reference implementation for LBaaS, though it of course doesn't need to be
the only one. (In fact, a given operator should be able to use multiple vendors
with potentially multiple drivers and multiple driver configurations through
the Neutron Flavor framework.)


OPERATOR API HANDLER
--------------------
This is exactly like the USER API HANDLER in function, except that
implementation details are exposed to the operator, and certain admin-level
features are exposed (ex. listing a given tenant's loadbalancers, & etc.)

It's also anticipated that the Operator API needs will vary enough from
implementation to implementation that no single Operator API will be sufficient
for the needs of all vendor implementations. (And operators will definitely
have implementation-specific concerns.) Also, we anticipate that most vendors
will already have an operator API or other interface which is controlled and
configured outsite the purview of OpenStack in general. As such it makes sense
for Octavia to have its own operator API / interface.

**Notes:**

* This interface is stateless. State should be managed by the controller, and
  stored in a highly available database.


CONTROLLER
----------
This is the component providing all the command and control for the
amphorae. On the front end, it takes its commands and controls from the LBaaS
driver.

It should be noted that in later releases of Octavia, the controller functions
will be split across several components. At this stage we are less concerned
with how this internal communication will happen, and are most concerned with
ensuring communication with amphorae, the amphora LB driver, and the Network
driver are all made as perfect as possible.

Among the controller's responsibilities are:

* Sending configuration and certificate information to an amphora LB
  driver, which in the reference implementation will be generating
  configuration files for haproxy and PEM-formatted user certificates and
  sending these to individual amphorae. Configuration files will be
  generated from jinja templates kept in an template directory specific to
  the haproxy driver.

* Processing the configuration updates that need to be applied to individual
  amphorae, as sent by the amphora LB driver.

* Interfacing with network driver to plumb additional interfaces on the
  amphorae as necessary.

* Monitoring the health of all amphorae (via a driver interface).

* Receiving and routing certain kinds of notifications originating on the
  amphorae (ex. "member down")

* This is a stateful service, and should keep its state in a central, highly
  available database of some sort.

* Respecting colocation / apolocation requirements of loadbalancers as set
  forth by users.

* Receiving notifications, statistics data and other short, regular messages
  from amphorae and routing them to the appropriate entity.

* Responding to requests from amphorae for configuration data.

* Responding to requests from the user API or operator API handler driver for
  data about specific loadbalancers or sub-objects, their status, and
  statistics.

* Amphora lifecycle management, including interfacing with Nova and Neutron
  to spin up new amphorae as necessary and handle initial configuration and
  network plumbing for their LB network interface, and cleaning this up when an
  amphora is destroyed.

* Maintaining a pool of spare amphorae (ie. spawning new ones as necessary
  and deleting ones from the pool when we have too much inventory here.)

* Gracefully spinning down "dirty old amphorae"

* Loading and calling configured amphora drivers.

**Notes:**

* Almost all the intelligence around putting together and validating
  loadbalancer configurations will live here-- the Amphora API is meant to
  be as simple as possible so that minor feature improvements do not
  necessarily entail pushing out new amphorae across an entire installation.

* The size of the spare amphora pool should be determined by the flavor
  being offered.

* The controller also handles spinning up amphorae in the case of a true
  active/standby topology (ie. where the spares pool is effectively zero.) It
  should have enough intelligence to communicate to Nova that these amphorae
  should not be on the same physical host in this topology.

* It also handles spinning up new amphorae when one fails in the above
  topology.

* Since spinning up a new amphora is a task that can take a long time, the
  controller should spawn a job or child process which handles this highly
  asynchronous request.


AMPHORA LOAD BALANCER (LB) DRIVER
---------------------------------
This is the abstraction layer that the controller talks to for communicating
with the amphorae. Since we want to keep Octavia flexible enough so that
certain components (like the amphora) can be replaced by third party
products if the operator so desires, it's important to keep many of the
implementation-specific details contained within driver layers. An amphora
LB driver also gives the operator the ability to have different open-source
amphorae with potentially different capabilities (accessed via different
flavors) which can be handy for, for example, field-testing a new amphora
image.

The reference implementation for the amphora LB driver will be for the amphora
described below.

Responsibilities of the amphora LB driver include:

* Generating configuration files for haproxy and PEM-formatted user
  certificates and sending these to individual amphorae. Configuration
  files will be generated from jinja templates kept in an template directory
  specific to the haproxy driver.

* Handling all communication to and from amphorae.


LB NETWORK
----------
This is the subnet that controllers will use to communicate with amphorae.
This means that controllers must have connectivity (either layer 2 or routed)
to this subnet in order to function, and vice versa. Since amphorae will be
communicating on it, this means the network is not part of the "undercloud."

**Notes:**

* As certain sensitive data (TLS private keys, for example) will be transmitted
  over this communication infrastructure, all messages carrying a sensitive
  payload should be done via encrypted and authenticated means. Further, we
  recommend that messages to and from amphorae be signed regardless of the
  sensitivity of their content.


AMPHORAE
----------
This is a Nova VM which actually provides the load balancing services as
configured by the user. Responsibilities of these entities include:

* Actually accomplishing the load balancing services for user-configured
  loadbalancers using haproxy.

* Sending regular heartbeats (which should include some status information).

* Responding to specific requests from the controller for very basic
  loadbalancer or sub-object status data, including statistics.

* Doing common high workload, low intelligence tasks that we don't want to
  burden the controller with. (ex. Shipping listener logs to a swift data
  store, if configured.)

* Sending "edge" notifications (ie. status changes) to the controller when
  members go up and down, when listeners go up and down, etc.

**Notes:**

* Each amphora will generally need its own dedicated LB network IP address,
  both so that we don't accidentally bind to any IP:port the user wants to use
  for loadbalancing services, and so that an amphora that is not yet in use
  by any loadbalancer service can still communicate on the network and receive
  commands from its controller. Whether this IP address exists on the same
  subnet as the loadbalancer services it hosts is immaterial, so long as
  front-end and back-end interfaces can be plumbed after an amphora is
  launched.

* Since amphorae speak to controllers in a "trusted" way, it's important to
  ensure that users do not have command-line access to the amphorae. In
  other words, the amphorae should be a black box from the users'
  perspective.

* Amphorae will be powered using haproxy 1.5 initially. We may decide to use
  other software (especially for TLS termination) later on.

* The "glue scripts" which communicate with the controller should be as
  lightweight as possible: Intelligence about how to put together an haproxy
  config, for example, should not live on the amphora. Rather, the amphora
  should perform simple syntax checks, start / restart haproxy if the checks
  pass, and report success/failure of the haproxy restart.

* With few exceptions, most of the API commands the amphora will ever do
  should be safely handled synchronously (ie. nothing should take longer than a
  second or two to complete).

* Connection logs, and other things anticipated to generate a potential large
  amount of data should be communicated by the amphora directly to which
  ever service is going to consume that data. (for example, if logs are being
  shunted off to swift on a nightly basis, the amphora should handle this
  directly and not go through the controller.)


INTERNAL HEALTH MONITORS
------------------------
There are actually a few of these, all of which need to be driven by some
daemon(s) which periodically check that heartbeats from monitored entities are
both current and showing "good" status, if applicable.  Specifically:

* Controllers need to be able to monitor the availability and overall health
  of amphorae they control. For active amphorae, this check should
  happen pretty quickly: About once every 5 seconds. For spare amphorae,
  the check can happen much more infrequently (say, once per minute).

The idea here is that internal health monitors will monitor a periodic
heartbeat coming from the amphorae, and take appropriate action (assuming
these are down) if they fail to check in with a heartbeat frequently enough.
This means that internal health monitors need to take the form of a daemon
which is constantly checking for and processing heartbeat requests (and
updating controller or amphorae statuses, and triggering other events as
appropriate).


======================================================
Some notes on Controller <-> Amphorae communications
======================================================
In order to keep things as scalable as possible, the thought was that short,
periodic and arguably less vital messages being emitted by the amphora and
associated controller would be done via HMAC-signed UDP, and more vital, more
sensitive, and potentially longer transactional messages would be handled via a
RESTful API on the controller, accessed via bi-directionally authenticated
HTTPS.

Specifically, we should expect the following to happen over UDP:
* heartbeats from the amphora VM to the controller

* stats data from the amphora to the controller

* "edge" alert notifications (change in status) from the amphora to the
  controller

* Notification of pending tasks in queue from controller to amphora

And the following would happen over TCP:
* haproxy / tls certificate configuration changes

=================================================
Supported Amphora Virtual Appliance Topologies
=================================================
Initially, I propose we support two topologies with version 0.5 of Octavia:

Option 1: "Single active node + spares pool"
--------------------------------------------
* This is similar to what HP is doing right now with Libra: Each amphora is
  stand-alone with a frequent health-check monitor in place and upon failure,
  an already-spun-up amphora is moved from the spares pool and configured to
  take the old one's place. This allows for acceptable recovery times on
  amphora failure while still remaining efficient, as far as VM resource
  utilization is concerned.

Option 2: "True Active / Standby"
---------------------------------
* This is similar to what Blue Box is doing right now where amphorae are
  deployed in pairs and use corosync / pacemaker to monitor each other's health
  and automatically take over (usually in less than 5 seconds) if the "active"
  node fails. This provides for the fastest possible recovery time on hardware
  failure, but is much less efficient, as far as VM resource utilization is
  concerned.

* In this topology a floating IP address (different from a Neutron floating
  IP!) is used to determine which amphora is the "active" one at any given
  time.

* In this topology, both amphorae need to be colocated on the same subnet.
  As such a "spares pool" doesn't make sense for this type of layout, unless
  all spares are on the same management network with the active nodes.

We considered also supporting "Single node" topology, but this turns out to be
the same thing as option 1 above with a spares pool size of zero.

============================
Supported Network Topologies
============================
This is actually where things get tricky, as far as amphora plumbing is
concerned. And it only grows trickier when we consider that front-end
connectivity (ie. to the 'loadbalancer' vip_address) and back-end connectivity
(ie. to members of a loadbalancing pool) can be handled in different ways.
Having said this, we can break things down into LB network, front-end and
back-end topology to discuss the various possible permutations here.

LB Network
----------
Each amphora needs to have a connection to a LB network. And each controller
needs to have access to this management network (this could be layer-2 or
routed connectivity). Command and control will happen via the amphorae's
LB network IP.

Front-end topologies
--------------------
There are generally two ways to handle the amphorae's connection to the
front-end IP address (this is the vip_address of the loadbalancer object):

**Option 1: Layer-2 connectivity**

The amphora can have layer-2 connectivity to the neutron network which is
host to the subnet on which the loadbalancer vip_address resides. In this
scenario, the amphora would need to send ARP responses to requests for the
vip_address, and therefore amphorae need to have interfaces plumbed on said
vip_address subnets which participate in ARP.

Note that this is somewhat problematic for active / standby virtual appliance
topologies because the vip_address for a given load balancer effectively
becomes a highly-available IP address (a true floating VIP), which means on
service failover from active to standby, the active amphora needs to
relinquish all the vip_addresses it has, and the standby needs to take them
over *and* start up haproxy services. This is OK if a given amphora
only has a few load balancers, but can lead to several minutes' down-time
during a graceful failover if there are a dozen or more load balancers on the
active/standby amphora pair. It's also more risky: The standby node might
not be able to start up all the haproxy services during such a
failover. What's more, most types of VRRP-like services which handle floating
IPs require amphorae to have an additional IP address on the subnet housing
the floating vip_address in order for the standby amphora to monitor the
active amphora.

Also note that in this topology, amphorae need an additional virtual network
interface plumbed when new front-end loadbalancer vip_addresses are assigned to
them which exist on subnets to which they don't already have access.

**Option 2: Routed (layer-3) connectivity**

In this layout, static routes are injected into the routing infrastructure
(Neutron) which essentially allow traffic destined for any given loadbalancer
vip_address to be routed to an IP address which lives on the amphora. (I
would recommend this be something other than the LB network IP.) In this
topology, it's actually important that the loadbalancer vip_address does *not*
exist in any subnet with potential front-end clients because in order for
traffic to reach the loadbalancer, it must pass through the routing
infrastructure (and in this case, front-end clients would attempt layer-2
connectivity to the vip_address).

This topology also works much better for active/standby configurations, because
both the active and standby amphorae can bind to the vip_addresses of all
their assigned loadbalancer objects on a dummy, non-ARPing interface, both can
be running all haproxy services at the same time, and keep the
standby server processes from interfering with active loadbalancer traffic
through the use of fencing scripts on the amphorae. Static routing is
accomplished to a highly available floating "routing IP" (using some VRRP-like
service for just this IP) which becomes the trigger for the fencing scripts on
the amphora. In this scenario, fail-overs are both much more reliable, and
can be accomplished in usually < 5 seconds.

Further, in this topology, amphorae do not need any additional virtual
interfaces plumbed when new front-end loadbalancer vip_addresses are assigned
to them.


Back-end topologies
-------------------
There are also two ways that amphorae can potentially talk to back-end
member IP addresses. Unlike the front-end topologies (where option 1 and option
2 are basically mutually exclusive, if not practically exclusive) both of these
types of connectivity can be used on a single amphora, and indeed, within a
single loadbalancer configuration.

**Option 1: Layer-2 connectivity**

This is layer-2 connectivity to back-end members, and is implied when a member
object has a subnet_id assigned to it. In this case, the existence of the
subnet_id implies amphorae need to have layer-2 connectivity to that subnet,
which means they need to have a virtual interface plumbed to it, as well as an
IP address on the subnet. This type of connectivity is useful for "secure"
back-end subnets that exist behind a NATing firewall where PAT is not in use on
the firewall. (In this way it effectively bypasses the firewall.) We anticipate
this will be the most common form of back-end connectivity in use by most
OpenStack users.

**Option 2: Routed (layer-3) connectivity**

This is routed connectivity to back-end members. This is implied when a member
object does not have a subnet_id specified. In this topology, it is assumed
that member ip_addresses are reachable through standard neutron routing, and
therefore connections to them can be initiated from the amphora's default
gateway. No new virtual interfaces need to be plumbed for this type of
connectivity to members.

