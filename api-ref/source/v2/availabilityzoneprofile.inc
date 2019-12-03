.. -*- rst -*-

List Availability Zone Profiles
===============================

.. rest_method:: GET /v2.0/lbaas/availabilityzoneprofiles

List all available Availability Zone Profiles.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

The list might be empty.

**New in version 2.14**

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

.. literalinclude:: examples/availabilityzoneprofile-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - availability_zone_data: availability-zone-data
   - availability_zone_profiles: availability-zone-profiles
   - id: availability-zone-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/availabilityzoneprofile-list-response.json
   :language: javascript

Create Availability Zone Profile
================================

.. rest_method:: POST /v2.0/lbaas/availabilityzoneprofiles

Creates a Availability Zone Profile.

If the API cannot fulfill the request due to insufficient data or
data that is not valid, the service returns the HTTP ``Bad Request
(400)`` response code with information about the failure in the
response body. Validation errors require that you correct the error
and submit the request again.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.14**

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

   - availability_zone_data: availability-zone-data
   - availability_zone_profile: availability-zone-profile
   - name: name
   - provider_name: provider-name

Request Example
---------------

.. literalinclude:: examples/availabilityzoneprofile-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/availabilityzoneprofile-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - availability_zone_data: availability-zone-data
   - availability_zone_profile: availability-zone-profile
   - id: availability-zone-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/availabilityzoneprofile-create-response.json
   :language: javascript

Show Availability Zone Profile Details
======================================

.. rest_method:: GET /v2.0/lbaas/availabilityzoneprofiles/{availability_zone_profile_id}

Shows the details of a Availability Zone Profile.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

This operation does not require a request body.

**New in version 2.14**

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
   - availability_zone_profile_id: path-availability-zone-profile-id

Curl Example
------------

.. literalinclude:: examples/availabilityzoneprofile-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - availability_zone_data: availability-zone-data
   - availability_zone_profile: availability-zone-profile
   - id: availability-zone-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/availabilityzoneprofile-show-response.json
   :language: javascript

Update a Availability Zone Profile
==================================

.. rest_method:: PUT /v2.0/lbaas/availabilityzoneprofiles/{availability_zone_profile_id}

Update a Availability Zone Profile.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.14**

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

   - availability_zone_data: availability-zone-data-optional
   - availability_zone_profile: availability-zone-profile
   - availability_zone_profile_id: path-availability-zone-profile-id
   - name: name-optional
   - provider_name: provider-name-optional

Request Example
---------------

.. literalinclude:: examples/availabilityzoneprofile-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/availabilityzoneprofile-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - availability_zone_data: availability-zone-data
   - availability_zone_profile: availability-zone-profile
   - id: availability-zone-profile-id
   - name: name
   - provider_name: provider-name

Response Example
----------------

.. literalinclude:: examples/availabilityzoneprofile-update-response.json
   :language: javascript

Remove a Availability Zone Profile
==================================

.. rest_method:: DELETE /v2.0/lbaas/availabilityzoneprofiles/{availability_zone_profile_id}

Remove a Availability Zone Profile and its associated configuration.

If any availability zone is using this Availability Zone Profile the service
returns the HTTP ``Conflict (409)`` response code.

If you are not an administrative user the service returns the HTTP ``Forbidden
(403)`` response code.

**New in version 2.14**

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

   - availability_zone_profile_id: path-availability-zone-profile-id

Curl Example
------------

.. literalinclude:: examples/availabilityzoneprofile-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
