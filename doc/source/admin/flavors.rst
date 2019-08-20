..
      Copyright 2018 Rackspace, US Inc.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

===============
Octavia Flavors
===============

Octavia flavors are a powerful tool for operators to bring enhanced load
balancing capabilities to their users. An Octavia flavor is a predefined
set of provider configuration options that are created by the operator.
When an user requests a load balancer they can request the load balancer
be built with one of the defined flavors. Flavors are defined per provider
driver and expose the unique capabilites of each provider.

This document is intended to explain the flavors capability for operators
that wish to create flavors for their users.

There are three steps to creating a new Octavia flavor:

#. Decide on the provider flavor capabilites that will be configured in the
   flavor.
#. Create the flavor profile with the flavor capabilities.
#. Create the user facing flavor.

Provider Capabilities
=====================

.. _provider driver flavor capabilities: https://docs.openstack.org/api-ref/load-balancer/v2/index.html##show-provider-flavor-capabilities

To start the process of defining a flavor, you will want to look at the
flavor capabilities that the provider driver exposes. To do this you can use
the `provider driver flavor capabilities`_ API or the OpenStack client.

.. code-block:: bash

    openstack loadbalancer provider capability list <provider>

With the default RBAC policy, this command is only available to administrators.

This will list all of the flavor capabilities the provider supports and may
be configured via a flavor.

As an example, the amphora provider supports the `loadbalancer_topology`
capability, among many others::

  +-----------------------+---------------------------------------------------+
  | name                  | description                                       |
  +-----------------------+---------------------------------------------------+
  | loadbalancer_topology | The load balancer topology. One of: SINGLE - One  |
  |                       | amphora per load balancer. ACTIVE_STANDBY - Two   |
  |                       | amphora per load balancer.                        |
  | ...                   | ...                                               |
  +-----------------------+---------------------------------------------------+

Flavor Profiles
===============

.. _flavor profile: https://docs.openstack.org/api-ref/load-balancer/v2/index.html#create-flavor-profile

The next step in the process of creating a flavor is to define a flavor
profile. The flavor profile includes the provider and the flavor data.
The flavor capabilities are the supported flavor data settings for a given
provider. A flavor profile can be created using the `flavor profile`_ API or
the OpenStack client.

For example, to create a flavor for the amphora provider, we would create the
following flavor profile:

.. code-block:: bash

    openstack loadbalancer flavorprofile create --name amphora-single-profile --provider amphora --flavor-data '{"loadbalancer_topology": "SINGLE"}'

With the default RBAC policy, this command is only available to administrators.

This will create a flavor profile for the amphora provider that creates a load
balancer with a single amphora. When you create a flavor profile, the settings
are validated with the provider to make sure the provider can support the
capabilities specified.

The output of the command above is::

  +---------------+--------------------------------------+
  | Field         | Value                                |
  +---------------+--------------------------------------+
  | id            | 72b53ac2-b191-48eb-8f73-ed012caca23a |
  | name          | amphora-single-profile               |
  | provider_name | amphora                              |
  | flavor_data   | {"loadbalancer_topology": "SINGLE"}  |
  +---------------+--------------------------------------+

Flavors
=======

.. _flavor: https://docs.openstack.org/api-ref/load-balancer/v2/index.html#create-flavor

Finally we will create the user facing Octavia flavor. This defines the
information users will see and use to create a load balancer with an Octavia
flavor. The name of the flavor is the term users can use when creating a load
balancer.  We encourage you to include a detailed description for users to
clearly understand the capabilities of the flavor you are providing.

To continue the example above, to create a flavor with the flavor profile we
created in the previous step we call:

.. code-block:: bash

    openstack loadbalancer flavor create --name standalone-lb --flavorprofile 72b53ac2-b191-48eb-8f73-ed012caca23a --description "A non-high availability load balancer for testing." --enable

This will create a user visible Octavia flavor that will create a load balancer
that uses one amphora and is not highly available. Users can specify this
flavor when creating a new load balancer. Disabled flavors are still visible
to users, but they will not be able to create a load balancer using the flavor.

The output of the command above is::

  +-------------------+--------------------------------------+
  | Field             | Value                                |
  +-------------------+--------------------------------------+
  | id                | 25cda2d8-f735-4744-b936-d30405c05359 |
  | name              | standalone-lb                        |
  | flavor_profile_id | 72b53ac2-b191-48eb-8f73-ed012caca23a |
  | enabled           | True                                 |
  | description       | A non-high availability load b       |
  |                   | alancer for testing.                 |
  +-------------------+--------------------------------------+

At this point, the flavor is available for use by users creating new load
balancers.
