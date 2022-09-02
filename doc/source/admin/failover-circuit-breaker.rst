..
      Copyright Red Hat

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========================================
Octavia Amphora Failover Circuit Breaker
========================================

During a large infrastructure outage, the automatic failover of stale
amphorae can lead to a mass failover event and create a considerable
amount of extra load on servers. By using the amphora failover
circuit breaker feature, you can avoid these unwanted failover events.
The circuit breaker is a configurable threshold value that you can set,
and will stop amphorae from automatically failing over whenever that
threshold value is met. The circuit breaker feature is disabled by default.

Configuration
=============

You define the threshold value for the failover circuit breaker feature
by setting the *failover_threshold* variable. The *failover_threshold*
variable is a member of the *health_manager* group within the
configuration file ``/etc/octavia/octavia.conf``.

Whenever the number of stale amphorae reaches or surpasses the value
of *failover_threshold*, Octavia performs the following actions:

* stops automatic failovers of amphorae.
* sets the status of the stale amphorae to *FAILOVER_STOPPED*.
* logs an error message.

The line below shows a typical error message:

.. code-block:: bash

    ERROR octavia.db.repositories [-] Stale amphora count reached the threshold (3). 4 amphorae were set into FAILOVER_STOPPED status.

.. note:: Base the value that you set for *failover_threshold* on the
    size of your environment. We recommend that you set the value to a number
    greater than the typical number of amphorae that you estimate to run on a
    single host, or to a value that reflects between 20% and 30%
    of the total number of amphorae.

Error Recovery
==============

Automatic Error Recovery
------------------------

For amphorae whose status is *FAILOVER_STOPPED*, Octavia will
automatically reset their status to *ALLOCATED* after receiving
new updates from these amphorae.

Manual Error Recovery
---------------------

To recover from the *FAILOVER_STOPPED* condition, you must
manually reduce the value of the stale amphorae below the
circuit breaker threshold.

You can use the ``openstack loadbalancer amphora list`` command
to list the amphorae that are in *FAILOVER_STOPPED* state.
Use the ``openstack loadbalancer amphora failover`` command to
manually trigger the amphora to failover.

In this example, *failover_threshold = 3* and an infrastructure
outage caused four amphorae to become unavailable. After the
health manager process detects this state, it sets the status
of all stale amphorae to *FAILOVER_STOPPED* as shown below.

.. code-block:: bash

    openstack loadbalancer amphora list
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+
    | id                                   | loadbalancer_id                      | status           | role   | lb_network_ip | ha_ip      |
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+
    | 79f0e06d-446d-448a-9d2b-c3b89d0c700d | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | FAILOVER_STOPPED | BACKUP | 192.168.0.108 | 192.0.2.17 |
    | 9c0416d7-6293-4f13-8f67-61e5d757b36e | 4b13dda1-296a-400c-8248-1abad5728057 | ALLOCATED        | MASTER | 192.168.0.198 | 192.0.2.42 |
    | e11208b7-f13d-4db3-9ded-1ee6f70a0502 | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | FAILOVER_STOPPED | MASTER | 192.168.0.154 | 192.0.2.17 |
    | ceea9fff-71a2-48c8-a968-e51dc440c572 | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | ALLOCATED        | MASTER | 192.168.0.149 | 192.0.2.26 |
    | a1351933-2270-493c-8201-d8f9f9fe42f7 | 4b13dda1-296a-400c-8248-1abad5728057 | FAILOVER_STOPPED | BACKUP | 192.168.0.103 | 192.0.2.42 |
    | 441718e7-0956-436b-9f99-9a476339d7d2 | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | FAILOVER_STOPPED | BACKUP | 192.168.0.148 | 192.0.2.26 |
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+

After operators have resolved the infrastructure outage,
they might need to manually trigger failovers to return to
normal operation. In this example, two manual failovers are
necessary to get the number of stale amphorae below the
configured threshold of three:

.. code-block:: bash

    openstack loadbalancer amphora failover --wait 79f0e06d-446d-448a-9d2b-c3b89d0c700d
    openstack loadbalancer amphora list
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+
    | id                                   | loadbalancer_id                      | status           | role   | lb_network_ip | ha_ip      |
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+
    | 9c0416d7-6293-4f13-8f67-61e5d757b36e | 4b13dda1-296a-400c-8248-1abad5728057 | ALLOCATED        | MASTER | 192.168.0.198 | 192.0.2.42 |
    | e11208b7-f13d-4db3-9ded-1ee6f70a0502 | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | FAILOVER_STOPPED | MASTER | 192.168.0.154 | 192.0.2.17 |
    | ceea9fff-71a2-48c8-a968-e51dc440c572 | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | ALLOCATED        | MASTER | 192.168.0.149 | 192.0.2.26 |
    | a1351933-2270-493c-8201-d8f9f9fe42f7 | 4b13dda1-296a-400c-8248-1abad5728057 | FAILOVER_STOPPED | BACKUP | 192.168.0.103 | 192.0.2.42 |
    | 441718e7-0956-436b-9f99-9a476339d7d2 | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | FAILOVER_STOPPED | BACKUP | 192.168.0.148 | 192.0.2.26 |
    | cf734b57-6019-4ec0-8437-115f76d1bbb0 | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | ALLOCATED        | BACKUP | 192.168.0.141 | 192.0.2.17 |
    +--------------------------------------+--------------------------------------+------------------+--------+---------------+------------+
    openstack loadbalancer amphora failover --wait e11208b7-f13d-4db3-9ded-1ee6f70a0502
    openstack loadbalancer amphora list
    +--------------------------------------+--------------------------------------+-----------+--------+---------------+------------+
    | id                                   | loadbalancer_id                      | status    | role   | lb_network_ip | ha_ip      |
    +--------------------------------------+--------------------------------------+-----------+--------+---------------+------------+
    | 9c0416d7-6293-4f13-8f67-61e5d757b36e | 4b13dda1-296a-400c-8248-1abad5728057 | ALLOCATED | MASTER | 192.168.0.198 | 192.0.2.42 |
    | ceea9fff-71a2-48c8-a968-e51dc440c572 | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | ALLOCATED | MASTER | 192.168.0.149 | 192.0.2.26 |
    | cf734b57-6019-4ec0-8437-115f76d1bbb0 | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | ALLOCATED | BACKUP | 192.168.0.141 | 192.0.2.17 |
    | d2909051-402e-4e75-86c9-ec6725c814a1 | 8fd2cac5-cbca-4bb1-bcfc-daba43e097ab | ALLOCATED | MASTER | 192.168.0.25  | 192.0.2.17 |
    | 5133e01a-fb53-457b-b810-edbb5202437e | 4b13dda1-296a-400c-8248-1abad5728057 | ALLOCATED | BACKUP | 192.168.0.76  | 192.0.2.42 |
    | f82eff89-e326-4e9d-86bc-58c720220a3f | ab513cb3-8f5d-461e-b7ae-a06b5083a371 | ALLOCATED | BACKUP | 192.168.0.86  | 192.0.2.26 |
    +--------------------------------------+--------------------------------------+-----------+--------+---------------+------------+

After the number of stale amphorae falls below the configured
threshold value, normal operation resumes and the automatic
failover process attempts to restore the remaining stale amphorae.
