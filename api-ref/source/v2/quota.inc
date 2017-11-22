.. -*- rst -*-

List Quota
==========

.. rest_method:: GET /v2.0/lbaas/quotas

Lists all quotas for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to list quotas for other projects.

If the quota is listed as ``null`` the quota is using the deployment default
quota settings.

A quota of ``-1`` means the quota is unlimited.

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

.. literalinclude:: examples/quotas-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - health_monitor: quota-health_monitor
   - listener: quota-listener
   - load_balancer: quota-load_balancer
   - member: quota-member
   - pool: quota-pool
   - project_id: project_id

Response Example
----------------

.. literalinclude:: examples/quotas-list-response.json
   :language: javascript

Show Quota Defaults
===================

.. rest_method:: GET /v2.0/lbaas/quotas/defaults

Show the quota defaults configured for the deployment.

A quota of ``-1`` means the quota is unlimited.

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 500

Request
-------

There are no request parameters for the show quota defaults API.

Curl Example
------------

.. literalinclude:: examples/quotas-defaults-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - health_monitor: quota-health_monitor
   - listener: quota-listener
   - load_balancer: quota-load_balancer
   - member: quota-member
   - pool: quota-pool

Response Example
----------------

.. literalinclude:: examples/quotas-defaults-response.json
   :language: javascript

Show Project Quota
==================

.. rest_method:: GET /v2.0/lbaas/quotas/{project_id}

Show the quota for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to show quota for other projects.

A quota of ``-1`` means the quota is unlimited.

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
   - project_id: path-project-id

Curl Example
------------

.. literalinclude:: examples/quota-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - health_monitor: quota-health_monitor
   - listener: quota-listener
   - load_balancer: quota-load_balancer
   - member: quota-member
   - pool: quota-pool

Response Example
----------------

.. literalinclude:: examples/quotas-show-response.json
   :language: javascript

Update a Quota
==============

.. rest_method:: PUT /v2.0/lbaas/quotas/{project_id}

Updates a quota for a project.

If the request is valid, the service returns the ``Accepted (202)``
response code.

This operation returns the updated quota object.

If the quota is specified as ``null`` the quota will use the deployment default
quota settings.

Specifying a quota of ``-1`` means the quota is unlimited.

Specifying a quota of ``0`` means the project cannot create any of the
resource.

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

   - health_monitor: quota-health_monitor-optional
   - listener: quota-listener-optional
   - load_balancer: quota-load_balancer-optional
   - member: quota-member-optional
   - pool: quota-pool-optional
   - project_id: path-project-id

Request Example
---------------

.. literalinclude:: examples/quota-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/quota-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - health_monitor: quota-health_monitor
   - listener: quota-listener
   - load_balancer: quota-load_balancer
   - member: quota-member
   - pool: quota-pool

Response Example
----------------

.. literalinclude:: examples/quota-update-response.json
   :language: javascript

Reset a Quota
=============

.. rest_method:: DELETE /v2.0/lbaas/quotas/{project_id}

Resets a project quota to use the deployment default quota.

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

   - project_id: path-project-id

Curl Example
------------

.. literalinclude:: examples/quota-reset-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.

