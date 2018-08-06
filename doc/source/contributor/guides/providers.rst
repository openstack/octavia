..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

=================================
Provider Driver Development Guide
=================================
This document is intended as a guide for developers creating provider drivers
for the Octavia API. This guide is intended to be an up to date version of the
`provider driver specification`_ previously approved.

.. _provider driver specification: ../specs/version1.1/enable-provider-driver.html

How Provider Drivers Integrate
==============================
Available drivers will be enabled by entries in the Octavia configuration file.
Drivers will be loaded via stevedore and Octavia will communicate with drivers
through a standard class interface defined below. Most driver functions will be
asynchronous to Octavia, and Octavia will provide a library of functions
that give drivers a way to update status and statistics. Functions that are
synchronous are noted below.

Octavia API functions not listed here will continue to be handled by the
Octavia API and will not call into the driver. Examples would be show, list,
and quota requests.

Driver Entry Points
-------------------

Provider drivers will be loaded via
`stevedore <https://docs.openstack.org/stevedore/latest/>`_. Drivers will
have an entry point defined in their setup tools configuration using the
Octavia driver namespace "octavia.api.drivers". This entry point name will
be used to enable the driver in the Octavia configuration file and as the
"provider" parameter users specify when creating a load balancer. An example
for the octavia reference driver would be:

.. code-block:: python

  amphora = octavia.api.drivers.amphora_driver.driver:AmphoraProviderDriver

Stable Provider Driver Interface
================================

Provider drivers should only access the following Octavia APIs. All other
Octavia APIs are not considered stable or safe for provider driver use and
may change at any time.

* octavia.api.drivers.data_models
* octavia.api.drivers.driver_lib
* octavia.api.drivers.exceptions
* octavia.api.drivers.provider_base

Octavia Provider Driver API
===========================

Provider drivers will be expected to support the full interface described
by the Octavia API, currently v2.0. If a driver does not implement an API
function, drivers should fail a request by raising a ``NotImplementedError``
exception. If a driver implements a function but does not support a particular
option passed in by the caller, the driver should raise an
``UnsupportedOptionError``.

It is recommended that drivers use the
`jsonschema <https://github.com/Julian/jsonschema>`_ package or
`voluptuous <https://pypi.org/project/voluptuous>`_ to validate the
request against the current driver capabilities.

See the `Exception Model`_ below for more details.

.. note:: Driver developers should refer to the official
          `Octavia API reference`_ document for details of the fields and
          expected outcome of these calls.

.. _Octavia API reference: https://developer.openstack.org/api-ref/load-balancer/v2/index.html

Load balancer
-------------

Create
^^^^^^

Creates a load balancer.

Octavia will pass in the load balancer object with all requested settings.

The load balancer will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver.  The driver
will be responsible for updating the provisioning status of the load
balancer to either ``ACTIVE`` if successfully created, or ``ERROR`` if not
created.

The Octavia API will accept and do basic API validation of the create
request from the user. The load balancer python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The provider will be removed as this is used for driver selection.
2. The flavor will be expanded from the provided ID to be the full
   dictionary representing the flavor metadata.

**Load balancer object**

As of the writing of this specification the create load balancer object may
contain the following:

+-----------------+--------+-----------------------------------------------+
| Name            | Type   | Description                                   |
+=================+========+===============================================+
| admin_state_up  | bool   | Admin state: True if up, False if down.       |
+-----------------+--------+-----------------------------------------------+
| description     | string | A human-readable description for the resource.|
+-----------------+--------+-----------------------------------------------+
| flavor          | dict   | The flavor keys and values.                   |
+-----------------+--------+-----------------------------------------------+
| listeners       | list   | A list of `Listener objects`_.                |
+-----------------+--------+-----------------------------------------------+
| loadbalancer_id | string | ID of load balancer to create.                |
+-----------------+--------+-----------------------------------------------+
| name            | string | Human-readable name of the resource.          |
+-----------------+--------+-----------------------------------------------+
| pools           | list   | A list of `Pool object`_.                     |
+-----------------+--------+-----------------------------------------------+
| project_id      | string | ID of the project owning this resource.       |
+-----------------+--------+-----------------------------------------------+
| vip_address     | string | The IP address of the Virtual IP (VIP).       |
+-----------------+--------+-----------------------------------------------+
| vip_network_id  | string | The ID of the network for the VIP.            |
+-----------------+--------+-----------------------------------------------+
| vip_port_id     | string | The ID of the VIP port.                       |
+-----------------+--------+-----------------------------------------------+
|vip_qos_policy_id| string | The ID of the qos policy for the VIP.         |
+-----------------+--------+-----------------------------------------------+
| vip_subnet_id   | string | The ID of the subnet for the VIP.             |
+-----------------+--------+-----------------------------------------------+

The driver is expected to validate that the driver supports the request
and raise an exception if the request cannot be accepted.

**VIP port creation**

Some provider drivers will want to create the Neutron port for the VIP, and
others will want Octavia to create the port instead. In order to support both
use cases, the create_vip_port() method will ask provider drivers to create
a VIP port. If the driver expects Octavia to create the port, the driver
will raise a  NotImplementedError exception. Octavia will call this function
before calling loadbalancer_create() in order to determine if it should
create the VIP port. Octavia will call create_vip_port() with a loadbalancer
ID and a partially defined VIP dictionary. Provider drivers that support
port creation will create the port and return a fully populated VIP
dictionary.

**VIP dictionary**

+-----------------+--------+-----------------------------------------------+
| Name            | Type   | Description                                   |
+=================+========+===============================================+
| project_id      | string | ID of the project owning this resource.       |
+-----------------+--------+-----------------------------------------------+
| vip_address     | string | The IP address of the Virtual IP (VIP).       |
+-----------------+--------+-----------------------------------------------+
| vip_network_id  | string | The ID of the network for the VIP.            |
+-----------------+--------+-----------------------------------------------+
| vip_port_id     | string | The ID of the VIP port.                       |
+-----------------+--------+-----------------------------------------------+
|vip_qos_policy_id| string | The ID of the qos policy for the VIP.         |
+-----------------+--------+-----------------------------------------------+
| vip_subnet_id   | string | The ID of the subnet for the VIP.             |
+-----------------+--------+-----------------------------------------------+

**Creating a Fully Populated Load Balancer**

If the "listener" option is specified, the provider driver will iterate
through the list and create all of the child objects in addition to
creating the load balancer instance.

Delete
^^^^^^

Removes an existing load balancer.

Octavia will pass in the load balancer object and cascade boolean as
parameters.

The load balancer will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

