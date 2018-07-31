..
      Copyright (c) 2016 IBM

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

======================================
Developer / Operator Quick Start Guide
======================================
This document is intended for developers and operators. For an end-user guide,
please see the end-user quick-start guide and cookbook in this documentation
repository.


Running Octavia in devstack
===========================

tl;dr
-----
* 8GB RAM minimum
* "vmx" or "svm" in ``/proc/cpuinfo``
* Ubuntu 16.04 or later
* On that host, copy and run as root:
  ``octavia/devstack/contrib/new-octavia-devstack.sh``


System requirements
-------------------
Octavia in devstack with a default (non-HA) configuration will deploy one
amphora VM per loadbalancer deployed. The current default amphora image also
requires at least 1GB of RAM to run effectively. As such it is important that
your devstack environment has enough resources dedicated to it to run all its
necessary components. For most devstack environments, the limiting resource
will be RAM. At the present time, we recommend at least 12GB of RAM for the
standard devstack defaults, or 8GB of RAM if cinder and swift are disabled.
More is recommended if you also want to run a couple of application server VMs
(so that Octavia has something to load balance within your devstack
environment).

Also, because the current implementation of Octavia delivers load balancing
services using amphorae that run as Nova virtual machines, it is effectively
mandatory to enable nested virtualization. The software will work with software
emulated CPUs, but be unusably slow. The idea is to make sure the BIOS of the
systems you're running your devstack on have virtualization features enabled
(Intel VT-x, AMD-V, etc.), and the virtualization software you're using exposes
these features to the guest VM (sometimes called nested virtualization).
For more information, see:
`Configure DevStack with KVM-based Nested Virtualization
<https://docs.openstack.org/devstack/latest/guides/devstack-with-nested-kvm.html>`__

The devstack environment we recommend should be running Ubuntu Linux 16.04 or
later. These instructions may work for other Linux operating systems or
environments. However, most people doing development on Octavia are using
Ubuntu for their test environment, so you will probably have the easiest time
getting your devstack working with that OS.


Deployment
----------
1. Deploy an Ubuntu 16.04 or later Linux host with at least 8GB of RAM. (This
   can be a VM, but again, make sure you have nested virtualization features
   enabled in your BIOS and virtualization software.)
2. Copy ``devstack/contrib/new-octavia-devstack.sh`` from this source
   repository onto that host.
3. Run new-octavia-devstack.sh as root.
4. Deploy loadbalancers, listeners, etc. as you would with any Neutron LBaaS v2
   enabled cloud.


Running Octavia in production
=============================

Notes
-----

Disclaimers
___________
This document is not a definitive guide for deploying Octavia in every
production environment. There are many ways to deploy Octavia depending on the
specifics and limitations of your situation. For example, in our experience,
large production environments often have restrictions, hidden "features" or
other elements in the network topology which mean the default Neutron
networking stack (with which Octavia was designed to operate) must be modified
or replaced with a custom networking solution. This may also mean that for your
particular environment, you may need to write your own custom networking driver
to plug into Octavia. Obviously, instructions for doing this are beyond the
scope of this document.

We hope this document provides the cloud operator or distribution creator with
a basic understanding of how the Octavia components fit together practically.
Through this, it should become more obvious how components of Octavia can be
divided or duplicated across physical hardware in a production cloud
environment to aid in achieving scalability and resiliency for the Octavia load
balancing system.

In the interest of keeping this guide somewhat high-level and avoiding
obsolescence or operator/distribution-specific environment assumptions by
specifying exact commands that should be run to accomplish the tasks below, we
will instead just describe what needs to be done and leave it to the cloud
operator or distribution creator to "do the right thing" to accomplish the task
for their environment. If you need guidance on specific commands to run to
accomplish the tasks described below, we recommend reading through the
plugin.sh script in devstack subdirectory of this project. The devstack plugin
exercises all the essential components of Octavia in the right order, and this
guide will mostly be an elaboration of this process.


Environment Assumptions
_______________________
The scope of this guide is to provide a basic overview of setting up all
the components of Octavia in a production environment, assuming that the
default in-tree drivers and components (including a "standard" Neutron install)
are going to be used.

For the purposes of this guide, we will therefore assume the following core
components have already been set up for your production OpenStack environment:

* Nova
* Neutron (with Neutron LBaaS v2)
* Glance
* Barbican (if TLS offloading functionality is enabled)
* Keystone
* Rabbit
* MySQL


Production Deployment Walkthrough
---------------------------------

Create Octavia User
___________________
By default Octavia will use the 'neutron' user for keystone authentication, and
the admin user for interactions with all other services. However, it doesn't
actually share neutron's database or otherwise access Neutron outside of
Neutron's API, so a dedicated 'octavia' keystone user should generally be
created for Octavia to use.

