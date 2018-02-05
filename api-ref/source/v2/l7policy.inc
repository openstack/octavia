.. -*- rst -*-

List L7 Policies
================

.. rest_method:: GET /v2.0/lbaas/l7policies

Lists all L7 policies for the project.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

Administrative users can specify a project ID that is different than their own
to list L7 policies for other projects.

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

.. literalinclude:: examples/l7policies-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - action: l7policy-action
   - admin_state_up: admin_state_up
   - created_at: created_at
   - description: description
   - id: l7policy-id
   - listener_id: listener-id
   - name: name
   - operating_status: operating_status
   - position: l7policy-position
   - project_id: project_id
   - provisioning_status: provisioning_status
   - redirect_pool_id: l7policy-redirect-pool_id
   - redirect_url: l7policy-redirect-url
   - rules: l7policy-rule-ids
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/l7policies-list-response.json
   :language: javascript

Create an L7 Policy
===================

.. rest_method:: POST /v2.0/lbaas/l7policies

Creates a L7 policy.

This operation provisions a new L7 policy by using the
configuration that you define in the request object. After the API
validates the request and starts the provisioning process, the API
returns a response object that contains a unique ID and the status
of provisioning the L7 policy.

In the response, the L7 policy :ref:`provisioning status<prov_status>` is
``ACTIVE``, ``PENDING_CREATE``, or ``ERROR``.

If the status is ``PENDING_CREATE``, issue GET
``/v2.0/lbaas/l7policies/{l7policy_id}`` to view the progress of
the provisioning operation. When the L7 policy status changes
to ``ACTIVE``, the L7 policy is successfully provisioned and
is ready for further configuration.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

All the rules associated with a given policy are logically ANDed together. A
request must match all the policy's rules to match the policy.

If you need to express a logical OR operation between rules, then do this by
creating multiple policies with the same action.

If a new policy is created with a position that matches that of an existing
policy, then the new policy is inserted at the given position.

L7 policies with ``action`` of ``REDIRECT_TO_URL`` will return a HTTP
``Found (302)`` response code with the ``redirect_url``.

L7 policies with ``action`` of ``REJECT`` will return a ``Forbidden (403)``
response code to the requester.

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

   - action: l7policy-action
   - admin_state_up: admin_state_up-default-optional
   - description: description-optional
   - listener_id: listener-id
   - name: name-optional
   - position: l7policy-position-optional
   - project_id: project_id-optional
   - redirect_pool_id: l7policy-redirect-pool_id-optional
   - redirect_url: l7policy-redirect-url-optional

Request Example
----------------

.. literalinclude:: examples/l7policy-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/l7policy-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - action: l7policy-action
   - admin_state_up: admin_state_up
   - created_at: created_at
   - description: description
   - id: l7policy-id
   - listener_id: listener-id
   - name: name
   - operating_status: operating_status
   - position: l7policy-position
   - project_id: project_id
   - provisioning_status: provisioning_status
   - redirect_pool_id: l7policy-redirect-pool_id
   - redirect_url: l7policy-redirect-url
   - rules: l7policy-rule-ids
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/l7policy-create-response.json
   :language: javascript

Show L7 Policy details
==========================

.. rest_method:: GET /v2.0/lbaas/l7policies/{l7policy_id}

Shows the details of a L7 policy.

If you are not an administrative user and the L7 policy object does not
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
   - l7policy_id: path-l7policy-id

Curl Example
------------

.. literalinclude:: examples/l7policy-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - action: l7policy-action
   - admin_state_up: admin_state_up
   - created_at: created_at
   - description: description
   - id: l7policy-id
   - listener_id: listener-id
   - name: name
   - operating_status: operating_status
   - position: l7policy-position
   - project_id: project_id
   - provisioning_status: provisioning_status
   - redirect_pool_id: l7policy-redirect-pool_id
   - redirect_url: l7policy-redirect-url
   - rules: l7policy-rule-ids
   - updated_at: updated_at


Response Example
----------------

.. literalinclude:: examples/l7policy-show-response.json
   :language: javascript

Update a L7 Policy
==================

.. rest_method:: PUT /v2.0/lbaas/l7policies/{l7policy_id}

Updates a L7 policy.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the update, check that the L7 policy
provisioning status is ``ACTIVE``. If the status is
``PENDING_UPDATE``, use a GET operation to poll the L7 policy
object for changes.

This operation returns the updated L7 policy object with the
``ACTIVE``, ``PENDING_UPDATE``, or ``ERROR`` provisioning status.

If a policy is updated with a position that matches that of an existing
policy, then the updated policy is inserted at the given position.

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

   - action: l7policy-action-optional
   - admin_state_up: admin_state_up-default-optional
   - description: description-optional
   - l7policy_id: path-l7policy-id
   - name: name-optional
   - position: l7policy-position-optional
   - redirect_pool_id: l7policy-redirect-pool_id-optional
   - redirect_url: l7policy-redirect-url-optional

Request Example
---------------

.. literalinclude:: examples/l7policy-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/l7policy-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - action: l7policy-action
   - admin_state_up: admin_state_up
   - created_at: created_at
   - description: description
   - id: l7policy-id
   - listener_id: listener-id
   - name: name
   - operating_status: operating_status
   - position: l7policy-position
   - project_id: project_id
   - provisioning_status: provisioning_status
   - redirect_pool_id: l7policy-redirect-pool_id
   - redirect_url: l7policy-redirect-url
   - rules: l7policy-rule-ids
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/l7policy-update-response.json
   :language: javascript

Remove a L7 Policy
==================

.. rest_method:: DELETE /v2.0/lbaas/l7policies/{l7policy_id}

Removes a L7 policy and its associated configuration from the project.

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

   - l7policy_id: path-l7policy-id

Curl Example
------------

.. literalinclude:: examples/l7policy-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