The API includes an option for cascade delete. When cascade is set to
True, the provider driver will delete all child objects of the load balancer.

Failover
^^^^^^^^

Performs a failover of a load balancer.

Octavia will pass in the load balancer ID as a parameter.

The load balancer will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the load balancer to either ``ACTIVE`` if successfully failed over, or
``ERROR`` if not failed over.

Failover can mean different things in the context of a provider driver. For
example, the Octavia driver replaces the current amphora(s) with another
amphora. For another provider driver, failover may mean failing over from
an active system to a standby system.

Update
^^^^^^

Modifies an existing load balancer using the values supplied in the load
balancer object.

Octavia will pass in the original load balancer object which is the baseline
for the update, and a load balancer object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update load balancer object may
contain the following:

+-----------------+--------+-----------------------------------------------+
| Name            | Type   | Description                                   |
+=================+========+===============================================+
| admin_state_up  | bool   | Admin state: True if up, False if down.       |
+-----------------+--------+-----------------------------------------------+
| description     | string | A human-readable description for the resource.|
+-----------------+--------+-----------------------------------------------+
| loadbalancer_id | string | ID of load balancer to update.                |
+-----------------+--------+-----------------------------------------------+
| name            | string | Human-readable name of the resource.          |
+-----------------+--------+-----------------------------------------------+
|vip_qos_policy_id| string | The ID of the qos policy for the VIP.         |
+-----------------+--------+-----------------------------------------------+

The load balancer will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the load balancer to either ``ACTIVE`` if successfully updated, or
``ERROR`` if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

   class Driver(object):

     def create_vip_port(self, loadbalancer_id, vip_dictionary):
         """Creates a port for a load balancer VIP.

         If the driver supports creating VIP ports, the driver will create a
         VIP port and return the vip_dictionary populated with the vip_port_id.
         If the driver does not support port creation, the driver will raise
         a NotImplementedError.

         :param: loadbalancer_id (string): ID of loadbalancer.
         :param: vip_dictionary (dict): The VIP dictionary.
         :returns: VIP dictionary with vip_port_id.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: The driver does not support creating
           VIP ports.
         """
         raise NotImplementedError()

     def loadbalancer_create(self, loadbalancer):
         """Creates a new load balancer.

         :param loadbalancer (object): The load balancer object.
         :return: Nothing if the create request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: The driver does not support create.
         :raises UnsupportedOptionError: The driver does not
           support one of the configuration options.
         """
         raise NotImplementedError()

     def loadbalancer_delete(self, loadbalancer, cascade=False):
         """Deletes a load balancer.

         :param loadbalancer (object): The load balancer object.
         :param cascade (bool): If True, deletes all child objects (listeners,
           pools, etc.) in addition to the load balancer.
         :return: Nothing if the delete request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: if driver does not support request.
         """
         raise NotImplementedError()

     def loadbalancer_failover(self, loadbalancer_id):
         """Performs a fail over of a load balancer.

         :param loadbalancer_id (string): ID of the load balancer to failover.
         :return: Nothing if the failover request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises: NotImplementedError if driver does not support request.
         """
         raise NotImplementedError()

     def loadbalancer_update(self, old_loadbalancer, new_loadbalancer):
         """Updates a load balancer.

         :param old_loadbalancer (object): The baseline load balancer object.
         :param new_loadbalancer (object): The updated load balancer object.
         :return: Nothing if the update request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: The driver does not support request.
         :raises UnsupportedOptionError: The driver does not
           support one of the configuration options.
         """
         raise NotImplementedError()

Listener
--------

Create
^^^^^^

Creates a listener for a load balancer.

Octavia will pass in the listener object with all requested settings.

The listener will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver. The driver
will be responsible for updating the provisioning status of the listener
to either ``ACTIVE`` if successfully created, or ``ERROR`` if not created.

The Octavia API will accept and do basic API validation of the create
request from the user.  The listener python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
deprecated. The listener will inherit the project_id from the parent
load balancer.
2. The default_tls_container_ref will be expanded and provided to the driver
in PEM format.
3. The sni_container_refs will be expanded and provided to the driver in
PEM format.

.. _Listener objects:

**Listener object**

As of the writing of this specification the create listener object may
contain the following:

+----------------------------+--------+-------------------------------------+
| Name                       | Type   | Description                         |
+============================+========+=====================================+
| admin_state_up             | bool   | Admin state: True if up, False if   |
|                            |        | down.                               |
+----------------------------+--------+-------------------------------------+
| connection_limit           | int    | The max number of connections       |
|                            |        | permitted for this listener. Default|
|                            |        | is -1, which is infinite            |
|                            |        | connections.                        |
+----------------------------+--------+-------------------------------------+
| default_pool               | object | A `Pool object`_.                   |
+----------------------------+--------+-------------------------------------+
| default_pool_id            | string | The ID of the pool used by the      |
|                            |        | listener if no L7 policies match.   |
+----------------------------+--------+-------------------------------------+
| default_tls_container_data | dict   | A `TLS container`_ dict.            |
+----------------------------+--------+-------------------------------------+
| default_tls_container_refs | string | The reference to the secrets        |
|                            |        | container.                          |
+----------------------------+--------+-------------------------------------+
| description                | string | A human-readable description for the|
|                            |        | listener.                           |
+----------------------------+--------+-------------------------------------+
| insert_headers             | dict   | A dictionary of optional headers to |
|                            |        | insert into the request before it is|
|                            |        | sent to the backend member. See     |
|                            |        | `Supported HTTP Header Insertions`_.|
|                            |        | Keys and values are specified as    |
|                            |        | strings.                            |
+----------------------------+--------+-------------------------------------+
| l7policies                 | list   | A list of `L7policy objects`_.      |
+----------------------------+--------+-------------------------------------+
| listener_id                | string | ID of listener to create.           |
+----------------------------+--------+-------------------------------------+
| loadbalancer_id            | string | ID of load balancer.                |
+----------------------------+--------+-------------------------------------+
| name                       | string | Human-readable name of the listener.|
+----------------------------+--------+-------------------------------------+
| protocol                   | string | Protocol type: One of HTTP, HTTPS,  |
|                            |        | TCP, or TERMINATED_HTTPS.           |
+----------------------------+--------+-------------------------------------+
| protocol_port              | int    | Protocol port number.               |
+----------------------------+--------+-------------------------------------+
| sni_container_data         | list   | A list of `TLS container`_ dict.    |
+----------------------------+--------+-------------------------------------+
| sni_container_refs         | list   | A list of references to the SNI     |
|                            |        | secrets containers.                 |
+----------------------------+--------+-------------------------------------+
| timeout_client_data        | int    | Frontend client inactivity timeout  |
|                            |        | in milliseconds.                    |
+----------------------------+--------+-------------------------------------+
| timeout_member_connect     | int    | Backend member connection timeout in|
|                            |        | milliseconds.                       |
+----------------------------+--------+-------------------------------------+
| timeout_member_data        | int    | Backend member inactivity timeout in|
|                            |        | milliseconds.                       |
+----------------------------+--------+-------------------------------------+
| timeout_tcp_inspect        | int    | Time, in milliseconds, to wait for  |
|                            |        | additional TCP packets for content  |
|                            |        | inspection.                         |
+----------------------------+--------+-------------------------------------+

