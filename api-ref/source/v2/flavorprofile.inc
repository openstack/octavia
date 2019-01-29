.. -*- rst -*-

List Flavor Profiles
====================

.. rest_method:: GET /v2.0/lbaas/flavorprofiles

List all available flavor profiles.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

The list might be empty.

**New in version 2.6**

.. rest_status_code:: success ../http-status.yaml

   - 200

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - fields: fields

Curl Example
------------

.. literalinclude:: examples/flavor-profile-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - flavor_data: flavor-data
   - flavorprofiles: flavorprofiles
   - id: flavor-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/flavorprofiles-list-response.json
   :language: javascript

Create Flavor Profile
=====================

.. rest_method:: POST /v2.0/lbaas/flavorprofiles

Creates a flavor profile.

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

   - flavor_data: flavor-data
   - flavorprofile: flavorprofile
   - name: name
   - provider_name: provider-name

Request Example
----------------

.. literalinclude:: examples/flavorprofile-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/flavorprofile-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - flavor_data: flavor-data
   - flavorprofile: flavorprofile
   - id: flavor-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/flavorprofile-create-response.json
   :language: javascript

Show Flavor Profile Details
===========================

.. rest_method:: GET /v2.0/lbaas/flavorprofiles/{flavorprofile_id}

Shows the details of a flavor profile.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

This operation does not require a request body.

**New in version 2.6**

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
   - flavorprofile_id: path-flavorprofile-id

Curl Example
------------

.. literalinclude:: examples/flavorprofile-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - flavor_data: flavor-data
   - flavorprofile: flavorprofile
   - id: flavor-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/flavorprofile-show-response.json
   :language: javascript

Update a Flavor Profile
=======================

.. rest_method:: PUT /v2.0/lbaas/flavorprofiles/{flavorprofile_id}

Update a flavor profile.

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

   - flavor_data: flavor-data-optional
   - flavorprofile: flavorprofile
   - flavorprofile_id: path-flavorprofile-id
   - name: name-optional
   - provider_name: provider-name-optional

Request Example
---------------

.. literalinclude:: examples/flavorprofile-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/flavorprofile-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - flavor_data: flavor-data
   - flavorprofile: flavorprofile
   - id: flavor-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/flavorprofile-update-response.json
   :language: javascript

Remove a Flavor Profile
=======================

.. rest_method:: DELETE /v2.0/lbaas/flavorprofiles/{flavorprofile_id}

Remove a flavor profile and its associated configuration.

If any flavors using this flavor profile the service returns the HTTP
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

   - flavorprofile_id: path-flavorprofile-id

Curl Example
------------

.. literalinclude:: examples/flavorprofile-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
