Octavia API
===========

Authentication
--------------

Using the version 1 API
-----------------------

For the purpose of examples, assume there is an Octavia API server running
at the URL ``http://octavia.example.com`` on the default port 80.

Note: Requests to update any resource on a load balancer in an immutable state
will fail with a response code ``409``.

Available Statuses on Entities
------------------------------

+---------------------+--------------------------------+
| Status type         | Statuses                       |
+---------------------+--------------------------------+
| Operating Status    | ``ONLINE``, ``OFFLINE``,       |
|                     | ``DEGRADED``, ``ERROR``,       |
|                     | ``NO_MONITOR``                 |
+---------------------+--------------------------------+
| Provisioning Status | ``ACTIVE``, ``DELETED``,       |
|                     | ``ERROR``, ``PENDING_DELETE``, |
|                     | ``PENDING_UPDATE``,            |
|                     | ``PENDING_CREATE``             |
+---------------------+--------------------------------+

Response Codes
--------------

- ``200`` - The synchronous request was successful

- ``202`` - The asynchronous request was accepted and is being processed

- ``400`` - The request could not be understood

  - Example:  Malformed JSON in request body

- ``401`` - Unauthorized: Access is denied due to invalid credentials

- ``404`` - The requested resource does not exist

- ``409`` - The request has a conflict with existing resources

  - Example:  Protocol for ``listener`` does not match protocol on ``pool``

- ``500`` - The request encountered an unexpected failure

Load Balancers
--------------

+-----------------------------------------------------------------------+
| **Fully Populated Load Balancer Object**                              |
+---------------------+------------+------------------------------------+
| Parameters          | Type       | Description                        |
+=====================+============+====================================+
| id                  | UUID       | Load Balancer ID                   |
+---------------------+------------+------------------------------------+
| vip                 | VIP Object | JSON VIP object below              |
+---------------------+------------+------------------------------------+
| project_id          | UUID       | ``UUID`` for project               |
+---------------------+------------+------------------------------------+
| name                | String     | String for load balancer name      |
+---------------------+------------+------------------------------------+
| description         | String     | String detailing information \     |
|                     |            | about the load balancer            |
+---------------------+------------+------------------------------------+
| enabled             | Boolean    | Whether or not the load \          |
|                     |            | balancer should be online \        |
|                     |            | immediately                        |
+---------------------+------------+------------------------------------+
| operating_status    | String     | Network status of a load balancer  |
+---------------------+------------+------------------------------------+
| provisioning_status | String     | Physical status of a load balancer |
+---------------------+------------+------------------------------------+

Virtual IP
**********
The following table lists the attributes of a VIP.  If only port_id is
provided then the network_id will be populated.  If only network_id is
provided then a port will be created and the port_id will be returned.
If an ip_address is provided then that IP will be attempted to be
assigned to the VIP as long as port_id or network_id is provided as well.

+----------------------------------------------------------------------+
| **Fully Populated VIP Object**                                       |
+------------------------+----------+----------------------------------+
| Parameters             | Type     | Description                      |
+========================+==========+==================================+
| ip_address             | IPv(4|6) | Frontend IP of load balancer     |
+------------------------+----------+----------------------------------+
| port_id                | UUID     | ``UUID`` for port                |
|                        |          | (equivalent to neutron port)     |
+------------------------+----------+----------------------------------+
| network_id             | UUID     | ``UUID`` for network             |
|                        |          | (equivalent to neutron subnet)   |
+------------------------+----------+----------------------------------+

List Load Balancers
*******************

Retrieve a list of load balancers.

+----------------+-------------------------------+
| Request Type   | ``GET``                       |
+----------------+-------------------------------+
| Endpoint       | ``URL/v1/loadbalancers``      |
+----------------+---------+---------------------+
|                | Success | 200                 |
| Response Codes +---------+---------------------+
|                | Error   | 400, 401, 404, 500  |
+----------------+---------+---------------------+

**Response Example**::



    [
        {
            'id': 'uuid',
            'vip': {
                'port_id': 'uuid',
                'network_id': 'uuid',
                'ip_address': '192.0.2.1'
            },
            'name': 'lb_name',
            'description': 'lb_description',
            'enabled': true,
            'provisioning_status': 'ACTIVE',
            'operating_status': 'ONLINE'
        }
    ]


List Load Balancer Details
**************************

Retrieve details of a load balancer.

+----------------+----------------------------------+
| Request Type   | ``GET``                          |
+----------------+----------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}`` |
+----------------+---------+------------------------+
|                | Success | 200                    |
| Response Codes +---------+------------------------+
|                | Error   | 401, 404, 500          |
+----------------+---------+------------------------+

**Response Example**::

    {
        'id': 'uuid',
        'vip':{
            'port_id': 'uuid',
            'network_id': 'uuid',
            'ip_address': '192.0.2.1'
        },
        'name': 'lb_name',
        'description': 'lb_description',
        'enabled': true,
        'provisioning_status': 'ACTIVE',
        'operating_status': 'ONLINE'
    }


Create Load Balancer
********************

Create a load balancer.

+----------------+------------------------------+
| Request Type   | ``POST``                     |
+----------------+------------------------------+
| Endpoint       | ``URL/v1/loadbalancers``     |
+----------------+---------+--------------------+
|                | Success | 202                |
| Response Codes +---------+--------------------+
|                | Error   | 400, 401, 404, 500 |
+----------------+---------+--------------------+

|

+------------------------+
| Request Parameters     |
+-------------+----------+
| Parameters  | Required |
+=============+==========+
| vip         | yes      |
+-------------+----------+
| project_id  | no       |
+-------------+----------+
| name        | no       |
+-------------+----------+
| description | no       |
+-------------+----------+
| enabled     | no       |
+-------------+----------+

**Request Example**::

    {
        'vip': {
            'subnet_id': 'uuid'
        },
        'name': 'lb_name',
        'description': 'lb_description',
    }

**Response Example**::

    {
        'id': 'uuid',
        'vip':{
            'port_id': 'uuid',
            'subnet_id': 'uuid',
            'ip_address': '192.0.2.1'
        },
        'name': 'lb_name',
        'description': 'lb_description',
        'enabled': true,
        'provisioning_status': 'PENDING_CREATE',
        'operating_status': 'OFFLINE'
    }


