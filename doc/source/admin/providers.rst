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

==========================
Available Provider Drivers
==========================

Octavia supports enabling multiple provider drivers via the Octavia v2 API.
Drivers, other than the reference Amphora driver, exist outside of the Octavia
repository and are not maintained by the Octavia team. This list is intended
to provide a place for operators to discover and find available load balancing
provider drivers.

This list is a "best effort" to keep updated, so please check with your
favorite load balancer provider to see if they support OpenStack load
balancing. If they don't, make a request for support!

.. Note:: The provider drivers listed here may not be maintained by the
          OpenStack LBaaS team. Please submit bugs for these projects through
          their respective bug tracking systems.

Drivers are installed on all of your Octavia API instances using pip and
automatically integrated with Octavia using `setuptools entry points`_. Once
installed, operators can enable the provider by adding the provider to the
Octavia configuration file `enabled_provider_drivers`_ setting in the
[api_settings] section. Be sure to install and enable the provider on all of
your Octavia API instances.

.. _setuptools entry points: http://setuptools.readthedocs.io/en/latest/pkg_resources.html?#entry-points
.. _enabled_provider_drivers: https://docs.openstack.org/octavia/latest/configuration/configref.html#api_settings.enabled_provider_drivers

Amphora
=======

This is the reference driver for Octavia, meaning it is used for testing the
Octavia code base. It is an open source, scalable, and highly available load
balancing provider.

Default provider name: **amphora**

The driver package: https://pypi.org/project/octavia/

The driver source: https://git.openstack.org/cgit/openstack/octavia/

The documentation: https://docs.openstack.org/octavia/latest/

Where to report issues with the driver: https://storyboard.openstack.org/#!/project/908
