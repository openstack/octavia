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

from oslo.config import cfg
from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.tasks import amphora_driver_tasks
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
            requires='loadbalancer',
            provides='amphora'))
        create_LB_flow.add(database_tasks.GetAmphoraByID(
            requires='amphora',
            provides='updated_amphora'))
        create_LB_flow.add(database_tasks.GetLoadbalancerByID(
            requires='loadbalancer',
            provides='updated_loadbalancer'))
        new_LB_net_subflow = self.get_new_LB_networking_subflow()
        create_LB_flow.add(new_LB_net_subflow)
        create_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires='loadbalancer'))

        return create_LB_flow

    def get_delete_load_balancer_flow(self):
        """Creates a flow to delete a load balancer.

        :returns: The flow for deleting a load balancer
        """
        delete_LB_flow = linear_flow.Flow(constants.DELETE_LOADBALANCER_FLOW)
        delete_LB_flow.add(controller_tasks.DeleteListenersOnLB(
            requires='loadbalancer'))
# TODO(johnsom) tear down the unplug vips? and networks
        delete_LB_flow.add(database_tasks.MarkLBDeletedInDB(
            requires='loadbalancer'))

        return delete_LB_flow

    def get_new_LB_networking_subflow(self):
        """Create a sub-flow to setup networking.

        :returns: The flow to setup networking for a new amphora
        """

        new_LB_net_subflow = linear_flow.Flow(constants.
                                              LOADBALANCER_NETWORKING_SUBFLOW)
        new_LB_net_subflow.add(network_tasks.GetPlumbedNetworks(
            rebind={'amphora': 'updated_amphora'},
            provides='nics'))
        new_LB_net_subflow.add(network_tasks.CalculateDelta(
            rebind={'amphora': 'updated_amphora'},
            requires='nics',
            provides='delta'))
        new_LB_net_subflow.add(network_tasks.PlugNetworks(
            rebind={'amphora': 'updated_amphora'},
            requires='delta'))
        new_LB_net_subflow.add(amphora_driver_tasks.AmphoraPostNetworkPlug(
            rebind={'amphora': 'updated_amphora'}))
        new_LB_net_subflow.add(network_tasks.PlugVIP(
            rebind={'amphora': 'updated_amphora'}))
        new_LB_net_subflow.add(amphora_driver_tasks.AmphoraPostVIPPlug(
            rebind={'loadbalancer': 'updated_loadbalancer'}))

        return new_LB_net_subflow

    def get_update_load_balancer_flow(self):
        """Creates a flow to update a load balancer.

        :returns: The flow for update a load balancer
        """
        update_LB_flow = linear_flow.Flow(constants.UPDATE_LOADBALANCER_FLOW)
        update_LB_flow.add(controller_tasks.DisableEnableLB(
            requires='loadbalancer'))
        update_LB_flow.add(database_tasks.MarkLBActiveInDB(
            requires='loadbalancer'))

        return update_LB_flow