Create Fully Populated Load Balancer
++++++++++++++++++++++++++++++++++++

Create a load balancer including listeners, sni containers, pools,
health monitors, l7 policies, and l7 rules.

Refer to the appropriate objects details for available attributes.

**Request Example**::

    {
        'vip': {
            'subnet_id': 'uuid'
        },
        'name': 'lb_name',
        'description': 'lb_description',
        'listeners': [{
            'protocol': 'HTTP',
            'protocol_port': 80,
            'connection_limit': 10,
            'name': 'listener_name',
            'description': 'listener_description',
            'enabled': true,
            'l7policies': [{
                'action': 'REDIRECT_TO_POOL',
                'redirect_pool': {
                    'protocol': 'HTTP',
                    'lb_algorithm': 'ROUND_ROBIN',
                    'session_persistence': {
                       'type': 'HTTP_COOKIE',
                       'cookie_name': 'cookie_name'
                    },
                    'name': 'redirect_pool',
                    'description': 'redirect_pool_description',
                    'enabled': true
                }
            }],
            'default_pool': {
                'protocol': 'HTTP',
                'lb_algorithm': 'ROUND_ROBIN',
                'session_persistence': {
                   'type': 'HTTP_COOKIE',
                   'cookie_name': 'cookie_name'
                },
                'name': 'pool_name',
                'description': 'pool_description',
                'enabled': true,
                'members': [{
                    'ip_address': '10.0.0.1',
                    'protocol_port': 80,
                    'weight': 10,
                    'subnet_id': 'uuid',
                    'enabled': true
                }],
                'health_monitor':{
                    'type': 'HTTP',
                    'delay': 10,
                    'timeout': 10,
                    'fall_threshold': 10,
                    'rise_threshold': 10,
                    'http_method': 'GET',
                    'url_path': '/some/custom/path',
                    'expected_codes': '200',
                    'enabled': true
                }
            }
        }]
    }

**Response Example**::

    {
        'description': 'lb_description',
        'provisioning_status': 'PENDING_CREATE',
        'enabled': true,
        'listeners': [{
            'tls_certificate_id': null,
            'protocol': 'HTTP',
            'description': 'listener_description',
            'provisioning_status': 'PENDING_CREATE',
            'default_pool': {
                'lb_algorithm': 'ROUND_ROBIN',
                'protocol': 'HTTP',
                'description': 'pool_description',
                'health_monitor': {
                    'project_id': null,
                    'expected_codes': '200',
                    'enabled': true,
                    'delay': 10,
                    'fall_threshold': 10,
                    'http_method': 'GET',
                    'rise_threshold': 10,
                    'timeout': 10,
                    'url_path': '/some/custom/path',
                    'type': 'HTTP'
                },
                'enabled': true,
                'session_persistence': {
                    'cookie_name': 'cookie_name',
                    'type': 'HTTP_COOKIE'
                },
                'members': [{
                    'project_id': null,
                    'weight': 10,
                    'subnet_id': 'uuid',
                    'enabled': true,
                    'protocol_port': 80,
                    'ip_address': '10.0.0.1',
                    'id': 'uuid',
                    'operating_status': 'OFFLINE'
                }],
                'project_id': null,
                'id': 'uuid',
                'operating_status': 'OFFLINE',
                'name': 'pool_name'
            },
            'connection_limit': 10,
            'enabled': true,
            'project_id': null,
            'default_pool_id': 'uuid',
            'l7policies': [{
                'redirect_pool_id': 'uuid',
                'description': null,
                'redirect_pool': {
                    'lb_algorithm': 'ROUND_ROBIN',
                    'protocol': 'HTTP',
                    'description': 'redirect_pool_description',
                    'enabled': true,
                    'session_persistence': {
                        'cookie_name': 'cookie_name',
                        'type': 'HTTP_COOKIE'
                    },
                    'members': [],
                    'project_id': null,
                    'id': 'uuid',
                    'operating_status': 'OFFLINE',
                    'name': 'redirect_pool'
                },
                'l7rules': [],
                'enabled': true,
                'redirect_url': null,
                'action': 'REDIRECT_TO_POOL',
                'position': 1,
                'id': 'uuid',
                'name': null
            }],
            'sni_containers': [],
            'protocol_port': 80,
            'id': 'uuid',
            'operating_status': 'OFFLINE',
            'name': 'listener_name'
        }],
        'vip': {
            'subnet_id': 'uuid',
            'port_id': null,
            'ip_address': null
        },
        'project_id': null,
        'id': 'uuid',
        'operating_status': 'OFFLINE',
        'name': 'lb_name'
    }


Update Load Balancer
********************

Modify mutable fields of a load balancer.

+----------------+-----------------------------------+
| Request Type   | ``PUT``                           |
+----------------+-----------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``  |
+----------------+---------+-------------------------+
|                | Success | 202                     |
| Response Codes +---------+-------------------------+
|                | Error   | 400, 401, 404, 409, 500 |
+----------------+---------+-------------------------+

|

+-------------+----------+
| Parameters  | Required |
+=============+==========+
| name        | no       |
+-------------+----------+
| description | no       |
+-------------+----------+
| enabled     | no       |
+-------------+----------+

**Request Example**::

    {
        'name': 'diff_lb_name',
        'description': 'diff_lb_description',
        'enabled': false
    }

**Response Example**::

    {
        'id': 'uuid',
        'vip':{
            'port_id': 'uuid',
            'network_id': 'uuid',
            'ip_address': '192.0.2.1'
        },
        'name': 'diff_lb_name',
        'description': 'diff_lb_description',
        'enabled': true,
        'provisioning_status': 'PENDING_CREATE',
        'operating_status': 'OFFLINE'
    }

Delete Load Balancer
********************

Delete a load balancer.

+----------------+----------------------------------+
| Request Type   | ``DELETE``                       |
+----------------+----------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}`` |
+----------------+---------+------------------------+
|                | Success | 202                    |
| Response Codes +---------+------------------------+
|                | Error   | 401, 404, 409, 500     |
+----------------+---------+------------------------+

**No request/response body**

Delete Load Balancer Cascade
****************************