.. _TLS container:

As of the writing of this specification the TLS container dictionary
contains the following:

+---------------+--------+------------------------------------------------+
| Key           | Type   | Description                                    |
+===============+========+================================================+
| certificate   | string | The PEM encoded certificate.                   |
+---------------+--------+------------------------------------------------+
| intermediates | List   | A list of intermediate PEM certificates.       |
+---------------+--------+------------------------------------------------+
| passphrase    | string | The private_key passphrase.                    |
+---------------+--------+------------------------------------------------+
| primary_cn    | string | The primary common name of the certificate.    |
+---------------+--------+------------------------------------------------+
| private_key   | string | The PEM encoded private key.                   |
+---------------+--------+------------------------------------------------+

.. _Supported HTTP Header Insertions:

As of the writing of this specification the Supported HTTP Header Insertions
are:

+-------------------+--------+------------------------------------------------+
| Key               | Type   | Description                                    |
+===================+========+================================================+
| X-Forwarded-For   | bool   | When True a X-Forwarded-For header is inserted |
|                   |        | into the request to the backend member that    |
|                   |        | specifies the client IP address.               |
+-------------------+--------+------------------------------------------------+
| X-Forwarded-Port  | int    | A X-Forwarded-Port header is inserted into the |
|                   |        | request to the backend member that specifies   |
|                   |        | the integer provided. Typically this is used to|
|                   |        | indicate the port the client connected to on   |
|                   |        | the load balancer.                             |
+-------------------+--------+------------------------------------------------+
| X-Forwarded-Proto | bool   | A X-Forwarded-Proto header is inserted into    |
|                   |        | the end of request to the backend member.      |
|                   |        | HTTP for the HTTP listener protocol type,      |
|                   |        | HTTPS for the TERMINATED_HTTPS listener        |
|                   |        | protocol type.                                 |
+-------------------+--------+------------------------------------------------+

**Creating a Fully Populated Listener**

If the "default_pool" or "l7policies" option is specified, the provider
driver will create all of the child objects in addition to creating the
listener instance.

Delete
^^^^^^

Deletes an existing listener.

Octavia will pass the listener object as a parameter.

The listener will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

Update
^^^^^^

Modifies an existing listener using the values supplied in the listener
object.

Octavia will pass in the original listener object which is the baseline for the
update, and a listener object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update listener object may
contain the following:

+----------------------------+--------+-------------------------------------+
| Name                       | Type   | Description                         |
+============================+========+=====================================+
| admin_state_up             | bool   | Admin state: True if up, False if   |
|                            |        | down.                               |
+----------------------------+--------+-------------------------------------+
| connection_limit           | int    | The max number of connections       |
|                            |        | permitted for this listener. Default|
|                            |        | is -1, which is infinite            |
|                            |        | connections.                        |
+----------------------------+--------+-------------------------------------+
| default_pool_id            | string | The ID of the pool used by the      |
|                            |        | listener if no L7 policies match.   |
+----------------------------+--------+-------------------------------------+
| default_tls_container_data | dict   | A `TLS container`_ dict.            |
+----------------------------+--------+-------------------------------------+
| default_tls_container_refs | string | The reference to the secrets        |
|                            |        | container.                          |
+----------------------------+--------+-------------------------------------+
| description                | string |  A human-readable description for   |
|                            |        |  the listener.                      |
+----------------------------+--------+-------------------------------------+
| insert_headers             | dict   | A dictionary of optional headers to |
|                            |        | insert into the request before it is|
|                            |        | sent to the backend member. See     |
|                            |        | `Supported HTTP Header Insertions`_.|
|                            |        | Keys and values are specified as    |
|                            |        | strings.                            |
+----------------------------+--------+-------------------------------------+
| listener_id                | string | ID of listener to update.           |
+----------------------------+--------+-------------------------------------+
| name                       | string | Human-readable name of the listener.|
+----------------------------+--------+-------------------------------------+
| sni_container_data         | list   | A list of `TLS container`_ dict.    |
+----------------------------+--------+-------------------------------------+
| sni_container_refs         | list   | A list of references to the SNI     |
|                            |        | secrets containers.                 |
+----------------------------+--------+-------------------------------------+
| timeout_client_data        | int    | Frontend client inactivity timeout  |
|                            |        | in milliseconds.                    |
+----------------------------+--------+-------------------------------------+
| timeout_member_connect     | int    | Backend member connection timeout in|
|                            |        | milliseconds.                       |
+----------------------------+--------+-------------------------------------+
| timeout_member_data        | int    | Backend member inactivity timeout in|
|                            |        | milliseconds.                       |
+----------------------------+--------+-------------------------------------+
| timeout_tcp_inspect        | int    | Time, in milliseconds, to wait for  |
|                            |        | additional TCP packets for content  |
|                            |        | inspection.                         |
+----------------------------+--------+-------------------------------------+

The listener will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the listener to either ``ACTIVE`` if successfully updated, or ``ERROR``
if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

    class Driver(object):
      def listener_create(self, listener):
          """Creates a new listener.

          :param listener (object): The listener object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
        raise NotImplementedError()

      def listener_delete(self, listener):
          """Deletes a listener.

          :param listener (object): The listener object.
          :return: Nothing if the delete request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          """
          raise NotImplementedError()

      def listener_update(self, old_listener, new_listener):
          """Updates a listener.

          :param old_listener (object): The baseline listener object.
          :param new_listener (object): The updated listener object.
          :return: Nothing if the update request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

Pool
----

Create
^^^^^^

Creates a pool for a load balancer.

Octavia will pass in the pool object with all requested settings.

The pool will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver. The driver
will be responsible for updating the provisioning status of the pool
to either ``ACTIVE`` if successfully created, or ``ERROR`` if not created.

The Octavia API will accept and do basic API validation of the create
request from the user.  The pool python object representing the request
body will be passed to the driver create method as it was received and
validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
   deprecated. The listener will inherit the project_id from the parent
   load balancer.

