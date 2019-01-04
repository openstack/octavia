..
      Copyright (c) 2017 Rackspace

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
Operator Maintenance  Guide
======================================
This document is intended for operators. For a developer guide see the
:doc:`../../contributor/guides/dev-quick-start` in this documentation
repository. For an end-user guide, please see the
:doc:`../../user/guides/basic-cookbook` in this documentation repository.

Monitoring
==========


Monitoring Load Balancer Amphora
--------------------------------
Octavia will monitor the load balancing amphorae itself and initiate failovers
and/or replacements if they malfunction. Therefore, most installations won't
need to monitor the amphorae running the load balancer.

Octavia will log each failover to the corresponding health manager logs. It is
advisable to use log analytics to monitor failover trends to notice problems
in the OpenStack installation early. We have seen neutron (network)
connectivity issues, Denial of Service attacks, and nova (compute)
malfunctions lead to a higher than normal failover rate. Alternatively, the
monitoring of the other services showed problems as well, so depending on
your overall monitoring strategy this might be optional.

If additional monitoring is necessary, review the corresponding calls on
the amphora agent REST interface (see
:doc:`../../contributor/api/haproxy-amphora-api`)

Monitoring Pool Members
-----------------------

Octavia will use the health information from the underlying load balancing
application to determine the health of members. This information will be
streamed to the Octavia database and made available via the status
tree or other API methods. For critical applications we recommend to
poll this information in regular intervals.

Monitoring Load Balancers
-------------------------

For critical applications, we recommend to monitor the access to the
application with a tool which polls the application from various points
on the Internet and measures response times. Alerts should be triggered
when response times become too high.

An additional check might be to monitor the provisioning status of a
load balancer (see `Load Balance Status Codes
<https://developer.openstack.org/api-ref/load-balancer/v2/#status-codes>`_)
and alert depending on the application if the provisioning status is
not ACTIVE. For some applications other states might not lead to alerts:
For instance if an application is making regular changes to the pool
several PENDING stages should not alert as well.

In most cases, when a load balancer is in states other than ACTIVE it
will still be passing traffic, which is why the response time check
mentioned above is recommended. However, even if the load balancer
is still functioning, it is advisable to investigate and potentially
recreate it if it is stuck in a non-ACTIVE state.

Monitoring load balancer functionality
--------------------------------------

For production sites we recommend to use outside monitoring services. They
will use servers distributed around the globe to not only monitor if the site
is up but also parts of the system outside the visibility of Octavia like
routers, network connectivity, etc.

.. _Monasca Octavia plugin: https://github.com/openstack/monasca-agent/blob/master/monasca_setup/detection/plugins/octavia.py

Monitoring Octavia Control Plane
--------------------------------

To monitor the Octavia control plane we recommend process monitoring of the
main Octavia processes:

* octavia-api

* octavia-worker

* octavia-health-manager

* octavia-housekeeping

The Monasca project has a plugin for such monitoring (see
`Monasca Octavia plugin`_).
Please refer to this project for further information.

Octavia's control plane components are shared nothing and can be scaled
lineary. For high availability of the control plane we recommend to run at
least one set of components in each availability zone. Furthermore, the
octavia-api endpoint could be behind a load balancer or other HA technology.
That said, if one or more components fail the system will still be available
(though potentially degraded). For instance if you have installed one set of
components in three availability zones even if you lose a whole zone
Octavia will still be responsive and available - only if you lose the
Octavia control plane in all three zones will the service be unavailable.
Please note this only addresses control plane availability; the availability
of the load balancing function depends highly on the chosen topology and the
anti-affinity settings. See our forthcoming HA guide for more details.

Additionally, we recommend to monitor the Octavia API endpoint(s). There
currently is no special url to use so just polling the root URL in regular
intervals is sufficient.

There is a host of information in the log files which can be used for log
analytics. A few examples of what could be monitored are:

* Amphora Build Rate - to determine load of the system

* Amphora Build Time - to determine how long it takes to build an amphora

* Failures/Errors - to be notified of system problems early

.. _rotating_amphora:

Rotating the Amphora Images
===========================

Octavia will start load balancers with a pre-built image which contain the
amphora agent, a load balancing application, and are seeded with cryptographic
certificates through the config drive at start up.

Rotating the image means making a load balancer amphora running with an old
image failover to an amphora with a new image. This should be without any
measurable interruption in the load balancing functionality when using
ACTIVE/STANDBY topology. Standalone load balancers might experience a short
outage.

Here are some reasons you might need to rotate the amphora image:

* There has been a (security) update to the underlying operating system

