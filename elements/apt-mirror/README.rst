This element enables the use of a mirror for updating Ubuntu cloud images.
Using a local mirror increases the speed of building the image.

Note: This element is deprectated in favor of the diskimage-builder methods
for setting a mirror. See
http://docs.openstack.org/developer/diskimage-builder/elements/ubuntu/README.html
and
http://docs.openstack.org/developer/diskimage-builder/elements/apt-sources/README.html
for more information.

The Ubuntu mirror URL is specified by setting the 'UBUNTU_MIRROR' environment
variable.

.. code:: bash

    $ export UBUNTU_MIRROR=http://<local mirror hostname>/<path to mirror>
