..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Vip QoS Policy Application
==========================


Problem description
===================
For real cases, the bandwidth of vip should be limited, because the upstream
network resource is provided by the ISP or other organizations. That means it
is not free. The openstack provider or users should pay for the limited
bandwidth, for example, users buy the 50M bandwidth from ISP for openstack
environment to access Internet, also it will be used for the connection outside
of openstack to access the servers in openstack. And the servers are behind
LoadBalance VIP. We cannot offer the whole bandwidth to the servers, as maybe
there also are the VMs want to access the external network. So we should take a
bandwidth limitation towards vip port.

Also, if the upstream network resource had been used up mostly, we still want
the backend servers behind loadbalancer are accessible and stable. The min
bandwidth limitation is needed for this scenario.

For more QoS functions, in reality, we can't limit our users or
deployers to use loadbalance default drivers, such as haproxy driver and
Octavia driver. They may be more concerned about the fields/functions related
to QoS, like DSCP markings. They could integrate the third-party drivers which
are concerned about these fields.


Proposed change
===============
This spec introduces the Neutron QoS function to meet the requirements.
Currently, there are 3 ports(at least) in the loadbalancer created by Octavia.
One is from the lb-mgmt-net, the others are from the vip-subnet, called
"loadbalancer-LOADBALANCER_ID" and "octavia-lb-vrrp-LOADBALNCER_ID". The first
one is vip port, the second one is for vrrp HA, and it will set
"allowed_address_pairs" toward vip fixed_ip. The QoS policy should focus on the
attached port "octavia-lb-vrrp-LOADBALNCER_ID".

We could apply the Neutron QoS policy to the "octavia-lb-vrrp-LOADBALNCER_ID"
ports, whether the topology is active-active or standalone.

There are the following changes:

* Extend a new column named "qos_policy_id" in vip table.
* Extend Octavia API, we need pass the vip-qos-policy-id which created in
  Neutron into LoadBalancer creation/update.
* Apply QoS policy on vip port in Loadbalancer working flow.

Alternatives
------------
We accept the QoS parameters and implement the QoS function on our own.

Data model impact
-----------------
In this spec, the QoS function will be provided by Neutron, so Octavia should
know the relationship of QoS policies and the vip port of Loadbalancers.
There will be some minor data model changes to Octavia in support of this
change.

* vip table
  - `qos_policy_id`: associate QoS policy id with vip port.

REST API impact
---------------

Proposed attribute::

        EXTEND_FIELDS = {
            'vip_qos_policy_id':{'allow_post': True, 'allow_put': True,
                                'validate': {'type:uuid': None},
                                'is_visible': True,
                                'default': None}
        }

The definition in Octavia is like::
        vip_qos_policy_id = wtypes.wsattr(wtypes.UuidType())

Some samples in Loadbalancer creation/update. Users allow pass
"vip_qos_policy_id".

Create/Update Loadbalancer Request::

        POST/PUT /v2.0/lbaas/loadbalancers
        {
            "loadbalancer": {
                "name": "loadbalancer1",
                "description": "simple lb",
                "project_id": "b7c1a69e88bf4b21a8148f787aef2081",
                "tenant_id": "b7c1a69e88bf4b21a8148f787aef2081",
                "vip_subnet_id": "013d3059-87a4-45a5-91e9-d721068ae0b2",
                "vip_address": "10.0.0.4",
                "admin_state_up": true,
                "flavor": "a7ae5d5a-d855-4f9a-b187-af66b53f4d04",
                "vip_qos_policy_id": "b61f8b45-e888-4056-94f0-e3d5af96211f"
            }
        }

        Response:
        {
            "loadbalancer": {
                "admin_state_up": true,
                "description": "simple lb",
                "id": "a36c20d0-18e9-42ce-88fd-82a35977ee8c",
                "listeners": [],
                "name": "loadbalancer1",
                "operating_status": "ONLINE",
                "provisioning_status": "ACTIVE",
                "project_id": "b7c1a69e88bf4b21a8148f787aef2081",
                "tenant_id": "b7c1a69e88bf4b21a8148f787aef2081",
                "vip_address": "10.0.0.4",
                "vip_subnet_id": "013d3059-87a4-45a5-91e9-d721068ae0b2",
                "flavor": "a7ae5d5a-d855-4f9a-b187-af66b53f4d04",
                "provider": "sample_provider",
                "pools": [],
                "vip_qos_policy_id": "b61f8b45-e888-4056-94f0-e3d5af96211f"
            }
        }


Security impact
---------------
None

Notifications impact
--------------------
No expected change.

Other end user impact
---------------------
Users will be able to specify qos_policy to create/update Loadbalancers.

Performance Impact
------------------
* It will be a very short time to cost in loadbalancer creation, as we need
  validate the input QoS policy.
* The QoS policy in Neutron side will affect the network performance based on
  the different types of QoS rules.

Other deployer impact
---------------------
None

Developer impact
----------------
TBD.

Implementation
==============

Assignee(s)
-----------
zhaobo
reedip

Work Items
----------
* Add the DB model and extend the table column.
* Extending Octavia V2 API to accept QoS policy.
* Add QoS application logic into Loadbalancer workflow.
* Add API validation code to validate access/existence of the qos_policy which
  created in Neutron.
* Add UTs to Octavia.
* Add API tests.
* Update CLI to accept QoS fields.
* Documentation work.

Dependencies
============
None

Testing
=======
Unit tests, Functional tests, API tests and Scenario tests are necessary.

Documentation Impact
====================
The Octavia API reference will need to be updated.

References
==========