.. _Pool object:

**Pool object**

As of the writing of this specification the create pool object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| description           | string | A human-readable description for the     |
|                       |        | pool.                                    |
+-----------------------+--------+------------------------------------------+
| healthmonitor         | object | A `Healthmonitor object`_.               |
+-----------------------+--------+------------------------------------------+
| lb_algorithm          | string | Load balancing algorithm: One of         |
|                       |        | ROUND_ROBIN, LEAST_CONNECTIONS, or       |
|                       |        | SOURCE_IP.                               |
+-----------------------+--------+------------------------------------------+
| loadbalancer_id       | string | ID of load balancer.                     |
+-----------------------+--------+------------------------------------------+
| listener_id           | string | ID of listener.                          |
+-----------------------+--------+------------------------------------------+
| members               | list   | A list of `Member objects`_.             |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the pool.         |
+-----------------------+--------+------------------------------------------+
| pool_id               | string | ID of pool to create.                    |
+-----------------------+--------+------------------------------------------+
| protocol              | string | Protocol type: One of HTTP, HTTPS,       |
|                       |        | PROXY, or TCP.                           |
+-----------------------+--------+------------------------------------------+
| session_persistence   | dict   | Defines session persistence as one of    |
|                       |        | {'type': <'HTTP_COOKIE' | 'SOURCE_IP'>}  |
|                       |        | OR                                       |
|                       |        | {'type': 'APP_COOKIE',                   |
|                       |        | 'cookie_name': <cookie_name>}            |
+-----------------------+--------+------------------------------------------+

Delete
^^^^^^

Removes an existing pool and all of its members.

Octavia will pass the pool object as a parameter.

The pool will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

Update
^^^^^^

Modifies an existing pool using the values supplied in the pool object.

Octavia will pass in the original pool object which is the baseline for the
update, and a pool object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update pool object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| description           | string | A human-readable description for the     |
|                       |        | pool.                                    |
+-----------------------+--------+------------------------------------------+
| lb_algorithm          | string | Load balancing algorithm: One of         |
|                       |        | ROUND_ROBIN, LEAST_CONNECTIONS, or       |
|                       |        | SOURCE_IP.                               |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the pool.         |
+-----------------------+--------+------------------------------------------+
| pool_id               | string | ID of pool to update.                    |
+-----------------------+--------+------------------------------------------+
| session_persistence   | dict   | Defines session persistence as one of    |
|                       |        | {'type': <'HTTP_COOKIE' | 'SOURCE_IP'>}  |
|                       |        | OR                                       |
|                       |        | {'type': 'APP_COOKIE',                   |
|                       |        | 'cookie_name': <cookie_name>}            |
+-----------------------+--------+------------------------------------------+

The pool will be in the ``PENDING_UPDATE`` provisioning_status when it is
passed to the driver. The driver will update the provisioning_status of the
pool to either ``ACTIVE`` if successfully updated, or ``ERROR`` if the
update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

    class Driver(object):
      def pool_create(self, pool):
          """Creates a new pool.

          :param pool (object): The pool object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

      def pool_delete(self, pool):
          """Deletes a pool and its members.

          :param pool (object): The pool object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          """
          raise NotImplementedError()

      def pool_update(self, old_pool, new_pool):
          """Updates a pool.

          :param old_pool (object): The baseline pool object.
          :param new_pool (object): The updated pool object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

Member
------

Create
^^^^^^

Creates a member for a pool.

Octavia will pass in the member object with all requested settings.

The member will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver. The driver
will be responsible for updating the provisioning status of the member
to either ``ACTIVE`` if successfully created, or ``ERROR`` if not created.

The Octavia API will accept and do basic API validation of the create
request from the user.  The member python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
   deprecated. The member will inherit the project_id from the parent
   load balancer.

.. _Member objects:

**Member object**

As of the writing of this specification the create member object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| address               | string | The IP address of the backend member to  |
|                       |        | receive traffic from the load balancer.  |
+-----------------------+--------+------------------------------------------+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| backup                | bool   | Is the member a backup? Backup members   |
|                       |        | only receive traffic when all non-backup |
|                       |        | members are down.                        |
+-----------------------+--------+------------------------------------------+
| member_id             | string | ID of member to create.                  |
+-----------------------+--------+------------------------------------------+
| monitor_address       | string | An alternate IP address used for health  |
|                       |        | monitoring a backend member.             |
+-----------------------+--------+------------------------------------------+
| monitor_port          | int    | An alternate protocol port used for      |
|                       |        | health monitoring a backend member.      |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the member.       |
+-----------------------+--------+------------------------------------------+
| pool_id               | string | ID of pool.                              |
+-----------------------+--------+------------------------------------------+
| protocol_port         | int    | The port on which the backend member     |
|                       |        | listens for traffic.                     |
+-----------------------+--------+------------------------------------------+
| subnet_id             | string | Subnet ID.                               |
+-----------------------+--------+------------------------------------------+
| weight                | int    | The weight of a member determines the    |
|                       |        | portion of requests or connections it    |
|                       |        | services compared to the other members of|
|                       |        | the pool. For example, a member with a   |
|                       |        | weight of 10 receives five times as many |
|                       |        | requests as a member with a weight of 2. |
|                       |        | A value of 0 means the member does not   |
|                       |        | receive new connections but continues to |
|                       |        | service existing connections. A valid    |
|                       |        | value is from 0 to 256. Default is 1.    |
+-----------------------+--------+------------------------------------------+

Delete
^^^^^^

Removes a pool member.

Octavia will pass the member object as a parameter.

The member will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

Update
^^^^^^

Modifies an existing member using the values supplied in the listener object.

Octavia will pass in the original member object which is the baseline for the
update, and a member object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update member object may contain
the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| backup                | bool   | Is the member a backup? Backup members   |
|                       |        | only receive traffic when all non-backup |
|                       |        | members are down.                        |
+-----------------------+--------+------------------------------------------+
| member_id             | string | ID of member to update.                  |
+-----------------------+--------+------------------------------------------+
| monitor_address       | string | An alternate IP address used for health  |
|                       |        | monitoring a backend member.             |
+-----------------------+--------+------------------------------------------+
| monitor_port          | int    | An alternate protocol port used for      |
|                       |        | health monitoring a backend member.      |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the member.       |
+-----------------------+--------+------------------------------------------+
| weight                | int    | The weight of a member determines the    |
|                       |        | portion of requests or connections it    |
|                       |        | services compared to the other members of|
|                       |        | the pool. For example, a member with a   |
|                       |        | weight of 10 receives five times as many |
|                       |        | requests as a member with a weight of 2. |
|                       |        | A value of 0 means the member does not   |
|                       |        | receive new connections but continues to |
|                       |        | service existing connections. A valid    |
|                       |        | value is from 0 to 256. Default is 1.    |
+-----------------------+--------+------------------------------------------+

