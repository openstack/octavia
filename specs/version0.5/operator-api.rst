..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Octavia Operator API Foundation
==========================================

https://blueprints.launchpad.net/octavia/+spec/operator-api

Octavia needs the foundation of the Operator API created.  This spec is not
meant to address every functionality needed in the operator API, only to
create a solid foundation to iterate on in the future.

Problem description
===================
This is needed because this will be the mechanism to actually communicate with
Octavia.  Doing CRUD operations on all entities will be needed ASAP so that the
system can be thoroughly tested.

Proposed change
===============
Expose Pecan resources
- Defined explicitly below in the REST API Impact

Create WSME types
- These will be responsible for request validation and deserialization, and
also response serialization

Setup paste deploy
- This will be used in the future to interact with keystone and other
middleware, however at first this will not have any authentication so
tenant_ids will just have to be made up uuids.

Create a handler interface and a noop logging implementation
- A handler interface will be created.  This abstraction layer is needed
because calling the controller in the resource layer will work for 0.5 but 1.0
will be sending it off to a queue.  With this abstraction layer we can easily
swap out a 0.5 controller with a 1.0 controller.

Call database repositories
- Most if not all resources will make a call to the database

Call handler
- Only create, update, and delete operations should call the handler

Alternatives
------------
None

Data model impact
-----------------
Will need to add some methods to the database repository

REST API impact
---------------
Exposed Resources and Methods

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

DELETE /loadbalancers/{lb_id}
* Successful Status Code - 202
* No response or request body

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

GET /loadbalancers?tenant_id
* Successful Status Code - 200
* tenant_id is an optional query parameter to filter by tenant_id
* returns a list of load balancers


POST /loadbalancers/{lb_id}/listeners
* Successful Status Code - 202
* JSON Request Body Attributes
** protocol - string enum - (TCP, HTTP, HTTPS) - required
** protocol_port - integer - required
** connection_limit - integer - optional
** default_tls_container_id - uuid - optional
** tenant_id - string - optional - default "0" * 36 (for now)
** name - string - optional - default null
** description - string - optional - default null
** enabled - boolean - optional - default true
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** protocol_port - integer
** connection_limit - integer
** default_tls_container_id - uuid
** tenant_id - string - optional
** name - string - optional
** description - string - optional
** enabled - boolean - optional
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

PUT /loadbalancers/{lb_id}/listeners/{listener_id}
* Successful Status Code - 202
* JSON Request Body Attributes
** protocol - string enum
** protocol_port - integer
** connection_limit - integer
** default_tls_container_id - uuid
** name - string
** description - string
** enabled - boolean
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** protocol_port - integer
** connection_limit - integer
** default_tls_container_id - uuid
** tenant_id - string - optional
** name - string - optional
** description - string - optional
** enabled - boolean - optional
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

DELETE /loadbalancers/{lb_id}/listeners/{listener_id}
* Successful Status Code - 202
* No response or request body

GET /loadbalancers/{lb_id}/listeners/{listener_id}
* Successful Status Code - 200
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** protocol_port - integer
** connection_limit - integer
** default_tls_container_id - uuid
** tenant_id - string - optional
** name - string - optional
** description - string - optional
** enabled - boolean - optional
** provisioning_status - string enum - (ACTIVE, PENDING_CREATE, PENDING_UPDATE,
PENDING_DELETE, DELETED, ERROR)
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

GET /loadbalancers/{lb_id}/listeners
* Successful Status Code - 200
* A list of listeners on load balancer lb_id


POST /loadbalancers/{lb_id}/listeners/{listener_id}/pools
* Successful Status Code - 202
* JSON Request Body Attributes
** protocol - string enum - (TCP, HTTP, HTTPS) - required
** lb_algorithm - string enum - (ROUND_ROBIN, LEAST_CONNECTIONS,
RANDOM) - required
** session_persistence - JSON object - optional
*** type - string enum - (SOURCE_IP, HTTP_COOKIE) - required
*** cookie_name - string - required for HTTP_COOKIE type
** tenant_id - string - optional - default "0" * 36 (for now)
** name - string - optional - default null
** description - string - optional - default null
** enabled - boolean - optional - default true
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** lb_algorithm - string enum - (ROUND_ROBIN, LEAST_CONNECTIONS, RANDOM)
** session_persistence - JSON object
*** type - string enum - (SOURCE_IP, HTTP_COOKIE)
*** cookie_name - string
** name - string
** description - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

PUT /loadbalancers/{lb_id}/listeners/{listener_id}/pools/{pool_id}
* Successful Status Code - 202
* JSON Request Body Attributes
** protocol - string enum - (TCP, HTTP, HTTPS)
** lb_algorithm - string enum - (ROUND_ROBIN, LEAST_CONNECTIONS, RANDOM)
** session_persistence - JSON object
*** type - string enum - (SOURCE_IP, HTTP_COOKIE)
*** cookie_name - string
** name - string
** description - string
** enabled - boolean
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** lb_algorithm - string enum - (ROUND_ROBIN, LEAST_CONNECTIONS, RANDOM)
** session_persistence - JSON object
*** type - string enum - (SOURCE_IP, HTTP_COOKIE)
*** cookie_name - string
** name - string
** description - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

