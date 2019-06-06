#    Copyright 2016 Rackspace
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from oslo_utils import uuidutils

from octavia.controller.worker.v2.tasks import lifecycle_tasks
import octavia.tests.unit.base as base


class TestLifecycleTasks(base.TestCase):

    def setUp(self):

        self.AMPHORA = mock.MagicMock()
        self.AMPHORA_ID = uuidutils.generate_uuid()
        self.AMPHORA.id = self.AMPHORA_ID
        self.HEALTH_MON = mock.MagicMock()
        self.HEALTH_MON_ID = uuidutils.generate_uuid()
        self.HEALTH_MON.pool_id = self.HEALTH_MON_ID
        self.L7POLICY = mock.MagicMock()
        self.L7POLICY_ID = uuidutils.generate_uuid()
        self.L7POLICY.id = self.L7POLICY_ID
        self.L7RULE = mock.MagicMock()
        self.L7RULE_ID = uuidutils.generate_uuid()
        self.L7RULE.id = self.L7RULE_ID
        self.LISTENER = mock.MagicMock()
        self.LISTENER_ID = uuidutils.generate_uuid()
        self.LISTENER.id = self.LISTENER_ID
        self.LISTENERS = [self.LISTENER]
        self.LOADBALANCER = mock.MagicMock()
        self.LOADBALANCER_ID = uuidutils.generate_uuid()
        self.LOADBALANCER.id = self.LOADBALANCER_ID
        self.LISTENER.load_balancer = self.LOADBALANCER
        self.MEMBER = mock.MagicMock()
        self.MEMBER_ID = uuidutils.generate_uuid()
        self.MEMBER.id = self.MEMBER_ID
        self.MEMBERS = [self.MEMBER]
        self.POOL = mock.MagicMock()
        self.POOL_ID = uuidutils.generate_uuid()
        self.POOL.id = self.POOL_ID

        super(TestLifecycleTasks, self).setUp()

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'unmark_amphora_health_busy')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_amphora_status_error')
    def test_AmphoraIDToErrorOnRevertTask(self, mock_amp_status_error,
                                          mock_amp_health_busy):

        amp_id_to_error_on_revert = (lifecycle_tasks.
                                     AmphoraIDToErrorOnRevertTask())

        # Execute
        amp_id_to_error_on_revert.execute(self.AMPHORA_ID)

        self.assertFalse(mock_amp_status_error.called)

        # Revert
        amp_id_to_error_on_revert.revert(self.AMPHORA_ID)

        mock_amp_status_error.assert_called_once_with(self.AMPHORA_ID)
        self.assertFalse(mock_amp_health_busy.called)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'unmark_amphora_health_busy')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_amphora_status_error')
    def test_AmphoraToErrorOnRevertTask(self, mock_amp_status_error,
                                        mock_amp_health_busy):

        amp_to_error_on_revert = lifecycle_tasks.AmphoraToErrorOnRevertTask()

        # Execute
        amp_to_error_on_revert.execute(self.AMPHORA)

        self.assertFalse(mock_amp_status_error.called)

        # Revert
        amp_to_error_on_revert.revert(self.AMPHORA)

        mock_amp_status_error.assert_called_once_with(self.AMPHORA_ID)
        self.assertFalse(mock_amp_health_busy.called)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_health_mon_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    def test_HealthMonitorToErrorOnRevertTask(
            self,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_health_mon_prov_status_error):

        health_mon_to_error_on_revert = (lifecycle_tasks.
                                         HealthMonitorToErrorOnRevertTask())

        # Execute
        health_mon_to_error_on_revert.execute(self.HEALTH_MON,
                                              self.LISTENERS,
                                              self.LOADBALANCER)

        self.assertFalse(mock_health_mon_prov_status_error.called)

        # Revert
        health_mon_to_error_on_revert.revert(self.HEALTH_MON,
                                             self.LISTENERS,
                                             self.LOADBALANCER)

        mock_health_mon_prov_status_error.assert_called_once_with(
            self.HEALTH_MON_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_l7policy_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    def test_L7PolicyToErrorOnRevertTask(
            self,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_l7policy_prov_status_error):

        l7policy_to_error_on_revert = (lifecycle_tasks.
                                       L7PolicyToErrorOnRevertTask())

        # Execute
        l7policy_to_error_on_revert.execute(self.L7POLICY,
                                            self.LISTENERS,
                                            self.LOADBALANCER)

        self.assertFalse(mock_l7policy_prov_status_error.called)

        # Revert
        l7policy_to_error_on_revert.revert(self.L7POLICY,
                                           self.LISTENERS,
                                           self.LOADBALANCER)

        mock_l7policy_prov_status_error.assert_called_once_with(
            self.L7POLICY_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_l7rule_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    def test_L7RuleToErrorOnRevertTask(
            self,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_l7rule_prov_status_error):

        l7rule_to_error_on_revert = (lifecycle_tasks.
                                     L7RuleToErrorOnRevertTask())

        # Execute
        l7rule_to_error_on_revert.execute(self.L7RULE,
                                          self.LISTENERS,
                                          self.LOADBALANCER)

        self.assertFalse(mock_l7rule_prov_status_error.called)

        # Revert
        l7rule_to_error_on_revert.revert(self.L7RULE,
                                         self.LISTENERS,
                                         self.LOADBALANCER)

        mock_l7rule_prov_status_error.assert_called_once_with(
            self.L7RULE_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_error')
    def test_ListenerToErrorOnRevertTask(
            self,
            mock_listener_prov_status_error,
            mock_loadbalancer_prov_status_active):

        listener_to_error_on_revert = (lifecycle_tasks.
                                       ListenerToErrorOnRevertTask())

        # Execute
        listener_to_error_on_revert.execute(self.LISTENER)

        self.assertFalse(mock_listener_prov_status_error.called)

        # Revert
        listener_to_error_on_revert.revert(self.LISTENER)

        mock_listener_prov_status_error.assert_called_once_with(
            self.LISTENER_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_error')
    def test_ListenersToErrorOnRevertTask(
            self,
            mock_listener_prov_status_error,
            mock_loadbalancer_prov_status_active):

        listeners_to_error_on_revert = (lifecycle_tasks.
                                        ListenersToErrorOnRevertTask())

        # Execute
        listeners_to_error_on_revert.execute(self.LISTENERS,
                                             self.LOADBALANCER)

        self.assertFalse(mock_listener_prov_status_error.called)

        # Revert
        listeners_to_error_on_revert.revert(self.LISTENERS,
                                            self.LOADBALANCER)

        mock_listener_prov_status_error.assert_called_once_with(
            self.LISTENER_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_error')
    def test_LoadBalancerIDToErrorOnRevertTask(
            self,
            mock_loadbalancer_prov_status_error):

        loadbalancer_id_to_error_on_revert = (
            lifecycle_tasks.LoadBalancerIDToErrorOnRevertTask())

        # Execute
        loadbalancer_id_to_error_on_revert.execute(self.LOADBALANCER_ID)

        self.assertFalse(mock_loadbalancer_prov_status_error.called)

        # Revert
        loadbalancer_id_to_error_on_revert.revert(self.LOADBALANCER_ID)

        mock_loadbalancer_prov_status_error.assert_called_once_with(
            self.LOADBALANCER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_error')
    def test_LoadBalancerToErrorOnRevertTask(
            self,
            mock_loadbalancer_prov_status_error):

        loadbalancer_to_error_on_revert = (
            lifecycle_tasks.LoadBalancerToErrorOnRevertTask())

        # Execute
        loadbalancer_to_error_on_revert.execute(self.LOADBALANCER)

        self.assertFalse(mock_loadbalancer_prov_status_error.called)

        # Revert
        loadbalancer_to_error_on_revert.revert(self.LOADBALANCER)

        mock_loadbalancer_prov_status_error.assert_called_once_with(
            self.LOADBALANCER_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_member_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_pool_prov_status_active')
    def test_MemberToErrorOnRevertTask(
            self,
            mock_pool_prov_status_active,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_member_prov_status_error):
        member_to_error_on_revert = lifecycle_tasks.MemberToErrorOnRevertTask()

        # Execute
        member_to_error_on_revert.execute(self.MEMBER,
                                          self.LISTENERS,
                                          self.LOADBALANCER,
                                          self.POOL)

        self.assertFalse(mock_member_prov_status_error.called)

        # Revert
        member_to_error_on_revert.revert(self.MEMBER,
                                         self.LISTENERS,
                                         self.LOADBALANCER,
                                         self.POOL)

        mock_member_prov_status_error.assert_called_once_with(
            self.MEMBER_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)
        mock_pool_prov_status_active.assert_called_once_with(
            self.POOL_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_member_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_pool_prov_status_active')
    def test_MembersToErrorOnRevertTask(
            self,
            mock_pool_prov_status_active,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_member_prov_status_error):
        members_to_error_on_revert = (
            lifecycle_tasks.MembersToErrorOnRevertTask())

        # Execute
        members_to_error_on_revert.execute(self.MEMBERS,
                                           self.LISTENERS,
                                           self.LOADBALANCER,
                                           self.POOL)

        self.assertFalse(mock_member_prov_status_error.called)

        # Revert
        members_to_error_on_revert.revert(self.MEMBERS,
                                          self.LISTENERS,
                                          self.LOADBALANCER,
                                          self.POOL)

        mock_member_prov_status_error.assert_called_once_with(
            self.MEMBER_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)
        mock_pool_prov_status_active.assert_called_once_with(
            self.POOL_ID)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_pool_prov_status_error')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_loadbalancer_prov_status_active')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_active')
    def test_PoolToErrorOnRevertTask(
            self,
            mock_listener_prov_status_active,
            mock_loadbalancer_prov_status_active,
            mock_pool_prov_status_error):

        pool_to_error_on_revert = lifecycle_tasks.PoolToErrorOnRevertTask()

        # Execute
        pool_to_error_on_revert.execute(self.POOL,
                                        self.LISTENERS,
                                        self.LOADBALANCER)

        self.assertFalse(mock_pool_prov_status_error.called)

        # Revert
        pool_to_error_on_revert.revert(self.POOL,
                                       self.LISTENERS,
                                       self.LOADBALANCER)

        mock_pool_prov_status_error.assert_called_once_with(
            self.POOL_ID)
        mock_loadbalancer_prov_status_active.assert_called_once_with(
            self.LOADBALANCER_ID)
        mock_listener_prov_status_active.assert_called_once_with(
            self.LISTENER_ID)
