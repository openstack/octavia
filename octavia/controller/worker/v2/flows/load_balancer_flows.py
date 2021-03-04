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
from octavia.common import exceptions
from octavia.common import utils
from octavia.controller.worker.v2.flows import amphora_flows
from octavia.controller.worker.v2.flows import listener_flows
from octavia.controller.worker.v2.flows import member_flows
from octavia.controller.worker.v2.flows import pool_flows
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.controller.worker.v2.tasks import compute_tasks
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import lifecycle_tasks
from octavia.controller.worker.v2.tasks import network_tasks
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class LoadBalancerFlows(object):

    def __init__(self):
        self.amp_flows = amphora_flows.AmphoraFlows()
        self.listener_flows = listener_flows.ListenerFlows()
        self.pool_flows = pool_flows.PoolFlows()
        self.member_flows = member_flows.MemberFlows()
        self.lb_repo = repo.LoadBalancerRepository()

    def get_create_load_balancer_flow(self, topology, listeners=None):
        """Creates a conditional graph flow that allocates a loadbalancer to

        two spare amphorae.
        :raises InvalidTopology: Invalid topology specified
        :return: The graph flow for creating a loadbalancer.
        """
        f_name = constants.CREATE_LOADBALANCER_FLOW
        lb_create_flow = linear_flow.Flow(f_name)

        lb_create_flow.add(lifecycle_tasks.LoadBalancerIDToErrorOnRevertTask(
            requires=constants.LOADBALANCER_ID))

        # allocate VIP
        lb_create_flow.add(database_tasks.ReloadLoadBalancer(
            name=constants.RELOAD_LB_BEFOR_ALLOCATE_VIP,
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER
        ))
        lb_create_flow.add(network_tasks.AllocateVIP(
            requires=constants.LOADBALANCER,
            provides=constants.VIP))
        lb_create_flow.add(database_tasks.UpdateVIPAfterAllocation(
            requires=(constants.LOADBALANCER_ID, constants.VIP),
            provides=constants.LOADBALANCER))
        lb_create_flow.add(network_tasks.UpdateVIPSecurityGroup(
            requires=constants.LOADBALANCER_ID))
        lb_create_flow.add(network_tasks.GetSubnetFromVIP(
            requires=constants.LOADBALANCER,
            provides=constants.SUBNET))

        if topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            lb_create_flow.add(*self._create_active_standby_topology())
        elif topology == constants.TOPOLOGY_SINGLE:
            lb_create_flow.add(*self._create_single_topology())
        else:
            LOG.error("Unknown topology: %s.  Unable to build load balancer.",
                      topology)
            raise exceptions.InvalidTopology(topology=topology)

        post_amp_prefix = constants.POST_LB_AMP_ASSOCIATION_SUBFLOW
        lb_create_flow.add(
            self.get_post_lb_amp_association_flow(
                post_amp_prefix, topology, mark_active=(not listeners)))

        if listeners:
            lb_create_flow.add(*self._create_listeners_flow())

        return lb_create_flow

    def _create_single_topology(self):
        sf_name = (constants.ROLE_STANDALONE + '-' +
                   constants.AMP_PLUG_NET_SUBFLOW)
        amp_for_lb_net_flow = linear_flow.Flow(sf_name)
        amp_for_lb_flow = self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_STANDALONE,
            role=constants.ROLE_STANDALONE)
        amp_for_lb_net_flow.add(amp_for_lb_flow)
        amp_for_lb_net_flow.add(*self._get_amp_net_subflow(sf_name))
        return amp_for_lb_net_flow

    def _create_active_standby_topology(
            self, lf_name=constants.CREATE_LOADBALANCER_FLOW):
        # When we boot up amphora for an active/standby topology,
        # we should leverage the Nova anti-affinity capabilities
        # to place the amphora on different hosts, also we need to check
        # if anti-affinity-flag is enabled or not:
        anti_affinity = CONF.nova.enable_anti_affinity
        flows = []
        if anti_affinity:
            # we need to create a server group first
            flows.append(
                compute_tasks.NovaServerGroupCreate(
                    name=lf_name + '-' +
                    constants.CREATE_SERVER_GROUP_FLOW,
                    requires=(constants.LOADBALANCER_ID),
                    provides=constants.SERVER_GROUP_ID))

            # update server group id in lb table
            flows.append(
                database_tasks.UpdateLBServerGroupInDB(
                    name=lf_name + '-' +
                    constants.UPDATE_LB_SERVERGROUPID_FLOW,
                    requires=(constants.LOADBALANCER_ID,
                              constants.SERVER_GROUP_ID)))

        f_name = constants.CREATE_LOADBALANCER_FLOW
        amps_flow = unordered_flow.Flow(f_name)

        master_sf_name = (constants.ROLE_MASTER + '-' +
                          constants.AMP_PLUG_NET_SUBFLOW)
        master_amp_sf = linear_flow.Flow(master_sf_name)
        master_amp_sf.add(self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_MASTER, role=constants.ROLE_MASTER))
        master_amp_sf.add(*self._get_amp_net_subflow(master_sf_name))

        backup_sf_name = (constants.ROLE_BACKUP + '-' +
                          constants.AMP_PLUG_NET_SUBFLOW)
        backup_amp_sf = linear_flow.Flow(backup_sf_name)
        backup_amp_sf.add(self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_BACKUP, role=constants.ROLE_BACKUP))
        backup_amp_sf.add(*self._get_amp_net_subflow(backup_sf_name))

        amps_flow.add(master_amp_sf, backup_amp_sf)

        return flows + [amps_flow]

    def _get_amp_net_subflow(self, sf_name):
        flows = []
        flows.append(network_tasks.PlugVIPAmphora(
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

    def _create_listeners_flow(self):
        flows = []
        flows.append(
            database_tasks.ReloadLoadBalancer(
                name=constants.RELOAD_LB_AFTER_AMP_ASSOC_FULL_GRAPH,
                requires=constants.LOADBALANCER_ID,
                provides=constants.LOADBALANCER
            )
        )
        flows.append(
            network_tasks.CalculateDelta(
                requires=(constants.LOADBALANCER, constants.AVAILABILITY_ZONE),
                provides=constants.DELTAS
            )
        )
        flows.append(
            network_tasks.HandleNetworkDeltas(
                requires=constants.DELTAS, provides=constants.ADDED_PORTS
            )
        )
        flows.append(
            amphora_driver_tasks.AmphoraePostNetworkPlug(
                requires=(constants.LOADBALANCER, constants.ADDED_PORTS)
            )
        )
        flows.append(
            self.listener_flows.get_create_all_listeners_flow()
        )
        flows.append(
            database_tasks.MarkLBActiveInDB(
                mark_subobjects=True,
                requires=constants.LOADBALANCER
            )
        )
        return flows

    def get_post_lb_amp_association_flow(self, prefix, topology,
                                         mark_active=True):
        """Reload the loadbalancer and create networking subflows for

        created/allocated amphorae.
        :return: Post amphorae association subflow
        """
        sf_name = prefix + '-' + constants.POST_LB_AMP_ASSOCIATION_SUBFLOW
        post_create_LB_flow = linear_flow.Flow(sf_name)
        post_create_LB_flow.add(
            database_tasks.ReloadLoadBalancer(
                name=sf_name + '-' + constants.RELOAD_LB_AFTER_AMP_ASSOC,
                requires=constants.LOADBALANCER_ID,
                provides=constants.LOADBALANCER))

        if topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            post_create_LB_flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
                requires=constants.LOADBALANCER_ID,
                provides=constants.AMPHORAE))
            vrrp_subflow = self.amp_flows.get_vrrp_subflow(prefix)
            post_create_LB_flow.add(vrrp_subflow)

        post_create_LB_flow.add(database_tasks.UpdateLoadbalancerInDB(
            requires=[constants.LOADBALANCER, constants.UPDATE_DICT]))
        if mark_active:
            post_create_LB_flow.add(database_tasks.MarkLBActiveInDB(
                name=sf_name + '-' + constants.MARK_LB_ACTIVE_INDB,
                requires=constants.LOADBALANCER))
        return post_create_LB_flow

    def _get_delete_listeners_flow(self, listeners):
        """Sets up an internal delete flow

        :param listeners: A list of listener dicts
        :return: The flow for the deletion
        """
        listeners_delete_flow = unordered_flow.Flow('listeners_delete_flow')
        for listener in listeners:
            listeners_delete_flow.add(
                self.listener_flows.get_delete_listener_internal_flow(
                    listener))
        return listeners_delete_flow

    def get_delete_load_balancer_flow(self, lb):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        return self._get_delete_load_balancer_flow(lb, False)

    def _get_delete_pools_flow(self, pools):
        """Sets up an internal delete flow

        Because task flow doesn't support loops we store each pool
        we want to delete in the store part and then rebind
        :param lb: load balancer
        :return: (flow, store) -- flow for the deletion and store with all
                    the listeners stored properly
        """
        pools_delete_flow = unordered_flow.Flow('pool_delete_flow')
        for pool in pools:
            pools_delete_flow.add(
                self.pool_flows.get_delete_pool_flow_internal(
                    pool[constants.POOL_ID]))
        return pools_delete_flow

    def _get_delete_load_balancer_flow(self, lb, cascade,
                                       listeners=(), pools=()):
        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
        delete_LB_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(compute_tasks.NovaServerGroupDelete(
            requires=constants.SERVER_GROUP_ID))
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeHealthBusy(
            requires=constants.LOADBALANCER))
        if cascade:
            listeners_delete = self._get_delete_listeners_flow(listeners)
            pools_delete = self._get_delete_pools_flow(pools)
            delete_LB_flow.add(pools_delete)
            delete_LB_flow.add(listeners_delete)
        delete_LB_flow.add(network_tasks.UnplugVIP(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(network_tasks.DeallocateVIP(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(compute_tasks.DeleteAmphoraeOnLoadBalancer(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeDeletedInDB(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.DisableLBAmphoraeHealthMonitoring(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.MarkLBDeletedInDB(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.DecrementLoadBalancerQuota(
            requires=constants.PROJECT_ID))
        return delete_LB_flow

    def get_cascade_delete_load_balancer_flow(self, lb, listeners, pools):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        return self._get_delete_load_balancer_flow(lb, True,
                                                   listeners=listeners,
                                                   pools=pools)

    def get_update_load_balancer_flow(self):
        """Creates a flow to update a load balancer.

        :returns: The flow for update a load balancer
        """
        update_LB_flow = linear_flow.Flow(constants.UPDATE_LOADBALANCER_FLOW)
        update_LB_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))
        update_LB_flow.add(network_tasks.ApplyQos(
            requires=(constants.LOADBALANCER, constants.UPDATE_DICT)))
        update_LB_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        update_LB_flow.add(database_tasks.UpdateLoadbalancerInDB(
            requires=[constants.LOADBALANCER, constants.UPDATE_DICT]))
        update_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires=constants.LOADBALANCER))

        return update_LB_flow

    def get_failover_LB_flow(self, amps, lb):
        """Failover a load balancer.

        1. Validate the VIP port is correct and present.
        2. Build a replacement amphora.
        3. Delete the failed amphora.
        4. Configure the replacement amphora listeners.
        5. Configure VRRP for the listeners.
        6. Build the second replacement amphora.
        7. Delete the second failed amphora.
        8. Delete any extraneous amphora.
        9. Configure the listeners on the new amphorae.
        10. Configure the VRRP on the new amphorae.
        11. Reload the listener configurations to pick up VRRP changes.
        12. Mark the load balancer back to ACTIVE.

        :returns: The flow that will provide the failover.
        """
        lb_topology = lb[constants.FLAVOR][constants.LOADBALANCER_TOPOLOGY]
        # Pick one amphora to be failed over if any exist.
        failed_amp = None
        if amps:
            failed_amp = amps.pop()

        failover_LB_flow = linear_flow.Flow(
            constants.FAILOVER_LOADBALANCER_FLOW)

        # Revert LB to provisioning_status ERROR if this flow goes wrong
        failover_LB_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))

        # Setup timeouts for our requests to the amphorae
        timeout_dict = {
            constants.CONN_MAX_RETRIES:
                CONF.haproxy_amphora.active_connection_max_retries,
            constants.CONN_RETRY_INTERVAL:
                CONF.haproxy_amphora.active_connection_rety_interval}

        if failed_amp:
            failed_amp_role = failed_amp.get(constants.ROLE)
            if failed_amp_role in (constants.ROLE_MASTER,
                                   constants.ROLE_BACKUP):
                amp_role = 'master_or_backup'
            elif failed_amp_role == constants.ROLE_STANDALONE:
                amp_role = 'standalone'
            elif failed_amp_role is None:
                amp_role = 'spare'
            else:
                amp_role = 'undefined'
            LOG.info("Performing failover for amphora: %s",
                     {"id": failed_amp.get(constants.ID),
                      "load_balancer_id": lb.get(constants.ID),
                      "lb_network_ip": failed_amp.get(constants.LB_NETWORK_IP),
                      "compute_id": failed_amp.get(constants.COMPUTE_ID),
                      "role": amp_role})

            failover_LB_flow.add(database_tasks.MarkAmphoraPendingDeleteInDB(
                requires=constants.AMPHORA,
                inject={constants.AMPHORA: failed_amp}))

            failover_LB_flow.add(database_tasks.MarkAmphoraHealthBusy(
                requires=constants.AMPHORA,
                inject={constants.AMPHORA: failed_amp}))

        # Check that the VIP port exists and is ok
        failover_LB_flow.add(
            network_tasks.AllocateVIPforFailover(
                requires=constants.LOADBALANCER, provides=constants.VIP))

        # Update the database with the VIP information
        failover_LB_flow.add(database_tasks.UpdateVIPAfterAllocation(
            requires=(constants.LOADBALANCER_ID, constants.VIP),
            provides=constants.LOADBALANCER))

        # Make sure the SG has the correct rules and re-apply to the
        # VIP port. It is not used on the VIP port, but will help lock
        # the SG as in use.
        failover_LB_flow.add(network_tasks.UpdateVIPSecurityGroup(
            requires=constants.LOADBALANCER_ID, provides=constants.VIP_SG_ID))

        new_amp_role = constants.ROLE_STANDALONE
        if lb_topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            new_amp_role = constants.ROLE_BACKUP

        # Get a replacement amphora and plug all of the networking.
        #
        # Do this early as the compute services have been observed to be
        # unreliable. The community decided the chance that deleting first
        # would open resources for an instance is less likely than the compute
        # service failing to boot an instance for other reasons.
        if failed_amp:
            failed_vrrp_is_ipv6 = False
            if failed_amp.get(constants.VRRP_IP):
                failed_vrrp_is_ipv6 = utils.is_ipv6(
                    failed_amp[constants.VRRP_IP])
            failover_LB_flow.add(
                self.amp_flows.get_amphora_for_lb_failover_subflow(
                    prefix=constants.FAILOVER_LOADBALANCER_FLOW,
                    role=new_amp_role,
                    failed_amp_vrrp_port_id=failed_amp.get(
                        constants.VRRP_PORT_ID),
                    is_vrrp_ipv6=failed_vrrp_is_ipv6))
        else:
            failover_LB_flow.add(
                self.amp_flows.get_amphora_for_lb_failover_subflow(
                    prefix=constants.FAILOVER_LOADBALANCER_FLOW,
                    role=new_amp_role))

        if lb_topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            failover_LB_flow.add(database_tasks.MarkAmphoraBackupInDB(
                name=constants.MARK_AMP_BACKUP_INDB,
                requires=constants.AMPHORA))

        # Delete the failed amp
        if failed_amp:
            failover_LB_flow.add(
                self.amp_flows.get_delete_amphora_flow(failed_amp))

        # Update the data stored in the flow from the database
        failover_LB_flow.add(database_tasks.ReloadLoadBalancer(
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))

        # Configure the listener(s)
        # We will run update on this amphora again later if this is
        # an active/standby load balancer because we want this amp
        # functional as soon as possible. It must run again to update
        # the configurations for the new peers.
        failover_LB_flow.add(amphora_driver_tasks.AmpListenersUpdate(
            name=constants.AMP_LISTENER_UPDATE,
            requires=(constants.LOADBALANCER, constants.AMPHORA),
            inject={constants.TIMEOUT_DICT: timeout_dict}))

        # Bring up the new "backup" amphora VIP now to reduce the outage
        # on the final failover. This dropped the outage from 8-9 seconds
        # to less than one in my lab.
        # This does mean some steps have to be repeated later to reconfigure
        # for the second amphora as a peer.
        if lb_topology == constants.TOPOLOGY_ACTIVE_STANDBY:

            failover_LB_flow.add(database_tasks.CreateVRRPGroupForLB(
                name=new_amp_role + '-' + constants.CREATE_VRRP_GROUP_FOR_LB,
                requires=constants.LOADBALANCER_ID))

            failover_LB_flow.add(network_tasks.GetAmphoraNetworkConfigsByID(
                name=(new_amp_role + '-' +
                      constants.GET_AMPHORA_NETWORK_CONFIGS_BY_ID),
                requires=(constants.LOADBALANCER_ID, constants.AMPHORA_ID),
                provides=constants.FIRST_AMP_NETWORK_CONFIGS))

            failover_LB_flow.add(
                amphora_driver_tasks.AmphoraUpdateVRRPInterface(
                    name=new_amp_role + '-' + constants.AMP_UPDATE_VRRP_INTF,
                    requires=constants.AMPHORA,
                    inject={constants.TIMEOUT_DICT: timeout_dict},
                    provides=constants.FIRST_AMP_VRRP_INTERFACE))

            failover_LB_flow.add(amphora_driver_tasks.AmphoraVRRPUpdate(
                name=new_amp_role + '-' + constants.AMP_VRRP_UPDATE,
                requires=(constants.LOADBALANCER_ID, constants.AMPHORA),
                rebind={constants.AMPHORAE_NETWORK_CONFIG:
                        constants.FIRST_AMP_NETWORK_CONFIGS,
                        constants.AMP_VRRP_INT:
                        constants.FIRST_AMP_VRRP_INTERFACE},
                inject={constants.TIMEOUT_DICT: timeout_dict}))

            failover_LB_flow.add(amphora_driver_tasks.AmphoraVRRPStart(
                name=new_amp_role + '-' + constants.AMP_VRRP_START,
                requires=constants.AMPHORA,
                inject={constants.TIMEOUT_DICT: timeout_dict}))

            # Start the listener. This needs to be done here because
            # it will create the required haproxy check scripts for
            # the VRRP deployed above.
            # A "V" or newer amphora-agent will remove the need for this
            # task here.
            # TODO(johnsom) Remove this in the "X" cycle
            failover_LB_flow.add(amphora_driver_tasks.ListenersStart(
                name=new_amp_role + '-' + constants.AMP_LISTENER_START,
                requires=(constants.LOADBALANCER, constants.AMPHORA)))

            #  #### Work on standby amphora if needed #####

            new_amp_role = constants.ROLE_MASTER
            failed_amp = None
            if amps:
                failed_amp = amps.pop()

            if failed_amp:
                failed_amp_role = failed_amp.get(constants.ROLE)
                if failed_amp_role in (constants.ROLE_MASTER,
                                       constants.ROLE_BACKUP):
                    amp_role = 'master_or_backup'
                elif failed_amp_role == constants.ROLE_STANDALONE:
                    amp_role = 'standalone'
                elif failed_amp_role is None:
                    amp_role = 'spare'
                else:
                    amp_role = 'undefined'
                LOG.info("Performing failover for amphora: %s",
                         {"id": failed_amp.get(constants.ID),
                          "load_balancer_id": lb.get(constants.ID),
                          "lb_network_ip": failed_amp.get(
                              constants.LB_NETWORK_IP),
                          "compute_id": failed_amp.get(constants.COMPUTE_ID),
                          "role": amp_role})

                failover_LB_flow.add(
                    database_tasks.MarkAmphoraPendingDeleteInDB(
                        name=(new_amp_role + '-' +
                              constants.MARK_AMPHORA_PENDING_DELETE),
                        requires=constants.AMPHORA,
                        inject={constants.AMPHORA: failed_amp}))

                failover_LB_flow.add(database_tasks.MarkAmphoraHealthBusy(
                    name=(new_amp_role + '-' +
                          constants.MARK_AMPHORA_HEALTH_BUSY),
                    requires=constants.AMPHORA,
                    inject={constants.AMPHORA: failed_amp}))

            # Get a replacement amphora and plug all of the networking.
            #
            # Do this early as the compute services have been observed to be
            # unreliable. The community decided the chance that deleting first
            # would open resources for an instance is less likely than the
            # compute service failing to boot an instance for other reasons.
            failover_LB_flow.add(
                self.amp_flows.get_amphora_for_lb_failover_subflow(
                    prefix=(new_amp_role + '-' +
                            constants.FAILOVER_LOADBALANCER_FLOW),
                    role=new_amp_role))

            failover_LB_flow.add(database_tasks.MarkAmphoraMasterInDB(
                name=constants.MARK_AMP_MASTER_INDB,
                requires=constants.AMPHORA))

            # Delete the failed amp
            if failed_amp:
                failover_LB_flow.add(
                    self.amp_flows.get_delete_amphora_flow(
                        failed_amp))
                failover_LB_flow.add(
                    database_tasks.DisableAmphoraHealthMonitoring(
                        name=(new_amp_role + '-' +
                              constants.DISABLE_AMP_HEALTH_MONITORING),
                        requires=constants.AMPHORA,
                        inject={constants.AMPHORA: failed_amp}))

        # Remove any extraneous amphora
        # Note: This runs in all topology situations.
        #       It should run before the act/stdby final listener update so
        #       that we don't bother attempting to update dead amphorae.
        delete_extra_amps_flow = unordered_flow.Flow(
            constants.DELETE_EXTRA_AMPHORAE_FLOW)
        for amp in amps:
            LOG.debug('Found extraneous amphora %s on load balancer %s. '
                      'Deleting.', amp.get(constants.ID), lb.get(id))
            delete_extra_amps_flow.add(
                self.amp_flows.get_delete_amphora_flow(amp))

        failover_LB_flow.add(delete_extra_amps_flow)

        if lb_topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            # Update the data stored in the flow from the database
            failover_LB_flow.add(database_tasks.ReloadLoadBalancer(
                name=new_amp_role + '-' + constants.RELOAD_LB_AFTER_AMP_ASSOC,
                requires=constants.LOADBALANCER_ID,
                provides=constants.LOADBALANCER))

            failover_LB_flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
                name=new_amp_role + '-' + constants.GET_AMPHORAE_FROM_LB,
                requires=constants.LOADBALANCER_ID,
                provides=constants.AMPHORAE))

            # Listeners update needs to be run on all amphora to update
            # their peer configurations. So parallelize this with an
            # unordered subflow.
            update_amps_subflow = unordered_flow.Flow(
                constants.UPDATE_AMPS_SUBFLOW)

            # Setup parallel flows for each amp. We don't know the new amp
            # details at flow creation time, so setup a subflow for each
            # amp on the LB, they let the task index into a list of amps
            # to find the amphora it should work on.
            update_amps_subflow.add(
                amphora_driver_tasks.AmphoraIndexListenerUpdate(
                    name=(constants.AMPHORA + '-0-' +
                          constants.AMP_LISTENER_UPDATE),
                    requires=(constants.LOADBALANCER, constants.AMPHORAE),
                    inject={constants.AMPHORA_INDEX: 0,
                            constants.TIMEOUT_DICT: timeout_dict}))
            update_amps_subflow.add(
                amphora_driver_tasks.AmphoraIndexListenerUpdate(
                    name=(constants.AMPHORA + '-1-' +
                          constants.AMP_LISTENER_UPDATE),
                    requires=(constants.LOADBALANCER, constants.AMPHORAE),
                    inject={constants.AMPHORA_INDEX: 1,
                            constants.TIMEOUT_DICT: timeout_dict}))

            failover_LB_flow.add(update_amps_subflow)

            # Configure and enable keepalived in the amphora
            failover_LB_flow.add(self.amp_flows.get_vrrp_subflow(
                new_amp_role + '-' + constants.GET_VRRP_SUBFLOW,
                timeout_dict, create_vrrp_group=False))

            # #### End of standby ####

            # Reload the listener. This needs to be done here because
            # it will create the required haproxy check scripts for
            # the VRRP deployed above.
            # A "V" or newer amphora-agent will remove the need for this
            # task here.
            # TODO(johnsom) Remove this in the "X" cycle
            failover_LB_flow.add(
                amphora_driver_tasks.AmphoraIndexListenersReload(
                    name=(new_amp_role + '-' +
                          constants.AMPHORA_RELOAD_LISTENER),
                    requires=(constants.LOADBALANCER, constants.AMPHORAE),
                    inject={constants.AMPHORA_INDEX: 1,
                            constants.TIMEOUT_DICT: timeout_dict}))

        # Remove any extraneous ports
        # Note: Nova sometimes fails to delete ports attached to an instance.
        #       For example, if you create an LB with a listener, then
        #       'openstack server delete' the amphora, you will see the vrrp
        #       port attached to that instance will remain after the instance
        #       is deleted.
        # TODO(johnsom) Fix this as part of
        #               https://storyboard.openstack.org/#!/story/2007077

        # Mark LB ACTIVE
        failover_LB_flow.add(
            database_tasks.MarkLBActiveInDB(mark_subobjects=True,
                                            requires=constants.LOADBALANCER))

        return failover_LB_flow