Delete a load balancer and all the underlying resources (e.g. listener, pool).

+----------------+-------------------------------------------------+
| Request Type   | ``DELETE``                                      |
+----------------+-------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/delete_cascade`` |
+----------------+---------+---------------------------------------+
|                | Success | 202                                   |
| Response Codes +---------+---------------------------------------+
|                | Error   | 401, 404, 409, 500                    |
+----------------+---------+---------------------------------------+

**No request/response body**


Listeners
---------

+------------------------------------------------------------------------+
| **Fully Populated Listener Object**                                    |
+---------------------+------------+-------------------------------------+
| Parameters          | Type       | Description                         |
+=====================+============+=====================================+
| id                  | UUID       | Listener ID                         |
+---------------------+------------+-------------------------------------+
| protocol            | String     | Network protocol from the \         |
|                     |            | following: ``TCP``, ``HTTP``, \     |
|                     |            | ``HTTPS``                           |
+---------------------+------------+-------------------------------------+
| protocol_port       | UUID       | Port the protocol will listen on    |
+---------------------+------------+-------------------------------------+
| connection_limit    | String     | Number of connections allowed at \  |
|                     |            | any given time                      |
+---------------------+------------+-------------------------------------+
| default_tls\        | String     | Barbican ``UUID`` for TLS container |
| _container_id       |            |                                     |
+---------------------+------------+-------------------------------------+
| default_pool_id     | UUID       | ``UUID`` of the pool to which \     |
|                     |            | requests will be routed by default  |
+---------------------+------------+-------------------------------------+
| project_id          | String     | ``UUID`` for project                |
+---------------------+------------+-------------------------------------+
| name                | String     | String detailing the name of the \  |
|                     |            | listener                            |
+---------------------+------------+-------------------------------------+
| description         | String     | String detailing information \      |
|                     |            | about the listener                  |
+---------------------+------------+-------------------------------------+
| enabled             | Boolean    | Whether or not the listener \       |
|                     |            | should be online immediately        |
+---------------------+------------+-------------------------------------+
| operating_status    | String     | Network status of a listener        |
+---------------------+------------+-------------------------------------+
| provisioning_status | String     | Physical status of a listener       |
+---------------------+------------+-------------------------------------+

List Listeners
**************

Retrieve a list of listeners.

+----------------+--------------------------------------------+
| Request Type   | ``GET``                                    |
+----------------+--------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners`` |
+----------------+---------+----------------------------------+
|                | Success | 200                              |
| Response Codes +---------+----------------------------------+
|                | Error   | 401, 404, 500                    |
+----------------+---------+----------------------------------+

**Response Example**::

   [
       {
           'tls_certificate_id': null,
           'protocol': 'HTTP',
           'description': 'listener_description',
           'provisioning_status': 'ACTIVE',
           'connection_limit': 10,
           'enabled': true,
           'sni_containers': [],
           'protocol_port': 80,
           'id': 'uuid',
           'operating_status': 'ONLINE',
           'name': 'listener_name',
           'default_pool_id': 'uuid'
       }
   ］

List Listener Details
*********************

Retrieve details of a listener.

+----------------+----------------------------------------------------------+
| Request Type   | ``GET``                                                  |
+----------------+----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners/{listener_id}`` |
+----------------+---------+------------------------------------------------+
|                | Success | 200                                            |
| Response Codes +---------+------------------------------------------------+
|                | Error   | 401, 404, 500                                  |
+----------------+---------+------------------------------------------------+

**Response Example**::

    {
         'tls_certificate_id': null,
         'protocol': 'HTTP',
         'description': 'listener_description',
         'provisioning_status': 'ACTIVE',
         'connection_limit': 10,
         'enabled': true,
         'sni_containers': [],
         'protocol_port': 80,
         'id': 'uuid',
         'operating_status': 'ONLINE',
         'name': 'listener_name',
         'default_pool_id': 'uuid'
    }

List Listener Statistics
************************

Retrieve the stats of a listener.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners/{listener_id}``\ |
|                | ``/stats``                                                |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'bytes_in': 1000,
        'bytes_out': 1000,
        'active_connections': 1,
        'total_connections': 1
    }

Create Listener
***************

Create a listener.

+----------------+--------------------------------------------+
| Request Type   | ``POST``                                   |
+----------------+--------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners`` |
+----------------+---------+----------------------------------+
|                | Success | 202                              |
| Response Codes +---------+----------------------------------+
|                | Error   | 400, 401, 404,409,500            |
+----------------+---------+----------------------------------+

|

+------------------+----------+
| Parameters       | Required |
+==================+==========+
| protocol         | yes      |
+------------------+----------+
| protocol_port    | yes      |
+------------------+----------+
| connection_limit | no       |
+------------------+----------+
| default_tls\     | no       |
| _container_id    |          |
+------------------+----------+
| project_id       | no       |
+------------------+----------+
| name             | no       |
+------------------+----------+
| description      | no       |
+------------------+----------+
| default_pool_id  | no       |
+------------------+----------+
| enabled          | no       |
+------------------+----------+

**Request Example**::

    {
        'protocol': 'HTTPS',
        'protocol_port': 88,
        'connection_limit': 10,
        'default_tls_container_id': 'uuid',
        'name': 'listener_name',
        'description': 'listener_description',
        'default_pool_id': 'uuid',
        'enabled': true
    }

**Response Example**::

   {
        'tls_certificate_id': null,
        'protocol': 'HTTPS',
        'description': 'listener_description',
        'provisioning_status': 'PENDING_CREATE',
        'connection_limit': 10,
        'enabled': true,
        'sni_containers': [],
        'protocol_port': 88,
        'id': 'uuid',
        'operating_status': 'OFFLINE',
        'name': 'listener_name',
        'default_pool_id': 'uuid'
   }

Update Listener
***************

Modify mutable fields of a listener.

+----------------+----------------------------------------------------------+
| Request Type   | ``PUT``                                                  |
+----------------+----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners/{listener_id}`` |
+----------------+---------+------------------------------------------------+
|                | Success | 202                                            |
| Response Codes +---------+------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                        |
+----------------+---------+------------------------------------------------+

|

