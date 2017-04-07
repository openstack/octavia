..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
LBaaS Alternative Monitoring IP/Port
==========================================

https://blueprints.launchpad.net/octavia/+spec/lbaas-health-monitoring-port

In the current state, the health monitor IP address/port pair is derived
from a load balancer's pool member's address and protocol port. In some use
cases it would be desirable to monitor a different IP address/port pair for
the health of a load balanced pool's member than the already specified address
and protocol port. Due to the current state this is not possible.

Problem description
===================

The use case where this would be desirable would be when the End User is
making the health monitor application on the member available on a IP/port
that is mutually exclusive to the IP/port of the application that is being load
balanced on the member. The End User would find this advantageous when
attempting to limit access to health diagnostic information by not allowing it
to be served over the main ingress IP/port of their application.

Beyond limiting access to any health APIs, it allows the End Users to design
different methods of health monitoring, such as creating distinct daemons
responsible for the health of their hosts applications.

Proposed change
===============

The creation of a pool member would now allow the specification of an IP
address and port to monitor health. The process used to assess the health
of pool members would now use this new IP address and port to diagnose the
member.

If a health monitor IP address or port is not specified the default behavior
would be to use the IP address and port specified by the member.

There would likely need to be some Horizon changes to support this feature,
however by maintaining the old behavior as the default we will not create
a strong dependency.

Alternatives
------------

An alternative is to not allow this functionality, and force all End Users
to ensure their health checks are available over the member's load balanced IP
address and protocol port.

As stated in the *Problem Description* this would force End Users to provide
additional security around their health diagnostic information so that they do
not expose it to unintended audiences. Pushing this requirement on the End User
is a heavier burden and limits their configuration options of the applications
they run on Openstack that are load balanced.

Data model impact
-----------------

The Member data model would gain two new member fields called monitor_port
and monitor_address. These two member fields would store the port and IP
address, respectively, that the monitor will query for the health of the load
balancer's listener's pool member.

It is important to have the default behavior fall back on the address and
protocol port of the member as this will allow any migrations to not break
existing deployments of Openstack.

Any Member data models without this new feature would have the fields default
to the value of null to signify that Octavia's LBaaS service should use the
member's protocol port to assess health status.

REST API impact
---------------

There are two APIs that will need to be modified, only slightly, to facilitate
this change.

.. csv-table:: Octavia LBaaS APIs
   :header: "Method", "URI"
   :widths: 15, 30

   "POST", "/v2.0/lbaas/pools/{pool_id}/members"
   "PUT", "/v2.0/lbaas/pools/{pool_id}/members/{member_id}"
   "GET", "/v2.0/lbaas/pools/{pool_id}/members/{member_id}"

The POST and PUT calls will need two additional fields added to their JSON body
data for the request and the JSON response data.

The GET call will need two additional fields as well, however they would only
be added to the JSON response data.

The fields to be added to each is:

.. csv-table:: Added Fields
    :header: "Attribute Name","Type", "Access", "Default Value","Validation Conversion","Description"

    monitor_port,int,"RW, all",null,int,health check port (optional)
    monitor_address,string,"RW, all",null,types.IPAddressType(),health check IP address (optional)

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

Other plugins do not have to implement this feature as it is optional due to
the default behavior. If they decide to implement this feature, they would just
need to supply the protocol port in their POSTs and PUTs to the health monitor
APIs.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  a.amerine

Other contributors:
  None

Work Items
----------

- Alter the Member Data Model
- Alter Pool Member APIs
- Update API reference documentation to reflect changes
- Write or Alter Unit, Functional, and Tempest Tests to verify new
  functionality


Dependencies
============

None


Testing
=======

Integration tests can be written to verify functionality. Generally, it should
only require an existing Openstack deployment that is running LBaaS to verify
health checks.


Documentation Impact
====================

The REST API impact will need to be addressed in documentation so developers
moving forward know about the feature and can use it.

References
==========

- Octavia Roadmap Considerations: Health monitoring on alternate IPs and/or
  ports (https://wiki.openstack.org/wiki/Octavia/Roadmap)
- RFE Port based HealthMonitor in neutron_lbaas
  (https://launchpad.net/bugs/1541579)
