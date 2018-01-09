.. -*- rst -*-

List Amphora
============

.. rest_method:: GET /v2.0/octavia/amphorae

Lists all amphora for the project.

If you are not an administrative user, the service returns the HTTP
``Forbidden (403)`` response code.

Use the ``fields`` query parameter to control which fields are
returned in the response body. Additionally, you can filter results
by using query string parameters. For information, see :ref:`filtering`.

The list might be empty.

.. NOTE::

    The field `cached_zone` should be used for quick filtering and reference
    only, as it may out of date. If an up-to-date zone is vital, we recommend
    retrieving details directly from the compute service.

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

.. literalinclude:: examples/amphora-list-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - id: amphora-id
   - loadbalancer_id: loadbalancer-id
   - compute_id: compute-id
   - lb_network_ip: lb-network-ip
   - vrrp_ip: vrrp-ip
   - ha_ip: vip_address
   - vrrp_port_id: vrrp-port-id
   - ha_port_id: vip_port_id
   - cert_expiration: cert-expiration
   - cert_busy: cert-busy
   - role: amphora-role
   - status: amphora-status
   - vrrp_interface: vrrp-interface
   - vrrp_id: vrrp-id
   - vrrp_priority: vrrp-priority
   - cached_zone: cached-zone

Response Example
----------------

.. literalinclude:: examples/amphora-list-response.json
   :language: javascript

Show Amphora details
===========================

.. rest_method:: GET /v2.0/octavia/amphorae/{amphora_id}

Shows the details of an amphora.

If you are not an administrative user, the service returns the HTTP
``Forbidden (403)`` response code.

This operation does not require a request body.

.. NOTE::

    The field `cached_zone` should be used for quick filtering and reference
    only, as it may out of date. If an up-to-date zone is vital, we recommend
    retrieving details directly from the compute service.

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
   - amphora_id: path-amphora-id

Curl Example
------------

.. literalinclude:: examples/amphora-show-curl
   :language: bash

Response Parameters
-------------------

.. rest_parameters:: ../parameters.yaml

   - id: amphora-id
   - loadbalancer_id: loadbalancer-id
   - compute_id: compute-id
   - lb_network_ip: lb-network-ip
   - vrrp_ip: vrrp-ip
   - ha_ip: vip_address
   - vrrp_port_id: vrrp-port-id
   - ha_port_id: vip_port_id
   - cert_expiration: cert-expiration
   - cert_busy: cert-busy
   - role: amphora-role
   - status: amphora-status
   - vrrp_interface: vrrp-interface
   - vrrp_id: vrrp-id
   - vrrp_priority: vrrp-priority
   - cached_zone: cached-zone

Response Example
----------------

.. literalinclude:: examples/amphora-show-response.json
   :language: javascript

Failover Amphora
================

.. rest_method:: PUT /v2.0/octavia/amphorae/{amphora_id}/failover

Force an amphora to failover.

If you are not an administrative user, the service returns the HTTP
``Forbidden (403)`` response code.

This operation does not require a request body.

.. rest_status_code:: success ../http-status.yaml

   - 202

.. rest_status_code:: error ../http-status.yaml

   - 400
   - 401
   - 403
   - 500

Request
-------

.. rest_parameters:: ../parameters.yaml

   - amphora_id: path-amphora-id

Curl Example
------------

.. literalinclude:: examples/amphora-failover-curl
   :language: bash

Response
--------

There is no body content for the response of a successful PUT request.
