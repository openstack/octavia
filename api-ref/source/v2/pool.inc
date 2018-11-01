.. -*- rst -*-

List Pools
==========

.. rest_method:: GET /v2/lbaas/pools

Lists all pools for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to list pools for other projects.

The list might be empty.

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - fields: fields
   - project_id: project_id_query

Curl Example
------------

.. literalinclude:: examples/pools-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - ca_tls_container_ref: ca_tls_container_ref
   - created_at: created_at
   - crl_container_ref: crl_container_ref
   - description: description
   - healthmonitor_id: healthmonitor-id
   - id: pool-id
   - lb_algorithm: lb-algorithm
   - listeners: listener-ids
   - loadbalancers: loadbalancer-ids
   - members: member-ids
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol: protocol-pools
   - provisioning_status: provisioning_status
   - session_persistence: session_persistence
   - tags: tags
   - tls_container_ref: tls_container_ref
   - tls_enabled: tls_enabled
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/pools-list-response.json
   :language: javascript

Create Pool
===========

.. rest_method:: POST /v2/lbaas/pools

Creates a pool for a load balancer.

The pool defines how requests should be balanced across the backend
member servers.

This operation provisions a pool by using the configuration that
you define in the request object. After the API validates the
request and starts the provisioning process, the API returns a
response object, which contains a unique ID.

In the response, the pool :ref:`provisioning status<prov_status>` is
``ACTIVE``, ``PENDING_CREATE``, or ``ERROR``.

If the status is ``PENDING_CREATE``, issue GET
``/v2/lbaas/pools/{pool_id}`` to view the progress of
the provisioning operation. When the pool status changes
to ``ACTIVE``, the pool is successfully provisioned and
is ready for further configuration.

At a minimum, you must specify these pool attributes:

- ``protocol`` The protocol for which this pool and its members
  listen. A valid value is ``HTTP``, ``HTTPS``, ``PROXY``, ``TCP``, or ``UDP``.

- ``lb_algorithm`` The load-balancer algorithm, such as
  ``ROUND_ROBIN``, ``LEAST_CONNECTIONS``, and ``SOURCE_IP``, that
  distributes traffic to the pool members. The load-balancer
  provider must support this algorithm.

- ``listener_id`` The ID of the listener in which this pool
  becomes the default pool. Each listener has only one default
  pool.

  ---OR---

- ``loadbalancer_id`` The ID of the load balancer under which this
  pool will be created.  Each load balancer can have zero or more pools
  associated with it.  These pools can be used for L7policies.

.. note::
   Either ``listener_id`` or ``loadbalancer_id`` must be specified.

Some attributes receive default values if you omit them from the
request:

- ``admin_state_up`` Default is ``true``.

- ``name`` Default is an empty string.

- ``description`` Default is an empty string.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

Specifying a project_id is deprecated.  The pool will inherit the
project_id of the parent load balancer.

You can configure all documented features of the pool at creation time by
specifying the additional elements or attributes in the request.

To create a pool, the parent load balancer must have an ``ACTIVE``
provisioning status.

.. rest_status_code:: success ../http-status.yaml

   - 201

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409
   - 500
   - 503

Request
-------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up-default-optional
   - ca_tls_container_ref: ca_tls_container_ref-optional
   - crl_container_ref: crl_container_ref-optional
   - description: description-optional
   - lb_algorithm: lb-algorithm
   - listener_id: listener-id-pool-optional
   - loadbalancer_id: loadbalancer-id-pool-optional
   - name: name-optional
   - project_id: project_id-optional-deprecated
   - protocol: protocol-pools
   - session_persistence: session_persistence-optional
   - tags: tags-optional
   - tls_enabled: tls_enabled-optional
   - tls_container_ref: tls_container_ref-optional

.. _session_persistence:

Pool Session Persistence
------------------------

Pool session persistence tells the load balancer to attempt to send future
requests from a client to the same backend member as the initial request.

When the pool has no session persistence, the session persistence object is
``null``.

Octavia currently support three session persistence methods:

+-----------------+----------------------------------------------------------+
| Method          | Description                                              |
+=================+==========================================================+
| ``APP_COOKIE``  | Use the specified ``cookie_name`` send future requests   |
|                 | to the same member.                                      |
+-----------------+----------------------------------------------------------+
| ``HTTP_COOKIE`` | The load balancer will generate a cookie that is         |
|                 | inserted into the response.  This cookie will be used to |
|                 | send future requests to the same member.                 |
+-----------------+----------------------------------------------------------+
| ``SOURCE_IP``   | The source IP address on the request will be hashed to   |
|                 | send future requests to the same member.                 |
+-----------------+----------------------------------------------------------+

