:tocdepth: 2

=============
 Octavia API
=============

This is a reference for the OpenStack Load Balancing API which is provided by
the Octavia project.

Current API version

    :doc:`Octavia API v2.0<v2/index>`

Deprecated API version

    :doc:`Octavia API v1<v1/index>`

.. toctree::
   :hidden:

   v2/index
   v1/index

.. rest_expand_all::

-------------
API Discovery
-------------

List All Major Versions
=======================

.. rest_method:: GET /

This fetches all the information about all known major API versions in the
deployment.

Response codes
--------------

.. rest_status_code:: success http-status.yaml

   - 200

.. rest_status_code:: error http-status.yaml

   - 500

Response
--------

.. rest_parameters:: parameters.yaml

   - id: api_version_id
   - status: api_version_status
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/versions-get-resp.json
   :language: javascript

.. note::
   This is just an example output and does not represent the current API
   versions available.
