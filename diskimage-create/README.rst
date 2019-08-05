Diskimage-builder script for creating Octavia Amphora images
============================================================

Octavia is an operator-grade reference implementation for Load Balancing as a
Service (LBaaS) for OpenStack.  The component of Octavia that does the load
balancing is known as amphora.  Amphora may be a virtual machine, may be a
container, or may run on bare metal.  Creating images for bare metal amphora
installs is outside the scope of this version but may be added in a
future release.

Prerequisites
=============

This script assumes a typical Linux environment and was developed on
Ubuntu 12.04.5 LTS.

Python pip should be installed as well as the python modules found in the
requirements.txt file.

To do so, you can use the following command on ubuntu:

.. code:: bash

   $ # Install python pip
   $ sudo apt install python-pip
   $ # Eventually create a virtualenv
   $ sudo apt install python-virtualenv
   $ virtualenv octavia_disk_image_create
   $ source octavia_disk_image_create/bin/activate
   $ # Install octavia requirements
   $ cd octavia/diskimage-create
   $ pip install -r requirements.txt


Your cache directory should have at least 1GB available, the working directory
will need ~1.5GB, and your image destination will need ~500MB

The script will use the version of diskimage-builder installed on your system,
or it can be overridden by setting the following environment variables:

 | DIB_REPO_PATH = /<some directory>/diskimage-builder
 | DIB_ELEMENTS = /<some directory>/diskimage-builder/elements


The following packages are required on each platform:

Ubuntu

.. code:: bash

   $ sudo apt install qemu-utils git kpartx debootstrap

Fedora, CentOS and Red Hat Enterprise Linux

.. code:: bash

   $ sudo yum install qemu-img git e2fsprogs policycoreutils-python

Test Prerequisites
------------------
The tox image tests require libguestfs-tools 1.24 or newer.
Libguestfs allows testing the Amphora image without requiring root privileges.
On Ubuntu systems you also need to give read access to the kernels for the user
running the tests:

.. code:: bash

    $ sudo chmod 0644 /boot/vmlinuz*

Tests were run on Ubuntu 14.04.1 LTS during development.

Usage
=====
This script and associated elements will build Amphora images.  Current support
is with an Ubuntu base OS and HAProxy.  The script can use Fedora
as a base OS but these will not initially be tested or supported.
As the project progresses and/or the diskimage-builder project adds support
for additional base OS options they may become available for Amphora images.
This does not mean that they are necessarily supported or tested.

.. note::

    If your cloud has multiple hardware architectures available to nova,
    remember to set the appropriate hw_architecture property on the
    image when you load it into glance. For example, when loading an
    amphora image built for "amd64" you would add
    "--property hw_architecture='x86_64'" to your "openstack image create"
    command line.

The script will use environment variables to customize the build beyond the
Octavia project defaults, such as adding elements.

The supported and tested image is created by using the diskimage-create.sh
defaults (no command line parameters or environment variables set).  As the
project progresses we may add additional supported configurations.

Command syntax:


.. line-block::

    $ diskimage-create.sh
            [-a i386 | **amd64** | armhf | ppc64le ]
            [-b **haproxy** ]
            [-c **~/.cache/image-create** | <cache directory> ]
            [-d **bionic**/**7** | xenial | 8 | <other release id> ]
            [-e]
            [-f]
            [-h]
            [-i **ubuntu-minimal** | fedora | centos-minimal | rhel ]
            [-k <kernel package name> ]
            [-l <log file> ]
            [-n]
            [-o **amphora-x64-haproxy** | <filename> ]
            [-p]
            [-r <root password> ]
            [-s **2** | <size in GB> ]
            [-t **qcow2** | tar ]
            [-v]
            [-w <working directory> ]
            [-x]

        '-a' is the architecture type for the image (default: amd64)
        '-b' is the backend type (default: haproxy)
        '-c' is the path to the cache directory (default: ~/.cache/image-create)
        '-d' distribution release id (default on ubuntu: bionic)
        '-e' enable complete mandatory access control systems when available (default: permissive)
        '-f' disable tmpfs for build
        '-h' display help message
        '-i' is the base OS (default: ubuntu-minimal)
        '-k' is the kernel meta package name, currently only for ubuntu-minimal base OS (default: linux-image-virtual)
        '-l' is output logfile (default: none)
        '-n' disable sshd (default: enabled)
        '-o' is the output image file name
        '-p' install amphora-agent from distribution packages (default: disabled)"
        '-r' enable the root account in the generated image (default: disabled)
        '-s' is the image size to produce in gigabytes (default: 2)
        '-t' is the image type (default: qcow2)
        '-v' display the script version
        '-w' working directory for image building (default: .)
        '-x' enable tracing for diskimage-builder


Environment Variables
=====================
These are optional environment variables that can be set to override the script
defaults.

DIB_REPOLOCATION_amphora_agent
    - Location of the amphora-agent code that will be installed in the image.
    - Default: https://opendev.org/openstack/octavia
    - Example: /tmp/octavia

DIB_REPOREF_amphora_agent
    - The git reference to checkout for the amphora-agent code inside the image.
    - Default: master
    - Example: stable/stein
    - Example: refs/changes/40/674140/7

CLOUD_INIT_DATASOURCES
    - Comma separated list of cloud-int datasources
    - Default: ConfigDrive
    - Options: NoCloud, ConfigDrive, OVF, MAAS, Ec2, <others>
    - Reference: https://launchpad.net/cloud-init

DIB_DISTRIBUTION_MIRROR
    - URL to a mirror for the base OS selected
    - Default: None

DIB_ELEMENTS
    - Override the elements used to build the image
    - Default: None

DIB_LOCAL_ELEMENTS
    - Elements to add to the build (requires DIB_LOCAL_ELEMENTS_PATH be
      specified)
    - Default: None

DIB_LOCAL_ELEMENTS_PATH
    - Path to the local elements directory
    - Default: None

DIB_REPO_PATH
    - Directory containing diskimage-builder
    - Default: <directory above OCTAVIA_HOME>/diskimage-builder
    - Reference: https://github.com/openstack/diskimage-builder

OCTAVIA_REPO_PATH
    - Directory containing octavia
    - Default: <directory above the script location>
    - Reference: https://github.com/openstack/octavia

Using distribution packages for amphora agent
---------------------------------------------
By default, amphora agent is installed from Octavia Git repository.
To use distribution packages, use the "-p" option.

Note this needs a base system image with the required repositories enabled (for
example RDO repositories for CentOS/Fedora). One of these variables must be
set:

DIB_LOCAL_IMAGE
    - Path to the locally downloaded image
    - Default: None

DIB_CLOUD_IMAGES
    - Directory base URL to download the image from
    - Default: depends on the distribution

For example to build a CentOS 7 amphora with Pike RPM packages:
.. code:: bash

    # Get image
    $ wget https://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2

    # Add repository
    $ virt-customize -a CentOS-7-x86_64-GenericCloud.qcow2  --selinux-relabel --run-command 'yum install -y centos-release-openstack-pike'

    # Point to modified image and run script
    $ export DIB_LOCAL_IMAGE=/home/stack/CentOS-7-x86_64-GenericCloud.qcow2
    $ ./diskimage-create.sh -p -i centos-minimal

RHEL specific variables
------------------------
Building a RHEL-based image requires:
    - a Red Hat Enterprise Linux KVM Guest Image, manually download from the
      Red Hat Customer Portal. Set the DIB_LOCAL_IMAGE variable to point to
      the file. More details at:
      <DIB_REPO_PATH>/elements/rhel

    - a Red Hat subscription for the matching Red Hat OpenStack Platform
      repository if you want to install the amphora agent from the official
      distribution package (requires setting -p option in diskimage-create.sh).
      Set the needed registration parameters depending on your configuration.
      More details at:
      <DIB_REPO_PATH>/elements/rhel-common

Here is an example with Customer Portal registration and OSP 13 repository:
.. code:: bash

    $ export DIB_LOCAL_IMAGE='/tmp/rhel-server-7.6-x86_64-kvm.qcow2'

    $ export REG_METHOD='portal' REG_REPOS='rhel-7-server-openstack-13-rpms'

    $ export REG_USER='<user>' REG_PASSWORD='<password>' REG_AUTO_ATTACH=true

This example uses registration via a Satellite (the activation key must enable
an OSP repository):
.. code:: bash

    $ export DIB_LOCAL_IMAGE='/tmp/rhel-server-7.6-x86_64-kvm.qcow2'

    $ export REG_METHOD='satellite' REG_ACTIVATION_KEY="<activation key>"

    $ export REG_SAT_URL="<satellite url>" REG_ORG="<satellite org>"

Building in a virtualenv with tox
---------------------------------
To make use of a virtualenv for Python dependencies you may run ``tox``.  Note that
you may still need to install binary dependencies on the host for the build to succeed.

If you wish to customize your build modify ``tox.ini`` to pass on relevant
environment variables or command line arguments to the ``diskimage-create.sh`` script.

.. code:: bash

    $ tox -e build


Container Support
=================
The Docker command line required to import a tar file created with this script
is:

.. code:: bash

    $ docker import - image:amphora-x64-haproxy < amphora-x64-haproxy.tar


References
==========

This documentation and script(s) leverage prior work by the OpenStack TripleO
and Sahara teams.  Thank you to everyone that worked on them for providing a
great foundation for creating Octavia Amphora images.

    | https://github.com/openstack/diskimage-builder
    | https://github.com/openstack/tripleo-image-elements
    | https://github.com/openstack/sahara-image-elements

Copyright
=========

Copyright 2014 Hewlett-Packard Development Company, L.P.

All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

   | http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
