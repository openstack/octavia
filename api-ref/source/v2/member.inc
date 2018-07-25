.. -*- rst -*-

List Members
============

.. rest_method:: GET /v2/lbaas/pools/{pool_id}/members

Lists all members for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to list members for other projects.

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
   - pool_id: path-pool-id
   - project_id: project_id_query

Curl Example
------------

.. literalinclude:: examples/members-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - address: address-member
   - admin_state_up: admin_state_up
   - backup: backup
   - created_at: created_at
   - id: member-id
   - monitor_address: monitor_address
   - monitor_port: monitor_port
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol_port: protocol_port-member
   - provisioning_status: provisioning_status
   - subnet_id: subnet_id
   - updated_at: updated_at
   - weight: weight

Response Example
----------------

.. literalinclude:: examples/members-list-response.json
   :language: javascript

Create Member
=============

.. rest_method:: POST /v2/lbaas/pools/{pool_id}/members

This operation provisions a member and adds it to a pool by using
the configuration that you define in the request object. After the
API validates the request and starts the provisioning process, it
returns a response object, which contains a unique ID.

In the response, the member :ref:`provisioning status<prov_status>` is
``ACTIVE``, ``PENDING_CREATE``, or ``ERROR``.

If the status is ``PENDING_CREATE``, issue GET
``/v2/lbaas/pools/{pool_id}/members/{member_id}`` to view the progress of
the provisioning operation. When the member status changes
to ``ACTIVE``, the member is successfully provisioned and
is ready for further configuration.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

At a minimum, you must specify these member attributes:

- ``address``. The IP address of the backend member to receive traffic from
  the load balancer.

- ``protocol_port`` The port on which the backend member listens for
  traffic.

Some attributes receive default values if you omit them from the
request:

- ``admin_state_up``. Default is ``true``.

- ``backup``. Default is ``false``.

- ``weight``. Default is ``1``.

If you omit the ``subnet_id`` parameter, the ``vip_subnet_id`` for the parent
load balancer will be used for the member subnet UUID.

The member ``address`` does not necessarily need to be a member of the
``subnet_id`` subnet.  Members can be routable from the subnet specified
either via the default route or by using ``host_routes`` defined on the subnet.

Administrative users can specify a project ID that is different than
their own to create members for other projects.

``monitor_address`` and/or ``monitor_port`` can be used to have the health
monitor, if one is configured for the pool, connect to an alternate IP address
and port when executing a health check on the member.

To create a member, the load balancer must have an ``ACTIVE``
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
   - address: address
   - backup: backup-optional
   - monitor_address: monitor_address-optional
   - monitor_port: monitor_port-optional
   - name: name-optional
   - pool_id: path-pool-id
   - project_id: project_id-optional-deprecated
   - protocol_port: protocol_port
   - subnet_id: subnet_id-optional
   - weight: weight-optional

Request Example
----------------

.. literalinclude:: examples/member-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/member-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - address: address-member
   - admin_state_up: admin_state_up
   - backup: backup
   - created_at: created_at
   - id: member-id
   - monitor_address: monitor_address
   - monitor_port: monitor_port
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol_port: protocol_port-member
   - provisioning_status: provisioning_status
   - subnet_id: subnet_id
   - updated_at: updated_at
   - weight: weight

Response Example
----------------

.. literalinclude:: examples/member-create-response.json
   :language: javascript

Show Member details
===================

.. rest_method:: GET /v2/lbaas/pools/{pool_id}/members/{member-id}

Shows the details of a pool member.

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
   - member_id: path-member-id
   - pool_id: path-pool-id

Curl Example
------------

.. literalinclude:: examples/member-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - address: address-member
   - admin_state_up: admin_state_up
   - backup: backup
   - created_at: created_at
   - id: member-id
   - monitor_address: monitor_address
   - monitor_port: monitor_port
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol_port: protocol_port-member
   - provisioning_status: provisioning_status
   - subnet_id: subnet_id
   - updated_at: updated_at
   - weight: weight

Response Example
----------------

.. literalinclude:: examples/member-show-response.json
   :language: javascript

Update a Member
===============

.. rest_method:: PUT /v2/lbaas/pools/{pool_id}/members/{member_id}

Update an existing member.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the update, check that the member provisioning
status is ``ACTIVE``. If the status is ``PENDING_UPDATE``, use a GET
operation to poll the member object for changes.

Setting the member weight to ``0`` means that the member will not receive
new requests but will finish any existing connections.  This "drains" the
backend member of active connections.

This operation returns the updated member object with the
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
   - backup: backup-optional
   - member_id: path-member-id
   - monitor_address: monitor_address-optional
   - monitor_port: monitor_port-optional
   - name: name-optional
   - pool_id: path-pool-id
   - weight: weight-optional

Request Example
---------------

.. literalinclude:: examples/member-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/member-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - address: address-member
   - admin_state_up: admin_state_up
   - backup: backup
   - created_at: created_at
   - id: member-id
   - monitor_address: monitor_address
   - monitor_port: monitor_port
   - name: name
   - operating_status: operating_status
   - project_id: project_id
   - protocol_port: protocol_port-member
   - provisioning_status: provisioning_status
   - subnet_id: subnet_id
   - updated_at: updated_at
   - weight: weight

Response Example
----------------

.. literalinclude:: examples/member-update-response.json
   :language: javascript

Batch Update Members
====================

.. rest_method:: PUT /v2/lbaas/pools/{pool_id}/members

Set the state of members for a pool in one API call. This may include
creating new members, deleting old members, and updating existing members.
Existing members are matched based on address/port combination.

For example, assume a pool currently has two members. These members have the
following address/port combinations: '192.0.2.15:80' and '192.0.2.16:80'.
Now assume a PUT request is made that includes members with address/port
combinations: '192.0.2.16:80' and '192.0.2.17:80'.
The member '192.0.2.15:80' will be deleted, because it was not in the request.
The member '192.0.2.16:80' will be updated to match the request data for that
member, because it was matched.
The member '192.0.2.17:80' will be created, because no such member existed.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the updates, check that the member provisioning
statuses are ``ACTIVE`` for new or updated members, and that any unspecified
members were correctly deleted. If the statuses are ``PENDING_UPDATE`` or
``PENDING_DELETE``, use GET to poll the member objects for changes.

.. rest_status_code:: success ../http-status.yaml

   - 202

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
   - address: address
   - backup: backup-optional
   - monitor_address: monitor_address-optional
   - monitor_port: monitor_port-optional
   - name: name-optional
   - pool_id: path-pool-id
   - project_id: project_id-optional-deprecated
   - protocol_port: protocol_port
   - subnet_id: subnet_id-optional
   - weight: weight-optional

Request Example
---------------

.. literalinclude:: examples/member-batch-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/member-batch-update-curl
   :language: bash

Response
--------

There is no body content for the response of a successful PUT request.

Remove a Member
===============

.. rest_method:: DELETE /v2/lbaas/pools/{pool_id}/members/{member_id}

Removes a member and its associated configuration from the pool.

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

   - member_id: path-member-id
   - pool_id: path-pool-id

Curl Example
------------

.. literalinclude:: examples/member-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
