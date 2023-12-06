..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Support SR-IOV network ports in Octavia
==========================================

The maximum performance of Octavia Amphora based load balancers is often
limited by the Software Defined Networking (SDN) used in the OpenStack
deployment. There are users that want very high connection rates and high
bandwidth through their load balancers.

This specification describes how we can add Single Root I/O Virtualization
(SR-IOV) support to Octavia Amphora load balancers.

Problem description
===================

* Users would like to use SR-IOV VFs for the VIP and member ports on their
  Amphora based load balancers for improved maximum performance and reduced
  latency. Initial testing showed a 9% increase in bandwidth and a 70% drop
  in latency through the load balancer when using SR-IOV.

* Users are overflowing tap interfaces with bursty "thundering herd" traffic
  such that packets are unable to make it into the Amphora instance.

Proposed change
===============

Since Octavia hot plugs the network interfaces into the Amphora instances, the
first work will be documenting how to configure nova to properly place the
Amphorae on hosts with the required hardware and networks. There is some
existing documentation for this in the nova guide, but we should summarize it
with a focus on Amphora.

This documentation will include how to configure host aggregates, the compute
flavor, and the Octavia flavor to properly schedule the Amphora instances.

In general, the SR-IOV ports will be handled the same as ports are with the
AAP driver, including registering the VIP as an AAP address even though this
is technically not required for SR-IOV ports, it will make sure the address is
allocated in neutron. Only the base VRRP ports will allocate an SR-IOV VF as
the AAP port will be "unbound" with a vnic_type of "normal".

The create load balancer flow creation will be enhanced to create the base VRRP
port using an SR-IOV VF if the Octavia flavor has SRIOV_VIP set to true. If
placement/nova scheduling fail to find an appropriate host or the SR-IOV VF
port fails to plug into the Amphora, additional logging may be required, but
the normal revert flows should continue to handle the error situation and mark
the load balancer in provisioning status ERROR.

The building of the listener create and update flows will need to be updated to
include extra tasks to configure nftables inside the Amphora to
replace the functionality of the neutron security groups lost when using
SR-IOV ports.

The Amphora agent will need to be enhanced for a new "security group" endpoint
and to configure the Amphora nftables. The nftables rules will be added as
stateless rules, meaning conntrack will not be enabled. The load balancing
engines are already managing state for the flows, so there is no reason to also
have state management in the firewall.

I am proposing we only support nftables inside the Amphora as most
distributions are moving away from iptables towards nftables.

Alternatives
------------

There are two obvious alternatives:

* Do nothing and continue to rely on SDN performance.

* Use provider networks to remove some of the overhead of the SDN.

It is not clear that SDN performance can improve to a level that would meet the
needs of Octavia Amphora load balancers and provider networks still have some
overhead and limitations depending on how they are implemented (tap interfaces,
etc.)

Data model impact
-----------------

The load balancer and member objects will be expanded to include the vnic type
for the ports.

REST API impact
---------------

The Octavia API will be expanded to include the vnic type used for the VIP and
member ports. The field with either be "normal" for OVS/OVN ports or "direct"
for SR-IOV ports. This field with use the same terminology as neutron uses.

The Amphora API will need to be expanded to have a security group endpoint.
This endpoint will accept POST calls that contain the: allowed_cidrs, protocol,
and port information required to configure the appropriate nftable rules.

When this endpoint is called, the amphora agent will flush the current tables
and build up a fresh table. There will be chains for the VIP, VRRP, and member
ports. This will be implemented using the python nftables bindings.

Security impact
---------------

Neutron security groups do not work on SR-IOV ports, so the amphora agent will
need to manage nftables for the SR-IOV ports.

There is no current use case where Octavia would need TRUST mode VFs, so this
specification does not include any discussion of enabling TRUST on VFs used by
the Octavia amphora driver. The amphora will treat TRUST VFs as if they were
not TRUST enabled.

Notifications impact
--------------------

None

Other end user impact
---------------------

End users will need to select the appropriate Octavia flavor at load balancer
creation time. They will also need to specify the proper network that matches
the network(s) defined in the compute and Octavia flavors.

Performance Impact
------------------

This proposal is specifically about improving data plane performance.

I would expect little change to the provisioning time, or possibly a faster
provisioning time, when using SR-IOV ports as it should require fewer API
calls to Neutron.

Other deployer impact
---------------------

If deployers want SR-IOV interface support at deployment time, they will need
to configure the required compute host aggregates, compute flavors, and
octavia flavor supporting the SR-IOV enabled hosts and networks.

We also recommend that the FDB L2 agent be enabled, when needed, so that
virtual ports on the same compute host can communicate with the SR-IOV ports.

The Amphora images will now require the nftables and python3-nftables packages.

Developer impact
----------------

There should be minimal developer impact as it is enhancing existing flows.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  johnsom

Work Items
----------

1. Document the required host aggregates, compute flavor, and Octavia flavor.
2. Update the load balancer "create" flow creation to use the SR-IOV tasks
   when creating the VRRP base ports.
3. Update the load balancer data model to store the port vnic type.
4. Expand the load balancer API to include the vnic type used for the VIP.
5. Update the listener create/update flows to add the extra tasks to configure
   the nftables inside the Amphora.
6. Add a security group endpoint to the Amphora agent to allow configuring and
   updating the nftables inside the Amphora.
7. Add any necessary logging and error handling should nova fail to attach
   SR-IOV ports.
8. Add the required unit and functional tests for the new code.
9. Add the required tempest tests to cover the usage scenarios (pending igb
   driver support in the PTI platforms)

Dependencies
============

None

Testing
=======

Currently this feature cannot fully be tested in the OpenDev gates as it will
require an SR-IOV capable nic in the test system.

There will be unit and function test coverage.

Recently qemu has added a virtual device, the "igb" device, that is capable of
emulating an SR-IOV device. Versions of qemu and the associated libraries that
include this new device are not yet shipping in any distribution supported by
OpenStack.

When the "igb" device becomes available, we should be able to run scenario
tests with SR-IOV VIP and member ports.

Performance testing will be out of scope because the OpenDev testing
environment does not contain SR-IOV capable NICs and is not setup for data
plane performance testing.

Documentation Impact
====================

An administrative document will need to be created that describes the process
required to setup a compute and octavia flavor for SR-IOV devices.

References
==========

* https://docs.openstack.org/neutron/latest/admin/config-sriov.html

* https://docs.openstack.org/nova/latest/reference/scheduler-hints-vs-flavor-extra-specs.html

* https://specs.openstack.org/openstack/nova-specs/specs/rocky/implemented/granular-resource-requests.html

* https://www.qemu.org/docs/master/system/devices/igb.html
