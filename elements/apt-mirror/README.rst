This element enables the use of a mirror for updating Ubuntu cloud images.
Using a local mirror increases the speed of building the image.

The Ubuntu mirror URL is specified by setting the 'UBUNTU_MIRROR' environment
variable.

.. code:: bash

    $ export UBUNTU_MIRROR=http://<local mirror hostname>/<path to mirror>
