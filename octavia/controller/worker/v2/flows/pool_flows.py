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
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import lifecycle_tasks
from octavia.controller.worker.v2.tasks import model_tasks


class PoolFlows(object):

    def get_create_pool_flow(self):
        """Create a flow to create a pool

        :returns: The flow for creating a pool
        """
        create_pool_flow = linear_flow.Flow(constants.CREATE_POOL_FLOW)
        create_pool_flow.add(lifecycle_tasks.PoolToErrorOnRevertTask(
            requires=[constants.POOL,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        create_pool_flow.add(database_tasks.MarkPoolPendingCreateInDB(
            requires=constants.POOL))
        create_pool_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        create_pool_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL))
        create_pool_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return create_pool_flow

    def get_delete_pool_flow(self):
        """Create a flow to delete a pool

        :returns: The flow for deleting a pool
        """
        delete_pool_flow = linear_flow.Flow(constants.DELETE_POOL_FLOW)
        delete_pool_flow.add(lifecycle_tasks.PoolToErrorOnRevertTask(
            requires=[constants.POOL,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        delete_pool_flow.add(database_tasks.MarkPoolPendingDeleteInDB(
            requires=constants.POOL))
        delete_pool_flow.add(database_tasks.CountPoolChildrenForQuota(
            requires=constants.POOL, provides=constants.POOL_CHILD_COUNT))
        delete_pool_flow.add(model_tasks.DeleteModelObject(
            rebind={constants.OBJECT: constants.POOL}))
        delete_pool_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        delete_pool_flow.add(database_tasks.DeletePoolInDB(
            requires=constants.POOL))
        delete_pool_flow.add(database_tasks.DecrementPoolQuota(
            requires=[constants.POOL, constants.POOL_CHILD_COUNT]))
        delete_pool_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return delete_pool_flow

    def get_delete_pool_flow_internal(self, name):
        """Create a flow to delete a pool, etc.

        :returns: The flow for deleting a pool
        """
        delete_pool_flow = linear_flow.Flow(constants.DELETE_POOL_FLOW)
        # health monitor should cascade
        # members should cascade
        delete_pool_flow.add(database_tasks.MarkPoolPendingDeleteInDB(
            name='mark_pool_pending_delete_in_db_' + name,
            requires=constants.POOL,
            rebind={constants.POOL: name}))
        delete_pool_flow.add(database_tasks.CountPoolChildrenForQuota(
            name='count_pool_children_for_quota_' + name,
            requires=constants.POOL,
            provides=constants.POOL_CHILD_COUNT,
            rebind={constants.POOL: name}))
        delete_pool_flow.add(model_tasks.DeleteModelObject(
            name='delete_model_object_' + name,
            rebind={constants.OBJECT: name}))
        delete_pool_flow.add(database_tasks.DeletePoolInDB(
            name='delete_pool_in_db_' + name,
            requires=constants.POOL,
            rebind={constants.POOL: name}))
        delete_pool_flow.add(database_tasks.DecrementPoolQuota(
            name='decrement_pool_quota_' + name,
            requires=[constants.POOL, constants.POOL_CHILD_COUNT],
            rebind={constants.POOL: name}))

        return delete_pool_flow

    def get_update_pool_flow(self):
        """Create a flow to update a pool

        :returns: The flow for updating a pool
        """
        update_pool_flow = linear_flow.Flow(constants.UPDATE_POOL_FLOW)
        update_pool_flow.add(lifecycle_tasks.PoolToErrorOnRevertTask(
            requires=[constants.POOL,
                      constants.LISTENERS,
                      constants.LOADBALANCER]))
        update_pool_flow.add(database_tasks.MarkPoolPendingUpdateInDB(
            requires=constants.POOL))
        update_pool_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER))
        update_pool_flow.add(database_tasks.UpdatePoolInDB(
            requires=[constants.POOL, constants.UPDATE_DICT]))
        update_pool_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL))
        update_pool_flow.add(database_tasks.MarkLBAndListenersActiveInDB(
            requires=[constants.LOADBALANCER, constants.LISTENERS]))

        return update_pool_flow