You must:

* Create 'octavia' user.
* Add the 'admin' role to this user.


Load Balancer Network Configuration
___________________________________
Octavia makes use of an "LB Network" exclusively as a management network that
the controller uses to talk to amphorae and vice versa. All the amphorae that
Octavia deploys will have interfaces and IP addresses on this network.
Therefore, it's important that the subnet deployed on this network be
sufficiently large to allow for the maximum number of amphorae and controllers
likely to be deployed throughout the lifespan of the cloud installation.

At the present time, though IPv4 subnets are used by default for the LB Network
(for example: 172.16.0.0/12), IPv6 subnets can be used for the LB Network.

The LB Network is isolated from tenant networks on the amphorae by means of
network namespaces on the amphorae. Therefore, operators need not be concerned
about overlapping subnet ranges with tenant networks.

You must also create a Neutron security group which will be applied to amphorae
created on the LB network. It needs to allow amphorae to send UDP heartbeat
packets to the health monitor (by default, UDP port 5555), and ingress on the
amphora's API (by default, TCP port 9443). It can also be helpful to allow SSH
access to the amphorae from the controller for troubleshooting purposes (ie.
TCP port 22), though this is not strictly necessary in production environments.

Amphorae will send periodic health checks to the controller's health manager.
Any firewall protecting the interface on which the health manager listens must
allow these packets from amphorae on the LB Network (by default, UDP port
5555).

Finally, you need to add routing or interfaces to this network such that the
Octavia controller (which will be described below) is able to communicate with
hosts on this network. This also implies you should have some idea where you're
going to run the Octavia controller components.

You must:

* Create the 'lb-mgmt-net'.
* Assign the 'lb-mgmt-net' to the admin tenant.
* Create a subnet and assign it to the 'lb-mgmt-net'.
* Create neutron security group for amphorae created on the 'lb-mgmt-net'.
  which allows appropriate access to the amphorae.
* Update firewall rules on the host running the octavia health manager to allow
  health check messages from amphorae.
* Add appropriate routing to / from the 'lb-mgmt-net' such that egress is
  allowed, and the controller (to be created later) can talk to hosts on this
  network.


Create Amphora Image
____________________
Octavia deploys amphorae based on a virtual machine disk image. By default we
use the OpenStack diskimage-builder project for this. Scripts to accomplish
this are within the diskimage-create directory of this repository. In addition
to creating the disk image, configure a Nova flavor to use for amphorae, and
upload the disk image to glance.

You must:

* Create amphora disk image using OpenStack diskimage-builder.
* Create a Nova flavor for the amphorae.
* Add amphora disk image to glance.
* Tag the above glance disk image with 'amphora'.


Install Octavia Controller Software
___________________________________
This seems somewhat obvious, but the important things to note here are that you
should put this somewhere on the network where it will have access to the
database (to be initialized below), the oslo messaging system, and the LB
network. Octavia uses the standard python setuptools, so installation of the
software itself should be straightforward.

Running multiple instances of the individual Octavia controller components on
separate physical hosts is recommended in order to provide scalability and
availability of the controller software.

One important security note: In 0.9 of Octavia, the Octavia API is designed to
be consumed only by the Neutron-LBaaS v2 Octavia driver. As such, there is
presently no authentication required to use the Octavia API, and therefore the
Octavia API should only be accessible on trusted network segments
(specifically, the segment that runs the neutron-services daemons.)

The Octavia controller presently consists of several components which may be
split across several physical machines. For the 0.9 release of Octavia, the
important (and potentially separable) components are the controller worker,
housekeeper, health manager and API controller. Please see the component
diagrams elsewhere in this repository's documentation for detailed descriptions
of each. Please use the following table for hints on which controller
components need access to outside resources:

+-------------------+----------------------------------------+
| **Component**     | **Resource**                           |
+-------------------+------------+----------+----------------+
|                   | LB Network | Database | OSLO messaging |
+===================+============+==========+================+
| API               | No         | Yes      | Yes            |
+-------------------+------------+----------+----------------+
| controller worker | Yes        | Yes      | Yes            |
+-------------------+------------+----------+----------------+
| health monitor    | Yes        | Yes      | No             |
+-------------------+------------+----------+----------------+
| housekeeper       | Yes        | Yes      | No             |
+-------------------+------------+----------+----------------+

In addition to talking to each other via OSLO messaging, various controller
components must also communicate with other OpenStack components, like nova,
neutron, barbican, etc. via their APIs.

You must:

* Pick appropriate host(s) to run the Octavia components.
* Install the dependencies for Octavia.
* Install the Octavia software.


Create Octavia Keys and Certificates
____________________________________
Octavia presently allows for one method for the controller to communicate with
amphorae: The amphora REST API. Both amphora API and Octavia controller do
bi-directional certificate-based authentication in order to authenticate and
encrypt communication. You must therefore create appropriate TLS certificates
which will be used for key signing, authentication, and encryption. There is a
helper script to do this in this repository under:
``bin/create_certificates.sh``

Please note that certificates created with this helper script may not meet your
organization's security policies, since they are self-signed certificates with
arbitrary bit lengths, expiration dates, etc.  Operators should obviously
follow their own security guidelines in creating these certificates.

In addition to the above, it can sometimes be useful for cloud operators to log
into running amphorae to troubleshoot problems. The standard method for doing
this is to use SSH from the host running the controller worker. In order to do
this, you must create an SSH public/private key pair specific to your cloud
(for obvious security reasons). You must add this keypair to nova. You must
then also update octavia.conf with the keypair name you used when adding it to
nova so that amphorae are initialized with it on boot.

See the Troubleshooting Tips section below for an example of how an operator
can SSH into an amphora.

You must:

* Create TLS certificates for communicating with the amphorae.
* Create SSH keys for communicating with the amphorae.
* Add the SSH keypair to nova.


Configuring Octavia
___________________
Going into all of the specifics of how Octavia can be configured is actually
beyond the scope of this document. For full documentation of this, please see
the configuration reference: :doc:`../../configuration/configref`

A configuration template can be found in ``etc/octavia.conf`` in this
repository.

It's also important to note that this configuration file will need to be
updated with UUIDs of the LB network, amphora security group, amphora image
tag, SSH key path, TLS certificate path, database credentials, etc.

At a minimum, the configuration should specify the following, beyond the
defaults. Your specific environment may require more than this:

