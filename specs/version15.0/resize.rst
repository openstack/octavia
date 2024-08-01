======================
Load balancer resizing
======================
Link to blueprint: https://blueprints.launchpad.net/octavia/+spec/octavia-resize-loadbalancer

This spec's goal is to describe the functionality of resizing of load
balancers. The main aim of this new feature is to enable you to change the
flavor directly from the API.

Problem description
===================
Today's users can't easily change the flavor. They have to recreate their load
balancer with the new flavor and migrate their configurations such as
l7 rules, listeners, etc.
This can be very tedious for a user who wants to quickly resize his load
balancer. It can be especially complicated to script.

Proposed change
===============
The proposed change would be to add an endpoint to allow load balancer
resizing. It would also be easy to cancel a resize in progress and return
to the previous flavor.

To achieve this, the endpoint will launch a workflow to initiate a failover
with the new flavor ID. This will involve patching the `get_failover_LB_flow`
to add the `flavorId` parameter. At the end of the workflow the `flavor_id`
will be updated in the `loadbalancer` table.

A check will be added before the start of the failover to prevent migration
to a flavor profile topology different from the original one. A user cannot
migrate from a flavorprofile standalone to active/passive.

If a problem occurs during resizing, the load balancer status will be set
to ERROR. The flavor will remain the same in database, allowing the user
to perform a failover or retry the same call.

Alternatives
------------
 * Rebuild the vm of the loadbalancer with the new flavor compute.
 * Use the "backup" and "restore".


Data model impact
-----------------
None


REST API impact
---------------
Add one endpoint in `/v2.0/lbaas/loadbalancers`.

To run this endpoint, the user must have the role `load-balancer:write"`.

Start a resize of a load balancer::

    PUT /v2.0/lbaas/loadbalancers/{loadbalancer_id}/resize

    {
        "new_flavor_id": "6d425a5e-429f-4848-b240-ab31c6d211e4"
    }

.. list-table:: Response code
    :widths: 15 50
    :header-rows: 1

    * - Code
      - Description
    * - 202 Accepted
      - Resize starting
    * - 400 Bad request
      - Resize object is invalid
    * - 401 Unauthorized
      - X-Auth-Token is invalid
    * - 403 Forbidden
      - X-Auth-Token is valid, but the associated project does not have
        the appropriate role/scope
    * - 404 Not Found
      - Load balancer not found

Security impact
---------------
None

Notifications impact
--------------------
Add a notification to announce a loadbalancer resize.

Other end user impact
---------------------
Add one command to launch resize in CLI client.

Start a resize: openstack loadbalancer resize \
                --flavor <flavor-id|flavor-name> \
                <lb-id|lb-name>

Add functions to resize in the `openstacksdk`.

Performance Impact
------------------
None


Other deployer impact
---------------------
None


Developer impact
----------------
None


Implementation
==============

Assignee(s)
-----------
TBD

Work Items
----------
 - Create endpoints
 - Patch the `get_failover_LB_flow` to add `flavorId` parameter.
 - Add unit tests
 - Add API functional tests
 - Add tempest tests
 - Update Octavia CLI and OpenstackSDK
 - Write Documentation

Dependencies
============
None

Testing
=======
Tempest tests should be added for testing this new feature:
 - Create a loadbalancer
 - Try to resize

Documentation Impact
====================
 - A user guide to explain how that works.
 - Add a note on the fact that some flavor changes can cause data plane
   downtime. Similarly, going from a newer image tag to an older one may
   cause failures or features to be disabled.

References
==========
None
