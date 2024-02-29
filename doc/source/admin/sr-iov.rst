..
      Copyright 2023 Red Hat, Inc. All rights reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============================
Using SR-IOV Ports with Octavia
===============================

Single Root I/O Virtualization (SR-IOV) can significantly reduce the latency
through an Octavia Amphora based load balancer while maximizing bandwith and
request rates. With Octavia Amphora load balancers, you can attach SR-IOV
Virtual Functions (VF) as the VIP port and/or backend member ports.

Enabling SR-IOV on Your Compute Hosts
-------------------------------------

To allow Octavia load balancers to use SR-IOV, you must configure nova and
neutron to make SR-IOV available on at least one compute host. Please follow
the `Networking Guide <https://docs.openstack.org/neutron/latest/admin/config-sriov.html>`_ to setup your compute hosts for SR-IOV.

Configuring Host Aggregates, Compute and Octavia Flavors
--------------------------------------------------------

Octavia hot-plugs the network ports into the Amphora as the load balancer is
being provisioned. This means we need to use host aggregates and compute flavor
properties to make sure the Amphora are created on SR-IOV enable compute hosts
with the correct networks.

Host Aggregates
~~~~~~~~~~~~~~~

This configuration can be as simple or complex as you need it to be. A simple
approach would be to add one property for the SR-IOV host aggregate, such as:

.. code-block:: bash

   $ openstack aggregate create sriov_aggregate
   $ openstack aggregate add host sriov_aggregate sriov-host.example.org
   $ openstack aggregate set --property sriov-nic=true sriov_aggregate

A more advanced configuration may list out the specific networks that are
available via the SR-IOV VFs:

.. code-block:: bash

   $ openstack aggregate create sriov_aggregate
   $ openstack aggregate add host sriov_aggregate sriov-host.example.org
   $ openstack aggregate set --property public-sriov=true --property members-sriov=true sriov_aggregate

Compute Flavors
~~~~~~~~~~~~~~~

Next we need to create a compute flavor that includes the required properties
to match the host aggregate. Here is an example for a basic Octavia Amphora
compute flavor using the advanced host aggregate discussed in the previous
section:

.. code-block:: bash

   $ openstack flavor create --id amphora-sriov-flavor --ram 1024 --disk 3 --vcpus 1 --private sriov.amphora --property hw_rng:allowed=True --property public-sriov=true --property members-sriov=true

.. note::
   This flavor is marked "private" so must be created inside the Octavia
   service account project.

Octavia Flavors
~~~~~~~~~~~~~~~

Now that we have the compute service setup to properly place our Amphora
instances on hosts with SR-IOV NICs on the right networks, we can create an
Octavia flavor that will use the compute flavor.

.. code-block:: bash

   $ openstack loadbalancer flavorprofile create --name amphora-sriov-profile --provider amphora --flavor-data '{"compute_flavor": "amphora-sriov-flavor", "sriov_vip": true}'
   $ openstack loadbalancer flavor create --name SRIOV-public-members --flavorprofile amphora-sriov-profile --description "A load balancer that uses SR-IOV for the 'public' network and 'members' network." --enable

Building the Amphora Image
~~~~~~~~~~~~~~~~~~~~~~~~~~

Neutron does not support security groups on SR-IOV ports, so Octavia will use
nftables inside the Amphroa to provide network security. The amphora image
must be built with nftables enabled for SR-IOV enabled load balancers. Images
with nftables enabled can be used for both SR-IOV enabled load balancers as
well as load balancers that are not using SR-IOV ports. When the SR-IOV for
load balancer VIP ports feature was added to Octavia, the default setting for
using nftables has been changed to `True`. Prior to this it needed to be
enabled by setting an environment variable before building the Amphora image:

.. code-block:: bash

   $ export DIB_OCTAVIA_AMP_USE_NFTABLES=True
   $ ./diskimage-create.sh