+-----------------------+-------------------------------+
| Section               | Configuration parameter       |
+=======================+===============================+
| DEFAULT               | transport_url                 |
+-----------------------+-------------------------------+
| database              | connection                    |
+-----------------------+-------------------------------+
| certificates          | ca_certificate                |
+-----------------------+-------------------------------+
| certificates          | ca_private_key                |
+-----------------------+-------------------------------+
| certificates          | ca_private_key_passphrase     |
+-----------------------+-------------------------------+
| controller_worker     | amp_boot_network_list         |
+-----------------------+-------------------------------+
| controller_worker     | amp_flavor_id                 |
+-----------------------+-------------------------------+
| controller_worker     | amp_image_owner_id            |
+-----------------------+-------------------------------+
| controller_worker     | amp_image_tag                 |
+-----------------------+-------------------------------+
| controller_worker     | amp_secgroup_list             |
+-----------------------+-------------------------------+
| controller_worker     | amp_ssh_key_name [#]_         |
+-----------------------+-------------------------------+
| controller_worker     | amphora_driver                |
+-----------------------+-------------------------------+
| controller_worker     | compute_driver                |
+-----------------------+-------------------------------+
| controller_worker     | loadbalancer_topology         |
+-----------------------+-------------------------------+
| controller_worker     | network_driver                |
+-----------------------+-------------------------------+
| haproxy_amphora       | client_cert                   |
+-----------------------+-------------------------------+
| haproxy_amphora       | server_ca                     |
+-----------------------+-------------------------------+
| health_manager        | bind_ip                       |
+-----------------------+-------------------------------+
| health_manager        | controller_ip_port_list       |
+-----------------------+-------------------------------+
| health_manager        | heartbeat_key                 |
+-----------------------+-------------------------------+
| house_keeping         | spare_amphora_pool_size       |
+-----------------------+-------------------------------+
| keystone_authtoken    | admin_password                |
+-----------------------+-------------------------------+
| keystone_authtoken    | admin_tenant_name             |
+-----------------------+-------------------------------+
| keystone_authtoken    | admin_user                    |
+-----------------------+-------------------------------+
| keystone_authtoken    | www_authenticate_uri          |
+-----------------------+-------------------------------+
| keystone_authtoken    | auth_version                  |
+-----------------------+-------------------------------+
| oslo_messaging        | topic                         |
+-----------------------+-------------------------------+
| oslo_messaging_rabbit | rabbit_host                   |
+-----------------------+-------------------------------+
| oslo_messaging_rabbit | rabbit_userid                 |
+-----------------------+-------------------------------+
| oslo_messaging_rabbit | rabbit_password               |
+-----------------------+-------------------------------+

.. [#] This is technically optional, but extremely useful for troubleshooting.

You must:

* Create or update ``/etc/octavia/octavia.conf`` appropriately.


Spares pool considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^
One configuration directive deserves some extra consideration in this document:

Depending on the specifics of your production environment, you may decide to
run Octavia with a non-empty "spares pool." Since the time it takes to spin up
a new amphora can be non-trivial in some cloud environments (and the
reliability of such operations can sometimes be less than ideal), this
directive instructs Octavia to attempt to maintain a certain number of amphorae
running in an idle, unconfigured state. These amphora will run base amphora
health checks and wait for configuration from the Octavia controller. The
overall effect of this is to greatly reduce the time it takes and increase the
reliability of deploying a new load balancing service on demand. This comes at
the cost of having a number of deployed amphorae which consume resources but
are not actively providing load balancing services, and at the cost of not
being able to use Nova anti-affinity features for ACTIVE-STANDBY load
balancer topologies.


Initialize Octavia Database
___________________________
This is controlled through alembic migrations under the octavia/db directory in
this repository. A tool has been created to aid in the initialization of the
octavia database. This should be available under
``/usr/local/bin/octavia-db-manage`` on the host on which the octavia
controller worker is installed. Note that this tool looks at the
``/etc/octavia/octavia.conf`` file for its database credentials, so
initializing the database must happen after Octavia is configured.

It's also important to note here that all of the components of the Octavia
controller will need direct access to the database (including the API handler),
so you must ensure these components are able to communicate with whichever host
is housing your database.

You must:

* Create database credentials for Octavia.
* Add these to the ``/etc/octavia/octavia.conf`` file.
* Run ``/usr/local/bin/octavia-db-manage upgrade head`` on the controller
  worker host to initialize the octavia database.


Launching the Octavia Controller
________________________________
We recommend using upstart / systemd scripts to ensure the components of the
Octavia controller are all started and kept running. It of course doesn't hurt
to first start by running these manually to ensure configuration and
communication is working between all the components.

You must:

* Make sure each Octavia controller component is started appropriately.


Configuring Neutron LBaaS
_________________________
This is fairly straightforward. Neutron LBaaS needs to be directed to use the
Octavia service provider. There should be a line like the following in
``/etc/neutron/neutron_lbaas.conf`` file's ``[service providers]`` section:

::

    service_provider = LOADBALANCERV2:Octavia:neutron_lbaas.drivers.octavia.driver.OctaviaDriver:default

In addition to the above you must add the octavia API ``base_url`` to the
``[octavia]`` section of ``/etc/neutron/neutron.conf``. For example:

::

    [octavia]
    base_url=http://127.0.0.1:9876

You must:

* Update ``/etc/neutron/neutron_lbaas.conf`` as described above.
* Add the octavia API URL to ``/etc/neutron/neutron.conf``.


Install Neutron-LBaaS v2 extension in Horizon
_____________________________________________
This isn't strictly necessary for all cloud installations, however, if yours
makes use of the Horizon GUI interface for tenants, it is probably also a good
idea to make sure that it is configured with the Neutron-LBaaS v2 extension.

You may:

* Install the neutron-lbaasv2 GUI extension in Horizon


Test deployment
_______________
If all of the above instructions have been followed, it should now be possible
to deploy load balancing services using the python neutronclient CLI,
communicating with the neutron-lbaas v2 API.

Example:

::

    # openstack loadbalancer create --name lb1 --vip-subnet-id private-subnet
    # openstack loadbalancer show lb1
    # openstack loadbalancer listener create --name listener1 --protocol HTTP --protocol-port 80 lb1

Upon executing the above, log files should indicate that an amphora is deployed
to house the load balancer, and that this load balancer is further modified to
include a listener. The amphora should be visible to the octavia or admin
tenant using the ``openstack server list`` command, and the listener should
respond on the load balancer's IP on port 80 (with an error 503 in this case,
since no pool or members have been defined yet—but this is usually enough to
see that the Octavia load balancing system is working). For more information
on configuring load balancing services as a tenant, please see the end-user
quick-start guide and cookbook.


Troubleshooting Tips
====================
The troubleshooting hints in this section are meant primarily for developers
or operators troubleshooting underlying Octavia components, rather than
end-users or tenants troubleshooting the load balancing service itself.


SSH into Amphorae
-----------------
If you are using the reference amphora image, it may be helpful to log into
running amphorae when troubleshooting service problems. To do this, first
discover the ``lb_network_ip`` address of the amphora you would like to SSH
into by looking in the ``amphora`` table in the octavia database. Then from the
host housing the controller worker, run:

::

    ssh -i /etc/octavia/.ssh/octavia_ssh_key ubuntu@[lb_network_ip]
