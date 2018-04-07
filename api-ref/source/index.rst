:tocdepth: 2

=============
 Octavia API
=============

This is a reference for the OpenStack Load Balancing API which is provided by
the Octavia project.

Current API version

    :doc:`Octavia API v2<v2/index>`

Supported API version

    None

Deprecated API version

    :doc:`v1/octaviaapi`

.. toctree::
   :hidden:

   v2/index
   v1/octaviaapi

Octavia API minor releases are additive to the API major revision and share
the same URL path. Minor revision changes to the API are called out in the API
reference in the section the change occured in. Subsquent minor versions are a
superset of the previous versions of the same major revision.

The API status reflects the state of the endpoint on the service.

* Current indicates a stable version that is up-to-date, recent, and might
  receive future versions. This endpoint should be prioritized over all
  others.
* Supported is a stable version that is available on the server. However, it
  is not likely the most recent available and might not be updated or might
  be deprecated at some time in the future.
* Deprecated is a stable version that is still available but is being
  deprecated and might be removed in the future.
* Experimental is not a stable version. This version is under development or
  contains features that are otherwise subject to change. For more
  information about API status values and version information, see
  `Version Discovery <https://wiki.openstack.org/wiki/VersionDiscovery>`__.

.. rest_expand_all::

-------------
API Discovery
-------------

List All Versions
=======================

.. rest_method:: GET /

This fetches all the information about all known API versions in the
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
   - links: links
   - status: api_version_status
   - updated_at: updated_at

Response Example
----------------

.. literalinclude:: examples/versions-get-resp.json
   :language: javascript

.. note::
   This is just an example output and does not represent the current API
   versions available.