Pool Session Persistence Object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. rest_parameters:: ../parameters.yaml

   - type: session_persistence_type
   - cookie_name: session_persistence_cookie
   - persistence_timeout: session_persistence_timeout
   - persistence_granularity: session_persistence_granularity

Pool Session Persistence Object Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: examples/pool-session-persistence-obj.json
   :language: javascript

Request Example
----------------

.. literalinclude:: examples/pool-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/pool-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - ca_tls_container_ref: ca_tls_container_ref
   - created_at: created_at
   - crl_container_ref: crl_container_ref
   - description: description
   - healthmonitor_id: healthmonitor-id
   - id: pool-id
   - lb_algorithm: lb-algorithm
   - listeners: listener-ids
   - loadbalancers: loadbalancer-ids
   - members: member-ids
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol: protocol-pools
   - provisioning_status: provisioning_status
   - session_persistence: session_persistence
   - tags: tags
   - tls_enabled: tls_enabled
   - tls_container_ref: tls_container_ref
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/pool-create-response.json
   :language: javascript

Show Pool details
=================

.. rest_method:: GET /v2/lbaas/pools/{pool_id}

Shows the details of a pool.

If you are not an administrative user and the parent load balancer does not
belong to your project, the service returns the HTTP ``Forbidden (403)``
response code.

This operation does not require a request body.

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 401
   - 403
   - 404
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - fields: fields
   - pool_id: path-pool-id

Curl Example
------------

.. literalinclude:: examples/pool-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - ca_tls_container_ref: ca_tls_container_ref
   - created_at: created_at
   - crl_container_ref: crl_container_ref
   - description: description
   - healthmonitor_id: healthmonitor-id
   - id: pool-id
   - lb_algorithm: lb-algorithm
   - listeners: listener-ids
   - loadbalancers: loadbalancer-ids
   - members: member-ids
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol: protocol-pools
   - provisioning_status: provisioning_status
   - session_persistence: session_persistence
   - tags: tags
   - tls_enabled: tls_enabled
   - tls_container_ref: tls_container_ref
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/pool-show-response.json
   :language: javascript

Update a Pool
=============

.. rest_method:: PUT /v2/lbaas/pools/{pool_id}

Update an existing pool.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the update, check that the pool provisioning
status is ``ACTIVE``. If the status is ``PENDING_UPDATE``, use a GET
operation to poll the pool object for changes.

This operation returns the updated pool object with the
``ACTIVE``, ``PENDING_UPDATE``, or ``ERROR`` provisioning status.

.. rest_status_code:: success ../http-status.yaml

   - 202

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up-default-optional
   - ca_tls_container_ref: ca_tls_container_ref-optional
   - crl_container_ref: crl_container_ref-optional
   - description: description-optional
   - lb_algorithm: lb-algorithm-optional
   - name: name-optional
   - pool_id: path-pool-id
   - session_persistence: session_persistence-optional
   - tags: tags-optional
   - tls_enabled: tls_enabled-optional
   - tls_container_ref: tls_container_ref-optional

Request Example
---------------

.. literalinclude:: examples/pool-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/pool-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - ca_tls_container_ref: ca_tls_container_ref
   - created_at: created_at
   - crl_container_ref: crl_container_ref
   - description: description
   - healthmonitor_id: healthmonitor-id
   - id: pool-id
   - lb_algorithm: lb-algorithm
   - listeners: listener-ids
   - loadbalancers: loadbalancer-ids
   - members: member-ids
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol: protocol-pools
   - provisioning_status: provisioning_status
   - session_persistence: session_persistence
   - tags: tags
   - tls_enabled: tls_enabled
   - tls_container_ref: tls_container_ref
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/pool-update-response.json
   :language: javascript

Remove a Pool
=============

.. rest_method:: DELETE /v2/lbaas/pools/{pool_id}

Removes a pool and its associated configuration from the load balancer.

The API immediately purges any and all configuration data, depending on the
configuration settings. You cannot recover it.

.. rest_status_code:: success ../http-status.yaml

   - 204

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 404
   - 409
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - pool_id: path-pool-id

Curl Example
------------

.. literalinclude:: examples/pool-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
