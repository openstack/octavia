..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========================================
Support for pool member update across pools
===========================================

Allow updating pool members across multiple pools with a single update request
(PUT).

Problem description
===================

At SAP cloud infrastructure (and probably in other places), Octavia load
balancers are often used to implement (Gardener) Kubernetes services; One
listener-pool pair is created per service port, and one member per pool per K8s
node.
When the Kubernetes nodes are updated one after another, each node needs to be
removed from the load balancer and then added again. This means node updates
cause many LB updates, at least one for every pool member in every pool. This
can mean hundreds of LB updates even when rolling the nodes only once. Each
update means the client has to wait for the Octavia provider driver to sync the
load balancer and set it to ACTIVE, before the next pool member can be updated.
For hundreds of pool members this can accumulate to an update time of an hour or
more.
The amount of update requests can be reduced to one by implementing support for
updating all pool members of a load balancer at the same time.

Proposed change
===============

Add new endpoint for batch-updating members across several pools, similar to
the existing endpoint for batch-updating members of a single pool.

This new endpoint behaves like the member batch update endpoint, but affects
members across several pools. It does *not* affect pools themselves, i.e.
you cannot add/remove or update pools with this new endpoint, only pool
members.


Alternatives
------------

1. Updating the load balancer for every single pool member in every single pool,
   for possibly hundred of pool members. As described above, this means waiting
   for the provider driver to sync the LB after each update, accumulating a lot
   of time, up to an hour or even more. This is the only current option.

2. Introducing a custom update logic in the provider driver, independent of the
   API, e. g. by sending one update per pool member, with a special flag (e. g.
   a special tag) in the update request that marks it as preliminary, so that
   the provider driver does not apply the update yet and instead sets the load
   balancer's provisioning status back to `ACTIVE` to allow the client to send
   more updates. Only when an update without the preliminary flag is received
   does the provider driver actually set the load balancer' provisioning status
   to `PENDING_UPDATE` and syncs the load balancer to the backend.
   This approach is hacky, unintuitive, and depends on the provider driver in
   use. Also, it does not reduce the amount of updates that need to be sent,
   only the time needed to wait for each update.

3. Use the existing "fully-populated load balancer" creation feature with a
   special token (e. g. a special tag) that denotes that a load balancer with a
   specified ID should be updated instead of creating a new one. This would also
   have to be handled by the provider driver, which would have to delete the
   load balancer database entry created by Octavia API, to then update the
   intended load balancer instead. This approach is just as hacky and provider
   driver dependent as the last one, but additionally introduces the possibility
   of the request being rejected, e. g. due to missing quota, even though it's
   not the intention to create a new load balancer.

Data model impact
-----------------

This change requires no modification to the data model. Octavia updates DB
entries for members just as it does with update requests to a single member and
batch update requests to members of a given pool.

REST API impact
---------------

This change adds new endpoint `/v2/lbaas/pools/members` for batch-updating
members across several pools, similar to the existing
`/v2/lbaas/pools/{pool_id}/members` `PUT` endpoint for batch-updating members
of a single pool.

The payload follows the same specification as the payload for the
`/v2/lbaas/pools/{pool_id}/members` `PUT` endpoint, except that every member
must include a `pool_id` field in order to identify which pool it belongs to.
Pool members are matched by their pool_id/IP/port combination (similar to how
the existing batch pool member update matches them by their IP/port
combination).
This means that - just like in the existing member batch update endpoint - pool
members not specified in the payload will be deleted, unless `additive_only` is
set to `true`.

No new API resources are being implemented, only existing API resources are
used.
