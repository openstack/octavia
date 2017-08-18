.. -*- rst -*-

This section introduces readers to OpenStack Octavia v2.0 ReSTful HTTP API and
provides guidelines on how to use it.

Service Endpoints
=================

All API calls described throughout the rest of this document require
authentication with the `OpenStack Identity service
<https://docs.openstack.org/keystone/latest/>`_. After authentication, the
base ``endpoint URL`` for the ``service type`` of ``load-balancer`` and
``service name`` of  ``octavia`` can be extracted from the service catalog
returned with the identity token.

**Example token snippet with service catalog**

.. code::

    {
        "token": {
            "catalog": [
                {
                    "endpoints": [
                        {
                            "url": "http://198.51.100.10:9876/",
                            "interface": "public",
                            "region": "RegionOne",
                            "region_id": "RegionOne",
                            "id": "cd1c3c2dc6434c739ed0a12015373754"
                        }
                    ],
                    "type": "load-balancer",
                    "id": "1209701aecd3453e9803119cd28cb013",
                    "name": "octavia"
                }
            ]
        }
    }


For instance, if the ``endpoint URL`` is ``http://198.51.100.10:9876/`` then
the full API call for ``/v2.0/lbaas/loadbalancers`` is
``http://198.51.100.10:9876/v2.0/lbaas/loadbalancers``.

Depending on the deployment, the ``load-balancer`` ``endpoint URL`` might be
http or https, a custom port, a custom path, and include your project id. The
only way to know the URLs for your deployment is by using the service catalog.
The ``load-balancer`` ``endpoint URL`` should never be hard coded in
applications, even if they are only expected to work at a single site. It
should always be discovered from the Identity token.

As such, for the rest of this document we will be using short hand where ``GET
/v2.0/lbaas/loadbalancers`` really means ``GET
{your_load-balancer_endpoint_URL}/v2.0/lbaas/loadbalancers``.

Neutron-lbaas and Octavia v2 APIs
=================================

The Octavia v2 API is fully backward compatible with the neutron-lbaas v2 API
and is a superset of the neutron-lbaas v2 API. This is intended to provide a
simple migration path for deployments currently using the neutron-lbaas v2 API.
You can update the endpoint your application is using from the keystone
service catalog to use the ``octavia`` endpoint instead of the ``neutron``
endpoint for load balancer activities.

During the neutron-lbaas deprecation period a pass-through proxy will be
included in neutron to allow requests via neutron and the neutron-lbaas v2 API
to continue to function.  Users are strongly encouraged to update their
applications to access load balancing via the Octavia v2 API.

.. warning::

   Load balancing functions accessed via the neutron endpoint are deprecated
   and will be removed in a future release. Users are strongly encouraged to
   migrate to using the octavia endpoint.

Authentication and authorization
================================

The Octavia API v2.0 uses the `OpenStack Identity service
<https://docs.openstack.org/keystone/latest/>`_ as the default authentication
service. When Keystone is enabled, users that submit requests to the Octavia
service must provide an authentication token in **X-Auth-Token** request
header. You obtain the token by authenticating to the Keystone endpoint.

When Keystone is enabled, the ``project_id`` attribute is not required in create
requests because the project ID is derived from the authentication token.

The default authorization settings allow only administrative users to create
resources on behalf of a different project.

Octavia uses information received from Keystone to authorize user requests.
Octavia Networking handles the following types of authorization policies:

-  **Operation-based policies** specify access criteria for specific
   operations, possibly with fine-grained control over specific attributes.

-  **Resource-based policies** access a specific resource. Permissions might or
   might not be granted depending on the permissions configured for the
   resource.  Currently available for only the network resource.

The actual authorization policies enforced in Octavia might vary from
deployment to deployment.

Request and response formats
============================

The Octavia API v2.0 supports JSON data serialization request and response
formats only.

Request format
--------------

The Octavia API v2.0 only accepts requests with the JSON data serialization
format. The ``Content-Type`` header is ignored.

Response format
---------------

The Octavia API v2.0 always responds with the JSON data serialization
format. The ``Accept`` header is ignored.

Query extension
    A ``.json`` extension can be added to the request URI. For example, the
    ``.json`` extension in the following requests are equivalent:

    - **GET** *publicURL*/loadbalancers

    - **GET** *publicURL*/loadbalancers.json

.. _filtering:

