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
|                | ``/pools/{pool_id}/health_monitor``                       |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/health_monitor``                                       |
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
|                | ``/pools/{pool_id}/health_monitor``                       |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/health_monitor``                                       |
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
|                | ``/pools/{pool_id}/health_monitor``                       |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/health_monitor``                                       |
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
|                | ``/pools/{pool_id}/health_monitor``                       |
|                |                                                           |
|                | **DEPRECATED:** ``URL/v1/loadbalancers/{lb_id}``\         |
|                | ``/listeners/{listener_id}/pools/{pool_id}``\             |
|                | ``/health_monitor``                                       |
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