* You want to deploy a new version of the amphora agent or haproxy

* The cryptographic certificates and/or keys on the amphora have been
  compromised.

* Though not related to rotating images, this procedure might be invoked if you
  are switching to a different flavor for the underlying virtual machine.

Preparing a New Amphora Image
-----------------------------

To prepare a new amphora image you will need to use diskimage-create.sh as
described in the README in the diskimage-create directory.

For instance, in the ``octavia/diskimage-create`` directory, run:

   .. code-block:: bash

     ./diskimage-create.sh

Once you have created a new image you will need to upload it into glance. The
following shows how to do this if you have set the image tag in the
Octavia configuration file. Make sure to use a user with the same tenant as
the Octavia service account:

 .. code-block:: bash

      openstack image create --file amphora-x64-haproxy.qcow2 \
      --disk-format qcow2 --tag <amphora-image-tag> --private \
      --container-format bare /var/lib/octavia/amphora-x64-haproxy.qcow2

If you didn't configure image tags and instead configured an image id, you
will need to update the Octavia configuration file with the new id and restart
the Octavia services (except octavia-api).

Generating a List of Load Balancers to Rotate
---------------------------------------------

The easiest way to generate a list, is to just list the IDs of all
load balancers:

 .. code-block:: bash

        openstack loadbalancer list -c id -f value

Take note of the IDs.

Rotate a Load Balancer
----------------------

Octavia has an API call to initiate the failover of a load balancer:

    .. code-block:: bash

        openstack loadbalancer failover <loadbalancer id>

You can observe the failover by querying octavia ``openstack load balancer
show  <loadbalancer id>`` until the load balancer goes ``ACTIVE`` again.

.. _best_practice:

Best Practices/Optimizations
----------------------------

To speed up the failovers, the spare pool can be temporarily increased to
accommodate the rapid failover of the amphora. In this case after the
new image has been loaded into glance, shut down or initiate a failover of the
amphora in the spare pool. They can be found, for instance, by looking for the
servers in ``openstack server list --all`` who only have an ip on the
management network assigned but not any tenant network. Alternatively, use this
database query:


    .. code-block:: bash

        mysql octavia -e 'select id, compute_id, lb_network_ip from amphora where status="READY";'


After you have increased the spare pool size and restarted all Octavia
services, failovers will be greatly accelerated. To preserve resources,
restore the old settings and restart the Octavia services. Since Octavia won't
terminate superfluous spare amphora on its own, they can be left in the system
and will automatically be used up as new load balancers are created and/or
load balancers in error state are failed over.

.. warning::
    If you are using the anti-affinity feature please be aware that it is
    not compatible with spare pools and you are risking both the ACTIVE and
    BACKUP amphora being scheduled on the same host. It is recommended to
    not increase the spare pool during fail overs in this case (and not to use
    the spare pool at all).

Since a failover puts significant load on the OpenStack installation by
creating new virtual machines and ports, it should either be done at a very
slow pace, during a time with little load, or with the right throttling
enabled in Octavia. The throttling will make sure to prioritize failovers
higher than other operations and depending on how many failovers are
initiated this might crowd out other operations.

.. note::
    In Pike a failover command is being added to the API which allows to failover
    a load balancer's amphora while taking care of the intricacies of different
    topologies and prioritizes administrative failovers behind other operations.
    This function should be used instead of the ones described above once it
    becomes available.

Rotating Cryptographic Certificates
===================================

Octavia secures the communication between the amphora agent and the control
plane with two-way SSL encryption. To accomplish that, several certificates
are distributed in the system:

* Control plane:

  * Amphora certificate authority (CA) certificate: Used to validate
    amphora certificates if Octavia acts as a Certificate Authority to
    issue new amphora certificates

  * Client certificate: Used to authenticate with the amphora

* Amphora:

  * Client CA certificate: Used to validate control plane
    client certificate

  * Amphora certificate: Presented to control plane processes to prove amphora
    identity.

The heartbeat UDP packets emitted from the amphora are secured with a
symmetric encryption key. This is set by the configuration option
`heartbeat_key` in the `health_manager` section. We recommend setting it to a
random string of a sufficient length.

.. _rotate-amphora-certs:

Rotating Amphora Certificates
-----------------------------

For the server part Octavia will either act as a certificate authority itself,
or use :doc:`../Anchor` to issue amphora certificates to be used
by each amphora. Octavia will also monitor those certificates and refresh them
before they expire.

There are three ways to initiate a rotation manually:

