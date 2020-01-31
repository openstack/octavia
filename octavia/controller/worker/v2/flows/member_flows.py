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
from taskflow.patterns import unordered_flow

from octavia.common import constants
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import lifecycle_tasks
from octavia.controller.worker.v2.tasks import network_tasks


class MemberFlows(object):

    def get_create_member_flow(self):
        """Create a flow to create a member

        :returns: The flow for creating a member
        """
        create_member_flow = linear_flow.Flow(constants.CREATE_MEMBER_FLOW)
        create_member_flow.add(lifecycle_tasks.MemberToErrorOnRevertTask(
            requires=[constants.MEMBER,
                      constants.LISTENERS,
                      constants.LOADBALANCER,
                      constants.POOL_ID]))
        create_member_flow.add(database_tasks.MarkMemberPendingCreateInDB(
            requires=constants.MEMBER))
        create_member_flow.add(network_tasks.CalculateDelta(
            requires=(constants.LOADBALANCER, constants.AVAILABILITY_ZONE),
            provides=constants.DELTAS))
        create_member_flow.add(network_tasks.HandleNetworkDeltas(
            requires=constants.DELTAS, provides=constants.ADDED_PORTS))
        create_member_flow.add(amphora_driver_tasks.AmphoraePostNetworkPlug(
            requires=(constants.LOADBALANCER, constants.ADDED_PORTS)
        ))
        create_member_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        create_member_flow.add(database_tasks.MarkMemberActiveInDB(
            requires=constants.MEMBER))
        create_member_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL_ID))
        create_member_flow.add(database_tasks.
                               MarkLBAndListenersActiveInDB(
                                   requires=(constants.LISTENERS,
                                             constants.LOADBALANCER_ID)))

        return create_member_flow

    def get_delete_member_flow(self):
        """Create a flow to delete a member

        :returns: The flow for deleting a member
        """
        delete_member_flow = linear_flow.Flow(constants.DELETE_MEMBER_FLOW)
        delete_member_flow.add(lifecycle_tasks.MemberToErrorOnRevertTask(
            requires=[constants.MEMBER,
                      constants.LISTENERS,
                      constants.LOADBALANCER,
                      constants.POOL_ID]))
        delete_member_flow.add(database_tasks.MarkMemberPendingDeleteInDB(
            requires=constants.MEMBER))
        delete_member_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        delete_member_flow.add(database_tasks.DeleteMemberInDB(
            requires=constants.MEMBER))
        delete_member_flow.add(database_tasks.DecrementMemberQuota(
            requires=constants.PROJECT_ID))
        delete_member_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL_ID))
        delete_member_flow.add(database_tasks.
                               MarkLBAndListenersActiveInDB(
                                   requires=(constants.LISTENERS,
                                             constants.LOADBALANCER_ID)))

        return delete_member_flow

    def get_update_member_flow(self):
        """Create a flow to update a member

        :returns: The flow for updating a member
        """
        update_member_flow = linear_flow.Flow(constants.UPDATE_MEMBER_FLOW)
        update_member_flow.add(lifecycle_tasks.MemberToErrorOnRevertTask(
            requires=[constants.MEMBER,
                      constants.LISTENERS,
                      constants.LOADBALANCER,
                      constants.POOL_ID]))
        update_member_flow.add(database_tasks.MarkMemberPendingUpdateInDB(
            requires=constants.MEMBER))
        update_member_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        update_member_flow.add(database_tasks.UpdateMemberInDB(
            requires=[constants.MEMBER, constants.UPDATE_DICT]))
        update_member_flow.add(database_tasks.MarkMemberActiveInDB(
            requires=constants.MEMBER))
        update_member_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL_ID))
        update_member_flow.add(database_tasks.
                               MarkLBAndListenersActiveInDB(
                                   requires=(constants.LISTENERS,
                                             constants.LOADBALANCER_ID)))

        return update_member_flow

    def get_batch_update_members_flow(self, old_members, new_members,
                                      updated_members):
        """Create a flow to batch update members

        :returns: The flow for batch updating members
        """
        batch_update_members_flow = linear_flow.Flow(
            constants.BATCH_UPDATE_MEMBERS_FLOW)
        unordered_members_flow = unordered_flow.Flow(
            constants.UNORDERED_MEMBER_UPDATES_FLOW)
        unordered_members_active_flow = unordered_flow.Flow(
            constants.UNORDERED_MEMBER_ACTIVE_FLOW)

        # Delete old members
        unordered_members_flow.add(
            lifecycle_tasks.MembersToErrorOnRevertTask(
                inject={constants.MEMBERS: old_members},
                name='{flow}-deleted'.format(
                    flow=constants.MEMBER_TO_ERROR_ON_REVERT_FLOW)))
        for m in old_members:
            unordered_members_flow.add(database_tasks.DeleteMemberInDB(
                inject={constants.MEMBER: m},
                name='{flow}-{id}'.format(
                    id=m[constants.MEMBER_ID],
                    flow=constants.DELETE_MEMBER_INDB)))
            unordered_members_flow.add(database_tasks.DecrementMemberQuota(
                requires=constants.PROJECT_ID,
                name='{flow}-{id}'.format(
                    id=m[constants.MEMBER_ID],
                    flow=constants.DECREMENT_MEMBER_QUOTA_FLOW)))

        # Create new members
        unordered_members_flow.add(
            lifecycle_tasks.MembersToErrorOnRevertTask(
                inject={constants.MEMBERS: new_members},
                name='{flow}-created'.format(
                    flow=constants.MEMBER_TO_ERROR_ON_REVERT_FLOW)))
        for m in new_members:
            unordered_members_active_flow.add(
                database_tasks.MarkMemberActiveInDB(
                    inject={constants.MEMBER: m},
                    name='{flow}-{id}'.format(
                        id=m[constants.MEMBER_ID],
                        flow=constants.MARK_MEMBER_ACTIVE_INDB)))

        # Update existing members
        unordered_members_flow.add(
            lifecycle_tasks.MembersToErrorOnRevertTask(
                # updated_members is a list of (obj, dict), only pass `obj`
                inject={constants.MEMBERS: [m[0] for m in updated_members]},
                name='{flow}-updated'.format(
                    flow=constants.MEMBER_TO_ERROR_ON_REVERT_FLOW)))
        for m, um in updated_members:
            um.pop(constants.ID, None)
            unordered_members_active_flow.add(
                database_tasks.MarkMemberActiveInDB(
                    inject={constants.MEMBER: m},
                    name='{flow}-{id}'.format(
                        id=m[constants.MEMBER_ID],
                        flow=constants.MARK_MEMBER_ACTIVE_INDB)))

        batch_update_members_flow.add(unordered_members_flow)

        # Done, do real updates
        batch_update_members_flow.add(network_tasks.CalculateDelta(
            requires=(constants.LOADBALANCER, constants.AVAILABILITY_ZONE),
            provides=constants.DELTAS))
        batch_update_members_flow.add(network_tasks.HandleNetworkDeltas(
            requires=constants.DELTAS, provides=constants.ADDED_PORTS))
        batch_update_members_flow.add(
            amphora_driver_tasks.AmphoraePostNetworkPlug(
                requires=(constants.LOADBALANCER, constants.ADDED_PORTS)))

        # Update the Listener (this makes the changes active on the Amp)
        batch_update_members_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))

        # Mark all the members ACTIVE here, then pool then LB/Listeners
        batch_update_members_flow.add(unordered_members_active_flow)
        batch_update_members_flow.add(database_tasks.MarkPoolActiveInDB(
            requires=constants.POOL_ID))
        batch_update_members_flow.add(
            database_tasks.MarkLBAndListenersActiveInDB(
                requires=(constants.LISTENERS, constants.LOADBALANCER_ID)))

        return batch_update_members_flow