+------------------+----------+
| Parameters       | Required |
+==================+==========+
| protocol         | no       |
+------------------+----------+
| protocol_port    | no       |
+------------------+----------+
| connection_limit | no       |
+------------------+----------+
| default_tls\     | no       |
| _container_id    |          |
+------------------+----------+
| name             | no       |
+------------------+----------+
| description      | no       |
+------------------+----------+
| default_pool_id  | no       |
+------------------+----------+
| enabled          | no       |
+------------------+----------+

**Request Example**::

    {
        'protocol': 'HTTPS',
        'protocol_port': 88,
        'connection_limit': 10,
        'default_tls_container_id': 'uuid',
        'name': 'listener_name',
        'description': 'listener_description',
        'default_pool_id': 'uuid',
        'enabled': true
    }

**Response Example**::

    {
        'tls_certificate_id': null,
        'protocol': 'HTTPS',
        'description': 'listener_description',
        'provisioning_status': 'ACTIVE',
        'connection_limit': 10,
        'enabled': true,
        'sni_containers': [],
        'protocol_port': 88,
        'id': 'uuid',
        'operating_status': 'ONLINE',
        'name': 'listener_name',
        'default_pool_id': 'uuid'
    }

Delete Listener
***************

Delete a listener.

+----------------+----------------------------------------------------------+
| Request Type   | ``DELETE``                                               |
+----------------+----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/listeners/{listener_id}`` |
+----------------+---------+------------------------------------------------+
|                | Success | 202                                            |
| Response Codes +---------+------------------------------------------------+
|                | Error   | 401, 404, 409, 500                             |
+----------------+---------+------------------------------------------------+

**No request/reponse body**

Pools
-----

+--------------------------------------------------------------------------+
| **Fully Populated Pool Object**                                          |
+---------------------+---------------+------------------------------------+
| Parameters          | Type          | Description                        |
+=====================+===============+====================================+
| id                  | UUID          | Pool ID                            |
+---------------------+---------------+------------------------------------+
| protocol            | String        | Network protocol from the \        |
|                     |               | following: ``TCP``, ``HTTP``, \    |
|                     |               | ``HTTPS``                          |
+---------------------+---------------+------------------------------------+
| lb_algorithm        | UUID          | Load balancing algorithm from \    |
|                     |               | the following: \                   |
|                     |               | ``LEAST_CONNECTIONS``, \           |
|                     |               | ``SOURCE_IP``, ``ROUND_ROBIN``     |
+---------------------+---------------+------------------------------------+
| session_persistence | Session \     | Number of connections allowed at \ |
|                     | Persistence \ | any given time                     |
|                     | Object        |                                    |
+---------------------+---------------+------------------------------------+
| name                | String        | String for pool name               |
+---------------------+---------------+------------------------------------+
| description         | String        | String detailing information \     |
|                     |               | about the pool                     |
+---------------------+---------------+------------------------------------+
| enabled             | Boolean       | Whether or not the pool \          |
|                     |               | should be online immediately       |
+---------------------+---------------+------------------------------------+

|

+---------------------------------------------------------------+
| **Fully Populated Session Persistence Object**                |
+-------------+--------+----------------------------------------+
| Parameters  | Type   | Description                            |
+-------------+--------+----------------------------------------+
| type        | String | Type of session persistence from the \ |
|             |        | following: HTTP_COOKIE, SOURCE_IP      |
+-------------+--------+----------------------------------------+
| cookie_name | String | The name of the cookie. (Only \        |
|             |        | required for HTTP_COOKIE)              |
+-------------+--------+----------------------------------------+

List Pools
**********

Retrieve a list of pools on a loadbalancer. This API endpoint
will list all pools on a loadbalancer or optionally all the active pools
on a listener, depending on whether the ``listener_id`` query string is
appended below.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoints      | ``URL/v1/loadbalancers/{lb_id}/pools``\                   |
|                | ``[?listener_id={listener_id}]``                          |
|                |                                                           |
|                | **DEPRECATED** ``URL/v1/loadbalancers/{lb_id}``\          |
|                | ``/listeners/{listener_id}/pools``                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    [
       {
           'id': 'uuid',
           'protocol': 'HTTP',
           'lb_algorithm': 'ROUND_ROBIN',
           'session_persistence': {
                'type': 'HTTP_COOKIE',
                'cookie_name': 'cookie_name'
           },
           'name': 'pool_name',
           'description': 'pool_description',
           'enabled': true,
           'operating_status': 'ONLINE'
       }
    ]

List Pool Details
*****************

Retrieve details of a pool.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/pools/{pool_id}``          |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``              |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'id': 'uuid',
        'protocol': 'HTTP',
        'lb_algorithm': 'ROUND_ROBIN',
        'session_persistence': {
            'type': 'HTTP_COOKIE',
            'cookie_name': 'cookie_name'
        },
        'name': 'pool_name',
        'description': 'pool_description',
        'enabled': true,
        'operating_status': 'ONLINE'
    }

Create Pool
***********

Create a pool.

+----------------+-----------------------------------------------------------+
| Request Type   | ``POST``                                                  |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/pools``                    |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools``                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 500                              |
+----------------+---------+-------------------------------------------------+

|

+--------------+----------+
| Parameters   | Required |
+==============+==========+
| protocol     | yes      |
+--------------+----------+
| lb_algorithm | yes      |
+--------------+----------+
| session\     | no       |
| _persistence |          |
+--------------+----------+
| name         | no       |
+--------------+----------+
| description  | no       |
+--------------+----------+
| enabled      | no       |
+--------------+----------+

**Request Example**::

    {
        'protocol': 'HTTP',
        'lb_algorithm': 'ROUND_ROBIN',
        'session_persistence': {
           'type': 'HTTP_COOKIE',
           'cookie_name': 'cookie_name'
        },
        'name': 'pool_name',
        'description': 'pool_description',
        'enabled': true
    }

**Response Example**::

    {
        'lb_algorithm': 'ROUND_ROBIN',
        'protocol': 'HTTP',
        'description': 'pool_description',
        'enabled': true,
        'session_persistence': {
            'cookie_name': 'cookie_name',
            'type': 'HTTP_COOKIE'
        },
        'id': 'uuid',
        'operating_status': 'OFFLINE',
        'name': 'pool_name'
    }