The member will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the member to either ``ACTIVE`` if successfully updated, or ``ERROR``
if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

Batch Update
^^^^^^^^^^^^

Set the state of members for a pool in one API call. This may include
creating new members, deleting old members, and updating existing members.
Existing members are matched based on address/port combination.

For example, assume a pool currently has two members. These members have the
following address/port combinations: '192.0.2.15:80' and '192.0.2.16:80'.
Now assume a PUT request is made that includes members with address/port
combinations: '192.0.2.16:80' and '192.0.2.17:80'. The member '192.0.2.15:80'
will be deleted because it was not in the request. The member '192.0.2.16:80'
will be updated to match the request data for that member, because it was
matched. The member '192.0.2.17:80' will be created, because no such member
existed.

The members will be in the ``PENDING_CREATE``, ``PENDING_UPDATE``, or
``PENDING_DELETE`` provisioning_status when it is passed to the driver.
The driver will update the provisioning_status of the members to either
``ACTIVE`` or ``DELETED`` if successfully updated, or ``ERROR``
if the update was not successful.

The batch update method will supply a list of `Member objects`_.
Existing members not in this list should be deleted,
existing members in the list should be updated,
and members in the list that do not already exist should be created.

**Abstract class definition**

.. code-block:: python

    class Driver(object):
      def member_create(self, member):
          """Creates a new member for a pool.

          :param member (object): The member object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
      raise NotImplementedError()

      def member_delete(self, member):

          """Deletes a pool member.

          :param member (object): The member object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          """
          raise NotImplementedError()

      def member_update(self, old_member, new_member):

          """Updates a pool member.

          :param old_member (object): The baseline member object.
          :param new_member (object): The updated member object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

      def member_batch_update(self, members):
          """Creates, updates, or deletes a set of pool members.

          :param members (list): List of member objects.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

Health Monitor
--------------

Create
^^^^^^

Creates a health monitor on a pool.

Octavia will pass in the health monitor object with all requested settings.

The health monitor will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver. The driver
will be responsible for updating the provisioning status of the health
monitor to either ``ACTIVE`` if successfully created, or ``ERROR`` if not
created.

The Octavia API will accept and do basic API validation of the create
request from the user.  The healthmonitor python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
   deprecated. The listener will inherit the project_id from the parent
   load balancer.

.. _Healthmonitor object:

**Healthmonitor object**

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| delay                 | int    | The interval, in seconds, between health |
|                       |        | checks.                                  |
+-----------------------+--------+------------------------------------------+
| expected_codes        | string | The expected HTTP status codes to get    |
|                       |        | from a successful health check. This may |
|                       |        | be a single value, a list, or a range.   |
+-----------------------+--------+------------------------------------------+
| healthmonitor_id      | string | ID of health monitor to create.          |
+-----------------------+--------+------------------------------------------+
| http_method           | string | The HTTP method that the health monitor  |
|                       |        | uses for requests. One of CONNECT,       |
|                       |        | DELETE, GET, HEAD, OPTIONS, PATCH, POST, |
|                       |        | PUT, or TRACE.                           |
+-----------------------+--------+------------------------------------------+
| max_retries           | int    | The number of successful checks before   |
|                       |        | changing the operating status of the     |
|                       |        | member to ONLINE.                        |
+-----------------------+--------+------------------------------------------+
| max_retries_down      | int    | The number of allowed check failures     |
|                       |        | before changing the operating status of  |
|                       |        | the member to ERROR. A valid value is    |
|                       |        | from 1 to 10.                            |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the monitor.      |
+-----------------------+--------+------------------------------------------+
| pool_id               | string | The pool to monitor.                     |
+-----------------------+--------+------------------------------------------+
| timeout               | int    | The time, in seconds, after which a      |
|                       |        | health check times out. This value must  |
|                       |        | be less than the delay value.            |
+-----------------------+--------+------------------------------------------+
| type                  | string | The type of health monitor. One of HTTP, |
|                       |        | HTTPS, PING, TCP, or TLS-HELLO.          |
+-----------------------+--------+------------------------------------------+
| url_path              | string | The HTTP URL path of the request sent by |
|                       |        | the monitor to test the health of a      |
|                       |        | backend member. Must be a string that    |
|                       |        | begins with a forward slash (/).         |
+-----------------------+--------+------------------------------------------+

Delete
^^^^^^

Deletes an existing health monitor.

Octavia will pass in the health monitor object as a parameter.

The health monitor will be in the ``PENDING_DELETE`` provisioning_status
when it is passed to the driver. The driver will notify Octavia that the
delete was successful by setting the provisioning_status to ``DELETED``.
If the delete failed, the driver will update the provisioning_status to
``ERROR``.

Update
^^^^^^

Modifies an existing health monitor using the values supplied in the
health monitor object.

Octavia will pass in the original health monitor object which is the baseline
for the update, and a health monitor object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update health monitor object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| delay                 | int    | The interval, in seconds, between health |
|                       |        | checks.                                  |
+-----------------------+--------+------------------------------------------+
| expected_codes        | string | The expected HTTP status codes to get    |
|                       |        | from a successful health check. This may |
|                       |        | be a single value, a list, or a range.   |
+-----------------------+--------+------------------------------------------+
| healthmonitor_id      | string | ID of health monitor to create.          |
+-----------------------+--------+------------------------------------------+
| http_method           | string | The HTTP method that the health monitor  |
|                       |        | uses for requests. One of CONNECT,       |
|                       |        | DELETE, GET, HEAD, OPTIONS, PATCH, POST, |
|                       |        | PUT, or TRACE.                           |
+-----------------------+--------+------------------------------------------+
| max_retries           | int    | The number of successful checks before   |
|                       |        | changing the operating status of the     |
|                       |        | member to ONLINE.                        |
+-----------------------+--------+------------------------------------------+
| max_retries_down      | int    | The number of allowed check failures     |
|                       |        | before changing the operating status of  |
|                       |        | the member to ERROR. A valid value is    |
|                       |        | from 1 to 10.                            |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the monitor.      |
+-----------------------+--------+------------------------------------------+
| timeout               | int    | The time, in seconds, after which a      |
|                       |        | health check times out. This value must  |
|                       |        | be less than the delay value.            |
+-----------------------+--------+------------------------------------------+
| url_path              | string | The HTTP URL path of the request sent by |
|                       |        | the monitor to test the health of a      |
|                       |        | backend member. Must be a string that    |
|                       |        | begins with a forward slash (/).         |
+-----------------------+--------+------------------------------------------+

The health monitor will be in the ``PENDING_UPDATE`` provisioning_status
when it is passed to the driver. The driver will update the
provisioning_status of the health monitor to either ``ACTIVE`` if
successfully updated, or ``ERROR`` if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

    class Driver(object):
      def health_monitor_create(self, healthmonitor):
          """Creates a new health monitor.

          :param healthmonitor (object): The health monitor object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

      def health_monitor_delete(self, healthmonitor):
          """Deletes a healthmonitor_id.

          :param healthmonitor (object): The health monitor object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          """
          raise NotImplementedError()

      def health_monitor_update(self, old_healthmonitor, new_healthmonitor):
          """Updates a health monitor.

          :param old_healthmonitor (object): The baseline health monitor
            object.
          :param new_healthmonitor (object): The updated health monitor object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

L7 Policy
---------

Create
^^^^^^

Creates an L7 policy.

Octavia will pass in the L7 policy object with all requested settings.

The L7 policy will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver.  The driver
will be responsible for updating the provisioning status of the L7 policy
to either ``ACTIVE`` if successfully created, or ``ERROR`` if not created.

The Octavia API will accept and do basic API validation of the create
request from the user. The l7policy python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
   deprecated. The l7policy will inherit the project_id from the parent
   load balancer.

.. _L7policy objects:

**L7policy object**

As of the writing of this specification the create l7policy object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| action                | string | The L7 policy action. One of             |
|                       |        | REDIRECT_TO_POOL, REDIRECT_TO_URL, or    |
|                       |        | REJECT.                                  |
+-----------------------+--------+------------------------------------------+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| description           | string | A human-readable description for the     |
|                       |        | L7 policy.                               |
+-----------------------+--------+------------------------------------------+
| l7policy_id           | string | The ID of the L7 policy.                 |
+-----------------------+--------+------------------------------------------+
| listener_id           | string | The ID of the listener.                  |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the L7 policy.    |
+-----------------------+--------+------------------------------------------+
| position              | int    | The position of this policy on the       |
|                       |        | listener. Positions start at 1.          |
+-----------------------+--------+------------------------------------------+
| redirect_pool_id      | string | Requests matching this policy will be    |
|                       |        | redirected to the pool with this ID.     |
|                       |        | Only valid if action is REDIRECT_TO_POOL.|
+-----------------------+--------+------------------------------------------+
| redirect_url          | string | Requests matching this policy will be    |
|                       |        | redirected to this URL. Only valid if    |
|                       |        | action is REDIRECT_TO_URL.               |
+-----------------------+--------+------------------------------------------+
| rules                 | list   | A list of l7rule objects.                |
+-----------------------+--------+------------------------------------------+

*Creating a Fully Populated L7 policy*

If the "rules" option is specified, the provider driver will create all of
the child objects in addition to creating the L7 policy instance.

Delete
^^^^^^

Deletes an existing L7 policy.

Octavia will pass in the L7 policy object as a parameter.

The l7policy will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

Update
^^^^^^

Modifies an existing L7 policy using the values supplied in the l7policy
object.

Octavia will pass in the original L7 policy object which is the baseline for
the update, and an L7 policy object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update L7 policy object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| action                | string | The L7 policy action. One of             |
|                       |        | REDIRECT_TO_POOL, REDIRECT_TO_URL, or    |
|                       |        | REJECT.                                  |
+-----------------------+--------+------------------------------------------+
+-----------------------+--------+------------------------------------------+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| description           | string | A human-readable description for the     |
|                       |        | L7 policy.                               |
+-----------------------+--------+------------------------------------------+
| l7policy_id           | string | The ID of the L7 policy.                 |
+-----------------------+--------+------------------------------------------+
| name                  | string | Human-readable name of the L7 policy.    |
+-----------------------+--------+------------------------------------------+
| position              | int    | The position of this policy on the       |
|                       |        | listener. Positions start at 1.          |
+-----------------------+--------+------------------------------------------+
| redirect_pool_id      | string | Requests matching this policy will be    |
|                       |        | redirected to the pool with this ID.     |
|                       |        | Only valid if action is REDIRECT_TO_POOL.|
+-----------------------+--------+------------------------------------------+
| redirect_url          | string | Requests matching this policy will be    |
|                       |        | redirected to this URL. Only valid if    |
|                       |        | action is REDIRECT_TO_URL.               |
+-----------------------+--------+------------------------------------------+

The L7 policy will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the L7 policy to either ``ACTIVE`` if successfully updated, or ``ERROR``
if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

   class Driver(object):
     def l7policy_create(self, l7policy):
         """Creates a new L7 policy.

         :param l7policy (object): The l7policy object.
         :return: Nothing if the create request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: if driver does not support request.
         :raises UnsupportedOptionError: if driver does not
           support one of the configuration options.
         """
         raise NotImplementedError()

     def l7policy_delete(self, l7policy):
         """Deletes an L7 policy.

         :param l7policy (object): The l7policy object.
         :return: Nothing if the delete request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: if driver does not support request.
         """
         raise NotImplementedError()

    def l7policy_update(self, old_l7policy, new_l7policy):
         """Updates an L7 policy.

         :param old_l7policy (object): The baseline l7policy object.
         :param new_l7policy (object): The updated l7policy object.
         :return: Nothing if the update request was accepted.
         :raises DriverError: An unexpected error occurred in the driver.
         :raises NotImplementedError: if driver does not support request.
         :raises UnsupportedOptionError: if driver does not
           support one of the configuration options.
         """
         raise NotImplementedError()

L7 Rule
-------

Create
^^^^^^

Creates a new L7 rule for an existing L7 policy.

Octavia will pass in the L7 rule object with all requested settings.

The L7 rule will be in the ``PENDING_CREATE`` provisioning_status and
``OFFLINE`` operating_status when it is passed to the driver. The driver
will be responsible for updating the provisioning status of the L7 rule
to either ``ACTIVE`` if successfully created, or ``ERROR`` if not created.

The Octavia API will accept and do basic API validation of the create
request from the user.  The l7rule python object representing the
request body will be passed to the driver create method as it was received
and validated with the following exceptions:

1. The project_id will be removed, if present, as this field is now
   deprecated. The listener will inherit the project_id from the parent
   load balancer.

.. _L7rule objects:

**L7rule object**

As of the writing of this specification the create l7rule object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| compare_type          | string | The comparison type for the L7 rule. One |
|                       |        | of CONTAINS, ENDS_WITH, EQUAL_TO, REGEX, |
|                       |        | or STARTS_WITH.                          |
+-----------------------+--------+------------------------------------------+
| invert                | bool   | When True the logic of the rule is       |
|                       |        | inverted. For example, with invert True, |
|                       |        | equal to would become not equal to.      |
+-----------------------+--------+------------------------------------------+
| key                   | string | The key to use for the comparison. For   |
|                       |        | example, the name of the cookie to       |
|                       |        | evaluate.                                |
+-----------------------+--------+------------------------------------------+
| l7policy_id           | string | The ID of the L7 policy.                 |
+-----------------------+--------+------------------------------------------+
| l7rule_id             | string | The ID of the L7 rule.                   |
+-----------------------+--------+------------------------------------------+
| type                  | string | The L7 rule type. One of COOKIE,         |
|                       |        | FILE_TYPE, HEADER, HOST_NAME, or PATH.   |
+-----------------------+--------+------------------------------------------+
| value                 | string | The value to use for the comparison. For |
|                       |        | example, the file type to compare.       |
+-----------------------+--------+------------------------------------------+

Delete
^^^^^^

Deletes an existing L7 rule.

Octavia will pass in the L7 rule object as a parameter.

The L7 rule will be in the ``PENDING_DELETE`` provisioning_status when
it is passed to the driver. The driver will notify Octavia that the delete
was successful by setting the provisioning_status to ``DELETED``. If the
delete failed, the driver will update the provisioning_status to ``ERROR``.

Update
^^^^^^

Modifies an existing L7 rule using the values supplied in the l7rule object.

Octavia will pass in the original L7 rule object which is the baseline for the
update, and an L7 rule object with the fields to be updated.
Fields not updated by the user will contain "Unset" as defined in the data
model.

As of the writing of this specification the update L7 rule object may
contain the following:

+-----------------------+--------+------------------------------------------+
| Name                  | Type   | Description                              |
+=======================+========+==========================================+
| admin_state_up        | bool   | Admin state: True if up, False if down.  |
+-----------------------+--------+------------------------------------------+
| compare_type          | string | The comparison type for the L7 rule. One |
|                       |        | of CONTAINS, ENDS_WITH, EQUAL_TO, REGEX, |
|                       |        | or STARTS_WITH.                          |
+-----------------------+--------+------------------------------------------+
| invert                | bool   | When True the logic of the rule is       |
|                       |        | inverted. For example, with invert True, |
|                       |        | equal to would become not equal to.      |
+-----------------------+--------+------------------------------------------+
| key                   | string | The key to use for the comparison. For   |
|                       |        | example, the name of the cookie to       |
|                       |        | evaluate.                                |
+-----------------------+--------+------------------------------------------+
| l7rule_id             | string | The ID of the L7 rule.                   |
+-----------------------+--------+------------------------------------------+
| type                  | string | The L7 rule type. One of COOKIE,         |
|                       |        | FILE_TYPE, HEADER, HOST_NAME, or PATH.   |
+-----------------------+--------+------------------------------------------+
| value                 | string | The value to use for the comparison. For |
|                       |        | example, the file type to compare.       |
+-----------------------+--------+------------------------------------------+

The L7 rule will be in the ``PENDING_UPDATE`` provisioning_status when
it is passed to the driver. The driver will update the provisioning_status
of the L7 rule to either ``ACTIVE`` if successfully updated, or ``ERROR``
if the update was not successful.

The driver is expected to validate that the driver supports the request.
The method will then return or raise an exception if the request cannot be
accepted.

**Abstract class definition**

.. code-block:: python

  class Driver(object):
      def l7rule_create(self, l7rule):

          """Creates a new L7 rule.

          :param l7rule (object): The L7 rule object.
          :return: Nothing if the create request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

      def l7rule_delete(self, l7rule):

          """Deletes an L7 rule.

          :param l7rule (object): The L7 rule object.
          :return: Nothing if the delete request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          """
          raise NotImplementedError()

      def l7rule_update(self, old_l7rule, new_l7rule):

          """Updates an L7 rule.

          :param old_l7rule (object): The baseline L7 rule object.
          :param new_l7rule (object): The updated L7 rule object.
          :return: Nothing if the update request was accepted.
          :raises DriverError: An unexpected error occurred in the driver.
          :raises NotImplementedError: if driver does not support request.
          :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
          """
          raise NotImplementedError()

