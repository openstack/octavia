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
from oslo_log import log as logging
from taskflow.patterns import linear_flow
from taskflow.patterns import unordered_flow

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.flows import amphora_flows
from octavia.controller.worker.flows import listener_flows
from octavia.controller.worker.flows import member_flows
from octavia.controller.worker.flows import pool_flows
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import compute_tasks
from octavia.controller.worker.tasks import database_tasks
from octavia.controller.worker.tasks import lifecycle_tasks
from octavia.controller.worker.tasks import network_tasks

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class LoadBalancerFlows(object):

    def __init__(self):
        self.amp_flows = amphora_flows.AmphoraFlows()
        self.listener_flows = listener_flows.ListenerFlows()
        self.pool_flows = pool_flows.PoolFlows()
        self.member_flows = member_flows.MemberFlows()

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
        return (self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_STANDALONE,
            role=constants.ROLE_STANDALONE), )

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
        master_amp_sf = self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_MASTER, role=constants.ROLE_MASTER)

        backup_amp_sf = self.amp_flows.get_amphora_for_lb_subflow(
            prefix=constants.ROLE_BACKUP, role=constants.ROLE_BACKUP)
        amps_flow.add(master_amp_sf, backup_amp_sf)

        return flows + [amps_flow]

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
                requires=constants.LOADBALANCER, provides=constants.DELTAS
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

        # Note: If any task in this flow failed, the created amphorae will be
        #  left ''incorrectly'' allocated to the loadbalancer. Likely,
        # the get_new_LB_networking_subflow is the most prune to failure
        # shall deallocate the amphora from its loadbalancer and put it in a
        # READY state.

        sf_name = prefix + '-' + constants.POST_LB_AMP_ASSOCIATION_SUBFLOW
        post_create_LB_flow = linear_flow.Flow(sf_name)
        post_create_LB_flow.add(
            database_tasks.ReloadLoadBalancer(
                name=sf_name + '-' + constants.RELOAD_LB_AFTER_AMP_ASSOC,
                requires=constants.LOADBALANCER_ID,
                provides=constants.LOADBALANCER))

        new_LB_net_subflow = self.get_new_LB_networking_subflow()
        post_create_LB_flow.add(new_LB_net_subflow)

        if topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            vrrp_subflow = self.amp_flows.get_vrrp_subflow(prefix)
            post_create_LB_flow.add(vrrp_subflow)

        post_create_LB_flow.add(database_tasks.UpdateLoadbalancerInDB(
            requires=[constants.LOADBALANCER, constants.UPDATE_DICT]))
        if mark_active:
            post_create_LB_flow.add(database_tasks.MarkLBActiveInDB(
                name=sf_name + '-' + constants.MARK_LB_ACTIVE_INDB,
                requires=constants.LOADBALANCER))
        return post_create_LB_flow

    def _get_delete_listeners_flow(self, lb):
        """Sets up an internal delete flow

        Because task flow doesn't support loops we store each listener
        we want to delete in the store part and then rebind
        :param lb: load balancer
        :return: (flow, store) -- flow for the deletion and store with all
                    the listeners stored properly
        """
        listeners_delete_flow = unordered_flow.Flow('listener_delete_flow')
        store = {}
        for listener in lb.listeners:
            listener_name = 'listener_' + listener.id
            store[listener_name] = listener
            listeners_delete_flow.add(
                self.listener_flows.get_delete_listener_internal_flow(
                    listener_name))
        return (listeners_delete_flow, store)

    def get_delete_load_balancer_flow(self, lb):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        (listeners_delete, store) = self._get_delete_listeners_flow(lb)

        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
        delete_LB_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(compute_tasks.NovaServerGroupDelete(
            requires=constants.SERVER_GROUP_ID))
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeHealthBusy(
            requires=constants.LOADBALANCER))
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
            requires=constants.LOADBALANCER))

        return (delete_LB_flow, store)

    def _get_delete_pools_flow(self, lb):
        """Sets up an internal delete flow

        Because task flow doesn't support loops we store each pool
        we want to delete in the store part and then rebind
        :param lb: load balancer
        :return: (flow, store) -- flow for the deletion and store with all
                    the listeners stored properly
        """
        pools_delete_flow = unordered_flow.Flow('pool_delete_flow')
        store = {}
        for pool in lb.pools:
            pool_name = 'pool' + pool.id
            store[pool_name] = pool
            pools_delete_flow.add(
                self.pool_flows.get_delete_pool_flow_internal(
                    pool_name))
        return (pools_delete_flow, store)

    def get_cascade_delete_load_balancer_flow(self, lb):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """

        (listeners_delete, store) = self._get_delete_listeners_flow(lb)
        (pools_delete, pool_store) = self._get_delete_pools_flow(lb)
        store.update(pool_store)

        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
        delete_LB_flow.add(lifecycle_tasks.LoadBalancerToErrorOnRevertTask(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(compute_tasks.NovaServerGroupDelete(
            requires=constants.SERVER_GROUP_ID))
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeHealthBusy(
            requires=constants.LOADBALANCER))
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
            requires=constants.LOADBALANCER))

        return (delete_LB_flow, store)

    def get_new_LB_networking_subflow(self):
        """Create a sub-flow to setup networking.

        :returns: The flow to setup networking for a new amphora
        """

        new_LB_net_subflow = linear_flow.Flow(constants.
                                              LOADBALANCER_NETWORKING_SUBFLOW)
        new_LB_net_subflow.add(network_tasks.AllocateVIP(
            requires=constants.LOADBALANCER,
            provides=constants.VIP))
        new_LB_net_subflow.add(database_tasks.UpdateVIPAfterAllocation(
            requires=(constants.LOADBALANCER_ID, constants.VIP),
            provides=constants.LOADBALANCER))
        new_LB_net_subflow.add(network_tasks.PlugVIP(
            requires=constants.LOADBALANCER,
            provides=constants.AMPS_DATA))
        new_LB_net_subflow.add(network_tasks.ApplyQos(
            requires=(constants.LOADBALANCER, constants.AMPS_DATA,
                      constants.UPDATE_DICT)))
        new_LB_net_subflow.add(database_tasks.UpdateAmphoraVIPData(
            requires=constants.AMPS_DATA))
        new_LB_net_subflow.add(database_tasks.ReloadLoadBalancer(
            name=constants.RELOAD_LB_AFTER_PLUG_VIP,
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))
        new_LB_net_subflow.add(network_tasks.GetAmphoraeNetworkConfigs(
            requires=constants.LOADBALANCER,
            provides=constants.AMPHORAE_NETWORK_CONFIG))
        new_LB_net_subflow.add(amphora_driver_tasks.AmphoraePostVIPPlug(
            requires=(constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))

        return new_LB_net_subflow

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
            requires=[constants.LOADBALANCER, constants.LISTENERS]))
        update_LB_flow.add(database_tasks.UpdateLoadbalancerInDB(
            requires=[constants.LOADBALANCER, constants.UPDATE_DICT]))
        update_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires=constants.LOADBALANCER))

        return update_LB_flow
