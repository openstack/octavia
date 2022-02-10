===========================
Octavia Event Notifications
===========================
Octavia uses the oslo messaging notification system to send notifications for
certain events, such as "octavia.loadbalancer.create.end" after the completion
of a loadbalancer create operation.

Configuring oslo messaging for event notifications
==================================================
By default, the notifications driver in oslo_messaging is set to an empty
string; therefore, this option must be configured in order for notifications
to be sent. Valid options are defined in `oslo.messaging documentation
<https://docs.openstack.org/oslo.messaging/latest/configuration/opts.html#oslo-messaging-notifications>`__.
The example provided below is the format produced by the messagingv2 driver.

You may specify a custom list of topics on which to send notifications.
A topic is created for each notification level, with a dot and the level
appended to the value(s) specified in this list, e.g.: notifications.info,
octavia-notifications.info, etc..

Oslo messaging supports separate backends for RPC and notifications. If
different from the **[DEFAULT]** **transport_url** configuration, you
must specify the **transport_url** in the
**[oslo_messaging_notifications]** section of your *octavia.conf*
configuration.

.. code-block:: ini

    [oslo_messaging_notifications]
    driver = messagingv2
    topics = octavia-notifications,notifications
    transport_url = transport://user:pass@host1:port/virtual_host


Event Types
===========
Event types supported in Octavia are:

``'octavia.loadbalancer.update.end'``

``'octavia.loadbalancer.create.end'``

``'octavia.loadbalancer.delete.end'``

Example Notification
====================
The payload for an oslo.message notification for Octavia loadbalancer events
is the complete loadbalancer dict in json format.
The complete contents of an oslo.message notification for a loadbalancer
event in Octavia follows the format of the following example:

.. code-block:: json

    {
      "message_id": "d84a3800-06ca-410e-a1a3-b40a02306a97",
      "publisher_id": null,
      "event_type": "octavia.loadbalancer.create.end",
      "priority": "INFO",
      "payload": {
        "enabled": true,
        "availability_zone": null,
        "created_at": "2022-04-22T23:02:14.000000",
        "description": "",
        "flavor_id": null,
        "id": "8d4c8f66-7ac1-408e-82d5-59f6fcdea9ee",
        "listeners": [],
        "name": "my-octavia-loadbalancer",
        "operating_status": "OFFLINE",
        "pools": [],
        "project_id": "qs59p6z696cp9cho8ze96edddvpfyvgz",
        "provider": "amphora",
        "provisioning_status": "PENDING_CREATE",
        "tags": [],
        "updated_at": null,
        "vip": {
          "ip_address": "192.168.100.2",
          "network_id": "849b08a9-4397-4d6e-929d-90efc055ab8e",
          "port_id": "303870a4-bbc3-428c-98dd-492f423869d9",
          "qos_policy_id": null,
          "subnet_id": "d59311ee-ed3a-42c0-ac97-cebf7945facc"
        }
      },
      "timestamp": "2022-04-22 23:02:15.717375",
      "_unique_id": "71f03f00c96342328f09dbd92fe0d398",
      "_context_user": null,
      "_context_tenant": "qs59p6z696cp9cho8ze96edddvpfyvgz",
      "_context_system_scope": null,
      "_context_project": "qs59p6z696cp9cho8ze96edddvpfyvgz",
      "_context_domain": null,
      "_context_user_domain": null,
      "_context_project_domain": null,
      "_context_is_admin": false,
      "_context_read_only": false,
      "_context_show_deleted": false,
      "_context_auth_token": null,
      "_context_request_id": "req-072bab53-1b9b-46fa-92b0-7f04305c31bf",
      "_context_global_request_id": null,
      "_context_resource_uuid": null,
      "_context_roles": [],
      "_context_user_identity": "- qs59p6z696cp9cho8ze96edddvpfyvgz - - -",
      "_context_is_admin_project": true
    }


Disabling Event Notifications
=============================
By default, event notifications are enabled (see configuring oslo messaging
section above for additional requirements). To disable this feature, use
the following setting in your Octavia configuration file:

.. code-block:: ini

    [controller_worker]
    event_notifications = False

