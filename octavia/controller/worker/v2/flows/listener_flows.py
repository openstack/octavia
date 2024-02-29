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


class ListenerFlows(object):

    def get_create_listener_flow(self, flavor_dict=None):
        """Create a flow to create a listener

        :returns: The flow for creating a listener
        """
        create_listener_flow = linear_flow.Flow(constants.CREATE_LISTENER_FLOW)
        create_listener_flow.add(lifecycle_tasks.ListenersToErrorOnRevertTask(
            requires=constants.LISTENERS))
        create_listener_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        create_listener_flow.add(network_tasks.UpdateVIP(
            requires=constants.LISTENERS))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            create_listener_flow.add(*self._get_firewall_rules_subflow(
                flavor_dict))

        create_listener_flow.add(database_tasks.
                                 MarkLBAndListenersActiveInDB(
                                     requires=(constants.LOADBALANCER_ID,
                                               constants.LISTENERS)))
        return create_listener_flow

    def get_create_all_listeners_flow(self, flavor_dict=None):
        """Create a flow to create all listeners

        :returns: The flow for creating all listeners
        """
        create_all_listeners_flow = linear_flow.Flow(
            constants.CREATE_LISTENERS_FLOW)
        create_all_listeners_flow.add(
            database_tasks.GetListenersFromLoadbalancer(
                requires=constants.LOADBALANCER,
                provides=constants.LISTENERS))
        create_all_listeners_flow.add(database_tasks.ReloadLoadBalancer(
            requires=constants.LOADBALANCER_ID,
            provides=constants.LOADBALANCER))
        create_all_listeners_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        create_all_listeners_flow.add(network_tasks.UpdateVIP(
            requires=constants.LISTENERS))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            create_all_listeners_flow.add(*self._get_firewall_rules_subflow(
                flavor_dict))

        create_all_listeners_flow.add(
            database_tasks.MarkHealthMonitorsOnlineInDB(
                requires=constants.LOADBALANCER))
        return create_all_listeners_flow

    def get_delete_listener_flow(self, flavor_dict=None):
        """Create a flow to delete a listener

        :returns: The flow for deleting a listener
        """
        delete_listener_flow = linear_flow.Flow(constants.DELETE_LISTENER_FLOW)
        delete_listener_flow.add(lifecycle_tasks.ListenerToErrorOnRevertTask(
            requires=constants.LISTENER))
        delete_listener_flow.add(amphora_driver_tasks.ListenerDelete(
            requires=constants.LISTENER))
        delete_listener_flow.add(network_tasks.UpdateVIPForDelete(
            requires=constants.LOADBALANCER_ID))
        delete_listener_flow.add(database_tasks.DeleteListenerInDB(
            requires=constants.LISTENER))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            delete_listener_flow.add(*self._get_firewall_rules_subflow(
                flavor_dict))

        delete_listener_flow.add(database_tasks.DecrementListenerQuota(
            requires=constants.PROJECT_ID))
        delete_listener_flow.add(database_tasks.MarkLBActiveInDBByListener(
            requires=constants.LISTENER))

        return delete_listener_flow

    def get_delete_listener_internal_flow(self, listener, flavor_dict=None):
        """Create a flow to delete a listener and l7policies internally

           (will skip deletion on the amp and marking LB active)

        :returns: The flow for deleting a listener
        """
        listener_id = listener[constants.LISTENER_ID]
        delete_listener_flow = linear_flow.Flow(
            constants.DELETE_LISTENER_FLOW + '-' + listener_id)
        # Should cascade delete all L7 policies
        delete_listener_flow.add(network_tasks.UpdateVIPForDelete(
            name='delete_update_vip_' + listener_id,
            requires=constants.LOADBALANCER_ID))
        delete_listener_flow.add(database_tasks.DeleteListenerInDB(
            name='delete_listener_in_db_' + listener_id,
            requires=constants.LISTENER,
            inject={constants.LISTENER: listener}))

        # Currently the flavor_dict will always be None since there is
        # no point updating the firewall rules when deleting the LB.
        # However, this may be used for additional flows in the future, so
        # adding this code for completeness.
        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            delete_listener_flow.add(*self._get_firewall_rules_subflow(
                flavor_dict))

        delete_listener_flow.add(database_tasks.DecrementListenerQuota(
            name='decrement_listener_quota_' + listener_id,
            requires=constants.PROJECT_ID))

        return delete_listener_flow

    def get_update_listener_flow(self, flavor_dict=None):
        """Create a flow to update a listener

        :returns: The flow for updating a listener
        """
        update_listener_flow = linear_flow.Flow(constants.UPDATE_LISTENER_FLOW)
        update_listener_flow.add(lifecycle_tasks.ListenerToErrorOnRevertTask(
            requires=constants.LISTENER))
        update_listener_flow.add(amphora_driver_tasks.ListenersUpdate(
            requires=constants.LOADBALANCER_ID))
        update_listener_flow.add(network_tasks.UpdateVIP(
            requires=constants.LISTENERS))

        if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
            update_listener_flow.add(*self._get_firewall_rules_subflow(
                flavor_dict))

        update_listener_flow.add(database_tasks.UpdateListenerInDB(
            requires=[constants.LISTENER, constants.UPDATE_DICT]))
        update_listener_flow.add(database_tasks.
                                 MarkLBAndListenersActiveInDB(
                                     requires=(constants.LOADBALANCER_ID,
                                               constants.LISTENERS)))

        return update_listener_flow

    def _get_firewall_rules_subflow(self, flavor_dict):
        """Creates a subflow that updates the firewall rules in the amphorae.

        :returns: The subflow for updating firewall rules in the amphorae.
        """
        sf_name = constants.FIREWALL_RULES_SUBFLOW
        fw_rules_subflow = linear_flow.Flow(sf_name)

        fw_rules_subflow.add(database_tasks.GetAmphoraeFromLoadbalancer(
            name=sf_name + '-' + constants.GET_AMPHORAE_FROM_LB,
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORAE))

        fw_rules_subflow.add(network_tasks.GetAmphoraeNetworkConfigs(
            name=sf_name + '-' + constants.GET_AMP_NETWORK_CONFIG,
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORAE_NETWORK_CONFIG))

        update_amps_subflow = unordered_flow.Flow(
            constants.AMP_UPDATE_FW_SUBFLOW)

        amp_0_subflow = linear_flow.Flow('amp-0-fw-update')

        amp_0_subflow.add(database_tasks.GetAmphoraFirewallRules(
            name=sf_name + '-0-' + constants.GET_AMPHORA_FIREWALL_RULES,
            requires=(constants.AMPHORAE, constants.AMPHORAE_NETWORK_CONFIG),
            provides=constants.AMPHORA_FIREWALL_RULES,
            inject={constants.AMPHORA_INDEX: 0}))

        amp_0_subflow.add(amphora_driver_tasks.SetAmphoraFirewallRules(
            name=sf_name + '-0-' + constants.SET_AMPHORA_FIREWALL_RULES,
            requires=(constants.AMPHORAE, constants.AMPHORA_FIREWALL_RULES),
            inject={constants.AMPHORA_INDEX: 0}))

        update_amps_subflow.add(amp_0_subflow)

        if (flavor_dict[constants.LOADBALANCER_TOPOLOGY] ==
                constants.TOPOLOGY_ACTIVE_STANDBY):

            amp_1_subflow = linear_flow.Flow('amp-1-fw-update')

            amp_1_subflow.add(database_tasks.GetAmphoraFirewallRules(
                name=sf_name + '-1-' + constants.GET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE,
                          constants.AMPHORAE_NETWORK_CONFIG),
                provides=constants.AMPHORA_FIREWALL_RULES,
                inject={constants.AMPHORA_INDEX: 1}))

            amp_1_subflow.add(amphora_driver_tasks.SetAmphoraFirewallRules(
                name=sf_name + '-1-' + constants.SET_AMPHORA_FIREWALL_RULES,
                requires=(constants.AMPHORAE,
                          constants.AMPHORA_FIREWALL_RULES),
                inject={constants.AMPHORA_INDEX: 1}))

            update_amps_subflow.add(amp_1_subflow)

        fw_rules_subflow.add(update_amps_subflow)

        return fw_rules_subflow
