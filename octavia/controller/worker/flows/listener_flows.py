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
from octavia.controller.worker.tasks import network_tasks


class ListenerFlows(object):

    def get_create_listener_flow(self):
        """Create a flow to create a listener

        :returns: The flow for creating a listener
        """
        create_listener_flow = linear_flow.Flow(constants.CREATE_LISTENER_FLOW)
        create_listener_flow.add(amphora_driver_tasks.ListenerUpdate(
            requires=[constants.LISTENER, constants.VIP]))
        create_listener_flow.add(network_tasks.UpdateVIP(
            requires=constants.LOADBALANCER))
        create_listener_flow.add(database_tasks.
                                 MarkLBAndListenerActiveInDB(
                                     requires=[constants.LOADBALANCER,
                                               constants.LISTENER]))

        return create_listener_flow

    def get_delete_listener_flow(self):
        """Create a flow to delete a listener

        :returns: The flow for deleting a listener
        """
        delete_listener_flow = linear_flow.Flow(constants.DELETE_LISTENER_FLOW)
        delete_listener_flow.add(amphora_driver_tasks.ListenerDelete(
            requires=[constants.LISTENER, constants.VIP]))
        delete_listener_flow.add(network_tasks.UpdateVIP(
            requires=constants.LOADBALANCER))
        delete_listener_flow.add(database_tasks.DeleteListenerInDB(
            requires=constants.LISTENER))
        delete_listener_flow.add(database_tasks.MarkLBActiveInDB(
            requires=constants.LOADBALANCER))

        return delete_listener_flow

    def get_update_listener_flow(self):
        """Create a flow to update a listener

        :returns: The flow for updating a listener
        """
        update_listener_flow = linear_flow.Flow(constants.UPDATE_LISTENER_FLOW)
        update_listener_flow.add(model_tasks.
                                 UpdateAttributes(
                                     rebind={'object': constants.LISTENER},
                                     requires=[constants.UPDATE_DICT]))
        update_listener_flow.add(amphora_driver_tasks.ListenerUpdate(
            requires=[constants.LISTENER, constants.VIP]))
        update_listener_flow.add(database_tasks.UpdateListenerInDB(
            requires=[constants.LISTENER, constants.UPDATE_DICT]))
        update_listener_flow.add(database_tasks.
                                 MarkLBAndListenerActiveInDB(
                                     requires=[constants.LOADBALANCER,
                                               constants.LISTENER]))

        return update_listener_flow
