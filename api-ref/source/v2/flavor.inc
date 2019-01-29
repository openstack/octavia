.. -*- rst -*-

List Flavors
============

.. rest_method:: GET /v2.0/lbaas/flavors

List all available flavors.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

The list might be empty.

**New in version 2.6**

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

Curl Example
------------

.. literalinclude:: examples/flavor-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - flavor_profile_id: flavor-profile-id
   - flavors: flavors
   - id: flavor-id
   - name: name

Response Example
----------------

.. literalinclude:: examples/flavors-list-response.json
   :language: javascript

Create Flavor
=============

.. rest_method:: POST /v2.0/lbaas/flavors

Creates a flavor.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.6**

.. rest_status_code:: success ../http-status.yaml

   - 201

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - description: description-optional
   - enabled: enabled-optional
   - flavor: flavor
   - flavor_profile_id: flavor-profile-id
   - name: name

Request Example
----------------

.. literalinclude:: examples/flavor-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/flavor-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - flavor_profile_id: flavor-profile-id
   - flavor: flavor
   - id: flavor-id
   - name: name

Response Example
----------------

.. literalinclude:: examples/flavor-create-response.json
   :language: javascript


Show Flavor Details
===================

.. rest_method:: GET /v2.0/lbaas/flavors/{flavor_id}

Shows the details of a flavor.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

This operation does not require a request body.

**New in version 2.6**

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 401
   - 404
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - fields: fields
   - flavor_id: path-flavor-id

Curl Example
------------

.. literalinclude:: examples/flavor-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - flavor_profile_id: flavor-profile-id
   - flavor: flavor
   - id: flavor-id
   - name: name

Response Example
----------------

.. literalinclude:: examples/flavor-show-response.json
   :language: javascript

Update a Flavor
===============

.. rest_method:: PUT /v2.0/lbaas/flavors/{flavor_id}

Update a flavor.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.6**

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 404
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - description: description-optional
   - enabled: enabled-optional
   - flavor: flavor
   - flavor_id: path-flavor-id
   - name: name-optional

Request Example
---------------

.. literalinclude:: examples/flavor-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/flavor-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - flavor_profile_id: flavor-profile-id
   - flavor: flavor
   - id: flavor-id
   - name: name

Response Example
----------------

.. literalinclude:: examples/flavor-update-response.json
   :language: javascript

Remove a Flavor
===============

.. rest_method:: DELETE /v2.0/lbaas/flavors/{flavor_id}

Remove a flavor and its associated configuration.

If any load balancers are using this flavor the service returns the HTTP
``Conflict (409)`` response code.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.6**

.. rest_status_code:: success ../http-status.yaml

   - 204

.. rest_status_code:: error ../http-status.yaml

   - 401
   - 403
   - 404
   - 409
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - flavor_id: path-flavor-id

Curl Example
------------

.. literalinclude:: examples/flavor-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
