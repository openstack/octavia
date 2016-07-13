This element enables the use of a mirror for updating CentOS cloud images.
Using a local mirror increases the speed of building the image.

The CentOS mirror URL is specified by setting the 'CENTOS_MIRROR' environment
variable.

.. code:: bash

    $ export CENTOS_MIRROR=http://<local mirror hostname>/<path to mirror>
