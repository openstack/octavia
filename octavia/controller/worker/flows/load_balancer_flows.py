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
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import compute_tasks
from octavia.controller.worker.tasks import controller_tasks
from octavia.controller.worker.tasks import database_tasks
from octavia.controller.worker.tasks import network_tasks
from octavia.i18n import _LE


CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')
LOG = logging.getLogger(__name__)


class LoadBalancerFlows(object):

    def __init__(self):
        self.amp_flows = amphora_flows.AmphoraFlows()

    def get_create_load_balancer_flow(self, topology):
        """Creates a conditional graph flow that allocates a loadbalancer to

        two spare amphorae.
        :raises InvalidTopology: Invalid topology specified
        :return: The graph flow for creating an active_standby loadbalancer.
        """

        f_name = constants.CREATE_LOADBALANCER_FLOW
        lb_create_flow = unordered_flow.Flow(f_name)

        if topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            master_amp_sf = self.amp_flows.get_amphora_for_lb_subflow(
                prefix=constants.ROLE_MASTER, role=constants.ROLE_MASTER)
            backup_amp_sf = self.amp_flows.get_amphora_for_lb_subflow(
                prefix=constants.ROLE_BACKUP, role=constants.ROLE_BACKUP)
            lb_create_flow.add(master_amp_sf, backup_amp_sf)
        elif topology == constants.TOPOLOGY_SINGLE:
            amphora_sf = self.amp_flows.get_amphora_for_lb_subflow(
                prefix=constants.ROLE_STANDALONE,
                role=constants.ROLE_STANDALONE)
            lb_create_flow.add(amphora_sf)
        else:
            LOG.error(_LE("Unknown topology: %s.  Unable to build load "
                          "balancer."), topology)
            raise exceptions.InvalidTopology(topology=topology)

        return lb_create_flow

    def get_post_lb_amp_association_flow(self, prefix, topology):
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
        post_create_LB_flow.add(database_tasks.MarkLBActiveInDB(
            name=sf_name + '-' + constants.MARK_LB_ACTIVE_INDB,
            requires=constants.LOADBALANCER))
        return post_create_LB_flow

    def get_delete_load_balancer_flow(self):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeHealthBusy(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(controller_tasks.DeleteListenersOnLB(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(network_tasks.UnplugVIP(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(compute_tasks.DeleteAmphoraeOnLoadBalancer(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.MarkLBAmphoraeDeletedInDB(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(network_tasks.DeallocateVIP(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.DisableLBAmphoraeHealthMonitoring(
            requires=constants.LOADBALANCER))
        delete_LB_flow.add(database_tasks.MarkLBDeletedInDB(
            requires=constants.LOADBALANCER))

        return delete_LB_flow

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
        new_LB_net_subflow.add(database_tasks.UpdateAmphoraVIPData(
            requires=constants.AMPS_DATA))
        new_LB_net_subflow.add(database_tasks.ReloadLoadBalancer(
            name=constants.RELOAD_LB_AFTER_PLUG_VIP,
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))
        new_LB_net_subflow.add(network_tasks.GetAmphoraeNetworkConfigs(
            requires=constants.LOADBALANCER,
            provides=constants.AMPHORAE_NETWORK_CONFIG))
        new_LB_net_subflow.add(amphora_driver_tasks.AmphoraPostVIPPlug(
            requires=(constants.LOADBALANCER,
                      constants.AMPHORAE_NETWORK_CONFIG)))

        return new_LB_net_subflow

    def get_update_load_balancer_flow(self):
        """Creates a flow to update a load balancer.

        :returns: The flow for update a load balancer
        """
        update_LB_flow = linear_flow.Flow(constants.UPDATE_LOADBALANCER_FLOW)
        update_LB_flow.add(controller_tasks.DisableEnableLB(
            requires=constants.LOADBALANCER))
        update_LB_flow.add(database_tasks.UpdateLoadbalancerInDB(
            requires=[constants.LOADBALANCER, constants.UPDATE_DICT]))
        update_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires=constants.LOADBALANCER))

        return update_LB_flow
