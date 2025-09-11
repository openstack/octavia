# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

from oslo_config import cfg
from oslo_log import log as logging
from taskflow.patterns import linear_flow
from taskflow.patterns import unordered_flow

from octavia.common import constants
from octavia.common import utils
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.controller.worker.v2.tasks import cert_task
from octavia.controller.worker.v2.tasks import compute_tasks
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import lifecycle_tasks
from octavia.controller.worker.v2.tasks import network_tasks
from octavia.controller.worker.v2.tasks import retry_tasks
from octavia.controller.worker.v2.tasks import shim_tasks

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class AmphoraFlows:

    def get_amphora_for_lb_subflow(self, prefix, role):
        """Create a new amphora for lb."""

        sf_name = prefix + '-' + constants.CREATE_AMP_FOR_LB_SUBFLOW
        create_amp_for_lb_subflow = linear_flow.Flow(sf_name)
        create_amp_for_lb_subflow.add(database_tasks.CreateAmphoraInDB(
            name=sf_name + '-' + constants.CREATE_AMPHORA_INDB,
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORA_ID))

        create_amp_for_lb_subflow.add(cert_task.GenerateServerPEMTask(
            name=sf_name + '-' + constants.GENERATE_SERVER_PEM,
            provides=constants.SERVER_PEM))

        create_amp_for_lb_subflow.add(
            database_tasks.UpdateAmphoraDBCertExpiration(
                name=sf_name + '-' + constants.UPDATE_CERT_EXPIRATION,
                requires=(constants.AMPHORA_ID, constants.SERVER_PEM)))

        create_amp_for_lb_subflow.add(compute_tasks.CertComputeCreate(
            name=sf_name + '-' + constants.CERT_COMPUTE_CREATE,
            requires=(constants.AMPHORA_ID, constants.SERVER_PEM,
                      constants.BUILD_TYPE_PRIORITY,
                      constants.SERVER_GROUP_ID,
                      constants.FLAVOR, constants.AVAILABILITY_ZONE),
            provides=constants.COMPUTE_ID))
        create_amp_for_lb_subflow.add(database_tasks.UpdateAmphoraComputeId(
            name=sf_name + '-' + constants.UPDATE_AMPHORA_COMPUTEID,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amp_for_lb_subflow.add(database_tasks.MarkAmphoraBootingInDB(
            name=sf_name + '-' + constants.MARK_AMPHORA_BOOTING_INDB,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amp_for_lb_subflow.add(self._retry_compute_wait_flow(sf_name))
        create_amp_for_lb_subflow.add(database_tasks.UpdateAmphoraInfo(
            name=sf_name + '-' + constants.UPDATE_AMPHORA_INFO,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_OBJ),
            provides=constants.AMPHORA))
        create_amp_for_lb_subflow.add(self._retry_flow(sf_name))
        create_amp_for_lb_subflow.add(amphora_driver_tasks.AmphoraFinalize(
            name=sf_name + '-' + constants.AMPHORA_FINALIZE,
            requires=constants.AMPHORA))
        create_amp_for_lb_subflow.add(
            database_tasks.MarkAmphoraAllocatedInDB(
                name=sf_name + '-' + constants.MARK_AMPHORA_ALLOCATED_INDB,
                requires=(constants.AMPHORA, constants.LOADBALANCER_ID)))
        if role == constants.ROLE_MASTER:
            create_amp_for_lb_subflow.add(database_tasks.MarkAmphoraMasterInDB(
                name=sf_name + '-' + constants.MARK_AMP_MASTER_INDB,
                requires=constants.AMPHORA))
        elif role == constants.ROLE_BACKUP:
            create_amp_for_lb_subflow.add(database_tasks.MarkAmphoraBackupInDB(
                name=sf_name + '-' + constants.MARK_AMP_BACKUP_INDB,
                requires=constants.AMPHORA))
        elif role == constants.ROLE_STANDALONE:
            create_amp_for_lb_subflow.add(
                database_tasks.MarkAmphoraStandAloneInDB(
                    name=sf_name + '-' + constants.MARK_AMP_STANDALONE_INDB,
                    requires=constants.AMPHORA))

        return create_amp_for_lb_subflow

    def _retry_compute_wait_flow(self, sf_name):
        retry_task = sf_name + '-' + constants.COMPUTE_WAIT
        retry_subflow = linear_flow.Flow(
            sf_name + '-' + constants.COMPUTE_CREATE_RETRY_SUBFLOW,
            retry=compute_tasks.ComputeRetry())
        retry_subflow.add(
            compute_tasks.ComputeWait(
                name=retry_task,
                requires=(constants.COMPUTE_ID, constants.AMPHORA_ID),
                provides=constants.COMPUTE_OBJ))
        return retry_subflow

    def _retry_flow(self, sf_name):
        retry_task = sf_name + '-' + constants.AMP_COMPUTE_CONNECTIVITY_WAIT
        retry_subflow = linear_flow.Flow(
            sf_name + '-' + constants.CREATE_AMPHORA_RETRY_SUBFLOW,
            retry=amphora_driver_tasks.AmpRetry())
        retry_subflow.add(
            amphora_driver_tasks.AmphoraComputeConnectivityWait(
                name=retry_task, requires=constants.AMPHORA,
                inject={'raise_retry_exception': True}))
        return retry_subflow

    def get_delete_amphora_flow(
            self, amphora,
            retry_attempts=CONF.controller_worker.amphora_delete_retries,
            retry_interval=(
                CONF.controller_worker.amphora_delete_retry_interval)):
        """Creates a subflow to delete an amphora and it's port.

        This flow is idempotent and safe to retry.

        :param amphora: An amphora dict object.
        :param retry_attempts: The number of times the flow is retried.
        :param retry_interval: The time to wait, in seconds, between retries.
        :returns: The subflow for deleting the amphora.
        :raises AmphoraNotFound: The referenced Amphora was not found.
        """
        amphora_id = amphora[constants.ID]
        delete_amphora_flow = linear_flow.Flow(
            name=constants.DELETE_AMPHORA_FLOW + '-' + amphora_id,
            retry=retry_tasks.SleepingRetryTimesController(
                name='retry-' + constants.DELETE_AMPHORA_FLOW + '-' +
                     amphora_id,
                attempts=retry_attempts, interval=retry_interval))
        delete_amphora_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            name=constants.AMPHORA_TO_ERROR_ON_REVERT + '-' + amphora_id,
            inject={constants.AMPHORA: amphora}))
        delete_amphora_flow.add(
            database_tasks.MarkAmphoraPendingDeleteInDB(
                name=constants.MARK_AMPHORA_PENDING_DELETE + '-' + amphora_id,
                inject={constants.AMPHORA: amphora}))
        delete_amphora_flow.add(database_tasks.MarkAmphoraHealthBusy(
            name=constants.MARK_AMPHORA_HEALTH_BUSY + '-' + amphora_id,
            inject={constants.AMPHORA: amphora}))
        delete_amphora_flow.add(compute_tasks.ComputeDelete(
            name=constants.DELETE_AMPHORA + '-' + amphora_id,
            inject={constants.AMPHORA: amphora,
                    constants.PASSIVE_FAILURE: True}))
        delete_amphora_flow.add(network_tasks.DeleteAmphoraMemberPorts(
            name=constants.DELETE_AMPHORA_MEMBER_PORTS + '-' + amphora_id,
            inject={constants.AMPHORA_ID: amphora[constants.ID]}))
        delete_amphora_flow.add(database_tasks.DisableAmphoraHealthMonitoring(
            name=constants.DISABLE_AMP_HEALTH_MONITORING + '-' + amphora_id,
            inject={constants.AMPHORA: amphora}))
        delete_amphora_flow.add(database_tasks.MarkAmphoraDeletedInDB(
            name=constants.MARK_AMPHORA_DELETED + '-' + amphora_id,
            inject={constants.AMPHORA: amphora}))
        if amphora.get(constants.VRRP_PORT_ID):
            delete_amphora_flow.add(network_tasks.DeletePort(
                name=(constants.DELETE_PORT + '-' + str(amphora_id) + '-' +
                      str(amphora[constants.VRRP_PORT_ID])),
                inject={constants.PORT_ID: amphora[constants.VRRP_PORT_ID],
                        constants.PASSIVE_FAILURE: True}))
        return delete_amphora_flow

    def get_vrrp_subflow(self, prefix, timeout_dict=None,
                         create_vrrp_group=True,
                         get_amphorae_status=True, flavor_dict=None):
        sf_name = prefix + '-' + constants.GET_VRRP_SUBFLOW
        vrrp_subflow = linear_flow.Flow(sf_name)

        # Optimization for failover flow. No reason to call this
        # when configuring the secondary amphora.
        if create_vrrp_group:
            vrrp_subflow.add(database_tasks.CreateVRRPGroupForLB(
                name=sf_name + '-' + constants.CREATE_VRRP_GROUP_FOR_LB,
                requires=constants.LOADBALANCER_ID))

        vrrp_subflow.add(network_tasks.GetAmphoraeNetworkConfigs(
            name=sf_name + '-' + constants.GET_AMP_NETWORK_CONFIG,
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORAE_NETWORK_CONFIG))

        if get_amphorae_status:
            # Get the amphorae_status dict in case the caller hasn't fetched
            # it yet.
            vrrp_subflow.add(
                amphora_driver_tasks.AmphoraeGetConnectivityStatus(
                    name=constants.AMPHORAE_GET_CONNECTIVITY_STATUS,
                    requires=constants.AMPHORAE,
                    rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
                    inject={constants.TIMEOUT_DICT: timeout_dict},
                    provides=constants.AMPHORAE_STATUS))

        # VRRP update needs to be run on all amphora to update
        # their peer configurations. So parallelize this with an
        # unordered subflow.
        update_amps_subflow = unordered_flow.Flow('VRRP-update-subflow')

        # We have tasks to run in order, per amphora
        amp_0_subflow = linear_flow.Flow('VRRP-amp-0-update-subflow')

        amp_0_subflow.add(amphora_driver_tasks.AmphoraIndexUpdateVRRPInterface(
            name=sf_name + '-0-' + constants.AMP_UPDATE_VRRP_INTF,
            requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 0,
                    constants.TIMEOUT_DICT: timeout_dict},
            provides=constants.AMP_VRRP_INT))

        amp_0_subflow.add(amphora_driver_tasks.AmphoraIndexVRRPUpdate(
            name=sf_name + '-0-' + constants.AMP_VRRP_UPDATE,
            requires=(constants.LOADBALANCER_ID,
                      constants.AMPHORAE_NETWORK_CONFIG, constants.AMPHORAE,
                      constants.AMPHORAE_STATUS, constants.AMP_VRRP_INT),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 0,
                    constants.TIMEOUT_DICT: timeout_dict}))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            amp_0_subflow.add(database_tasks.GetAmphoraFirewallRules(
                name=sf_name + '-0-' + constants.GET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE,
                          constants.AMPHORAE_NETWORK_CONFIG),
                provides=constants.AMPHORA_FIREWALL_RULES,
                inject={constants.AMPHORA_INDEX: 0}))

            amp_0_subflow.add(amphora_driver_tasks.SetAmphoraFirewallRules(
                name=sf_name + '-0-' + constants.SET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS,
                          constants.AMPHORA_FIREWALL_RULES),
                inject={constants.AMPHORA_INDEX: 0,
                        constants.TIMEOUT_DICT: timeout_dict}))

        amp_0_subflow.add(amphora_driver_tasks.AmphoraIndexVRRPStart(
            name=sf_name + '-0-' + constants.AMP_VRRP_START,
            requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 0,
                    constants.TIMEOUT_DICT: timeout_dict}))

        amp_1_subflow = linear_flow.Flow('VRRP-amp-1-update-subflow')

        amp_1_subflow.add(amphora_driver_tasks.AmphoraIndexUpdateVRRPInterface(
            name=sf_name + '-1-' + constants.AMP_UPDATE_VRRP_INTF,
            requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 1,
                    constants.TIMEOUT_DICT: timeout_dict},
            provides=constants.AMP_VRRP_INT))

        amp_1_subflow.add(amphora_driver_tasks.AmphoraIndexVRRPUpdate(
            name=sf_name + '-1-' + constants.AMP_VRRP_UPDATE,
            requires=(constants.LOADBALANCER_ID,
                      constants.AMPHORAE_NETWORK_CONFIG, constants.AMPHORAE,
                      constants.AMPHORAE_STATUS, constants.AMP_VRRP_INT),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 1,
                    constants.TIMEOUT_DICT: timeout_dict}))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            amp_1_subflow.add(database_tasks.GetAmphoraFirewallRules(
                name=sf_name + '-1-' + constants.GET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE,
                          constants.AMPHORAE_NETWORK_CONFIG),
                provides=constants.AMPHORA_FIREWALL_RULES,
                inject={constants.AMPHORA_INDEX: 1}))

            amp_1_subflow.add(amphora_driver_tasks.SetAmphoraFirewallRules(
                name=sf_name + '-1-' + constants.SET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS,
                          constants.AMPHORA_FIREWALL_RULES),
                inject={constants.AMPHORA_INDEX: 1,
                        constants.TIMEOUT_DICT: timeout_dict}))

        amp_1_subflow.add(amphora_driver_tasks.AmphoraIndexVRRPStart(
            name=sf_name + '-1-' + constants.AMP_VRRP_START,
            requires=(constants.AMPHORAE, constants.AMPHORAE_STATUS),
            rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
            inject={constants.AMPHORA_INDEX: 1,
                    constants.TIMEOUT_DICT: timeout_dict}))

        update_amps_subflow.add(amp_0_subflow)
        update_amps_subflow.add(amp_1_subflow)

        vrrp_subflow.add(update_amps_subflow)

        return vrrp_subflow

    def cert_rotate_amphora_flow(self):
        """Implement rotation for amphora's cert.

        1. Create a new certificate
        2. Upload the cert to amphora
        3. update the newly created certificate info to amphora
        4. update the cert_busy flag to be false after rotation

        :returns: The flow for updating an amphora
        """
        rotated_amphora_flow = linear_flow.Flow(
            constants.CERT_ROTATE_AMPHORA_FLOW)

        rotated_amphora_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            requires=constants.AMPHORA))

        # create a new certificate, the returned value is the newly created
        # certificate
        rotated_amphora_flow.add(cert_task.GenerateServerPEMTask(
            provides=constants.SERVER_PEM))

        # update it in amphora task
        rotated_amphora_flow.add(amphora_driver_tasks.AmphoraCertUpload(
            requires=(constants.AMPHORA, constants.SERVER_PEM)))

        # update the newly created certificate info to amphora
        rotated_amphora_flow.add(database_tasks.UpdateAmphoraDBCertExpiration(
            requires=(constants.AMPHORA_ID, constants.SERVER_PEM)))

        # update the cert_busy flag to be false after rotation
        rotated_amphora_flow.add(database_tasks.UpdateAmphoraCertBusyToFalse(
            requires=constants.AMPHORA_ID))

        return rotated_amphora_flow

    def update_amphora_config_flow(self):
        """Creates a flow to update the amphora agent configuration.

        :returns: The flow for updating an amphora
        """
        update_amphora_flow = linear_flow.Flow(
            constants.UPDATE_AMPHORA_CONFIG_FLOW)

        update_amphora_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            requires=constants.AMPHORA))

        update_amphora_flow.add(amphora_driver_tasks.AmphoraConfigUpdate(
            requires=(constants.AMPHORA, constants.FLAVOR)))

        return update_amphora_flow

    def get_amphora_for_lb_failover_subflow(
            self, prefix, role=constants.ROLE_STANDALONE,
            failed_amp_vrrp_port_id=None, is_vrrp_ipv6=False,
            flavor_dict=None, timeout_dict=None):
        """Creates a new amphora that will be used in a failover flow.

        :requires: loadbalancer_id, flavor, vip, vip_sg_id, loadbalancer
        :provides: amphora_id, amphora
        :param prefix: The flow name prefix to use on the flow and tasks.
        :param role: The role this amphora will have in the topology.
        :param failed_amp_vrrp_port_id: The base port ID of the failed amp.
        :param is_vrrp_ipv6: True if the base port IP is IPv6.
        :return: A Taskflow sub-flow that will create the amphora.
        """

        sf_name = prefix + '-' + constants.CREATE_AMP_FOR_FAILOVER_SUBFLOW

        amp_for_failover_flow = linear_flow.Flow(sf_name)

        # Try to allocate or boot an amphora instance (unconfigured)
        amp_for_failover_flow.add(self.get_amphora_for_lb_subflow(
            prefix=prefix + '-' + constants.FAILOVER_LOADBALANCER_FLOW,
            role=role))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            amp_for_failover_flow.add(network_tasks.GetSubnetFromVIP(
                name=prefix + '-' + constants.GET_SUBNET_FROM_VIP,
                requires=constants.LOADBALANCER,
                provides=constants.SUBNET))
            amp_for_failover_flow.add(network_tasks.CreateSRIOVBasePort(
                name=prefix + '-' + constants.PLUG_VIP_AMPHORA,
                requires=(constants.LOADBALANCER, constants.AMPHORA,
                          constants.SUBNET),
                provides=constants.BASE_PORT))
        else:
            # Create the VIP base (aka VRRP) port for the amphora.
            amp_for_failover_flow.add(network_tasks.CreateVIPBasePort(
                name=prefix + '-' + constants.CREATE_VIP_BASE_PORT,
                requires=(constants.VIP, constants.VIP_SG_ID,
                          constants.AMPHORA_ID,
                          constants.ADDITIONAL_VIPS),
                provides=constants.BASE_PORT))

        # Attach the VIP base (aka VRRP) port to the amphora.
        amp_for_failover_flow.add(compute_tasks.AttachPort(
            name=prefix + '-' + constants.ATTACH_PORT,
            requires=(constants.AMPHORA, constants.PORT),
            rebind={constants.PORT: constants.BASE_PORT}))

        # Update the amphora database record with the VIP base port info.
        amp_for_failover_flow.add(database_tasks.UpdateAmpFailoverDetails(
            name=prefix + '-' + constants.UPDATE_AMP_FAILOVER_DETAILS,
            requires=(constants.AMPHORA, constants.VIP, constants.BASE_PORT)))

        # Update the amphora networking for the plugged VIP port
        amp_for_failover_flow.add(network_tasks.GetAmphoraNetworkConfigsByID(
            name=prefix + '-' + constants.GET_AMPHORA_NETWORK_CONFIGS_BY_ID,
            requires=(constants.LOADBALANCER_ID, constants.AMPHORA_ID),
            provides=constants.AMPHORAE_NETWORK_CONFIG))

        # Disable the base (vrrp) port on the failed amphora
        # This prevents a DAD failure when bringing up the new amphora.
        # Keepalived will handle this for act/stdby.
        if (role == constants.ROLE_STANDALONE and failed_amp_vrrp_port_id and
                is_vrrp_ipv6):
            amp_for_failover_flow.add(network_tasks.AdminDownPort(
                name=prefix + '-' + constants.ADMIN_DOWN_PORT,
                inject={constants.PORT_ID: failed_amp_vrrp_port_id}))

        amp_for_failover_flow.add(amphora_driver_tasks.AmphoraPostVIPPlug(
            name=prefix + '-' + constants.AMPHORA_POST_VIP_PLUG,
            requires=(constants.AMPHORA, constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            amp_for_failover_flow.add(
                shim_tasks.AmphoraToAmphoraeWithVRRPIP(
                    name=prefix + '-' + constants.AMPHORA_TO_AMPHORAE_VRRP_IP,
                    requires=(constants.AMPHORA, constants.BASE_PORT),
                    provides=constants.NEW_AMPHORAE))
            amp_for_failover_flow.add(database_tasks.GetAmphoraFirewallRules(
                name=prefix + '-' + constants.GET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE,
                          constants.AMPHORAE_NETWORK_CONFIG),
                rebind={constants.AMPHORAE: constants.NEW_AMPHORAE},
                provides=constants.AMPHORA_FIREWALL_RULES,
                inject={constants.AMPHORA_INDEX: 0}))
            amp_for_failover_flow.add(
                amphora_driver_tasks.AmphoraeGetConnectivityStatus(
                    name=(prefix + '-' +
                          constants.AMPHORAE_GET_CONNECTIVITY_STATUS),
                    requires=constants.AMPHORAE,
                    rebind={constants.AMPHORAE: constants.NEW_AMPHORAE},
                    inject={constants.TIMEOUT_DICT: timeout_dict,
                            constants.NEW_AMPHORA_ID: constants.NIL_UUID},
                    provides=constants.AMPHORAE_STATUS))
            amp_for_failover_flow.add(
                amphora_driver_tasks.SetAmphoraFirewallRules(
                    name=prefix + '-' + constants.SET_AMPHORA_FIREWALL_RULES,
                    requires=(constants.AMPHORAE,
                              constants.AMPHORA_FIREWALL_RULES,
                              constants.AMPHORAE_STATUS),
                    rebind={constants.AMPHORAE: constants.NEW_AMPHORAE},
                    inject={constants.AMPHORA_INDEX: 0,
                            constants.TIMEOUT_DICT: timeout_dict}))

        # Plug member ports
        amp_for_failover_flow.add(network_tasks.CalculateAmphoraDelta(
            name=prefix + '-' + constants.CALCULATE_AMPHORA_DELTA,
            requires=(constants.LOADBALANCER, constants.AMPHORA,
                      constants.AVAILABILITY_ZONE),
            provides=constants.DELTA))

        amp_for_failover_flow.add(network_tasks.HandleNetworkDelta(
            name=prefix + '-' + constants.HANDLE_NETWORK_DELTA,
            requires=(constants.AMPHORA, constants.DELTA),
            provides=constants.UPDATED_PORTS))

        amp_for_failover_flow.add(amphora_driver_tasks.AmphoraePostNetworkPlug(
            name=prefix + '-' + constants.AMPHORAE_POST_NETWORK_PLUG,
            requires=(constants.LOADBALANCER, constants.UPDATED_PORTS)))

        return amp_for_failover_flow

    def get_failover_amphora_flow(self, failed_amphora, lb_amp_count,
                                  flavor_dict=None):
        """Get a Taskflow flow to failover an amphora.

        1. Build a replacement amphora.
        2. Delete the old amphora.
        3. Update the amphorae listener configurations.
        4. Update the VRRP configurations if needed.

        :param failed_amphora: The amphora dict to failover.
        :param lb_amp_count: The number of amphora on this load balancer.
        :param flavor_dict: The load balancer flavor dictionary.
        :returns: The flow that will provide the failover.
        """
        failover_amp_flow = linear_flow.Flow(
            constants.FAILOVER_AMPHORA_FLOW)

        # Revert LB to provisioning_status ERROR if this flow goes wrong
        failover_amp_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))

        # Revert amphora to status ERROR if this flow goes wrong
        failover_amp_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            requires=constants.AMPHORA,
            inject={constants.AMPHORA: failed_amphora}))

        if failed_amphora[constants.ROLE] in (constants.ROLE_MASTER,
                                              constants.ROLE_BACKUP):
            amp_role = 'master_or_backup'
        elif failed_amphora[constants.ROLE] == constants.ROLE_STANDALONE:
            amp_role = 'standalone'
        else:
            amp_role = 'undefined'
        LOG.info("Performing failover for amphora: %s",
                 {"id": failed_amphora[constants.ID],
                  "load_balancer_id": failed_amphora.get(
                      constants.LOAD_BALANCER_ID),
                  "lb_network_ip": failed_amphora.get(constants.LB_NETWORK_IP),
                  "compute_id": failed_amphora.get(constants.COMPUTE_ID),
                  "role": amp_role})

        failover_amp_flow.add(database_tasks.MarkAmphoraPendingDeleteInDB(
            requires=constants.AMPHORA,
            inject={constants.AMPHORA: failed_amphora}))

        failover_amp_flow.add(database_tasks.MarkAmphoraHealthBusy(
            requires=constants.AMPHORA,
            inject={constants.AMPHORA: failed_amphora}))

        failover_amp_flow.add(network_tasks.GetVIPSecurityGroupID(
            requires=constants.LOADBALANCER_ID,
            provides=constants.VIP_SG_ID))

        is_vrrp_ipv6 = False
        if failed_amphora.get(constants.LOAD_BALANCER_ID):
            if failed_amphora.get(constants.VRRP_IP):
                is_vrrp_ipv6 = utils.is_ipv6(failed_amphora[constants.VRRP_IP])

            # Get a replacement amphora and plug all of the networking.
            #
            # Do this early as the compute services have been observed to be
            # unreliable. The community decided the chance that deleting first
            # would open resources for an instance is less likely than the
            # compute service failing to boot an instance for other reasons.

            # TODO(johnsom) Move this back out to run for spares after
            #               delete amphora API is available.
            failover_amp_flow.add(self.get_amphora_for_lb_failover_subflow(
                prefix=constants.FAILOVER_LOADBALANCER_FLOW,
                role=failed_amphora[constants.ROLE],
                failed_amp_vrrp_port_id=failed_amphora.get(
                    constants.VRRP_PORT_ID),
                is_vrrp_ipv6=is_vrrp_ipv6, flavor_dict=flavor_dict))

        failover_amp_flow.add(
            self.get_delete_amphora_flow(
                failed_amphora,
                retry_attempts=CONF.controller_worker.amphora_delete_retries,
                retry_interval=(
                    CONF.controller_worker.amphora_delete_retry_interval)))
        failover_amp_flow.add(
            database_tasks.DisableAmphoraHealthMonitoring(
                requires=constants.AMPHORA,
                inject={constants.AMPHORA: failed_amphora}))

        if not failed_amphora.get(constants.LOAD_BALANCER_ID):
            # This is an unallocated amphora (bogus), we are done.
            return failover_amp_flow

        failover_amp_flow.add(database_tasks.GetLoadBalancer(
            requires=constants.LOADBALANCER_ID,
            inject={constants.LOADBALANCER_ID:
                    failed_amphora[constants.LOAD_BALANCER_ID]},
            provides=constants.LOADBALANCER))

        failover_amp_flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
            name=constants.GET_AMPHORAE_FROM_LB,
            requires=constants.LOADBALANCER_ID,
            inject={constants.LOADBALANCER_ID:
                    failed_amphora[constants.LOAD_BALANCER_ID]},
            provides=constants.AMPHORAE))

        # Setup timeouts for our requests to the amphorae
        timeout_dict = {
            constants.CONN_MAX_RETRIES:
                CONF.haproxy_amphora.active_connection_max_retries,
            constants.CONN_RETRY_INTERVAL:
                CONF.haproxy_amphora.active_connection_retry_interval}

        failover_amp_flow.add(
            amphora_driver_tasks.AmphoraeGetConnectivityStatus(
                name=constants.AMPHORAE_GET_CONNECTIVITY_STATUS,
                requires=constants.AMPHORAE,
                rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
                inject={constants.TIMEOUT_DICT: timeout_dict},
                provides=constants.AMPHORAE_STATUS))

        # Listeners update needs to be run on all amphora to update
        # their peer configurations. So parallelize this with an
        # unordered subflow.
        update_amps_subflow = unordered_flow.Flow(
            constants.UPDATE_AMPS_SUBFLOW)

        for amp_index in range(0, lb_amp_count):
            update_amps_subflow.add(
                amphora_driver_tasks.AmphoraIndexListenerUpdate(
                    name=str(amp_index) + '-' + constants.AMP_LISTENER_UPDATE,
                    requires=(constants.LOADBALANCER, constants.AMPHORAE,
                              constants.AMPHORAE_STATUS),
                    rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
                    inject={constants.AMPHORA_INDEX: amp_index,
                            constants.TIMEOUT_DICT: timeout_dict}))

        failover_amp_flow.add(update_amps_subflow)

        # Configure and enable keepalived in the amphora
        if lb_amp_count == 2:
            failover_amp_flow.add(
                self.get_vrrp_subflow(constants.GET_VRRP_SUBFLOW,
                                      timeout_dict, create_vrrp_group=False,
                                      get_amphorae_status=False,
                                      flavor_dict=flavor_dict))

        # Reload the listener. This needs to be done here because
        # it will create the required haproxy check scripts for
        # the VRRP deployed above.
        # A "U" or newer amphora-agent will remove the need for this
        # task here.
        # TODO(johnsom) Remove this in the "W" cycle
        reload_listener_subflow = unordered_flow.Flow(
            constants.AMPHORA_LISTENER_RELOAD_SUBFLOW)

        for amp_index in range(0, lb_amp_count):
            reload_listener_subflow.add(
                amphora_driver_tasks.AmphoraIndexListenersReload(
                    name=(str(amp_index) + '-' +
                          constants.AMPHORA_RELOAD_LISTENER),
                    requires=(constants.LOADBALANCER, constants.AMPHORAE,
                              constants.AMPHORAE_STATUS),
                    rebind={constants.NEW_AMPHORA_ID: constants.AMPHORA_ID},
                    inject={constants.AMPHORA_INDEX: amp_index,
                            constants.TIMEOUT_DICT: timeout_dict}))

        failover_amp_flow.add(reload_listener_subflow)

        # Remove any extraneous ports
        # Note: Nova sometimes fails to delete ports attached to an instance.
        #       For example, if you create an LB with a listener, then
        #       'openstack server delete' the amphora, you will see the vrrp
        #       port attached to that instance will remain after the instance
        #       is deleted.
        # TODO(johnsom) Fix this as part of
        #               https://storyboard.openstack.org/#!/story/2007077

        # Mark LB ACTIVE
        failover_amp_flow.add(
            database_tasks.MarkLBActiveInDB(mark_subobjects=True,
                                            requires=constants.LOADBALANCER))

        return failover_amp_flow
