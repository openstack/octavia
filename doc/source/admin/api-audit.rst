
====================
Octavia API Auditing
====================

The `keystonemiddleware audit middleware`_ supports delivery of Cloud Auditing
Data Federation (CADF) audit events via Oslo messaging notifier capability.
Based on `notification_driver` configuration, audit events can be routed to
messaging infrastructure (notification_driver = messagingv2) or can be routed
to a log file (notification_driver = log).

More information about the CADF format can be found on the `DMTF Cloud Auditing Data Federation website <https://www.dmtf.org/standards/cadf>`_.

Audit middleware creates two events per REST API interaction. First event has
information extracted from request data and the second one has request outcome
(response).

.. _keystonemiddleware audit middleware: https://docs.openstack.org/keystonemiddleware/latest/audit.html

Configuring Octavia API Auditing
================================

Auditing can be enabled by making the following changes to the Octavia
configuration file on your Octavia API instance(s).

#. Enable auditing::

    [audit]
    ...
    enabled = True

#. Optionally specify the location of the audit map file::

    [audit]
    ...
    audit_map_file = /etc/octavia/octavia_api_audit_map.conf

   The default audit map file location is /etc/octavia/octavia_api_audit_map.conf.

#. Copy the audit map file from the octavia/etc/audit directory to the
   location specified in the previous step. A sample file has been provided
   in octavia/etc/audit/octavia_api_audit_map.conf.sample.

#. Optionally specify the REST HTTP methods you do not want to audit::

    [audit]
    ...
    ignore_req_list =

#. Specify the driver to use for sending the audit notifications::

    [audit_middleware_notifications]
    ...
    driver = log

   Driver options are: messaging, messagingv2, routing, log, noop

#. Optionally specify the messaging topic::

    [audit_middleware_notifications]
    ...
    topics =

#. Optionally specify the messaging transport URL::

    [audit_middleware_notifications]
    ...
    transport_url =

#. Restart your Octavia API processes.

Sampe Audit Events
==================

Request
-------

.. code-block:: json

  {
    "event_type": "audit.http.request",
    "timestamp": "2018-10-11 22:42:22.721025",
    "payload": {
      "typeURI": "http://schemas.dmtf.org/cloud/audit/1.0/event",
      "eventTime": "2018-10-11T22:42:22.720112+0000",
      "target": {
        "id": "octavia",
        "typeURI": "service/load-balancer/loadbalancers",
        "addresses": [{
          "url": "http://10.21.21.53/load-balancer",
          "name": "admin"
        }, {
          "url": "http://10.21.21.53/load-balancer",
          "name": "private"
        }, {
          "url": "http://10.21.21.53/load-balancer",
          "name": "public"
        }],
        "name": "octavia"
      },
      "observer": {
        "id": "target"
      },
      "tags": ["correlation_id?value=e5b34bc3-4837-54fa-9892-8e65a9a2e73a"],
      "eventType": "activity",
      "initiator": {
        "typeURI": "service/security/account/user",
        "name": "admin",
        "credential": {
          "token": "***",
          "identity_status": "Confirmed"
        },
        "host": {
          "agent": "openstacksdk/0.17.2 keystoneauth1/3.11.0 python-requests/2.19.1 CPython/2.7.12",
          "address": "10.21.21.53"
        },
        "project_id": "90168d185e504b5580884a235ba31612",
        "id": "2af901396a424d5ca9dffa725226e8c7"
      },
      "action": "read/list",
      "outcome": "pending",
      "id": "8cf14af5-246e-5739-a11e-513ca13b7d36",
      "requestPath": "/load-balancer/v2.0/lbaas/loadbalancers"
    },
    "priority": "INFO",
    "publisher_id": "uwsgi",
    "message_id": "63264e0e-e60f-4adc-a656-0d87ab5d6329"
  }

Response
--------

.. code-block:: json

  {
    "event_type": "audit.http.response",
    "timestamp": "2018-10-11 22:42:22.853129",
    "payload": {
      "typeURI": "http://schemas.dmtf.org/cloud/audit/1.0/event",
      "eventTime": "2018-10-11T22:42:22.720112+0000",
      "target": {
        "id": "octavia",
        "typeURI": "service/load-balancer/loadbalancers",
        "addresses": [{
          "url": "http://10.21.21.53/load-balancer",
          "name": "admin"
        }, {
          "url": "http://10.21.21.53/load-balancer",
          "name": "private"
        }, {
          "url": "http://10.21.21.53/load-balancer",
          "name": "public"
        }],
        "name": "octavia"
      },
      "observer": {
        "id": "target"
      },
      "tags": ["correlation_id?value=e5b34bc3-4837-54fa-9892-8e65a9a2e73a"],
      "eventType": "activity",
      "initiator": {
        "typeURI": "service/security/account/user",
        "name": "admin",
        "credential": {
          "token": "***",
          "identity_status": "Confirmed"
        },
        "host": {
          "agent": "openstacksdk/0.17.2 keystoneauth1/3.11.0 python-requests/2.19.1 CPython/2.7.12",
          "address": "10.21.21.53"
        },
        "project_id": "90168d185e504b5580884a235ba31612",
        "id": "2af901396a424d5ca9dffa725226e8c7"
      },
      "reason": {
        "reasonCode": "200",
        "reasonType": "HTTP"
      },
      "reporterchain": [{
        "reporterTime": "2018-10-11T22:42:22.852613+0000",
        "role": "modifier",
        "reporter": {
          "id": "target"
        }
      }],
      "action": "read/list",
      "outcome": "success",
      "id": "8cf14af5-246e-5739-a11e-513ca13b7d36",
      "requestPath": "/load-balancer/v2.0/lbaas/loadbalancers"
    },
    "priority": "INFO",
    "publisher_id": "uwsgi",
    "message_id": "7cd89dce-af6e-40c5-8634-e87d1ed32a3c"
  }