DELETE /loadbalancers/{lb_id}/listeners/{listener_id}/pools/{pool_id}
* Successful Status Code - 202
No request or response body

GET /loadbalancers/{lb_id}/listeners/{listener_id}/pools/{pool_id}
* Successful Status Code - 200
* JSON Response Body Attributes
** id - uuid
** protocol - string enum - (TCP, HTTP, HTTPS)
** lb_algorithm - string enum - (ROUND_ROBIN, LEAST_CONNECTIONS, RANDOM)
** session_persistence - JSON object
*** type - string enum - (SOURCE_IP, HTTP_COOKIE)
*** cookie_name - string
** name - string
** description - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

GET /loadbalancers/{lb_id}/listeners/{listener_id}/pools
* Successful Status Code - 200
* Returns a list of pools


POST /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/healthmonitor
* Successful Status Code - 202
* JSON Request Body Attributes
** type - string enum - (HTTP, HTTPS, TCP) - required
** delay - integer - required
** timeout - integer - required
** fall_threshold - integer - required
** rise_threshold - integer - required
** http_method - string enum - (GET, POST, PUT, DELETE) - required for HTTP(S)
** url_path - string - required for HTTP(S)
** expected_codes - comma delimited string - required for HTTP(S)
** enabled - boolean - required - default true
* JSON Response Body Attributes
** type - string enum - (HTTP, HTTPS, TCP)
** delay - integer
** timeout - integer
** fall_threshold - integer
** rise_threshold - integer
** http_method - string enum - (GET, POST, PUT, DELETE)
** url_path - string
** expected_codes - comma delimited string
** enabled - boolean

PUT /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/healthmonitor
* Successful Status Code - 202
* JSON Request Body Attributes
** type - string enum - (HTTP, HTTPS, TCP)
** delay - integer
** timeout - integer
** fall_threshold - integer
** rise_threshold - integer
** http_method - string enum - (GET, POST, PUT, DELETE)
** url_path - string
** expected_codes - comma delimited string
** enabled - boolean
* JSON Response Body Attributes
** type - string enum - (HTTP, HTTPS, TCP)
** delay - integer
** timeout - integer
** fall_threshold - integer
** rise_threshold - integer
** http_method - string enum - (GET, POST, PUT, DELETE)
** url_path - string
** expected_codes - comma delimited string
** enabled - boolean

DELETE /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/healthmonitor
* Successful Status Code - 202
No request or response body

GET /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/healthmonitor
* Successful Status Code - 200
* JSON Response Body Attributes
** type - string enum - (HTTP, HTTPS, TCP)
** delay - integer
** timeout - integer
** fall_threshold - integer
** rise_threshold - integer
** http_method - string enum - (GET, POST, PUT, DELETE)
** url_path - string
** expected_codes - comma delimited string
** enabled - boolean


POST /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/members
* Successful Status Code - 202
* JSON Request Body Attributes
** ip_address - IP Address - required
** protocol_port - integer - required
** weight - integer - optional
** subnet_id - uuid - optional
** tenant_id - string - optional - default "0" * 36 (for now)
** enabled - boolean - optional - default true
* JSON Response Body Attributes
** id - uuid
** ip_address - IP Address
** protocol_port - integer
** weight - integer
** subnet_id - uuid
** tenant_id - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

PUT /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/members/{member_id}
* Successful Status Code - 202
* JSON Request Body Attributes
** protocol_port - integer - required
** weight - integer - optional
** enabled - boolean - optional - default true
* JSON Response Body Attributes
** id - uuid
** ip_address - IP Address
** protocol_port - integer
** weight - integer
** subnet_id - uuid
** tenant_id - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

DELETE /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/members/{member_id}
* Successful Status Code - 202
No request or response body

GET /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/members/{member_id}
* Successful Status Code - 200
* JSON Response Body Attributes
** id - uuid
** ip_address - IP Address
** protocol_port - integer
** weight - integer
** subnet_id - uuid
** tenant_id - string
** enabled - boolean
** operating_status - string enum - (ONLINE, OFFLINE, DEGRADED, ERROR)

GET /loadbalancers/{lb_id}/listeners/{listener_id}/
pools/{pool_id}/members
* Successful Status Code - 200
Returns a list of members

Security impact
---------------
No authentication with keystone

Notifications impact
--------------------
None

Other end user impact
---------------------
Not ready for end user

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
brandon-logan

Work Items
----------
Expose Pecan resources
Create WSME types
Setup paste deploy
Create a handler interface and a noop logging implementation
Call database repositories
Call handler

Dependencies
============
db-repositories

Testing
=======
Unit tests

Documentation Impact
====================
None

References
==========
None

