.. -*- rst -*-

List Availability Zones
=======================

.. rest_method:: GET /v2.0/lbaas/availabilityzones

List all available availability zones.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

The list might be empty.

**New in version 2.14**

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

.. literalinclude:: examples/availabilityzone-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - availability_zone_profile_id: availability-zone-profile-id
   - availability_zones: availability-zones
   - name: name

Response Example
----------------

.. literalinclude:: examples/availabilityzone-list-response.json
   :language: javascript

Create Availability Zone
========================

.. rest_method:: POST /v2.0/lbaas/availabilityzones

Creates an availability zone.

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

   - description: description-optional
   - enabled: enabled-optional
   - availability_zone: availability_zone
   - availability_zone_profile_id: availability-zone-profile-id
   - name: name

Request Example
---------------

.. literalinclude:: examples/availabilityzone-create-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/availabilityzone-create-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - availability_zone_profile_id: availability-zone-profile-id
   - availability_zone: availability_zone
   - name: name

Response Example
----------------

.. literalinclude:: examples/availabilityzone-create-response.json
   :language: javascript


Show Availability Zone Details
==============================

.. rest_method:: GET /v2.0/lbaas/availabilityzones/{availability_zone_name}

Shows the details of an availability zone.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

This operation does not require a request body.

**New in version 2.14**

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
   - availability_zone_name: path-availability-zone-name

Curl Example
------------

.. literalinclude:: examples/availabilityzone-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - availability_zone_profile_id: availability-zone-profile-id
   - availability_zone: availability_zone
   - name: name

Response Example
----------------

.. literalinclude:: examples/availabilityzone-show-response.json
   :language: javascript

Update an Availability Zone
===========================

.. rest_method:: PUT /v2.0/lbaas/availabilityzones/{availability_zone_name}

Update an availability zone.

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

   - description: description-optional
   - enabled: enabled-optional
   - availability_zone: availability_zone
   - availability_zone_name: path-availability-zone-name

Request Example
---------------

.. literalinclude:: examples/availabilityzone-update-request.json
   :language: javascript

Curl Example
------------

.. literalinclude:: examples/availabilityzone-update-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - description: description
   - enabled: enabled
   - availability_zone_profile_id: availability-zone-profile-id
   - availability_zone: availability_zone
   - name: name

Response Example
----------------

.. literalinclude:: examples/availabilityzone-update-response.json
   :language: javascript

Remove an Availability Zone
===========================

.. rest_method:: DELETE /v2.0/lbaas/availabilityzones/{availability_zone_name}

Remove an availability zone and its associated configuration.

If any load balancers are using this availability zone the service returns
the HTTP ``Conflict (409)`` response code.

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

   - availability_zone_name: path-availability-zone-name

Curl Example
------------

.. literalinclude:: examples/availabilityzone-delete-curl
   :language: bash

Response
--------

There is no body content for the response of a successful DELETE request.
