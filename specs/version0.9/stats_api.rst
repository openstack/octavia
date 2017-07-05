..
     This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================
Add statistics gathering API for loadbalancer
=============================================

https://blueprints.launchpad.net/octavia/+spec/stats-support

Problem description
===================
Currently, Octavia does not support the gathering of loadbalancer statistics.
This causes inconsistencies between the Octavia and Neutron-LBaaS APIs.
Another point is that the statistics data we get from the Octavia API for the
listener only reflects the first record for the listener in the Octavia
database, since we're supporting more topologies than SINGLE, this needs to
be to fixed too.

Proposed change
===============
Add one more data 'request_errors' to indicate the number of request errors
for each listener, we can get this data from the stats of haproxy 'ereq'.

Add a new module 'stats' to octavia.common with a class 'StatsMixin' to
do the actual statistics calculation for both listener and loadbalancer. Make
the mixin class as a new base class for
octavia.api.v1.controllers.listener_statistics.ListenerStatisticsController,
to make sure we get correct stats from Octavia API.

Add a new module 'loadbalancer_statistics' to octavia.api.v1.controllers with
a class LoadbalancerStatisticsController to provide a new REST API
for gathering statistics at the loadbalancer level.

Use evenstream to serialize the statistics messages from the octavia to
neutron-lbaas via oslo_messaging, to keep consistent with neutron-lbaas API.

Alternatives
------------
Update the 'stats' method in neutron-lbaas for octavia driver, allow the
neutron-lbaas to get stats from octavia through REST API request, to keep
consistent with neutron-lbaas API.

Data model impact
-----------------
One new column for table listener_statistics will be introduced to represent
request errors:

    +--------------------+-------------+------+-----+---------+-------+
    | Field              | Type        | Null | Key | Default | Extra |
    +--------------------+-------------+------+-----+---------+-------+
    | request_errors     | bigint(20)  | NO   |     | NULL    |       |
    +--------------------+-------------+------+-----+---------+-------+

REST API impact
---------------

Add 'request_errors' in the response of list listener statistics:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Example List listener statistics: JSON response**

.. code::

    {
        "listener": {
            "bytes_in": 0,
            "bytes_out": 0,
            "active_connections": 0,
            "total_connections": 0,
            "request_errors": 0
        }
    }

Add a new API to list loadbalancer statistics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lists loadbalancer statistics.

    +----------------+------------------------------------------------+
    | Request Type   | ``GET``                                        |
    +----------------+------------------------------------------------+
    | Endpoint       | ``URL/v1/loadbalancers/{lb_id}/stats``         |
    +----------------+---------+--------------------------------------+
    |                | Success | 200                                  |
    | Response Codes +---------+--------------------------------------+
    |                | Error   | 401, 404, 500                        |
    +----------------+---------+--------------------------------------+

**Example List loadbalancer statistics: JSON response**


.. code::

    {
        "loadbalancer": {
            "bytes_in": 0,
            "bytes_out": 0,
            "active_connections": 0,
            "total_connections": 0,
            "request_errors": 0,
            "listeners": [{
                "id": "uuid"
                "bytes_in": 0,
                "bytes_out": 0,
                "active_connections": 0,
                "total_connections": 0,
                "request_errors": 0,
            }]
        }
    }

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
None

Implementation
==============

Assignee(s)
-----------
li, chen <shchenli@cn.ibm.com>

Work Items
----------
* Extend current stats collection for listener amphora
* Add module 'stats'
* Add new API for gathering statistics at the loadbalancer level
* Update stats to neutron database

Dependencies
============
None

Testing
=======
Function tests with tox.

Documentation Impact
====================
Changes shall be introduced to the octavia APIs: see [1]

References
==========
[1] https://developer.openstack.org/api-ref/load-balancer/v1/octaviaapi.html
