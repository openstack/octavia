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
from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import compute_tasks
from octavia.controller.worker.tasks import controller_tasks
from octavia.controller.worker.tasks import database_tasks
from octavia.controller.worker.tasks import network_tasks

CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')


class LoadBalancerFlows(object):

    def get_create_load_balancer_flow(self):
        """Creates a flow to create a load balancer.

        :returns: The flow for creating a load balancer
        """

        # Note this flow is a bit strange in how it handles building
        # Amphora if there are no spares.  TaskFlow has a spec for
        # a conditional flow that would make this cleaner once implemented.
        # https://review.openstack.org/#/c/98946/

        create_LB_flow = linear_flow.Flow(constants.CREATE_LOADBALANCER_FLOW)

        create_LB_flow.add(database_tasks.MapLoadbalancerToAmphora(
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORA_ID))
        create_LB_flow.add(database_tasks.ReloadAmphora(
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))
        create_LB_flow.add(database_tasks.ReloadLoadBalancer(
            name=constants.RELOAD_LB_AFTER_AMP_ASSOC,
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))
        new_LB_net_subflow = self.get_new_LB_networking_subflow()
        create_LB_flow.add(new_LB_net_subflow)
        create_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires=constants.LOADBALANCER))

        return create_LB_flow

    def get_delete_load_balancer_flow(self):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
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
