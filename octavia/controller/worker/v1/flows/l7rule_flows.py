# Copyright 2016 Blue Box, an IBM Company
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

from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.v1.tasks import amphora_driver_tasks
from octavia.controller.worker.v1.tasks import database_tasks
from octavia.controller.worker.v1.tasks import lifecycle_tasks
from octavia.controller.worker.v1.tasks import model_tasks


class L7RuleFlows(object):

    def get_create_l7rule_flow(self):
        """Create a flow to create an L7 rule

        :returns: The flow for creating an L7 rule
        """
        create_l7rule_flow = linear_flow.Flow(constants.CREATE_L7RULE_FLOW)
        create_l7rule_flow.add(lifecycle_tasks.L7RuleToErrorOnRevertTask(
            requires=[constants.L7RULE,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        create_l7rule_flow.add(database_tasks.MarkL7RulePendingCreateInDB(
            requires=constants.L7RULE))
        create_l7rule_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        create_l7rule_flow.add(database_tasks.MarkL7RuleActiveInDB(
            requires=constants.L7RULE))
        create_l7rule_flow.add(database_tasks.MarkL7PolicyActiveInDB(
            requires=constants.L7POLICY))
        create_l7rule_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return create_l7rule_flow

    def get_delete_l7rule_flow(self):
        """Create a flow to delete an L7 rule

        :returns: The flow for deleting an L7 rule
        """
        delete_l7rule_flow = linear_flow.Flow(constants.DELETE_L7RULE_FLOW)
        delete_l7rule_flow.add(lifecycle_tasks.L7RuleToErrorOnRevertTask(
            requires=[constants.L7RULE,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        delete_l7rule_flow.add(database_tasks.MarkL7RulePendingDeleteInDB(
            requires=constants.L7RULE))
        delete_l7rule_flow.add(model_tasks.DeleteModelObject(
            rebind={constants.OBJECT: constants.L7RULE}))
        delete_l7rule_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        delete_l7rule_flow.add(database_tasks.DeleteL7RuleInDB(
            requires=constants.L7RULE))
        delete_l7rule_flow.add(database_tasks.MarkL7PolicyActiveInDB(
            requires=constants.L7POLICY))
        delete_l7rule_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return delete_l7rule_flow

    def get_update_l7rule_flow(self):
        """Create a flow to update an L7 rule

        :returns: The flow for updating an L7 rule
        """
        update_l7rule_flow = linear_flow.Flow(constants.UPDATE_L7RULE_FLOW)
        update_l7rule_flow.add(lifecycle_tasks.L7RuleToErrorOnRevertTask(
            requires=[constants.L7RULE,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        update_l7rule_flow.add(database_tasks.MarkL7RulePendingUpdateInDB(
            requires=constants.L7RULE))
        update_l7rule_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        update_l7rule_flow.add(database_tasks.UpdateL7RuleInDB(
            requires=[constants.L7RULE, constants.UPDATE_DICT]))
        update_l7rule_flow.add(database_tasks.MarkL7RuleActiveInDB(
            requires=constants.L7RULE))
        update_l7rule_flow.add(database_tasks.MarkL7PolicyActiveInDB(
            requires=constants.L7POLICY))
        update_l7rule_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return update_l7rule_flow