Flavor
------

Octavia flavors are defined in a separate `flavor specification`_.
Support for flavors will be provided through two provider driver interfaces,
one to query supported flavor metadata keys and another to validate that a
flavor is supported. Both functions are synchronous.

.. _flavor specification: ../specs/version1.0/flavors.html

get_supported_flavor_keys
^^^^^^^^^^^^^^^^^^^^^^^^^

Retrieves a dictionary of supported flavor keys and their description.

.. code-block:: python

    {"topology": "The load balancer topology for the flavor. One of: SINGLE, ACTIVE_STANDBY",
     "compute_flavor": "The compute driver flavor to use for the load balancer instances"}

validate_flavor
^^^^^^^^^^^^^^^

Validates that the driver supports the flavor metadata dictionary.

The validate_flavor method will be passed a flavor metadata dictionary that
the driver will validate. This is used when an operator uploads a new flavor
that applies to the driver.

The validate_flavor method will either return or raise a
``UnsupportedOptionError`` exception.

Following are interface definitions for flavor support:

.. code-block:: python

  def get_supported_flavor_metadata():
      """Returns a dictionary of flavor metadata keys supported by this driver.

      The returned dictionary will include key/value pairs, 'name' and
      'description.'

      :returns: The flavor metadata dictionary
      :raises DriverError: An unexpected error occurred in the driver.
      :raises NotImplementedError: The driver does not support flavors.
      """
      raise NotImplementedError()

