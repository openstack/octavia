..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Support for Custom Security Groups for VIP Ports
================================================

This specification describes how Octavia can allow users to provide their own
Neutron Security Groups for the VIP Port of a load balancer.


Problem description
===================

Many users have requested a method for customizing the security groups of the
VIP ports of a load balancer in Octavia. There are some benefits from using
custom security groups:

* Allowing incoming connections only from specific remote group IDs.

* Having a unique API (The networking Security Groups API) to configure the
  network security for all the users' resources.

Note: The specification is not about Security Groups for the member ports, this
feature could be the subject of another spec.


Proposed change
===============

A user will be able to provide a ``vip_sg_ids`` parameter when creating a load
balancer.

This parameter will be optional and defaulted to None. When set, it contains a
list of Neutron Security Group IDs. When it's not set, the behavior of the VIP
port would not change.
In this document, these security groups are called Custom security
groups, as opposed to the existing Octavia-managed security groups.

If the parameter is set, Octavia would apply these Custom security
groups to the VIP and Amphora ports (known as VRRP ports internally). Then
Octavia would create and manage a security group (Octavia-managed security
group) with rules for its internal communication (haproxy peering, VRRP
communication). Thus the VIP port would have more than one Neutron security
group.

No rules based on the port or the protocol of the listeners would be managed by
Octavia, for each new listener, the user would have to add their own rules to
their Custom security groups.


Alternatives
------------

An alternative method would be to implement an ``allowed_remote_group_ids``
parameter when creating a load balancer. Users would have a feature that covers
the first point described in "Problem Description".


Data model impact
-----------------

This feature requires some changes in the data model, a new table
``VipSecurityGroup`` is added, it contains:

* ``load_balancer_id``: the UUID of the load balancer (which also represents a
  Vip)

* ``sg_id``: the UUID of a Custom Security Group

A load balancer (identified by its ID) or a VIP are linked to one or more
Custom Security Groups.

It also requires an update of the data model in octavia-lib.


REST API impact
---------------

The POST /v2/lbaas/loadbalancers endpoint is updated to accept an optional
``vip_sg_ids`` parameter (a list of UUIDs that represents Custom Security
Groups).

If the parameter is set, Octavia checks that the Custom security groups exist
and that the user is allowed to use them, then Octavia creates new
VIPSecurityGroup objects with these new parameters.

The PUT /v2/lbaas/loadbalancers endpoint is also updated, allowing to update
the list of Custom Security Groups.

The ``vip_sg_ids`` parameter is also added to the reply of the GET method.

Using ``vip_sg_ids`` is incompatible with some existing features in Octavia,
like ``allowed_cidrs`` in the listeners. Setting ``allowed_cidrs`` in a load
balancer with ``vip_sg_ids`` should be denied, updating the ``vip_sg_ids`` of a
load balancer that includes listeners with ``allowed_cidrs`` too.

``vip_sg_ids`` is also incompatible with SR-IOV enabled load balancers and
other provider drivers.


Security impact
---------------

When this feature is enabled, Octavia no longer handles the security of the VIP
port, the users are responsible of the configuration of the Custom Security
Groups.

A RBAC policy is added to Octavia, an administrator can limit the access to
this feature to a specific role.


Notifications impact
--------------------

None.


Other end user impact
---------------------

The impact for the end user is that they are responsible for allowing the
incomming traffic to their load balancer. The creation of a new listener would
request at least 2 API calls, one for creating the listener in Octavia, one for
adding a new security group rule to the Custom security group.


Performance Impact
------------------

Performance could be impacted if the user adds too many rules to the
Custom security group, but this issue is outside the scope of Octavia.


Other deployer impact
---------------------

None.


Developer impact
----------------

Impact is minimal, a few changes in the API and in the DB, only a few new
conditionals in the allowed_address_pairs module.

It could have a more significant impact if this feature is added to the
octavia-dashboard.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  gthiemonge


Work Items
----------

1. Update the data model of the VIP port in octavia_lib and octavia.
2. Update the API to handle the new ``vip_sg_id`` parameter.
3. Update the allowed_address_pairs module to handle this new feature.
4. Update the api-ref and the user guide.
5. Add required unit and functional tests.
6. Add support to python-octaviaclient and openstacksdk
7. Add tempest tests for this feature.


Dependencies
============

None.


Testing
=======

The feature can easily be tested with tempest tests.

- creation of a load balancer and its Custom security groups, check that
  it's reachable
- update the list of Custom security groups, check that the connectivity
  to the load balancer is impacted.


Documentation Impact
====================

The feature will be included in the cookbook.
The api-ref and feature matrix will be also updated.


References
==========

None.
