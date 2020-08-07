Element to install octavia-lib from a Git source.

This element allows octavia-lib installs from an arbitraty Git repository.
This is especially useful for development environments.

By default, octavia-lib is installed from upstream master branch or from an
upstream stable branch for OpenStack release series.

To install from an alternative Git location, define the following:

.. sourcecode:: sh

    DIB_REPOLOCATION_octavia_lib=<path/to/octavia-lib>
    DIB_REPOREF_octavia_lib=<branch or ref>

If you wish to build an image using code from a Gerrit review, you can set
``DIB_REPOLOCATION_octavia_lib`` and ``DIB_REPOREF_octavia_lib`` to the values
given by Gerrit in the fetch/pull section of a review. For example, installing
octavia-lib with change 744519 at patchset 2:

.. sourcecode:: sh

    DIB_REPOLOCATION_octavia_lib=https://review.opendev.org/openstack/octavia-lib
    DIB_REPOREF_octavia_lib=refs/changes/19/744519/2
