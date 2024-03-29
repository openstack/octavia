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
from unittest import mock

from oslo_utils import uuidutils
import tenacity

from octavia.common import constants
from octavia.controller.worker import task_utils as task_utilities
import octavia.tests.unit.base as base


class TestTaskUtils(base.TestCase):

    def setUp(self):

        self.task_utils = task_utilities.TaskUtils()

        self.AMPHORA_ID = uuidutils.generate_uuid()
        self.HEALTH_MON_ID = uuidutils.generate_uuid()
        self.L7POLICY_ID = uuidutils.generate_uuid()
        self.L7RULE_ID = uuidutils.generate_uuid()
        self.LISTENER_ID = uuidutils.generate_uuid()
        self.LOADBALANCER_ID = uuidutils.generate_uuid()
        self.MEMBER_ID = uuidutils.generate_uuid()
        self.POOL_ID = uuidutils.generate_uuid()

        super().setUp()

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.AmphoraRepository.update')
    def test_mark_amphora_status_error(self,
                                       mock_amphora_repo_update,
                                       mock_get_session):

        # Happy path
        self.task_utils.mark_amphora_status_error(self.AMPHORA_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_amphora_repo_update.assert_called_once_with(
            mock_session,
            id=self.AMPHORA_ID,
            status=constants.ERROR)

        # Exception path
        mock_amphora_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_amphora_status_error(self.AMPHORA_ID)

        self.assertFalse(mock_amphora_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_mark_health_mon_prov_status_error(self,
                                               mock_health_mon_repo_update,
                                               mock_get_session):

        # Happy path
        self.task_utils.mark_health_mon_prov_status_error(self.HEALTH_MON_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=self.HEALTH_MON_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_health_mon_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_health_mon_prov_status_error(self.HEALTH_MON_ID)

        self.assertFalse(mock_health_mon_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_mark_l7policy_prov_status_error(self,
                                             mock_l7policy_repo_update,
                                             mock_get_session):

        # Happy path
        self.task_utils.mark_l7policy_prov_status_error(self.L7POLICY_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=self.L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_l7policy_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_l7policy_prov_status_error(self.L7POLICY_ID)

        self.assertFalse(mock_l7policy_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    def test_mark_l7rule_prov_status_error(self,
                                           mock_l7rule_repo_update,
                                           mock_get_session):

        # Happy path
        self.task_utils.mark_l7rule_prov_status_error(self.L7RULE_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=self.L7RULE_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_l7rule_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_l7rule_prov_status_error(self.L7RULE_ID)

        self.assertFalse(mock_l7rule_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.ListenerRepository.update')
    def test_mark_listener_prov_status_active(self,
                                              mock_listener_repo_update,
                                              mock_get_session):

        # Happy path
        self.task_utils.mark_listener_prov_status_active(self.LISTENER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_listener_repo_update.assert_called_once_with(
            mock_session,
            id=self.LISTENER_ID,
            provisioning_status=constants.ACTIVE)

        # Exception path
        mock_listener_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_listener_prov_status_active(self.LISTENER_ID)

        self.assertFalse(mock_listener_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.ListenerRepository.update')
    def test_mark_listener_prov_status_error(self,
                                             mock_listener_repo_update,
                                             mock_get_session):

        # Happy path
        self.task_utils.mark_listener_prov_status_error(self.LISTENER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_listener_repo_update.assert_called_once_with(
            mock_session,
            id=self.LISTENER_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_listener_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_listener_prov_status_error(self.LISTENER_ID)

        self.assertFalse(mock_listener_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('tenacity.nap.time')
    # mock LOG so we don't fill the console with log messages from
    # tenacity.retry
    @mock.patch('octavia.controller.worker.task_utils.LOG')
    def test_mark_loadbalancer_prov_status_active(self,
                                                  mock_LOG,
                                                  mock_time,
                                                  mock_lb_repo_update,
                                                  mock_get_session):

        # Happy path
        self.task_utils.mark_loadbalancer_prov_status_active(
            self.LOADBALANCER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_lb_repo_update.assert_called_once_with(
            mock_session,
            id=self.LOADBALANCER_ID,
            provisioning_status=constants.ACTIVE)

        # Exception path
        mock_lb_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.assertRaises(
            tenacity.RetryError,
            self.task_utils.mark_loadbalancer_prov_status_active,
            self.LOADBALANCER_ID)

        self.assertFalse(mock_lb_repo_update.called)

        # Exceptions then happy path
        mock_get_session.reset_mock(side_effect=True)
        mock_lb_repo_update.reset_mock()

        mock_session = mock_get_session()
        mock_session_context = mock_session.begin().__enter__()
        mock_get_session.side_effect = [
            Exception('fail'),
            Exception('fail'),
            Exception('fail'),
            mock_session]

        self.task_utils.mark_loadbalancer_prov_status_active(
            self.LOADBALANCER_ID)

        mock_lb_repo_update.assert_called_once_with(
            mock_session_context,
            id=self.LOADBALANCER_ID,
            provisioning_status=constants.ACTIVE)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('tenacity.nap.time')
    # mock LOG so we don't fill the console with log messages from
    # tenacity.retry
    @mock.patch('octavia.controller.worker.task_utils.LOG')
    def test_mark_loadbalancer_prov_status_error(self,
                                                 mock_LOG,
                                                 mock_time,
                                                 mock_lb_repo_update,
                                                 mock_get_session):

        # Happy path
        self.task_utils.mark_loadbalancer_prov_status_error(
            self.LOADBALANCER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_lb_repo_update.assert_called_once_with(
            mock_session,
            id=self.LOADBALANCER_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_lb_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.assertRaises(tenacity.RetryError,
                          self.task_utils.mark_loadbalancer_prov_status_error,
                          self.LOADBALANCER_ID)

        self.assertFalse(mock_lb_repo_update.called)

        # Exceptions then happy path
        mock_get_session.reset_mock(side_effect=True)
        mock_lb_repo_update.reset_mock()

        mock_session = mock_get_session()
        mock_session_context = mock_session.begin().__enter__()
        mock_get_session.side_effect = [
            Exception('fail'),
            Exception('fail'),
            Exception('fail'),
            mock_session]

        self.task_utils.mark_loadbalancer_prov_status_error(
            self.LOADBALANCER_ID)

        mock_lb_repo_update.assert_called_once_with(
            mock_session_context,
            id=self.LOADBALANCER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_mark_member_prov_status_error(self,
                                           mock_member_repo_update,
                                           mock_get_session):

        # Happy path
        self.task_utils.mark_member_prov_status_error(self.MEMBER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=self.MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_member_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_member_prov_status_error(self.MEMBER_ID)

        self.assertFalse(mock_member_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_mark_pool_prov_status_error(self,
                                         mock_pool_repo_update,
                                         mock_get_session):

        # Happy path
        self.task_utils.mark_pool_prov_status_error(self.POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=self.POOL_ID,
            provisioning_status=constants.ERROR)

        # Exception path
        mock_pool_repo_update.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.mark_pool_prov_status_error(self.POOL_ID)

        self.assertFalse(mock_pool_repo_update.called)

    @mock.patch('octavia.db.api.session')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_current_loadbalancer_from_db(self, mock_lb_repo_get,
                                              mock_get_session):
        # Happy path
        self.task_utils.get_current_loadbalancer_from_db(self.LOADBALANCER_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_lb_repo_get.assert_called_once_with(
            mock_session,
            id=self.LOADBALANCER_ID)

        # Exception path
        mock_lb_repo_get.reset_mock()
        mock_get_session.side_effect = Exception('fail')

        self.task_utils.get_current_loadbalancer_from_db(self.POOL_ID)

        self.assertFalse(mock_lb_repo_get.called)
