..
      Copyright 2019 Red Hat, Inc. All rights reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

==============================
Octavia Amphora Log Offloading
==============================

The default logging configuration will store the logs locally, on the amphora
filesystem with file rotation.

Octavia Amphorae can offload their log files via the syslog protocol to syslog
receivers via the load balancer management network (lb-mgmt-net). This allows
log aggregation of both administrative logs and also tenant traffic flow logs.
The syslog receivers can either be local to the load balancer management
network or routable via the load balancer management network.
By default any syslog receiver that supports UDP or TCP syslog protocol can
be used, however the operator also has the option to create an override
rsyslog configuration template to enable other features or protocols their
Amphora image may support.

This guide will discuss the features of :term:`Amphora` log offloading and how
to configure them.

Administrative Logs
===================

The administrative log offloading feature of the :term:`Amphora` covers all of
the system logging inside the :term:`Amphora` except for the tenant flow logs.
Tenant flow logs can be sent to and processed by the same syslog receiver used
by the administrative logs, but they are configured seperately.

All administrative log messages will be sent using the native log format
for the application sending the message.

Enabling Administrative Log Offloading
--------------------------------------

One or more syslog receiver endpoints must be configured in the Octavia
configuration file to enable administrative log offloading. The first endpoint
will be the primary endpoint to receive the syslog packets. Should the first
endpoint become unavailable, the additional endpoints listed will be tried
one at a time.

.. note::

    Secondary syslog endpoints will only be used if the log_protocol is
    configured for TCP. With the UDP syslog protocol, rsyslog is unable
    to detect if the primary endpoint has failed.

To configure administrative log offloading, set the following setting in your
Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [amphora_agent]
    admin_log_targets = 192.0.2.1:10514, 2001:db8:1::10:10514

In this example, the primary syslog receiver will be 192.0.2.1 on port 10514.
The backup syslog receiver will be 2001:db8:1::10 on port 10514.

.. note::

    Make sure your syslog receiver endpoints are accessible from the load
    balancer management network and you have configured the required
    security group or firewall rules to allow the traffic. These endpoints
    can be routable addresses from the load balancer management network.

The load balancer related administrative logs will be sent using a
LOG_LOCAL[0-7] facility. The facility number defaults to 1, but is configurable
using the administrative_log_facility setting in the Octavia configuration
file.

To configure administrative log facility, set the following setting in your
Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [amphora_agent]
    administrative_log_facility = 1

Forwarding All Administrative Logs
----------------------------------

By default, the Amphorae will only forward load balancer related administrative
logs, such as the haproxy admin logs, keepalived, and :term:`Amphora` agent
logs.
You can optionally configure the Amphorae to send all of the administrative
logs from the :term:`Amphora`, such as the kernel, system, and security logs.
Even with this setting the tenant flow logs will not be included. You can
configure tenant flow log forwarding in the `Tenant Flow Logs`_ section.

The load balancer related administrative logs will be sent using the
LOG_LOCAL[0-7] configured using the administrative_log_facility setting. All
other administrative log messages will use their native syslog facilities.

To configure the Amphorae to forward all administrative logs, set the following
setting in your Octavia configuration file for all of the controllers and
restart them:

.. code-block:: ini

    [amphora_agent]
    forward_all_logs = True

Tenant Flow Logs
================

Enabling Tenant Flow Log Offloading
-----------------------------------

One or more syslog receiver endpoints must be configured in the Octavia
configuration file to enable tenant flow log offloading. The first endpoint
will be the primary endpoint to receive the syslog packets. Should the first
endpoint become unavailable, the additional endpoints listed will be tried
one at a time. The endpoints configured for tenant flow log offloading may be
the same endpoints as the administrative log offloading configuration.

.. warning::

    Tenant flow logging can produce a large number of syslog messages
    depending on how many connections the load balancers are receiving.
    Tenant flow logging produces one log entry per connection to the
    load balancer. We recommend you monitor, size, and configure your syslog
    receivers appropriately based on the expected number of connections your
    load balancers will be handling.

.. note::

    Secondary syslog endpoints will only be used if the log_protocol is
    configured for TCP. With the UDP syslog protocol, rsyslog is unable
    to detect if the primary endpoint has failed.

To configure tenant flow log offloading, set the following setting in your
Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [amphora_agent]
    tenant_log_targets = 192.0.2.1:10514, 2001:db8:1::10:10514

