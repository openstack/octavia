# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
from taskflow.patterns import graph_flow
from taskflow.patterns import linear_flow
from taskflow.patterns import unordered_flow

from octavia.common import constants
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import cert_task
from octavia.controller.worker.tasks import compute_tasks
from octavia.controller.worker.tasks import database_tasks
from octavia.controller.worker.tasks import lifecycle_tasks
from octavia.controller.worker.tasks import network_tasks

CONF = cfg.CONF


class AmphoraFlows(object):
    def __init__(self):
        # for some reason only this has the values from the config file
        self.REST_AMPHORA_DRIVER = (CONF.controller_worker.amphora_driver ==
                                    'amphora_haproxy_rest_driver')

    def get_create_amphora_flow(self):
        """Creates a flow to create an amphora.

        :returns: The flow for creating the amphora
        """
        create_amphora_flow = linear_flow.Flow(constants.CREATE_AMPHORA_FLOW)
        create_amphora_flow.add(database_tasks.CreateAmphoraInDB(
                                provides=constants.AMPHORA_ID))
        create_amphora_flow.add(lifecycle_tasks.AmphoraIDToErrorOnRevertTask(
            requires=constants.AMPHORA_ID))
        if self.REST_AMPHORA_DRIVER:
            create_amphora_flow.add(cert_task.GenerateServerPEMTask(
                                    provides=constants.SERVER_PEM))

            create_amphora_flow.add(
                database_tasks.UpdateAmphoraDBCertExpiration(
                    requires=(constants.AMPHORA_ID, constants.SERVER_PEM)))

            create_amphora_flow.add(compute_tasks.CertComputeCreate(
                requires=(constants.AMPHORA_ID, constants.SERVER_PEM,
                          constants.BUILD_TYPE_PRIORITY, constants.FLAVOR),
                provides=constants.COMPUTE_ID))
        else:
            create_amphora_flow.add(compute_tasks.ComputeCreate(
                requires=(constants.AMPHORA_ID, constants.BUILD_TYPE_PRIORITY,
                          constants.FLAVOR),
                provides=constants.COMPUTE_ID))
        create_amphora_flow.add(database_tasks.MarkAmphoraBootingInDB(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amphora_flow.add(compute_tasks.ComputeActiveWait(
            requires=(constants.COMPUTE_ID, constants.AMPHORA_ID),
            provides=constants.COMPUTE_OBJ))
        create_amphora_flow.add(database_tasks.UpdateAmphoraInfo(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_OBJ),
            provides=constants.AMPHORA))
        create_amphora_flow.add(
            amphora_driver_tasks.AmphoraComputeConnectivityWait(
                requires=constants.AMPHORA))
        create_amphora_flow.add(database_tasks.ReloadAmphora(
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))
        create_amphora_flow.add(amphora_driver_tasks.AmphoraFinalize(
            requires=constants.AMPHORA))
        create_amphora_flow.add(database_tasks.MarkAmphoraReadyInDB(
            requires=constants.AMPHORA))

        return create_amphora_flow

    def _get_post_map_lb_subflow(self, prefix, role):
        """Set amphora type after mapped to lb."""

        sf_name = prefix + '-' + constants.POST_MAP_AMP_TO_LB_SUBFLOW
        post_map_amp_to_lb = linear_flow.Flow(
            sf_name)

        post_map_amp_to_lb.add(database_tasks.ReloadAmphora(
            name=sf_name + '-' + constants.RELOAD_AMPHORA,
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))

        post_map_amp_to_lb.add(amphora_driver_tasks.AmphoraConfigUpdate(
            name=sf_name + '-' + constants.AMPHORA_CONFIG_UPDATE_TASK,
            requires=(constants.AMPHORA, constants.FLAVOR)))

        if role == constants.ROLE_MASTER:
            post_map_amp_to_lb.add(database_tasks.MarkAmphoraMasterInDB(
                name=sf_name + '-' + constants.MARK_AMP_MASTER_INDB,
                requires=constants.AMPHORA))
        elif role == constants.ROLE_BACKUP:
            post_map_amp_to_lb.add(database_tasks.MarkAmphoraBackupInDB(
                name=sf_name + '-' + constants.MARK_AMP_BACKUP_INDB,
                requires=constants.AMPHORA))
        elif role == constants.ROLE_STANDALONE:
            post_map_amp_to_lb.add(database_tasks.MarkAmphoraStandAloneInDB(
                name=sf_name + '-' + constants.MARK_AMP_STANDALONE_INDB,
                requires=constants.AMPHORA))

        return post_map_amp_to_lb

    def _get_create_amp_for_lb_subflow(self, prefix, role):
        """Create a new amphora for lb."""

        sf_name = prefix + '-' + constants.CREATE_AMP_FOR_LB_SUBFLOW
        create_amp_for_lb_subflow = linear_flow.Flow(sf_name)
        create_amp_for_lb_subflow.add(database_tasks.CreateAmphoraInDB(
            name=sf_name + '-' + constants.CREATE_AMPHORA_INDB,
            provides=constants.AMPHORA_ID))

        require_server_group_id_condition = (
            role in (constants.ROLE_BACKUP, constants.ROLE_MASTER) and
            CONF.nova.enable_anti_affinity)

        if self.REST_AMPHORA_DRIVER:
            create_amp_for_lb_subflow.add(cert_task.GenerateServerPEMTask(
                name=sf_name + '-' + constants.GENERATE_SERVER_PEM,
                provides=constants.SERVER_PEM))

            create_amp_for_lb_subflow.add(
                database_tasks.UpdateAmphoraDBCertExpiration(
                    name=sf_name + '-' + constants.UPDATE_CERT_EXPIRATION,
                    requires=(constants.AMPHORA_ID, constants.SERVER_PEM)))

            if require_server_group_id_condition:
                create_amp_for_lb_subflow.add(compute_tasks.CertComputeCreate(
                    name=sf_name + '-' + constants.CERT_COMPUTE_CREATE,
                    requires=(
                        constants.AMPHORA_ID,
                        constants.SERVER_PEM,
                        constants.BUILD_TYPE_PRIORITY,
                        constants.SERVER_GROUP_ID,
                        constants.FLAVOR
                    ),
                    provides=constants.COMPUTE_ID))
            else:
                create_amp_for_lb_subflow.add(compute_tasks.CertComputeCreate(
                    name=sf_name + '-' + constants.CERT_COMPUTE_CREATE,
                    requires=(
                        constants.AMPHORA_ID,
                        constants.SERVER_PEM,
                        constants.BUILD_TYPE_PRIORITY,
                        constants.FLAVOR
                    ),
                    provides=constants.COMPUTE_ID))
        else:
            if require_server_group_id_condition:
                create_amp_for_lb_subflow.add(compute_tasks.ComputeCreate(
                    name=sf_name + '-' + constants.COMPUTE_CREATE,
                    requires=(
                        constants.AMPHORA_ID,
                        constants.BUILD_TYPE_PRIORITY,
                        constants.SERVER_GROUP_ID,
                        constants.FLAVOR
                    ),
                    provides=constants.COMPUTE_ID))
            else:
                create_amp_for_lb_subflow.add(compute_tasks.ComputeCreate(
                    name=sf_name + '-' + constants.COMPUTE_CREATE,
                    requires=(
                        constants.AMPHORA_ID,
                        constants.BUILD_TYPE_PRIORITY,
                        constants.FLAVOR
                    ),
                    provides=constants.COMPUTE_ID))

        create_amp_for_lb_subflow.add(database_tasks.UpdateAmphoraComputeId(
            name=sf_name + '-' + constants.UPDATE_AMPHORA_COMPUTEID,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amp_for_lb_subflow.add(database_tasks.MarkAmphoraBootingInDB(
            name=sf_name + '-' + constants.MARK_AMPHORA_BOOTING_INDB,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amp_for_lb_subflow.add(compute_tasks.ComputeActiveWait(
            name=sf_name + '-' + constants.COMPUTE_WAIT,
            requires=(constants.COMPUTE_ID, constants.AMPHORA_ID),
            provides=constants.COMPUTE_OBJ))
        create_amp_for_lb_subflow.add(database_tasks.UpdateAmphoraInfo(
            name=sf_name + '-' + constants.UPDATE_AMPHORA_INFO,
            requires=(constants.AMPHORA_ID, constants.COMPUTE_OBJ),
            provides=constants.AMPHORA))
        create_amp_for_lb_subflow.add(
            amphora_driver_tasks.AmphoraComputeConnectivityWait(
                name=sf_name + '-' + constants.AMP_COMPUTE_CONNECTIVITY_WAIT,
                requires=constants.AMPHORA))
        create_amp_for_lb_subflow.add(amphora_driver_tasks.AmphoraFinalize(
            name=sf_name + '-' + constants.AMPHORA_FINALIZE,
            requires=constants.AMPHORA))
        create_amp_for_lb_subflow.add(
            database_tasks.MarkAmphoraAllocatedInDB(
                name=sf_name + '-' + constants.MARK_AMPHORA_ALLOCATED_INDB,
                requires=(constants.AMPHORA, constants.LOADBALANCER_ID)))
        create_amp_for_lb_subflow.add(database_tasks.ReloadAmphora(
            name=sf_name + '-' + constants.RELOAD_AMPHORA,
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))

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

    def _allocate_amp_to_lb_decider(self, history):
        """decides if the lb shall be mapped to a spare amphora

        :return: True if a spare amphora exists in DB
        """

        return list(history.values())[0] is not None

    def _create_new_amp_for_lb_decider(self, history):
        """decides if a new amphora must be created for the lb

        :return: True if there is no spare amphora
        """

        return list(history.values())[0] is None

    def get_amphora_for_lb_subflow(
            self, prefix, role=constants.ROLE_STANDALONE):
        """Tries to allocate a spare amphora to a loadbalancer if none

        exists, create a new amphora.
        """

        sf_name = prefix + '-' + constants.GET_AMPHORA_FOR_LB_SUBFLOW

        # We need a graph flow here for a conditional flow
        amp_for_lb_flow = graph_flow.Flow(sf_name)

        # Setup the task that maps an amphora to a load balancer
        allocate_and_associate_amp = database_tasks.MapLoadbalancerToAmphora(
            name=sf_name + '-' + constants.MAP_LOADBALANCER_TO_AMPHORA,
            requires=(constants.LOADBALANCER_ID, constants.FLAVOR),
            provides=constants.AMPHORA_ID)

        # Define a subflow for if we successfully map an amphora
        map_lb_to_amp = self._get_post_map_lb_subflow(prefix, role)
        # Define a subflow for if we can't map an amphora
        create_amp = self._get_create_amp_for_lb_subflow(prefix, role)

        # Add them to the graph flow
        amp_for_lb_flow.add(allocate_and_associate_amp,
                            map_lb_to_amp, create_amp)

        # Setup the decider for the path if we can map an amphora
        amp_for_lb_flow.link(allocate_and_associate_amp, map_lb_to_amp,
                             decider=self._allocate_amp_to_lb_decider,
                             decider_depth='flow')
        # Setup the decider for the path if we can't map an amphora
        amp_for_lb_flow.link(allocate_and_associate_amp, create_amp,
                             decider=self._create_new_amp_for_lb_decider,
                             decider_depth='flow')

        # Plug the network
        # todo(xgerman): Rework failover flow
        if prefix != constants.FAILOVER_AMPHORA_FLOW:
            sf_name = prefix + '-' + constants.AMP_PLUG_NET_SUBFLOW
            amp_for_lb_net_flow = linear_flow.Flow(sf_name)
            amp_for_lb_net_flow.add(amp_for_lb_flow)
            amp_for_lb_net_flow.add(*self._get_amp_net_subflow(sf_name))
            return amp_for_lb_net_flow

        return amp_for_lb_flow

    def _get_amp_net_subflow(self, sf_name):
        flows = []
        flows.append(network_tasks.PlugVIPAmpphora(
            name=sf_name + '-' + constants.PLUG_VIP_AMPHORA,
            requires=(constants.LOADBALANCER, constants.AMPHORA,
                      constants.SUBNET),
            provides=constants.AMP_DATA))

        flows.append(network_tasks.ApplyQosAmphora(
            name=sf_name + '-' + constants.APPLY_QOS_AMP,
            requires=(constants.LOADBALANCER, constants.AMP_DATA,
                      constants.UPDATE_DICT)))
        flows.append(database_tasks.UpdateAmphoraVIPData(
            name=sf_name + '-' + constants.UPDATE_AMPHORA_VIP_DATA,
            requires=constants.AMP_DATA))
        flows.append(database_tasks.ReloadAmphora(
            name=sf_name + '-' + constants.RELOAD_AMP_AFTER_PLUG_VIP,
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))
        flows.append(database_tasks.ReloadLoadBalancer(
            name=sf_name + '-' + constants.RELOAD_LB_AFTER_PLUG_VIP,
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))
        flows.append(network_tasks.GetAmphoraNetworkConfigs(
            name=sf_name + '-' + constants.GET_AMP_NETWORK_CONFIG,
            requires=(constants.LOADBALANCER, constants.AMPHORA),
            provides=constants.AMPHORA_NETWORK_CONFIG))
        flows.append(amphora_driver_tasks.AmphoraPostVIPPlug(
            name=sf_name + '-' + constants.AMP_POST_VIP_PLUG,
            rebind={constants.AMPHORAE_NETWORK_CONFIG:
                    constants.AMPHORA_NETWORK_CONFIG},
            requires=(constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))
        return flows

    def get_delete_amphora_flow(self):
        """Creates a flow to delete an amphora.

        This should be configurable in the config file
        :returns: The flow for deleting the amphora
        :raises AmphoraNotFound: The referenced Amphora was not found
        """

        delete_amphora_flow = linear_flow.Flow(constants.DELETE_AMPHORA_FLOW)
        delete_amphora_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            requires=constants.AMPHORA))
        delete_amphora_flow.add(database_tasks.
                                MarkAmphoraPendingDeleteInDB(
                                    requires=constants.AMPHORA))
        delete_amphora_flow.add(database_tasks.
                                MarkAmphoraHealthBusy(
                                    requires=constants.AMPHORA))
        delete_amphora_flow.add(compute_tasks.ComputeDelete(
            requires=constants.AMPHORA))
        delete_amphora_flow.add(database_tasks.
                                DisableAmphoraHealthMonitoring(
                                    requires=constants.AMPHORA))
        delete_amphora_flow.add(database_tasks.
                                MarkAmphoraDeletedInDB(
                                    requires=constants.AMPHORA))
        return delete_amphora_flow

    def get_failover_flow(self, role=constants.ROLE_STANDALONE,
                          load_balancer=None):
        """Creates a flow to failover a stale amphora

        :returns: The flow for amphora failover
        """

        failover_amphora_flow = linear_flow.Flow(
            constants.FAILOVER_AMPHORA_FLOW)

        failover_amphora_flow.add(lifecycle_tasks.AmphoraToErrorOnRevertTask(
            rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
            requires=constants.AMPHORA))

        # Note: It seems intuitive to boot an amphora prior to deleting
        #       the old amphora, however this is a complicated issue.
        #       If the target host (due to anit-affinity) is resource
        #       constrained, this will fail where a post-delete will
        #       succeed. Since this is async with the API it would result
        #       in the LB ending in ERROR though the amps are still alive.
        #       Consider in the future making this a complicated
        #       try-on-failure-retry flow, or move upgrade failovers to be
        #       synchronous with the API. For now spares pool and act/stdby
        #       will mitigate most of this delay.

        # Delete the old amphora
        failover_amphora_flow.add(
            database_tasks.MarkAmphoraPendingDeleteInDB(
                rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
                requires=constants.AMPHORA))
        failover_amphora_flow.add(
            database_tasks.MarkAmphoraHealthBusy(
                rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
                requires=constants.AMPHORA))
        failover_amphora_flow.add(compute_tasks.ComputeDelete(
            rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
            requires=constants.AMPHORA))
        failover_amphora_flow.add(network_tasks.WaitForPortDetach(
            rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
            requires=constants.AMPHORA))
        failover_amphora_flow.add(database_tasks.MarkAmphoraDeletedInDB(
            rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
            requires=constants.AMPHORA))

        # If this is an unallocated amp (spares pool), we're done
        if not load_balancer:
            failover_amphora_flow.add(
                database_tasks.DisableAmphoraHealthMonitoring(
                    rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
                    requires=constants.AMPHORA))
            return failover_amphora_flow

        # Save failed amphora details for later
        failover_amphora_flow.add(
            database_tasks.GetAmphoraDetails(
                rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
                requires=constants.AMPHORA,
                provides=constants.AMP_DATA))

        # Get a new amphora
        # Note: Role doesn't matter here.  We will update it later.
        get_amp_subflow = self.get_amphora_for_lb_subflow(
            prefix=constants.FAILOVER_AMPHORA_FLOW)
        failover_amphora_flow.add(get_amp_subflow)

        # Update the new amphora with the failed amphora details
        failover_amphora_flow.add(database_tasks.UpdateAmpFailoverDetails(
            requires=(constants.AMPHORA, constants.AMP_DATA)))

        # Update the data stored in the flow from the database
        failover_amphora_flow.add(database_tasks.ReloadLoadBalancer(
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))

        failover_amphora_flow.add(database_tasks.ReloadAmphora(
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))

        # Prepare to reconnect the network interface(s)
        failover_amphora_flow.add(network_tasks.GetAmphoraeNetworkConfigs(
            requires=constants.LOADBALANCER,
            provides=constants.AMPHORAE_NETWORK_CONFIG))
        failover_amphora_flow.add(database_tasks.GetListenersFromLoadbalancer(
            requires=constants.LOADBALANCER, provides=constants.LISTENERS))
        failover_amphora_flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
            requires=constants.LOADBALANCER, provides=constants.AMPHORAE))

        # Plug the VIP ports into the new amphora
        # The reason for moving these steps here is the udp listeners want to
        # do some kernel configuration before Listener update for forbidding
        # failure during rebuild amphora.
        failover_amphora_flow.add(network_tasks.PlugVIPPort(
            requires=(constants.AMPHORA, constants.AMPHORAE_NETWORK_CONFIG)))
        failover_amphora_flow.add(amphora_driver_tasks.AmphoraPostVIPPlug(
            requires=(constants.AMPHORA, constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))

        # Listeners update needs to be run on all amphora to update
        # their peer configurations. So parallelize this with an
        # unordered subflow.
        update_amps_subflow = unordered_flow.Flow(
            constants.UPDATE_AMPS_SUBFLOW)

        timeout_dict = {
            constants.CONN_MAX_RETRIES:
                CONF.haproxy_amphora.active_connection_max_retries,
            constants.CONN_RETRY_INTERVAL:
                CONF.haproxy_amphora.active_connection_rety_interval}

        # Setup parallel flows for each amp. We don't know the new amp
        # details at flow creation time, so setup a subflow for each
        # amp on the LB, they let the task index into a list of amps
        # to find the amphora it should work on.
        amp_index = 0
        for amp in load_balancer.amphorae:
            if amp.status == constants.DELETED:
                continue
            update_amps_subflow.add(
                amphora_driver_tasks.AmpListenersUpdate(
                    name=constants.AMP_LISTENER_UPDATE + '-' + str(amp_index),
                    requires=(constants.LISTENERS, constants.AMPHORAE),
                    inject={constants.AMPHORA_INDEX: amp_index,
                            constants.TIMEOUT_DICT: timeout_dict}))
            amp_index += 1

        failover_amphora_flow.add(update_amps_subflow)

        # Plug the member networks into the new amphora
        failover_amphora_flow.add(network_tasks.CalculateAmphoraDelta(
            requires=(constants.LOADBALANCER, constants.AMPHORA),
            provides=constants.DELTA))

        failover_amphora_flow.add(network_tasks.HandleNetworkDelta(
            requires=(constants.AMPHORA, constants.DELTA),
            provides=constants.ADDED_PORTS))

        failover_amphora_flow.add(amphora_driver_tasks.AmphoraePostNetworkPlug(
            requires=(constants.LOADBALANCER, constants.ADDED_PORTS)))

        failover_amphora_flow.add(database_tasks.ReloadLoadBalancer(
            name='octavia-failover-LB-reload-2',
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))

        # Handle the amphora role and VRRP if necessary
        if role == constants.ROLE_MASTER:
            failover_amphora_flow.add(database_tasks.MarkAmphoraMasterInDB(
                name=constants.MARK_AMP_MASTER_INDB,
                requires=constants.AMPHORA))
            vrrp_subflow = self.get_vrrp_subflow(role)
            failover_amphora_flow.add(vrrp_subflow)
        elif role == constants.ROLE_BACKUP:
            failover_amphora_flow.add(database_tasks.MarkAmphoraBackupInDB(
                name=constants.MARK_AMP_BACKUP_INDB,
                requires=constants.AMPHORA))
            vrrp_subflow = self.get_vrrp_subflow(role)
            failover_amphora_flow.add(vrrp_subflow)
        elif role == constants.ROLE_STANDALONE:
            failover_amphora_flow.add(
                database_tasks.MarkAmphoraStandAloneInDB(
                    name=constants.MARK_AMP_STANDALONE_INDB,
                    requires=constants.AMPHORA))

        failover_amphora_flow.add(amphora_driver_tasks.ListenersStart(
            requires=(constants.LOADBALANCER, constants.LISTENERS,
                      constants.AMPHORA)))
        failover_amphora_flow.add(
            database_tasks.DisableAmphoraHealthMonitoring(
                rebind={constants.AMPHORA: constants.FAILED_AMPHORA},
                requires=constants.AMPHORA))

        return failover_amphora_flow

    def get_vrrp_subflow(self, prefix):
        sf_name = prefix + '-' + constants.GET_VRRP_SUBFLOW
        vrrp_subflow = linear_flow.Flow(sf_name)
        vrrp_subflow.add(network_tasks.GetAmphoraeNetworkConfigs(
            name=sf_name + '-' + constants.GET_AMP_NETWORK_CONFIG,
            requires=constants.LOADBALANCER,
            provides=constants.AMPHORAE_NETWORK_CONFIG))
        vrrp_subflow.add(amphora_driver_tasks.AmphoraUpdateVRRPInterface(
            name=sf_name + '-' + constants.AMP_UPDATE_VRRP_INTF,
            requires=constants.LOADBALANCER,
            provides=constants.LOADBALANCER))
        vrrp_subflow.add(database_tasks.CreateVRRPGroupForLB(
            name=sf_name + '-' + constants.CREATE_VRRP_GROUP_FOR_LB,
            requires=constants.LOADBALANCER,
            provides=constants.LOADBALANCER))
        vrrp_subflow.add(amphora_driver_tasks.AmphoraVRRPUpdate(
            name=sf_name + '-' + constants.AMP_VRRP_UPDATE,
            requires=(constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))
        vrrp_subflow.add(amphora_driver_tasks.AmphoraVRRPStart(
            name=sf_name + '-' + constants.AMP_VRRP_START,
            requires=constants.LOADBALANCER))
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
            requires=constants.AMPHORA))

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