* Change the expiration date of the certificate in the database. Octavia
  will then rotate the amphora certificates with newly issued ones. This
  requires the following:

  * Client CA certificate hasn't expired or the
    corresponding client certificate on the control plane hasn't been issued by
    a different client CA (in case the authority was
    compromised)

  * The Amphora CA certificate on the control plane didn't
    change in any way which jeopardizes validation of the amphora certificate
    (e.g. the certificate was reissued with a new private/public key)

* If the amphora CA changed in a way which jeopardizes
  validation of the amphora certificate an operator can manually upload newly
  issued amphora certificates by switching off validation of the old amphora
  certificate. This requires a client certificate which can be validated by the
  client CA file on the amphora. Refer to
  :doc:`../../contributor/api/haproxy-amphora-api` for more details.

* If the client certificate on the control plane changed in a way that it can't
  be validated by the client certificate authority certificate on the amphora,
  a failover (see :ref:`rotate-amphora-certs`) of all amphorae needs to be
  initiated. Until the failover is completed the amphorae can't be controlled
  by the control plane.

Rotating the Certificate Authority Certificates
-----------------------------------------------

If there is a compromise of the certificate authorities' certificates, or they
expired, new ones need to be installed into the system. If Octavia is
not acting as the certificate authority only the certificate authority's
cert needs to be changed in the system so amphora can be authenticated again.

# Issue new certificates (see the script in the bin folder of Octavia if
Octavia is acting as the certificate authority) or follow the instructions
of the third-party certificate authority. Copy the certificate and the
private key (if Octavia acts as a certificate authority) where Octavia can
find them.

# If the previous certificate files haven't been overridden, adjust the paths
to the new certs in the configuration file and restart all Octavia services
(except octavia-api).

# Review :ref:`rotate-amphora-certs` above to determine if and how the
amphora certificates needs to be rotated.

Rotating Client Certificates
----------------------------

If the client certificates expired new ones need to be issued and installed on
the system:

# Issue a new client certificate (see the script in the bin folder of Octavia
if self signed certificates are used) or use the ones provided to you by
your certificate authority.

# Copy the new cert where Octavia can find it.

# If the previous certificate files haven't been overridden, adjust the paths
to the new certs in the configuration file. In all cases restart all Octavia
services except octavia-api.

If the client CA certificate has been replaced in addition to
rotating the client certificate the new client CA
certificate needs to be installed in the system. After that initiate a
failover of all amphorae to distribute the new client CA
cert. Until the failover is completed the amphorae can't be controlled by the
control plane.

Changing The Heartbeat Encryption Key
-------------------------------------

Special caution needs to be taken to replace the heartbeat encryption key.
Once this is changed Octavia can't read any heartbeats and will assume
all amphora are in an error state and initiate an immediate failover.

In preparation, read the chapter on :ref:`best_practice` in
the Failover section. In particular, it is advisable if the throttling
enhancement (available in Pike) doesn't exist to create a sufficient
number of spare amphorae to mitigate the stress on the OpenStack installation
when Octavia starts to replace all amphora immediately.

Given the risks involved with changing this key it should not be changed
during routine maintenance but only when a compromise is strongly suspected.

.. note::
   For future versions of Octavia an "update amphora" API is planned which
   will allow this key to be changed without failover. At that time there would
   be a procedure to halt health monitoring while the keys are rotated and then
   resume health monitoring.

Handling a VM Node Failure
--------------------------

If a node fails which is running amphora, Octavia will automatically failover
the amphora to a different node (capacity permitting). In some cases, the
node can be recovered (e.g. through a hard reset) and the hypervisor might
bring back the amphora vms. In this case, an operator should manually delete
all amphora on this specific node since Octavia assumes they have been
deleted as part of the failover and will not touch them again.

.. note::
    As a safety measure an operator can, prior to deleting, manually check if
    the VM is in use. First, use the Amphora API to obtain the current list of
    amphorae, then match the nova instance ID to the compute_id column in the
    amphora API response (it is not currently possible to filter amphora by
    compute_id). If there are any matches where the amphora status is not
    'DELETED', the amphora is still considered to be in use.

Evacuating a Specific Amohora from a Host
-----------------------------------------

In some cases an amphora needs to be evacuated either because the host is being
shutdown for maintenance or as part of a failover. Octavia has a rich amphora
API to do that.

First use the amphora API to find the specific amphora. Then, if not already
performed, disable scheduling to this host in nova. Lastly, initiate a failover
of the specific amphora with the failover command on the amphora API.

Alternatively, a live migration might also work if it happens quick enough for
Octavia not to notice a stale amphora (the default configuration is 60s).

