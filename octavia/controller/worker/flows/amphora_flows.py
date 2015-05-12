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
from taskflow import retry

from octavia.common import constants
from octavia.controller.worker.flows import load_balancer_flows
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import compute_tasks
from octavia.controller.worker.tasks import controller_tasks
from octavia.controller.worker.tasks import database_tasks

CONF = cfg.CONF
CONF.import_group('controller_worker', 'octavia.common.config')


class AmphoraFlows(object):

    def __init__(self):
        self._lb_flows = load_balancer_flows.LoadBalancerFlows()

    def get_create_amphora_flow(self):
        """Creates a flow to create an amphora.

        Ideally that should be configurable in the
        config file - a db session needs to be placed
        into the flow

        :returns: The flow for creating the amphora
        """
        create_amphora_flow = linear_flow.Flow(constants.CREATE_AMPHORA_FLOW)
        create_amphora_flow.add(database_tasks.CreateAmphoraInDB(
                                provides=constants.AMPHORA_ID))
        create_amphora_flow.add(compute_tasks.ComputeCreate(
            requires=constants.AMPHORA_ID,
            provides=constants.COMPUTE_ID))
        create_amphora_flow.add(database_tasks.MarkAmphoraBootingInDB(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        wait_flow = linear_flow.Flow('wait_for_amphora',
                                     retry=retry.Times(CONF.
                                                       controller_worker.
                                                       amp_active_retries))
        wait_flow.add(compute_tasks.ComputeWait(
            requires=constants.COMPUTE_ID))
        create_amphora_flow.add(wait_flow)
        create_amphora_flow.add(database_tasks.ReloadAmphora(
            requires=constants.AMPHORA_ID,
            provides=constants.AMPHORA))
        create_amphora_flow.add(amphora_driver_tasks.AmphoraFinalize(
            requires=constants.AMPHORA))
        create_amphora_flow.add(database_tasks.MarkAmphoraReadyInDB(
            requires=constants.AMPHORA))

        return create_amphora_flow

    def get_create_amphora_for_lb_flow(self):
        """Creates a flow to create an amphora for a load balancer.

        This flow is used when there are no spare amphora available
        for a new load balancer.  It builds an amphora and allocates
        for the specific load balancer.

        :returns: The The flow for creating the amphora
        """
        create_amp_for_lb_flow = linear_flow.Flow(constants.
                                                  CREATE_AMPHORA_FOR_LB_FLOW)
        create_amp_for_lb_flow.add(database_tasks.CreateAmphoraInDB(
            provides=constants.AMPHORA_ID))
        create_amp_for_lb_flow.add(compute_tasks.ComputeCreate(
            requires=constants.AMPHORA_ID,
            provides=constants.COMPUTE_ID))
        create_amp_for_lb_flow.add(database_tasks.UpdateAmphoraComputeId(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        create_amp_for_lb_flow.add(database_tasks.MarkAmphoraBootingInDB(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_ID)))
        wait_flow = linear_flow.Flow('wait_for_amphora',
                                     retry=retry.Times(CONF.
                                                       controller_worker.
                                                       amp_active_retries))
        wait_flow.add(compute_tasks.ComputeWait(
            requires=constants.COMPUTE_ID,
            provides=constants.COMPUTE_OBJ))
        wait_flow.add(database_tasks.UpdateAmphoraInfo(
            requires=(constants.AMPHORA_ID, constants.COMPUTE_OBJ),
            provides=constants.AMPHORA))
        create_amp_for_lb_flow.add(wait_flow)
        create_amp_for_lb_flow.add(amphora_driver_tasks.AmphoraFinalize(
            requires=constants.AMPHORA))
        create_amp_for_lb_flow.add(
            database_tasks.MarkAmphoraAllocatedInDB(
                requires=(constants.AMPHORA, constants.LOADBALANCER_ID)))
        create_amp_for_lb_flow.add(
            database_tasks.ReloadAmphora(requires=constants.AMPHORA_ID,
                                         provides=constants.AMPHORA))
        create_amp_for_lb_flow.add(
            database_tasks.ReloadLoadBalancer(
                name=constants.RELOAD_LB_AFTER_AMP_ASSOC,
                requires=constants.LOADBALANCER_ID,
                provides=constants.LOADBALANCER))
        new_LB_net_subflow = self._lb_flows.get_new_LB_networking_subflow()
        create_amp_for_lb_flow.add(new_LB_net_subflow)
        create_amp_for_lb_flow.add(database_tasks.MarkLBActiveInDB(
                                   requires=constants.LOADBALANCER))

        return create_amp_for_lb_flow

    def get_delete_amphora_flow(self):
        """Creates a flow to delete an amphora.

        This should be configurable in the config file
        :returns: The flow for deleting the amphora
        :raises AmphoraNotFound: The referenced Amphora was not found
        """

        delete_amphora_flow = linear_flow.Flow(constants.DELETE_AMPHORA_FLOW)
        delete_amphora_flow.add(controller_tasks.DeleteLoadBalancersOnAmp(
                                requires='amphora'))
# TODO(johnsom) make this just delete it
        delete_amphora_flow.add(database_tasks.
                                MarkAmphoraPendingDeleteInDB(
                                    requires='amphora'))

        return delete_amphora_flow