Filtering and column selection
==============================

The Octavia API v2.0 supports filtering based on all top level attributes of
a resource. Filters are applicable to all list requests.

For example, the following request returns all loadbalancers named ``foobar``:

.. code::

    GET /v2.0/lbaas/loadbalancers?name=foobar

When you specify multiple filters, the Octavia API v2.0 returns only objects
that meet all filtering criteria. The operation applies an AND condition among
the filters.

Note
----

Octavia does not offer an OR mechanism for filters.

Alternatively, you can issue a distinct request for each filter and build a
response set from the received responses on the client-side.

By default, Octavia returns all attributes for any show or list call. The
Octavia API v2.0 has a mechanism to limit the set of attributes returned.
For example, return ``id``.

You can use the ``fields`` query parameter to control the attributes returned
from the Octavia API v2.0.

For example, the following request returns only ``id`` and ``name`` for each
load balancer:

.. code::

    GET /v2.0/lbaas/loadbalancers.json?fields=id&fields=name

Synchronous versus asynchronous plug-in behavior
================================================

The Octavia API v2.0 presents a logical model of load balancers consisting
of listeners, pools, and members. It is up to the OpenStack Octavia plug-in
to communicate with the underlying infrastructure to ensure load balancing
is consistent with the logical model. A plug-in might perform these
operations asynchronously.

When an API client modifies the logical model by issuing an HTTP **POST**,
**PUT**, or **DELETE** request, the API call might return before the plug-in
modifies underlying virtual and physical load balancing devices. However, an
API client is guaranteed that all subsequent API calls properly reflect the
changed logical model.

For example, if a client issues an HTTP **PUT** request to set the weight
of a member, there is no guarantee that the new weight will be in effect when
the HTTP call returns. This is indicated by an HTTP response code of 202.

You can use the ``provisioning_status`` attribute to determine whether the
Octavia plug-in has successfully completed the configuration of the resource.

Bulk-create
===========

The Octavia v2.0 API does not support bulk create. You cannot create more than
one load balancer per API call.

The Octavia v2.0 API does support single call create which allows you to
create a fully populated load balancer in one API call. This is discussed
in the load balancer create section of this reference.

Pagination
==========

To reduce load on the service, list operations will return a maximum number of
items at a time. To navigate the collection, the parameters limit, marker and
page\_reverse can be set in the URI. For example:

.. code::

    ?limit=100&marker=1234&page_reverse=False

The ``marker`` parameter is the ID of the last item in the previous list. The
``limit`` parameter sets the page size. The ``page_reverse`` parameter sets
the page direction. These parameters are optional. If the client requests a
limit beyond the maximum limit configured by the deployment, the server returns
the maximum limit number of items.

For convenience, list responses contain atom "next" links and "previous" links.
The last page in the list requested with 'page\_reverse=False' will not contain
"next" link, and the last page in the list requested with 'page\_reverse=True'
will not contain "previous" link. The following examples illustrate two pages
with three items. The first page was retrieved through:

.. code::

    GET http://198.51.100.10:9876/v2.0/lbaas/loadbalancers.json?limit=2

If a particular plug-in does not support pagination operations the Octavia API
v2.0 will emulate the pagination behavior so that users can expect the same
behavior regardless of the particular plug-in running in the background.

**Example load balancer list, first page: JSON request**

.. code::

    GET /v2.0/lbaas/loadbalancers.json?limit=2 HTTP/1.1
    Host: 198.51.100.10:9876
    Content-Type: application/json
    Accept: application/json


**Example load balancer list, first page: JSON response**