Update Pool
***********

Modify mutable attributes of a pool.

+----------------+-----------------------------------------------------------+
| Request Type   | ``PUT``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/pools/{pool_id}``          |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``              |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                         |
+----------------+---------+-------------------------------------------------+

|

+---------------------+----------+
| Parameters          | Required |
+=====================+==========+
| protocol            | no       |
+---------------------+----------+
| lb_algorithm        | yes      |
+---------------------+----------+
| session_persistence | no       |
+---------------------+----------+
| name                | no       |
+---------------------+----------+
| description         | no       |
+---------------------+----------+
| enabled             | no       |
+---------------------+----------+

**Request Example**::

    {
        'protocol': 'HTTP',
        'lb_algorithm': 'ROUND_ROBIN',
        'session_persistence': {
            'type': 'HTTP_COOKIE',
            'cookie_name': 'cookie_name'
        },
        'name': 'diff_pool_name',
        'description': 'pool_description',
        'enabled': true
    }

**Response Example**::

    {
        'id': 'uuid',
        'protocol': 'HTTP',
        'lb_algorithm': 'ROUND_ROBIN',
        'session_persistence': {
            'type': 'HTTP_COOKIE',
            'cookie_name': 'cookie_name'
        },
        'name': 'diff_pool_name',
        'description': 'pool_description',
        'enabled': true,
        'operating_status': 'ONLINE'
    }

Delete Pool
***********

Delete a pool.

+----------------+-----------------------------------------------------------+
| Request Type   | ``DELETE``                                                |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}/pools/{pool_id}``          |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``              |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 409, 500                              |
+----------------+---------+-------------------------------------------------+

**No request/reponse body**

Health Monitors
---------------

+-----------------------------------------------------------------+
| **Fully Populated Health Monitor Object**                       |
+----------------+---------+--------------------------------------+
| Parameters     | Type    | Description                          |
+================+=========+======================================+
| type           | String  | Type of health monitoring from \     |
|                |         | the following: ``PING``, ``TCP``, \  |
|                |         | ``HTTP``, ``HTTPS``                  |
+----------------+---------+--------------------------------------+
| delay          | Integer | Delay between health checks          |
+----------------+---------+--------------------------------------+
| timeout        | Integer | Timeout to decide whether or not \   |
|                |         | a health check fails                 |
+----------------+---------+--------------------------------------+
| fall_threshold | Integer | Number of health checks that can \   |
|                |         | pass before the pool member is \     |
|                |         | moved from ``ONLINE`` to ``OFFLINE`` |
+----------------+---------+--------------------------------------+
| rise_threshold | Integer | Number of health checks that can \   |
|                |         | pass before the pool member is \     |
|                |         | moved from ``OFFLINE`` to ``ONLINE`` |
+----------------+---------+--------------------------------------+
| http_method    | String  | HTTP protocol method to use for \    |
|                |         | the health check request             |
+----------------+---------+--------------------------------------+
| url_path       | String  | URL endpoint to hit for the \        |
|                |         | health check request                 |
+----------------+---------+--------------------------------------+
| expected_codes | String  | Comma separated list of expected \   |
|                |         | response codes during the health \   |
|                |         | check                                |
+----------------+---------+--------------------------------------+
| enabled        | Boolean | Enable/Disable health monitoring     |
+----------------+---------+--------------------------------------+

List Health Monitor Details
***************************

Retrieve details of a health monitor.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/healthmonitor``                        |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/healthmonitor``                                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'type': 'HTTP',
        'delay': 10,
        'timeout': 10,
        'fall_threshold': 10,
        'rise_threshold': 10,
        'http_method': 'GET',
        'url_path': '/some/custom/path',
        'expected_codes': '200',
        'enabled': true
    }

Create Health Monitor
*********************

Create a health monitor.

+----------------+-----------------------------------------------------------+
| Request Type   | ``POST``                                                  |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/healthmonitor``                        |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/healthmonitor``                                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 500                              |
+----------------+---------+-------------------------------------------------+

|

+----------------+----------+
| Parameters     | Required |
+================+==========+
| type           | yes      |
+----------------+----------+
| delay          | yes      |
+----------------+----------+
| timeout        | yes      |
+----------------+----------+
| fall_threshold | yes      |
+----------------+----------+
| rise_threshold | yes      |
+----------------+----------+
| http_method    | no       |
+----------------+----------+
| url_path       | no       |
+----------------+----------+
| expected_codes | no       |
+----------------+----------+
| enabled        | no       |
+----------------+----------+

**Request Example**::

    {
        'type': 'HTTP',
        'delay': 10,
        'timeout': 10,
        'fall_threshold': 10,
        'rise_threshold': 10,
        'http_method': 'GET',
        'url_path': '/some/custom/path',
        'expected_codes': '200',
        'enabled': true
    }

**Response Example**::

    {
        'type': 'HTTP',
        'delay': 10,
        'timeout': 10,
        'fall_threshold': 10,
        'rise_threshold': 10,
        'http_method': 'GET',
        'url_path': '/some/custom/path',
        'expected_codes': '200',
        'enabled': true
    }

Update Health Monitor
*********************

Modify mutable attributes of a health monitor.

+----------------+-----------------------------------------------------------+
| Request Type   | ``PUT``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/healthmonitor``                        |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/healthmonitor``                                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                         |
+----------------+---------+-------------------------------------------------+

|

+----------------+----------+
| Parameters     | Required |
+================+==========+
| type           | no       |
+----------------+----------+
| delay          | no       |
+----------------+----------+
| timeout        | no       |
+----------------+----------+
| fall_threshold | no       |
+----------------+----------+
| rise_threshold | no       |
+----------------+----------+
| http_method    | no       |
+----------------+----------+
| url_path       | no       |
+----------------+----------+
| expected_codes | no       |
+----------------+----------+
| enabled        | no       |
+----------------+----------+

**Request Example**::

    {
        'type': 'HTTP',
        'delay': 10,
        'timeout': 10,
        'fall_threshold': 10,
        'rise_threshold': 10,
        'http_method': 'GET',
        'url_path': '/some/custom/path',
        'expected_codes': '200',
        'enabled': true
    }