.. code-block:: python

  def validate_flavor(flavor_metadata):
      """Validates if driver can support flavor as defined in flavor_metadata.

      :param flavor_metadata (dict): Dictionary with flavor metadata.
      :return: Nothing if the flavor is valid and supported.
      :raises DriverError: An unexpected error occurred in the driver.
      :raises NotImplementedError: The driver does not support flavors.
      :raises UnsupportedOptionError: if driver does not
            support one of the configuration options.
      """
      raise NotImplementedError()

Exception Model
---------------

DriverError
^^^^^^^^^^^

This is a catch all exception that drivers can return if there is an
unexpected error. An example might be a delete call for a load balancer the
driver does not recognize. This exception includes two strings: The user fault
string and the optional operator fault string. The user fault string,
"user_fault_string", will be provided to the API requester. The operator fault
string, "operator_fault_string",  will be logged in the Octavia API log file
for the operator to use when debugging.

.. code-block:: python


  class DriverError(Exception):
      user_fault_string = _("An unknown driver error occurred.")
      operator_fault_string = _("An unknown driver error occurred.")

      def __init__(self, *args, **kwargs):
          self.user_fault_string = kwargs.pop('user_fault_string',
                                              self.user_fault_string)
          self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                  self.operator_fault_string)

          super(DriverError, self).__init__(*args, **kwargs)

