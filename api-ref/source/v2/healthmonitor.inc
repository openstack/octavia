.. -*- rst -*-

List Health Monitors
====================

.. rest_method:: GET /v2/lbaas/healthmonitors

Lists all health monitors for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to list health monitors for other projects.

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

.. literalinclude:: examples/healthmonitor-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - created_at: created_at
   - delay: healthmonitor-delay
   - expected_codes: healthmonitor-expected_codes
   - http_method: healthmonitor-http_method
   - id: healthmonitor-id
   - max_retries: healthmonitor-max-retries
   - max_retries_down: healthmonitor-max-retries-down
   - name: name
   - operating_status: operating_status
   - pool_id: pool-id
   - project_id: project_id
   - provisioning_status: provisioning_status
   - timeout: healthmonitor-timeout
   - type: healthmonitor-type
   - updated_at: updated_at
   - url_path: healthmonitor-url_path

Response Example
----------------

.. literalinclude:: examples/healthmonitors-list-response.json
   :language: javascript

Create Health Monitor
=====================

.. rest_method:: POST /v2/lbaas/healthmonitors

Creates a health monitor on a pool.

Health monitors define how the load balancer monitors backend servers
to determine if they are available to service requests.

This operation provisions a new health monitor by using the configuration that
you define in the request object. After the API validates the request and
starts the provisioning process, the API returns a response object that
contains a unique ID and the status of provisioning the health monitor.

In the response, the health monitor :ref:`provisioning status<prov_status>` is
``ACTIVE``, ``PENDING_CREATE``, or ``ERROR``.

If the status is ``PENDING_CREATE``, issue GET
``/v2/lbaas/healthmonitors/{healthmonitor_id}`` to view the progress of
the provisioning operation. When the health monitor status changes
to ``ACTIVE``, the health monitor is successfully provisioned and
is ready for further configuration.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

Specifying a project_id is deprecated.  The health monitor will inherit
the project_id of the parent load balancer.

At a minimum, you must specify these health monitor attributes:

- ``delay`` The interval, in seconds, between health checks.

- ``max_retries`` The number of successful checks before changing the
  operating status of the member to ONLINE.

- ``pool_id`` The pool to monitor.

- ``timeout`` The time, in seconds, after which a health check
  times out.

- ``type`` The type of health monitor. One of ``HTTP``, ``HTTPS``, ``PING``,
  ``TCP``, ``TLS-HELLO``, or ``UDP-CONNECT``.

Some attributes receive default values if you omit them from the request:

- ``admin_state_up`` The default is ``true``.

- ``expected_codes`` The expected HTTP status codes to get from a
  successful health check. The default is ``200``.

- ``http_method`` The default is ``GET``.

- ``max_retries_down`` The default is ``3``.

- ``url_path`` The default is ``/``.

To create a health monitor, the parent load balancer must have an ``ACTIVE``
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
   - delay: healthmonitor-delay
   - expected_codes: healthmonitor-expected_codes-optional
   - http_method: healthmonitor-http_method-optional
   - name: name-optional
   - max_retries: healthmonitor-max-retries
   - max_retries_down: healthmonitor-max-retries-down-optional
   - pool_id: pool-id
   - project_id: project_id-optional-deprecated
   - timeout: healthmonitor-timeout
   - type: healthmonitor-type
   - url_path: healthmonitor-url_path-optional

Request Example
----------------

.. literalinclude:: examples/healthmonitor-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/healthmonitor-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - created_at: created_at
   - delay: healthmonitor-delay
   - expected_codes: healthmonitor-expected_codes
   - http_method: healthmonitor-http_method
   - id: healthmonitor-id
   - max_retries: healthmonitor-max-retries
   - max_retries_down: healthmonitor-max-retries-down
   - name: name
   - operating_status: operating_status
   - pool_id: pool-id
   - project_id: project_id
   - provisioning_status: provisioning_status
   - timeout: healthmonitor-timeout
   - type: healthmonitor-type
   - updated_at: updated_at
   - url_path: healthmonitor-url_path

Response Example
----------------

.. literalinclude:: examples/healthmonitor-create-response.json
   :language: javascript

Show Health Monitor details
===========================

.. rest_method:: GET /v2/lbaas/healthmonitors/{healthmonitor_id}

Shows the details of a health monitor.

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
   - healthmonitor_id: path-healthmonitor-id

Curl Example
------------

.. literalinclude:: examples/healthmonitor-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - created_at: created_at
   - delay: healthmonitor-delay
   - expected_codes: healthmonitor-expected_codes
   - http_method: healthmonitor-http_method
   - id: healthmonitor-id
   - max_retries: healthmonitor-max-retries
   - max_retries_down: healthmonitor-max-retries-down
   - name: name
   - operating_status: operating_status
   - pool_id: pool-id
   - project_id: project_id
   - provisioning_status: provisioning_status
   - timeout: healthmonitor-timeout
   - type: healthmonitor-type
   - updated_at: updated_at
   - url_path: healthmonitor-url_path

Response Example
----------------

.. literalinclude:: examples/healthmonitor-show-response.json
   :language: javascript

Update a Health Monitor
=======================

.. rest_method:: PUT /v2/lbaas/healthmonitors/{healthmonitor_id}

Update an existing health monitor.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the update, check that the health monitor
provisioning status is ``ACTIVE``. If the status is ``PENDING_UPDATE``,
use a GET operation to poll the health monitor object for changes.

This operation returns the updated health monitor object with the
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
   - delay: healthmonitor-delay-optional
   - expected_codes: healthmonitor-expected_codes-optional
   - healthmonitor_id: path-healthmonitor-id
   - http_method: healthmonitor-http_method-optional
   - max_retries: healthmonitor-max-retries-optional
   - max_retries_down: healthmonitor-max-retries-down-optional
   - name: name-optional
   - timeout: healthmonitor-timeout-optional
   - url_path: healthmonitor-url_path-optional

Request Example
---------------

.. literalinclude:: examples/healthmonitor-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/healthmonitor-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - created_at: created_at
   - delay: healthmonitor-delay
   - expected_codes: healthmonitor-expected_codes
   - http_method: healthmonitor-http_method
   - id: healthmonitor-id
   - max_retries: healthmonitor-max-retries
   - max_retries_down: healthmonitor-max-retries-down
   - name: name
   - operating_status: operating_status
   - pool_id: pool-id
   - project_id: project_id
   - provisioning_status: provisioning_status
   - timeout: healthmonitor-timeout
   - type: healthmonitor-type
   - updated_at: updated_at
   - url_path: healthmonitor-url_path

Response Example
----------------

.. literalinclude:: examples/healthmonitor-update-response.json
   :language: javascript

Remove a Health Monitor
=======================

.. rest_method:: DELETE /v2/lbaas/healthmonitors/{healthmonitor_id}

Removes a health monitor and its associated configuration from the project.

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

   - healthmonitor_id: path-healthmonitor-id

Curl Example
------------

.. literalinclude:: examples/healthmonitor-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