**Response Example**::

    {
        'type': 'HTTP',
        'delay': 10,
        'timeout': 10,
        'fall_threshold': 10,
        'rise_threshold': 10,
        'http_method': 'GET',
        'url_path': '/some/custom/path',
        'expected_codes': '200',
        'enabled': true
    }

Delete Health Monitor
*********************

Delete a health monitor.

+----------------+-----------------------------------------------------------+
| Request Type   | ``DELETE``                                                |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/healthmonitor``                        |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/healthmonitor``                                        |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 409, 500                              |
+----------------+---------+-------------------------------------------------+

Pool Members
------------

+-----------------------------------------------------------------+
| **Fully Populated Pool Member Object**                          |
+------------------+---------+------------------------------------+
| Parameters       | Type    | Description                        |
+==================+=========+====================================+
| id               | UUID    | Pool member ID                     |
+------------------+---------+------------------------------------+
| ip_address       | String  | IP address of the pool member      |
+------------------+---------+------------------------------------+
| protocol_port    | String  | Port for the protocol to listen on |
+------------------+---------+------------------------------------+
| weight           | String  | Weight of the pool member          |
+------------------+---------+------------------------------------+
| subnet_id        | UUID    | ``UUID`` of the subnet this pool \ |
|                  |         | member lives on                    |
+------------------+---------+------------------------------------+
| enabled          | Boolean | Whether or not the pool member \   |
|                  |         | should be online immediately       |
+------------------+---------+------------------------------------+
| operating_status | String  | Network status of the pool member  |
+------------------+---------+------------------------------------+

List Members
************

Retrieve a list of pool members.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/members``                              |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/members``                                              |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::


     [
        {
           'id': 'uuid',
           'ip_address': '10.0.0.1',
           'protocol_port': 80,
           'weight': 10,
           'subnet_id': 'uuid',
           'enabled': true,
           'operating_status': 'ONLINE'
        }
     ]

List Member Details
*******************

Retrieve details of a pool member.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/members/{member_id}``                  |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/members/{member_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'id': 'uuid',
        'ip_address': '10.0.0.1',
        'protocol_port': 80,
        'weight': 10,
        'subnet_id': 'uuid',
        'enabled': true,
        'operating_status': 'ONLINE'
    }

Create Member
*************

Create a pool member.

+----------------+-----------------------------------------------------------+
| Request Type   | ``POST``                                                  |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/members``                              |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/members``                                              |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 500                              |
+----------------+---------+-------------------------------------------------+

|

+---------------+----------+
| Parameters    | Required |
+===============+==========+
| ip_address    | yes      |
+---------------+----------+
| protocol_port | yes      |
+---------------+----------+
| weight        | yes      |
+---------------+----------+
| subnet_id     | no       |
+---------------+----------+
| enabled       | no       |
+---------------+----------+

**Request Example**::

    {
        'ip_address': '10.0.0.1',
        'protocol_port': 80,
        'weight': 10,
        'subnet_id': 'uuid',
        'enabled': true
    }

**Response Example**::

    {
        'id': 'uuid',
        'ip_address': '10.0.0.1',
        'protocol_port': 80,
        'weight': 10,
        'subnet_id': 'uuid',
        'enabled': true,
        'operating_status': 'ONLINE'
    }

Update Member
*************

Modify mutable attributes of a pool member.

+----------------+-----------------------------------------------------------+
| Request Type   | ``PUT``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/members/{member_id}``                  |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/members/{member_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                         |
+----------------+---------+-------------------------------------------------+

|

+---------------+----------+
| Parameters    | Required |
+===============+==========+
| protocol_port | no       |
+---------------+----------+
| weight        | no       |
+---------------+----------+
| enabled       | no       |
+---------------+----------+

**Request Example**::

    {
        'protocol_port': 80,
        'weight': 10,
        'enabled': true
    }

**Response Example**::

    {
        'id': 'uuid',
        'ip_address': '10.0.0.1',
        'protocol_port': 80,
        'weight': 10,
        'subnet_id': 'uuid',
        'enabled': true,
        'operating_status': 'ONLINE'
    }

Delete Member
*************

Delete a pool member.

+----------------+-----------------------------------------------------------+
| Request Type   | ``DELETE``                                                |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/pools/{pool_id}/members/{member_id}``                  |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/members/{member_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 409, 500                              |
+----------------+---------+-------------------------------------------------+

Layer 7 Policies
----------------
Layer 7 policies can be used to alter the behavior of the load balancing
service such that some action can be taken other than sending requests
to the listener's default_pool. If a given request matches all the layer 7
rules associated with a layer 7 policy, that layer 7 policy's action will
be taken instead of the default behavior.

+------------------------------------------------------------------------+
| **Fully Populated L7Policy Object**                                    |
+------------------+-------------+---------------------------------------+
| Parameters       | Type        | Description                           |
+==================+=============+=======================================+
| id               | UUID        | L7 Policy ID                          |
+------------------+-------------+---------------------------------------+
| name             | String      | String detailing the name of the \    |
|                  |             | l7policy                              |
+------------------+-------------+---------------------------------------+
| description      | String      | String detailing information \        |
|                  |             | about the l7policy                    |
+------------------+-------------+---------------------------------------+
| action           | String      | What action to take if the l7policy \ |
|                  |             | is matched                            |
+------------------+-------------+---------------------------------------+
| redirect_pool_id | UUID        | ID of the pool to which requests \    |
|                  |             | should be sent if action is \         |
|                  |             | ``REDIRECT_TO_POOL``                  |
+------------------+-------------+---------------------------------------+
| redirect_url     | String      | URL to which requests should be \     |
|                  |             | redirected if action is \             |
|                  |             | ``REDIRECT_TO_URL``                   |
+------------------+-------------+---------------------------------------+
| position         | Integer     | Sequence number of this L7 Policy. \  |
|                  |             | L7 Policies are evaluated in order \  |
|                  |             | starting with 1.                      |
+------------------+-------------+---------------------------------------+
| enabled          | Boolean     | Whether or not the l7policy \         |
|                  |             | should be online immediately          |
+------------------+-------------+---------------------------------------+

Layer 7 Policy actions

+----------------------+---------------------------------+
| L7 policy action     | Description                     |
+======================+=================================+
| ``REJECT``           | Requests matching this policy \ |
|                      | will be blocked.                |
+----------------------+---------------------------------+
| ``REDIRECT_TO_POOL`` | Requests matching this policy \ |
|                      | will be sent to the pool \      |
|                      | referenced by \                 |
|                      | ``redirect_pool_id``            |
+----------------------+---------------------------------+
| ``REDIRECT_TO_URL``  | Requests matching this policy \ |
|                      | will be redirected to the URL \ |
|                      | referenced by ``redirect_url``  |
+----------------------+---------------------------------+

List L7 Policies
****************

Retrieve a list of layer 7 policies.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies``                   |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    [
        {
            'id': 'uuid',
            'name': 'Policy Name',
            'description': 'Policy Description',
            'action': 'REDIRECT_TO_POOL',
            'redirect_pool_id': 'uuid',
            'redirect_url': None,
            'position': 1,
            'enabled': True,
        },
        {
            'id': 'uuid',
            'name': 'Policy Name 2',
            'description': 'Policy Description 2',
            'action': 'REDIRECT_TO_URL',
            'redirect_pool_id': None,
            'redirect_url': 'http://www.example.com',
            'position': 2,
            'enabled': True,
        }
    ]

List L7 Policy Details
**********************

Retrieve details of a layer 7 policy.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}``     |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'id': 'uuid',
        'name': 'Policy Name',
        'description': 'Policy Description',
        'action': 'REDIRECT_TO_POOL',
        'redirect_pool_id': 'uuid',
        'redirect_url': None,
        'position': 1,
        'enabled': True,
    }

