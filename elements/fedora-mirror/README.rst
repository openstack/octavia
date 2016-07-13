This element enables the use of a mirror for updating Fedora cloud images.
Using a local mirror increases the speed of building the image.

The Fedora mirror URL is specified by setting the 'FEDORA_MIRROR' environment
variable.

.. code:: bash

    $ export FEDORA_MIRROR=http://<local mirror hostname>/<path to mirror>
