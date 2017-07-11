..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Octavia Base Image
==========================================

Launchpad blueprint:

https://blueprints.launchpad.net/octavia/+spec/base-image

Octavia is an operator-grade reference implementation for Load Balancing as a
Service (LBaaS) for OpenStack.  The component of Octavia that does the load
balancing is known as amphora.  Amphora may be a virtual machine, may be a
container, or may run on bare metal.  Creating images for bare metal amphora
installs is outside the scope of this 0.5 specification but may be added in a
future release.

Amphora will need a base image that can be deployed by Octavia to provide load
balancing.


Problem description
===================

Octavia needs a method for generating base images to be deployed as load
balancing entities.

Proposed change
===============

Leverage the OpenStack diskimage-builder project [1] tools to provide a script
that builds qcow2 images or a tar file suitable for use in creating containers.
This script will be modeled after the OpenStack Sahara [2] project's
diskimage-create.sh script.

This script and associated elements will build Amphora images.  Initial support
with be with an Ubuntu OS and HAProxy.  The script will be able to use Fedora
or CentOS as a base OS but these will not initially be tested or supported.
As the project progresses and/or the diskimage-builder project adds support
for additional base OS options they may become available for Amphora images.
This does not mean that they are necessarily supported or tested.

The script will use environment variables to customize the build beyond the
Octavia project defaults, such as adding elements.

The initial supported and tested image will be created using the
diskimage-create.sh defaults (no command line parameters or environment
variables set).  As the project progresses we may add additional supported
configurations.

Command syntax:

.. line-block::

    $ diskimage-create.sh
            [-a i386 | **amd64** | armhf ]
            [-b **haproxy** ]
            [-c **~/.cache/image-create** | <cache directory> ]
            [-h]
            [-i **ubuntu** | fedora | centos ]
            [-o **amphora-x64-haproxy** | <filename> ]
            [-r <root password> ]
            [-s **5** | <size in GB> ]
            [-t **qcow2** | tar ]
            [-w <working directory> ]
        '-a' is the architecture type for the image (default: amd64)
        '-b' is the backend type (default: haproxy)
        '-c' is the path to the cache directory (default: ~/.cache/image-create)
        '-h' display help message
        '-i' is the base OS (default: ubuntu)
        '-o' is the output image file name
        '-r' enable the root account in the generated image (default: disabled)
        '-s' is the image size to produce in gigabytes (default: 5)
        '-t' is the image type (default: qcow2)
        '-w' working directory for image building (default: .)


.. line-block::

    Environment variables supported by the script:
       DIB_DISTRIBUTION_MIRROR - URL to a mirror for the base OS selected  (-i).
       DIB_REPO_PATH - Path to the diskimage-builder repository (default: ../../diskimage-builder)
       ELEMENTS_REPO_PATH - Path to the /tripleo-image-elements repository (default: ../../tripleo-image-elements)
       DIB_ELEMENTS - Override the elements used to build the image
       DIB_LOCAL_ELEMENTS - Elements to add to the build (requires DIB_LOCAL_ELEMENTS_PATH be specified)
       DIB_LOCAL_ELEMENTS_PATH - Path to the local elements directory

.. topic:: Container support

    The Docker command line required to import a tar file created with this script is [3]:

.. code:: bash

    $ docker import - image:amphora-x64-haproxy < amphora-x64-haproxy.tar

Alternatives
------------

Deployers can manually create an image or container, but they would need to
make sure the required components are included.

Data model impact
-----------------
None

REST API impact
---------------
None

Security impact
---------------
None

Notifications impact
--------------------
None

Other end user impact
---------------------
None

Performance Impact
------------------
None

Other deployer impact
---------------------
This script will make creating an Octavia Amphora image or container simple.

Developer impact
----------------
None

Implementation
==============

Assignee(s)
-----------
Michael Johnson <johnsom>

Work Items
----------
1. Write diskimage-create.sh script based on Sahara project's script.

2. Identify the list of packages required for Octavia Amphora.

3. Create required elements not provided by the diskimage-builder project.

4. Create unit tests

Dependencies
============

This script will depend on the OpenStack diskimage-builder project.

Testing
=======

Initial testing will be completed using the default settings for the
diskimage-create.sh tool.

* Unit tests with tox
    * Validate that the image is the correct size and mounts via loopback
    * Check that a valid kernel is installed
    * Check that HAProxy and all required packages are installed
* tempest tests

Documentation Impact
====================


References
==========
.. line-block::
    [1] https://github.com/openstack/diskimage-builder
    [2] https://github.com/openstack/sahara-image-elements
    [3] https://github.com/openstack/diskimage-builder/blob/master/docs/docker.md