.. code::

    {
        "loadbalancers": [
            {
                "admin_state_up": true,
                "listeners": [],
                "vip_subnet_id": "08dce793-daef-411d-a896-d389cd45b1ea",
                "pools": [],
                "provider": "octavia",
                "description": "Best App load balancer 1",
                "name": "bestapplb1",
                "operating_status": "ONLINE",
                "id": "34d5f4a5-cbbc-43a0-878f-b8a26370e6e7",
                "provisioning_status": "ACTIVE",
                "vip_port_id": "1e20d91d-8df9-4c15-9778-28bc89226c19",
                "vip_address": "203.0.113.10",
                "project_id": "bf325b04-e7b1-4002-9b10-f4984630367f"
            },
            {
                "admin_state_up": true,
                "listeners": [],
                "vip_subnet_id": "08dce793-daef-411d-a896-d389cd45b1ea",
                "pools": [],
                "provider": "octavia",
                "description": "Second Best App load balancer 1",
                "name": "2ndbestapplb1",
                "operating_status": "ONLINE",
                "id": "0fdb0ca7-0a38-4aea-891c-daaed40bcafe",
                "provisioning_status": "ACTIVE",
                "vip_port_id": "21f7ac04-6824-4222-93cf-46e0d70607f9",
                "vip_address": "203.0.113.20",
                "project_id": "bf325b04-e7b1-4002-9b10-f4984630367f"
            }
        ],
        "loadbalancers_links": [
            {
                "href": "http://198.51.100.10:9876/v2.0/lbaas/loadbalancers.json?limit=2&marker=0fdb0ca7-0a38-4aea-891c-daaed40bcafe",
                "rel": "next"
            },
            {
                "href": "http://198.51.100.10:9876/v2.0/lbaas/loadbalancers.json?limit=2&marker=34d5f4a5-cbbc-43a0-878f-b8a26370e6e7&page_reverse=True",
                "rel": "previous"
            }
        ]
    }


The last page won't show the "next" links

**Example load balancer list, last page: JSON request**

.. code::

    GET /v2.0/lbaas/loadbalancers.json?limit=2&marker=4ef465f3-0233-44af-b93d-9d3eae4daf85 HTTP/1.1
    Host: 198.51.100.10:9876
    Content-Type: application/json
    Accept: application/json



**Example load balancer list, last page: JSON response**

.. code::

    {
        "loadbalancers": [
            {
                "admin_state_up": true,
                "listeners": [],
                "vip_subnet_id": "08dce793-daef-411d-a896-d389cd45b1ea",
                "pools": [],
                "provider": "octavia",
                "description": "Other App load balancer 1",
                "name": "otherapplb1",
                "operating_status": "ONLINE",
                "id": "4ef465f3-0233-44af-b93d-9d3eae4daf85",
                "provisioning_status": "ACTIVE",
                "vip_port_id": "f777a1c7-7f59-4a36-ad34-24dfebaf19e6",
                "vip_address": "203.0.113.50",
                "project_id": "bf325b04-e7b1-4002-9b10-f4984630367f"
            }
        ],
        "loadbalancers_links": [
            {
                "href": "http://198.51.100.10:9876/v2.0/lbaas/loadbalancers.json?limit=2&marker=4ef465f3-0233-44af-b93d-9d3eae4daf85&page_reverse=True",
                "rel": "previous"
            }
        ]
    }


Sorting
=======

Sorting is determined through the use of the 'sort' query string parameter. The
value of this parameter is a comma-separated list of sort keys. Sort directions
can optionally be appended to each sort key, separated by the ':' character.

The supported sort directions are either 'asc' for ascending or 'desc' for
descending.

The caller may (but is not required to) specify a sort direction for each key.
If a sort direction is not specified for a key, then a default is set by the
server.

For example:

- Only sort keys specified:

  + ``sort=key1,key2,key3``
  + 'key1' is the first key, 'key2' is the second key, etc.
  + Sort directions are defaulted by the server

- Some sort directions specified:

  + ``sort=key1:asc,key2,key3``
  + Any sort key without a corresponding direction is defaulted
  + 'key1' is the first key (ascending order), 'key2' is the second key
    (direction defaulted by the server), etc.

- Equal number of sort keys and directions specified:

  + ``sort=key1:asc,key2:desc,key3:asc``
  + Each key is paired with the corresponding direction
  + 'key1' is the first key (ascending order), 'key2' is the second key
    (descending order), etc.

You can also use the ``sort_key`` and ``sort_dir`` parameters to sort the
results of list operations. Currently sorting does not work with extended
attributes of resource. The ``sort_key`` and ``sort_dir`` can be repeated,
and the number of ``sort_key`` and ``sort_dir`` provided must be same. The
``sort_dir`` parameter indicates in which direction to sort. Acceptable
values are ``asc`` (ascending) and ``desc`` (descending).

If a particular plug-in does not support sorting operations the Octavia API
v2.0 emulates the sorting behavior so that users can expect the same behavior
regardless of the particular plug-in that runs in the background.


Response Codes
==============

The following HTTP response status codes are used by the Octavia v2.0 API.

Success
-------