NotImplementedError
^^^^^^^^^^^^^^^^^^^

Driver implementations may not support all operations, and are free to reject
a request. If the driver does not implement an API function, the driver will
raise a NotImplementedError exception.

.. code-block:: python

  class NotImplementedError(Exception):
      user_fault_string = _("A feature is not implemented by this driver.")
      operator_fault_string = _("A feature is not implemented by this driver.")

      def __init__(self, *args, **kwargs):
          self.user_fault_string = kwargs.pop('user_fault_string',
                                              self.user_fault_string)
          self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                  self.operator_fault_string)

          super(NotImplementedError, self).__init__(*args, **kwargs)

UnsupportedOptionError
^^^^^^^^^^^^^^^^^^^^^^

Provider drivers will validate that they can complete the request -- that all
options are supported by the driver. If the request fails validation, drivers
will raise an UnsupportedOptionError exception. For example, if a driver does
not support a flavor passed as an option to load balancer create(), the driver
will raise an UnsupportedOptionError and include a message parameter providing
an explanation of the failure.

.. code-block:: python

  class UnsupportedOptionError(Exception):
      user_fault_string = _("A specified option is not supported by this driver.")
      operator_fault_string = _("A specified option is not supported by this driver.")

      def __init__(self, *args, **kwargs):
          self.user_fault_string = kwargs.pop('user_fault_string',
                                              self.user_fault_string)
          self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                  self.operator_fault_string)

          super(UnsupportedOptionError, self).__init__(*args, **kwargs)


Driver Support Library
======================

Provider drivers need support for updating provisioning status, operating
status, and statistics. Drivers will not directly use database operations,
and instead will callback to Octavia using a new API.

.. warning::

  The methods listed here are the only callable methods for drivers.
  All other interfaces are not considered stable or safe for drivers to
  access. See `Stable Provider Driver Interface`_ for a list of acceptable
  APIs for provider driver use.

.. warning::

  This library is interim and will be removed when the driver support endpoint
  is made available. At which point drivers will not import any code from
  Octavia.

Update Provisioning and Operating Status API
--------------------------------------------

The update status API defined below can be used by provider drivers
to update the provisioning and/or operating status of Octavia resources
(load balancer, listener, pool, member, health monitor, L7 policy, or L7
rule).

For the following status API, valid values for provisioning status
and operating status parameters are as defined by Octavia status codes. If an
existing object is not included in the input parameter, the status remains
unchanged.

provisioning_status: status associated with lifecycle of the
resource. See `Octavia Provisioning Status Codes <https://developer.openstack.org/api-ref/load-balancer/v2/index.html#provisioning-status-codes>`_.

operating_status: the observed status of the resource. See `Octavia
Operating Status Codes <https://developer.openstack.org/api-ref/load-balancer/v2/index.html#operating-status-codes>`_.

The dictionary takes this form:

.. code-block:: python

  { "loadbalancers": [{"id": "123",
                       "provisioning_status": "ACTIVE",
                       "operating_status": "ONLINE"},...],
    "healthmonitors": [],
    "l7policies": [],
    "l7rules": [],
    "listeners": [],
    "members": [],
    "pools": []
  }

.. code-block:: python

  def update_loadbalancer_status(status):
      """Update load balancer status.

      :param status (dict): dictionary defining the provisioning status and
          operating status for load balancer objects, including pools,
          members, listeners, L7 policies, and L7 rules.
      :raises: UpdateStatusError
      :returns: None
      """

Update Statistics API
---------------------

Provider drivers can update statistics for listeners using the following API.
Similar to the status function above, a single dictionary
with multiple listener statistics is used to update statistics in a single
call. If an existing listener is not included, the statistics that object
remain unchanged.

The general form of the input dictionary is a list of listener statistics:

.. code-block:: python

  { "listeners": [{"id": "123",
                       "active_connections": 12,
                       "bytes_in": 238908,
                       "bytes_out": 290234,
                       "request_errors": 0,
                       "total_connections": 3530},...]
  }

.. code-block:: python

  def update_listener_statistics(statistics):
      """Update listener statistics.

      :param statistics (dict): Statistics for listeners:
            id (string): ID of the listener.
            active_connections (int): Number of currently active connections.
            bytes_in (int): Total bytes received.
            bytes_out (int): Total bytes sent.
            request_errors (int): Total requests not fulfilled.
            total_connections (int): The total connections handled.
      :raises: UpdateStatisticsError
      :returns: None
      """

Get Resource Support
--------------------

Provider drivers may need to get information about an Octavia resource.
As an example of its use, a provider driver may need to sync with Octavia,
and therefore need to fetch all of the Octavia resources it is responsible
for managing. Provider drivers can use the existing Octavia API to get these
resources. See the `Octavia API Reference <https://developer.openstack.org/api-ref/load-balancer/v2/index.html>`_.

API Exception Model
-------------------

The driver support API will include two Exceptions, one for each of the
two API groups:

* UpdateStatusError
* UpdateStatisticsError

Each exception class will include a message field that describes the error and
references to the failed record if available.

.. code-block:: python

  class UpdateStatusError(Exception):
      fault_string = _("The status update had an unknown error.")
      status_object = None
      status_object_id = None
      status_record = None

      def __init__(self, *args, **kwargs):
          self.fault_string = kwargs.pop('fault_string',
                                         self.fault_string)
          self.status_object = kwargs.pop('status_object', None)
          self.status_object_id = kwargs.pop('status_object_id', None)
          self.status_record = kwargs.pop('status_record', None)

          super(UpdateStatusError, self).__init__(*args, **kwargs)

  class UpdateStatisticsError(Exception):
      fault_string = _("The statistics update had an unknown error.")
      stats_object = None
      stats_object_id = None
      stats_record = None

      def __init__(self, *args, **kwargs):
          self.fault_string = kwargs.pop('fault_string',
                                         self.fault_string)
          self.stats_object = kwargs.pop('stats_object', None)
          self.stats_object_id = kwargs.pop('stats_object_id', None)
          self.stats_record = kwargs.pop('stats_record', None)

          super(UpdateStatisticsError, self).__init__(*args, **kwargs)
