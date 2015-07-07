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

from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.controller.worker.tasks import database_tasks
from octavia.controller.worker.tasks import model_tasks


class HealthMonitorFlows(object):

    def get_create_health_monitor_flow(self):
        """Create a flow to create a health monitor

        :returns: The flow for creating a health monitor
        """
        create_hm_flow = linear_flow.Flow(constants.CREATE_HEALTH_MONITOR_FLOW)
        create_hm_flow.add(amphora_driver_tasks.ListenerUpdate(
            requires=['listener', 'vip']))
        create_hm_flow.add(database_tasks.MarkLBAndListenerActiveInDB(
            requires=['loadbalancer', 'listener']))

        return create_hm_flow

    def get_delete_health_monitor_flow(self):
        """Create a flow to delete a health monitor

        :returns: The flow for deleting a health monitor
        """
        delete_hm_flow = linear_flow.Flow(constants.DELETE_HEALTH_MONITOR_FLOW)
        delete_hm_flow.add(model_tasks.
                           DeleteModelObject(rebind={'object': 'health_mon'}))
        delete_hm_flow.add(amphora_driver_tasks.ListenerUpdate(
            requires=['listener', 'vip']))
        delete_hm_flow.add(database_tasks.DeleteHealthMonitorInDB(
            requires='pool_id'))
        delete_hm_flow.add(database_tasks.MarkLBAndListenerActiveInDB(
            requires=['loadbalancer', 'listener']))

        return delete_hm_flow

    def get_update_health_monitor_flow(self):
        """Create a flow to update a health monitor

        :returns: The flow for updating a health monitor
        """
        update_hm_flow = linear_flow.Flow(constants.UPDATE_HEALTH_MONITOR_FLOW)
        update_hm_flow.add(model_tasks.
                           UpdateAttributes(
                               rebind={'object': 'health_mon'},
                               requires=['update_dict']))
        update_hm_flow.add(amphora_driver_tasks.ListenerUpdate(
            requires=['listener', 'vip']))
        update_hm_flow.add(database_tasks.UpdateHealthMonInDB(
            requires=['health_mon', 'update_dict']))
        update_hm_flow.add(database_tasks.MarkLBAndListenerActiveInDB(
            requires=['loadbalancer', 'listener']))

        return update_hm_flow