+------+----------------------------------------------------------------+
| Code | Description                                                    |
+======+================================================================+
| 200  | - The synchronous request was successful                       |
+------+----------------------------------------------------------------+
| 202  | - The asynchronous request was accepted and is being processed |
+------+----------------------------------------------------------------+
| 204  | - The request was successful, no content to return             |
|      | - The entity was successfully deleted                          |
+------+----------------------------------------------------------------+

Faults
------

The Octavia API v2.0 returns an error response if a failure occurs while
processing a request. Octavia uses only standard HTTP error codes.
4\ *nn* errors indicate problems in the particular request being sent from
the client.

+------+----------------------------------------------------------------+
| Code | Description                                                    |
+======+================================================================+
| 400  | - Bad request                                                  |
|      | - Malformed request URI or body requested                      |
|      | - The request could not be understood                          |
|      | - Invalid values entered                                       |
|      | - Bulk operations disallowed                                   |
|      | - Validation failed                                            |
|      | - Method not allowed for request body (such as trying to       |
|      |   update attributes that can be specified at create-time only) |
+------+----------------------------------------------------------------+
| 401  | - Unauthorized: Access is denied due to invalid credentials    |
+------+----------------------------------------------------------------+
| 403  | - Policy does not allow current user to do this operation      |
|      | - The project is over quota for the request                    |
+------+----------------------------------------------------------------+
| 404  | - Not Found                                                    |
|      | - Non existent URI                                             |
|      | - Resource not found                                           |
+------+----------------------------------------------------------------+
| 409  | - Conflict                                                     |
|      | - The resource is in an immutable state                        |
+------+----------------------------------------------------------------+
| 500  | - Internal server error                                        |
+------+----------------------------------------------------------------+
| 503  | - Service unavailable                                          |
|      | - The project is busy with other requests, try again later     |
+------+----------------------------------------------------------------+


Status Codes
============

Octavia API v2.0 entities have two status codes present in the response body.
The ``provisioning_status`` describes the lifecycle status of the entity while
the ``operating_status`` provides the observed status of the entity.

For example, a member may be in a ``provisioning_status`` of ``PENDING_UPDATE``
and have an ``operating_status`` of ``ONLINE``.  This would indicate that an
update operation is occurring on this member and it is in an immutable state
but it is healthy and able to service requests.  This situation could occur if
the user made a request to update the weight of the member.

.. _op_status:

Operating Status Codes
----------------------

+------------+--------------------------------------------------------------+
| Code       | Description                                                  |
+============+==============================================================+
| ONLINE     | - Entity is operating normally                               |
|            | - All pool members are healthy                               |
+------------+--------------------------------------------------------------+
| DRAINING   | - The member is not accepting new connections                |
+------------+--------------------------------------------------------------+
| OFFLINE    | - Entity is administratively disabled                        |
+------------+--------------------------------------------------------------+
| DEGRADED   | - One or more of the entity's components are in ERROR        |
+------------+--------------------------------------------------------------+
| ERROR      | - The entity has failed                                      |
|            | - The member is failing it's health monitoring checks        |
|            | - All of the pool members are in ERROR                       |
+------------+--------------------------------------------------------------+
| NO_MONITOR | - No health monitor is configured for this entity and it's   |
|            |   status is unknown                                          |
+------------+--------------------------------------------------------------+

.. _prov_status:

Provisioning Status Codes
-------------------------

+----------------+----------------------------------------------------------+
| Code           | Description                                              |
+================+==========================================================+
| ACTIVE         | - The entity was provisioned successfully                |
+----------------+----------------------------------------------------------+
| DELETED        | - The entity has been successfully deleted               |
+----------------+----------------------------------------------------------+
| ERROR          | - Provisioning failed                                    |
+----------------+----------------------------------------------------------+
| PENDING_CREATE | - The entity is being created                            |
+----------------+----------------------------------------------------------+
| PENDING_UPDATE | - The entity is being updated                            |
+----------------+----------------------------------------------------------+
| PENDING_DELETE | - The entity is being deleted                            |
+----------------+----------------------------------------------------------+

Entities in a ``PENDING_*`` state are immutable and cannot be modified until
the requested operation completes. The entity will return to the ``ACTIVE``
provisioning status once the asynchronus operation completes.

An entity in ``ERROR`` has failed provisioning. The entity may be deleted and
recreated.
