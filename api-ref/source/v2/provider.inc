.. -*- rst -*-

List Providers
==============

.. rest_method:: GET /v2/lbaas/providers

Lists all enabled provider drivers.

Use the ``fields`` query parameter to control which fields are
returned in the response body.

The list might be empty.

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

.. literalinclude:: examples/provider-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - name: provider-name
   - description: provider-description

Response Example
----------------

.. literalinclude:: examples/provider-list-response.json
   :language: javascript

Show Provider Flavor Capabilities
=================================

.. rest_method:: GET /v2/lbaas/providers/{provider}/flavor_capabilities

Shows the provider driver flavor capabilities. These are the features of the
provider driver that can be configured in an Octavia flavor. This API returns
a list of dictionaries with the name and description of each flavor capability
of the provider.

The list might be empty and a provider driver may not implement this feature.

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
   - provider: path-provider

Curl Example
------------

.. literalinclude:: examples/provider-flavor-capability-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - flavor_capabilities: flavor-capabilities
   - name: flavor-capability-name
   - description: flavor-capability-description

Response Example
----------------

.. literalinclude:: examples/provider-flavor-capability-show-response.json
   :language: javascript

Show Provider Availability Zone Capabilities
============================================

.. rest_method:: GET /v2/lbaas/providers/{provider}/availability_zone_capabilities

Shows the provider driver availability zone capabilities. These are the
features of the provider driver that can be configured in an Octavia
availability zone. This API returns a list of dictionaries with the name and
description of each availability zone capability of the provider.

The list might be empty and a provider driver may not implement this feature.

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
   - provider: path-provider

Curl Example
------------

.. literalinclude:: examples/provider-availability-zone-capability-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - availability_zone_capabilities: availability-zone-capabilities
   - name: availability-zone-capability-name
   - description: availability-zone-capability-description

Response Example
----------------

.. literalinclude:: examples/provider-availability-zone-capability-show-response.json
   :language: javascript