Create Layer 7 Policy
*********************

Create a layer 7 policy.

+----------------+-----------------------------------------------------------+
| Request Type   | ``POST``                                                  |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies``                   |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 500                              |
+----------------+---------+-------------------------------------------------+

|

+------------------+----------------------------------------+
| Parameters       | Required                               |
+==================+========================================+
| name             | no                                     |
+------------------+----------------------------------------+
| description      | no                                     |
+------------------+----------------------------------------+
| action           | yes                                    |
+------------------+----------------------------------------+
| redirect_pool_id | only if action == ``REDIRECT_TO_POOL`` |
+------------------+----------------------------------------+
| redirect_url     | only if action == ``REDIRECT_TO_URL``  |
+------------------+----------------------------------------+
| position         | no (defaults to append to list)        |
+------------------+----------------------------------------+
| enabled          | no (defaults to ``True``)              |
+------------------+----------------------------------------+

**Request Example**::

    {
        'action': 'REDIRECT_TO_POOL',
        'redirect_pool_id': 'uuid'
    }

**Response Example**::

    {
        'id': 'uuid',
        'name': None,
        'description': None,
        'action': 'REDIRECT_TO_POOL',
        'redirect_pool_id': 'uuid',
        'redirect_url': None,
        'position': 1,
        'enabled': True
    }

Update Layer 7 Policy
*********************

Modify mutable attributes of a layer 7 policy.

+----------------+-----------------------------------------------------------+
| Request Type   | ``PUT``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}``     |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                         |
+----------------+---------+-------------------------------------------------+

|

+------------------+----------------------------------------+
| Parameters       | Required                               |
+==================+========================================+
| name             | no                                     |
+------------------+----------------------------------------+
| description      | no                                     |
+------------------+----------------------------------------+
| action           | no                                     |
+------------------+----------------------------------------+
| redirect_pool_id | only if action == ``REDIRECT_TO_POOL`` |
+------------------+----------------------------------------+
| redirect_url     | only if action == ``REDIRECT_TO_URL``  |
+------------------+----------------------------------------+
| position         | no                                     |
+------------------+----------------------------------------+
| enabled          | no                                     |
+------------------+----------------------------------------+

**Request Example**::

    {
        'action': 'REDIRECT_TO_URL',
        'redirect_url': 'http://www.example.com',
        'enabled': True
    }

**Response Example**::

    {
        'id': 'uuid',
        'name': None,
        'description': None,
        'action': 'REDIRECT_TO_URL',
        'redirect_pool_id': None,
        'redirect_url': 'http://www.example.com',
        'position': 1,
        'enabled': True
    }

Delete Layer 7 Policy
*********************

Delete a layer 7 policy.

+----------------+-----------------------------------------------------------+
| Request Type   | ``DELETE``                                                |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}``     |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 409, 500                              |
+----------------+---------+-------------------------------------------------+

Layer 7 Rules
-------------
Layer 7 rules are individual statements of logic which match parts of
an HTTP request, session, or other protocol-specific data for any given
client request. All the layer 7 rules associated with a given layer 7 policy
are logically ANDed together to see wether the policy matches a given client
request. If logical OR behavior is desired instead, the user should instead
create multiple layer 7 policies with rules which match each of the components
of the logical OR statement.

+------------------------------------------------------------------------+
| **Fully Populated L7Rule Object**                                      |
+------------------+-------------+---------------------------------------+
| Parameters       | Type        | Description                           |
+==================+=============+=======================================+
| id               | UUID        | L7 Rule ID                            |
+------------------+-------------+---------------------------------------+
| type             | String      | type of L7 rule (see chart below)     |
+------------------+-------------+---------------------------------------+
| compare_type     | String      | comparison type to be used with the \ |
|                  |             | value in this L7 rule (see chart \    |
|                  |             | below)                                |
+------------------+-------------+---------------------------------------+
| key              | String      | Header or cookie name to match if \   |
|                  |             | rule type is ``HEADER`` or ``COOKIE`` |
+------------------+-------------+---------------------------------------+
| value            | String      | value to be compared with             |
+------------------+-------------+---------------------------------------+
| invert           | Boolean     | inverts the logic of the rule if \    |
|                  |             | ``True`` (ie. perform a logical NOT \ |
|                  |             | on the rule)                          |
+------------------+-------------+---------------------------------------+

Layer 7 rule types

