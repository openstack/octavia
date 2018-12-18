.. -*- rst -*-

List L7 Rules
=============

.. rest_method:: GET /v2/lbaas/l7policies/{l7policy_id}/rules

Lists all L7 rules for the project.

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
   - l7policy_id: path-l7policy-id
   - project_id: project_id_query

Curl Example
------------

.. literalinclude:: examples/l7rules-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - compare_type: l7rule-compare_type
   - created_at: created_at
   - id: l7rule-id
   - invert: l7rule-invert
   - key: l7rule-key
   - operating_status: operating_status
   - project_id: project_id
   - provisioning_status: provisioning_status
   - tags: tags
   - type: l7rule-type
   - updated_at: updated_at
   - value: l7rule-value

Response Example
----------------

.. literalinclude:: examples/l7rules-list-response.json
   :language: javascript

Create an L7 Rule
=================

.. rest_method:: POST /v2/lbaas/l7policies/{l7policy_id}/rules

Creates a L7 rule.

This operation provisions a new L7 rule by using the
configuration that you define in the request object. After the API
validates the request and starts the provisioning process, the API
returns a response object that contains a unique ID and the status
of provisioning the L7 rule.

In the response, the L7 rule :ref:`provisioning status<prov_status>` is
``ACTIVE``, ``PENDING_CREATE``, or ``ERROR``.

If the status is ``PENDING_CREATE``, issue GET
``/v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}`` to view the
progress of the provisioning operation. When the L7 rule status changes
to ``ACTIVE``, the L7 rule is successfully provisioned and
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
   - compare_type: l7rule-compare_type
   - invert: l7rule-invert-optional
   - key: l7rule-key-optional
   - l7policy_id: path-l7policy-id
   - project_id: project_id-optional
   - tags: tags-optional
   - type: l7rule-type
   - value: l7rule-value

Request Example
----------------

.. literalinclude:: examples/l7rule-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/l7rule-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - compare_type: l7rule-compare_type
   - created_at: created_at
   - id: l7rule-id
   - invert: l7rule-invert
   - key: l7rule-key
   - operating_status: operating_status
   - project_id: project_id
   - provisioning_status: provisioning_status
   - tags: tags
   - type: l7rule-type
   - updated_at: updated_at
   - value: l7rule-value

Response Example
----------------

.. literalinclude:: examples/l7rule-create-response.json
   :language: javascript

Show L7 Rule details
==========================

.. rest_method:: GET /v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}

Shows the details of a L7 rule.

If you are not an administrative user and the L7 rule object does not
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
   - l7rule_id: path-l7rule-id

Curl Example
------------

.. literalinclude:: examples/l7rule-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - compare_type: l7rule-compare_type
   - created_at: created_at
   - id: l7rule-id
   - invert: l7rule-invert
   - key: l7rule-key
   - operating_status: operating_status
   - project_id: project_id
   - provisioning_status: provisioning_status
   - tags: tags
   - type: l7rule-type
   - updated_at: updated_at
   - value: l7rule-value

Response Example
----------------

.. literalinclude:: examples/l7rule-show-response.json
   :language: javascript

Update a L7 Rule
================

.. rest_method:: PUT /v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}

Updates a L7 rule.

If the request is valid, the service returns the ``Accepted (202)``
response code. To confirm the update, check that the L7 rule
provisioning status is ``ACTIVE``. If the status is
``PENDING_UPDATE``, use a GET operation to poll the L7 rule
object for changes.

This operation returns the updated L7 rule object with the
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
   - compare_type: l7rule-compare_type-optional
   - invert: l7rule-invert-optional
   - key: l7rule-key-optional
   - l7policy_id: path-l7policy-id
   - l7rule_id: path-l7rule-id
   - tags: tags-optional
   - type: l7rule-type-optional
   - value: l7rule-value-optional

Request Example
---------------

.. literalinclude:: examples/l7rule-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/l7rule-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - admin_state_up: admin_state_up
   - compare_type: l7rule-compare_type
   - created_at: created_at
   - id: l7rule-id
   - invert: l7rule-invert
   - key: l7rule-key
   - operating_status: operating_status
   - project_id: project_id
   - provisioning_status: provisioning_status
   - tags: tags
   - type: l7rule-type
   - updated_at: updated_at
   - value: l7rule-value

Response Example
----------------

.. literalinclude:: examples/l7rule-update-response.json
   :language: javascript

Remove a L7 Rule
================

.. rest_method:: DELETE /v2/lbaas/l7policies/{l7policy_id}/rules/{l7rule_id}

Removes a L7 rule and its associated configuration from the project.

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
   - l7rule_id: path-l7rule-id

Curl Example
------------

.. literalinclude:: examples/l7rule-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
