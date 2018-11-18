..
      Copyright 2018 Red Hat, Inc.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain a
      copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

====================================
Load Balancing Service Upgrade Guide
====================================

This document outlines steps and notes for operators for reference when
upgrading their Load Balancing service from previous versions of OpenStack.

Plan the upgrade
================

Before jumping right in to the upgrade process, there are a few considerations
operators should observe:

* Carefully read the release notes, particularly the upgrade section.

* Upgrades are only supported between sequential releases. For example,
  upgrading from Pike to Queens is supported while from Pike to Rocky is not.

* It is expected that each Load Balancing provider provides its own upgrade
  documentation. Please refer to it for upgrade instructions.

* The Load Balancing service builds on top of other OpenStack services, e.g.
  Compute, Networking, Image and Identify. On a staging environment, upgrade
  the Load Balancing service and verify it works as expected. For example, a
  good indicator would be the successful run of `Octavia Tempest tests
  <https://git.openstack.org/cgit/openstack/octavia-tempest-plugin>`.

Cold upgrade
============

In a cold upgrade (also known as offline upgrade and non-rolling upgrade), the
Load Balancing service is not available because all the control plane services
have to be taken down. No data plane disruption should result during the course
of upgrading. In the case of the Load Balancing service, it means no downtime
nor reconfiguration of service-managed resources (e.g. load balancers,
listeners, pools and members).

#. Run the :ref:`octavia-status upgrade check <octavia-status-checks>`
   command to validate that Octavia is ready for upgrade.

#. Gracefully stop all Octavia processes. We recommend in this order:
   Housekeeping, Health manager, API, Worker.

#. Optional: Make a backup of the database.

#. Upgrade all Octavia control plane nodes to the next release.

#. Verify that all configuration option names are up-to-date with latest
   Octavia version. For example, pay special attention to deprecated
   configurations.

#. Run ``octavia-db-manage upgrade head`` from any Octavia node to upgrade the
   database and run any corresponding database migrations.

#. Start all Octavia processes.

#. Build a new image and upload it to the Image service. Do not forget to tag
   the image. We recommend updating images frequently to include latest bug
   fixes and security issues on installed software (operating system, amphora
   agent and its dependencies).

Amphorae upgrade
================

Amphorae upgrade may be required in the advent of API incompatibility between
the running amphora agent (old version) and Octavia services (new version).
Octavia will automatically recover by failing over amphorae and thus new
amphora instances will be running on latest amphora agent code. The drawback in
that case is data plane downtime during failover. API breakage is a very rare
case, and would be highlighted in the release notes if this scenario occurs.

Upgrade testing
===============

`Grenade <https://docs.openstack.org/grenade/latest/>`_ is an OpenStack test
harness project that validates upgrade scenarios between releases. It uses
DevStack to initially perform a base OpenStack install and then upgrade to a
target version.

Octavia has a `Grenade plugin
<https://git.openstack.org/cgit/openstack/octavia/tree/devstack/upgrade>`_ and
a CI gate job that validates cold upgrades of an OpenStack deployment with
Octavia enabled. The plugin creates load balancing resources and verifies that
resources are still working during and after upgrade.
