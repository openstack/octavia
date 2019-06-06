# Copyright 2017 Rackspace, US Inc.
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

import mock
from oslo_utils import uuidutils
from taskflow.types import failure

from octavia.common import data_models
from octavia.common import exceptions
from octavia.controller.worker.v2.tasks import database_tasks
import octavia.tests.unit.base as base


class TestDatabaseTasksQuota(base.TestCase):

    def setUp(self):

        self._tf_failure_mock = mock.Mock(spec=failure.Failure)
        self.zero_pool_child_count = {'HM': 0, 'member': 0}

        super(TestDatabaseTasksQuota, self).setUp()

    @mock.patch('octavia.db.api.get_session', return_value='TEST')
    @mock.patch('octavia.db.repositories.Repositories.decrement_quota')
    @mock.patch('octavia.db.repositories.Repositories.check_quota_met')
    def _test_decrement_quota(self,
                              task,
                              data_model,
                              mock_check_quota_met,
                              mock_decrement_quota,
                              mock_get_session):

        project_id = uuidutils.generate_uuid()
        test_object = mock.MagicMock()
        test_object.project_id = project_id

        # execute without exception
        mock_decrement_quota.reset_mock()
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_session = mock.MagicMock()
            mock_get_session_local.return_value = mock_session

            if data_model == data_models.Pool:
                task.execute(test_object, self.zero_pool_child_count)
            else:
                task.execute(test_object)

            mock_decrement_quota.assert_called_once_with(
                mock_session, data_model, project_id)

            mock_session.commit.assert_called_once_with()

        # execute with exception
        mock_decrement_quota.reset_mock()
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_session = mock.MagicMock()
            mock_get_session_local.return_value = mock_session

            mock_decrement_quota.side_effect = (
                exceptions.OctaviaException('fail'))
            if data_model == data_models.Pool:
                self.assertRaises(exceptions.OctaviaException,
                                  task.execute,
                                  test_object,
                                  self.zero_pool_child_count)
            else:
                self.assertRaises(exceptions.OctaviaException,
                                  task.execute,
                                  test_object)

            mock_decrement_quota.assert_called_once_with(
                mock_session, data_model, project_id)

            mock_session.rollback.assert_called_once_with()

        # revert with instance of failure
        mock_get_session.reset_mock()
        mock_check_quota_met.reset_mock()
        if data_model == data_models.Pool:
            task.revert(test_object,
                        self.zero_pool_child_count,
                        self._tf_failure_mock)
        else:
            task.revert(test_object, self._tf_failure_mock)
        self.assertFalse(mock_get_session.called)
        self.assertFalse(mock_check_quota_met.called)

        # revert
        mock_check_quota_met.reset_mock()
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_session = mock.MagicMock()
            mock_lock_session = mock.MagicMock()
            mock_get_session_local.side_effect = [mock_session,
                                                  mock_lock_session]

            if data_model == data_models.Pool:
                task.revert(test_object, self.zero_pool_child_count, None)
            else:
                task.revert(test_object, None)

            mock_check_quota_met.assert_called_once_with(
                mock_session, mock_lock_session, data_model,
                project_id)

            mock_lock_session.commit.assert_called_once_with()

        # revert with rollback
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_session = mock.MagicMock()
            mock_lock_session = mock.MagicMock()
            mock_get_session_local.side_effect = [mock_session,
                                                  mock_lock_session]
            mock_check_quota_met.side_effect = (
                exceptions.OctaviaException('fail'))

            if data_model == data_models.Pool:
                task.revert(test_object, self.zero_pool_child_count, None)
            else:
                task.revert(test_object, None)

            mock_lock_session.rollback.assert_called_once_with()

        # revert with db exception
        mock_check_quota_met.reset_mock()
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_get_session_local.side_effect = Exception('fail')

            if data_model == data_models.Pool:
                task.revert(test_object, self.zero_pool_child_count, None)
            else:
                task.revert(test_object, None)

            self.assertFalse(mock_check_quota_met.called)

    def test_decrement_health_monitor_quota(self):
        task = database_tasks.DecrementHealthMonitorQuota()
        data_model = data_models.HealthMonitor
        self._test_decrement_quota(task, data_model)

    def test_decrement_listener_quota(self):
        task = database_tasks.DecrementListenerQuota()
        data_model = data_models.Listener
        self._test_decrement_quota(task, data_model)

    def test_decrement_loadbalancer_quota(self):
        task = database_tasks.DecrementLoadBalancerQuota()
        data_model = data_models.LoadBalancer
        self._test_decrement_quota(task, data_model)

    def test_decrement_pool_quota(self):
        task = database_tasks.DecrementPoolQuota()
        data_model = data_models.Pool
        self._test_decrement_quota(task, data_model)

    def test_decrement_member_quota(self):
        task = database_tasks.DecrementMemberQuota()
        data_model = data_models.Member
        self._test_decrement_quota(task, data_model)

    @mock.patch('octavia.db.repositories.Repositories.decrement_quota')
    @mock.patch('octavia.db.repositories.Repositories.check_quota_met')
    def test_decrement_pool_quota_pool_children(self,
                                                mock_check_quota_met,
                                                mock_decrement_quota):
        pool_child_count = {'HM': 1, 'member': 2}
        project_id = uuidutils.generate_uuid()
        test_object = mock.MagicMock()
        test_object.project_id = project_id
        task = database_tasks.DecrementPoolQuota()
        mock_session = mock.MagicMock()

        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_get_session_local.return_value = mock_session

            task.execute(test_object, pool_child_count)

            calls = [mock.call(mock_session, data_models.Pool, project_id),
                     mock.call(mock_session, data_models.HealthMonitor,
                               project_id),
                     mock.call(mock_session, data_models.Member, project_id,
                               quantity=2)]

            mock_decrement_quota.assert_has_calls(calls)

            mock_session.commit.assert_called_once_with()

        # revert
        mock_session.reset_mock()
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_lock_session = mock.MagicMock()
            mock_get_session_local.side_effect = [mock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session]

            task.revert(test_object, pool_child_count, None)

            calls = [mock.call(mock_session, mock_lock_session,
                               data_models.Pool, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.HealthMonitor, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id)]

            mock_check_quota_met.assert_has_calls(calls)

            self.assertEqual(4, mock_lock_session.commit.call_count)

        # revert with health monitor quota exception
        mock_session.reset_mock()
        mock_check_quota_met.side_effect = [None, Exception('fail'), None,
                                            None]
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_lock_session = mock.MagicMock()
            mock_get_session_local.side_effect = [mock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session]

            task.revert(test_object, pool_child_count, None)

            calls = [mock.call(mock_session, mock_lock_session,
                               data_models.Pool, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.HealthMonitor, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id)]

            mock_check_quota_met.assert_has_calls(calls)

            self.assertEqual(3, mock_lock_session.commit.call_count)
            self.assertEqual(1, mock_lock_session.rollback.call_count)

        # revert with member quota exception
        mock_session.reset_mock()
        mock_check_quota_met.side_effect = [None, None, None,
                                            Exception('fail')]
        with mock.patch('octavia.db.api.'
                        'get_session') as mock_get_session_local:
            mock_lock_session = mock.MagicMock()
            mock_get_session_local.side_effect = [mock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session,
                                                  mock_lock_session]

            task.revert(test_object, pool_child_count, None)

            calls = [mock.call(mock_session, mock_lock_session,
                               data_models.Pool, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.HealthMonitor, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id),
                     mock.call(mock_session, mock_lock_session,
                               data_models.Member, project_id)]

            mock_check_quota_met.assert_has_calls(calls)

            self.assertEqual(3, mock_lock_session.commit.call_count)
            self.assertEqual(1, mock_lock_session.rollback.call_count)

    def test_count_pool_children_for_quota(self):
        project_id = uuidutils.generate_uuid()
        member1 = data_models.Member(id=1, project_id=project_id)
        member2 = data_models.Member(id=2, project_id=project_id)
        healtmon = data_models.HealthMonitor(id=1, project_id=project_id)
        pool_no_children = data_models.Pool(id=1, project_id=project_id)
        pool_1_mem = data_models.Pool(id=1, project_id=project_id,
                                      members=[member1])
        pool_hm = data_models.Pool(id=1, project_id=project_id,
                                   health_monitor=healtmon)
        pool_hm_2_mem = data_models.Pool(id=1, project_id=project_id,
                                         health_monitor=healtmon,
                                         members=[member1, member2])
        task = database_tasks.CountPoolChildrenForQuota()

        # Test pool with no children
        result = task.execute(pool_no_children)

        self.assertEqual({'HM': 0, 'member': 0}, result)

        # Test pool with one member
        result = task.execute(pool_1_mem)

        self.assertEqual({'HM': 0, 'member': 1}, result)

        # Test pool with health monitor and no members
        result = task.execute(pool_hm)

        self.assertEqual({'HM': 1, 'member': 0}, result)

        # Test pool with health monitor and two members
        result = task.execute(pool_hm_2_mem)

        self.assertEqual({'HM': 1, 'member': 2}, result)