In this example, the primary syslog receiver will be 192.0.2.1 on port 10514.
The backup syslog receiver will be 2001:db8:1::10 on port 10514.

.. note::

    Make sure your syslog receiver endpoints are accessible from the load
    balancer management network and you have configured the required
    security group or firewall rules to allow the traffic. These endpoints
    can be routable addresses from the load balancer management network.

The load balancer related tenant flow logs will be sent using a
LOG_LOCAL[0-7] facility. The facility number defaults to 0, but is configurable
using the user_log_facility setting in the Octavia configuration file.

To configure the tenant flow log facility, set the following setting in your
Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [amphora_agent]
    user_log_facility = 0

Tenant Flow Log Format
----------------------

The default tenant flow log format is:

.. code-block::

    project_id loadbalancer_id listener_id client_ip client_port data_time
    request_string http_status bytes_read bytes_uploaded
    client_certificate_verify(0 or 1) client_certificate_distinguised_name
    pool_id member_id processing_time(ms) termination_state

Any field that is unknown or not applicable to the connection will have a '-'
character in its place.

An example log entry when using rsyslog as the syslog receiver is:

.. note::

    The prefix[1] in this example comes from the rsyslog receiver and is not
    part of the syslog message from the amphora.

    [1] "Jun 12 00:44:13 amphora-3e0239c3-5496-4215-b76c-6abbe18de573 haproxy[1644]:"

.. code-block::

    Jun 12 00:44:13 amphora-3e0239c3-5496-4215-b76c-6abbe18de573 haproxy[1644]: 5408b89aa45b48c69a53dca1aaec58db fd8f23df-960b-4b12-ba62-2b1dff661ee7 261ecfc2-9e8e-4bba-9ec2-3c903459a895 172.24.4.1 41152 12/Jun/2019:00:44:13.030 "GET / HTTP/1.1" 200 76 73 - "" e37e0e04-68a3-435b-876c-cffe4f2138a4 6f2720b3-27dc-4496-9039-1aafe2fee105 4 --

Custom Tenant Flow Log Format
-----------------------------

You can optionally specify a custom log format for the tenant flow logs.
This string follows the HAProxy log format variables with the exception of
the "{{ project_id }}" and "{{ lb_id }}" variables that will be replaced
by the Octavia :term:`Amphora` driver. These custom variables are optional.

See the HAProxy documentation for `Custom log format <http://cbonte.github.io/haproxy-dconv/1.9/configuration.html#8.2.4>`_ variable definitions.

To configure a custom log format, set the following setting in your
Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [haproxy_amphora]
    user_log_format = '{{ project_id }} {{ lb_id }} %f %ci %cp %t %{+Q}r %ST %B %U %[ssl_c_verify] %{+Q}[ssl_c_s_dn] %b %s %Tt %tsc'

Disabling Logging
=================

There may be cases where you need to disable logging inside the
:term:`Amphora`, such as complying with regulatory standards.
Octavia provides multiple options for disabling :term:`Amphora` logging.

Disable Local Log Storage
-------------------------

This setting stops log entries from being written to the disk inside the
:term:`Amphora`. Logs can still be sent via :term:`Amphora` log offloading if
log offloading is configured for the Amphorae. Enabling this setting may
provide a performance benefit to the load balancer.

.. warning::

    This feature disables ALL log storage in the :term:`Amphora`, including
    kernel, system, and security logging.

.. note::

    If you enable this setting and are not using :term:`Amphora` log
    offloading, we recommend you also `Disable Tenant Flow Logging`_ to
    improve load balancing performance.

To disable local log storage in the :term:`Amphora`, set the following setting
in your Octavia configuration file for all of the controllers and restart them:

.. code-block:: ini

    [amphora_agent]
    disable_local_log_storage = True

Disable Tenant Flow Logging
---------------------------

This setting allows you to disable tenant flow logging irrespective of the
other logging configuration settings. It will take precedent over the other
settings. When this setting is enabled, no tenant flow (connection) logs will
be written to the disk inside the :term:`Amphora` or be sent via the
:term:`Amphora` log offloading.

.. note::

    Disabling tenant flow logging can also improve the load balancing
    performance of the amphora. Due to the potential performance improvement,
    we recommend you enable this setting when using the
    `Disable Local Log Storage`_ setting.

To disable tenant flow logging, set the following setting in your Octavia
configuration file for all of the controllers and restart them:

.. code-block:: ini

    [haproxy_amphora]
    connection_logging = False