+----------------------+---------------------------------+--------------------+
| L7 rule type         | Description                     | Valid comparisons  |
+======================+=================================+====================+
| ``HOST_NAME``        | Matches against the http \      | ``REGEX``, \       |
|                      | Host: header in the request.    | ``STARTS_WITH``, \ |
|                      |                                 | ``ENDS_WITH``, \   |
|                      |                                 | ``CONTAINS``, \    |
|                      |                                 | ``EQUAL_TO``       |
+----------------------+---------------------------------+--------------------+
| ``PATH``             | Matches against the path \      | ``REGEX``, \       |
|                      | portion of the URL requested    | ``STARTS_WITH``, \ |
|                      |                                 | ``ENDS_WITH``, \   |
|                      |                                 | ``CONTAINS``, \    |
|                      |                                 | ``EQUAL_TO``       |
+----------------------+---------------------------------+--------------------+
| ``FILE_TYPE``        | Matches against the file name \ | ``REGEX``, \       |
|                      | extension in the URL requested  | ``EQUAL_TO``       |
+----------------------+---------------------------------+--------------------+
| ``HEADER``           | Matches against a specified \   | ``REGEX``, \       |
|                      | header in the request           | ``STARTS_WITH``, \ |
|                      |                                 | ``ENDS_WITH``, \   |
|                      |                                 | ``CONTAINS``, \    |
|                      |                                 | ``EQUAL_TO``       |
+----------------------+---------------------------------+--------------------+
| ``COOKIE``           | Matches against a specified \   | ``REGEX``, \       |
|                      | cookie in the request           | ``STARTS_WITH``, \ |
|                      |                                 | ``ENDS_WITH``, \   |
|                      |                                 | ``CONTAINS``, \    |
|                      |                                 | ``EQUAL_TO``       |
+----------------------+---------------------------------+--------------------+

Layer 7 rule comparison types

+----------------------+----------------------------------------------------+
| L7 rule compare type | Description                                        |
+======================+====================================================+
| ``REGEX``            | string will be evaluated against regular \         |
|                      | expression stored in ``value``                     |
+----------------------+----------------------------------------------------+
| ``STARTS_WITH``      | start of string will be compared against ``value`` |
+----------------------+----------------------------------------------------+
| ``ENDS_WITH``        | end of string will be compared against ``value``   |
+----------------------+----------------------------------------------------+
| ``CONTAINS``         | string contains ``value``                          |
+----------------------+----------------------------------------------------+
| ``EQUAL_TO``         | string is exactly equal to ``value``               |
+----------------------+----------------------------------------------------+

List L7 Rules
*************

Retrieve a list of layer 7 rules.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}`` \   |
|                | ``/l7rules``                                              |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    [
        {
            'id': 'uuid',
            'type': 'PATH',
            'compare_type': 'STARTS_WITH',
            'key': None,
            'value': '/api',
            'invert': False
        },
        {
            'id': 'uuid',
            'type': 'COOKIE',
            'compare_type': 'REGEX',
            'key': 'my-cookie',
            'value': 'some-value',
            'invert': True
        }
    ]

List L7 Rule Details
********************

Retrieve details of a layer 7 rule.

+----------------+-----------------------------------------------------------+
| Request Type   | ``GET``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}`` \   |
|                | ``/l7rules/{l7rule_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 200                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 500                                   |
+----------------+---------+-------------------------------------------------+

**Response Example**::

    {
        'id': 'uuid',
        'type': 'PATH',
        'compare_type': 'STARTS_WITH',
        'key': None,
        'value': '/api',
        'invert': False
    }

Create Layer 7 Rule
*******************

Create a layer 7 rule.

+----------------+-----------------------------------------------------------+
| Request Type   | ``POST``                                                  |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}`` \   |
|                | ``/l7rules``                                              |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 500                              |
+----------------+---------+-------------------------------------------------+

|

+----------------+------------------------------------------+
| Parameters     | Required                                 |
+================+==========================================+
| type           | yes                                      |
+----------------+------------------------------------------+
| compare_type   | yes                                      |
+----------------+------------------------------------------+
| key            | only if type is ``HEADER`` or ``COOKIE`` |
+----------------+------------------------------------------+
| value          | yes                                      |
+----------------+------------------------------------------+
| invert         | no (Defaults to ``False``)               |
+----------------+------------------------------------------+

**Request Example**::

    {
        'type': 'HOST_NAME',
        'compare_type': 'ENDS_WITH',
        'value': '.example.com'
    }

**Response Example**::

    {
        'id': 'uuid',
        'type': 'HOST_NAME',
        'compare_type': 'ENDS_WITH',
        'key': None,
        'value': '.example.com',
        'invert': False
    }

Update Layer 7 Rule
*******************

Modify mutable attributes of a layer 7 rule.

+----------------+-----------------------------------------------------------+
| Request Type   | ``PUT``                                                   |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}`` \   |
|                | ``/l7rules/{l7rule_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 400, 401, 404, 409, 500                         |
+----------------+---------+-------------------------------------------------+

|

+----------------+------------------------------------------+
| Parameters     | Required                                 |
+================+==========================================+
| type           | no                                       |
+----------------+------------------------------------------+
| compare_type   | no                                       |
+----------------+------------------------------------------+
| key            | only if type is ``HEADER`` or ``COOKIE`` |
+----------------+------------------------------------------+
| value          | no                                       |
+----------------+------------------------------------------+
| invert         | no                                       |
+----------------+------------------------------------------+

**Request Example**::

    {
        'type': 'HEADER',
        'compare_type': 'CONTAINS',
        'key': 'X-My-Header',
        'value': 'sample_substring'
    }

**Response Example**::

    {
        'id': 'uuid',
        'type': 'HEADER',
        'compare_type': 'CONTAINS',
        'key': 'X-My-Header',
        'value': 'sample_substring',
        'invert': False
    }

Delete Layer 7 Rule
*******************

Delete a layer 7 rule.

+----------------+-----------------------------------------------------------+
| Request Type   | ``DELETE``                                                |
+----------------+-----------------------------------------------------------+
| Endpoint       | ``URL/v1/loadbalancers/{lb_id}``\                         |
|                | ``/listeners/{listener_id}/l7policies/{l7policy_id}`` \   |
|                | ``/l7rules/{l7rule_id}``                                  |
+----------------+---------+-------------------------------------------------+
|                | Success | 202                                             |
| Response Codes +---------+-------------------------------------------------+
|                | Error   | 401, 404, 409, 500                              |
+----------------+---------+-------------------------------------------------+
