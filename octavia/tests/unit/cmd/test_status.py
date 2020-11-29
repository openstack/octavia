# Copyright (c) 2018 NEC, Corp.
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

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_upgradecheck.upgradecheck import Code

from octavia.cmd import status
from octavia.common import constants
from octavia.common import policy
from octavia.tests.unit import base


class TestUpgradeChecks(base.TestCase):

    def setUp(self):
        super().setUp()
        self.cmd = status.Checks()

    def test__check_amphorav2_not_enabled(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings',
                         default_provider_driver=constants.AMPHORA,
                         enabled_provider_drivers={constants.AMPHORA: "Test"})
        check_result = self.cmd._check_amphorav2()
        self.assertEqual(
            Code.SUCCESS, check_result.code)

    def test__check_persistence_sqlite(self):
        check_result = self.cmd._check_persistence()
        self.assertEqual(
            Code.WARNING, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'MysqlPersistenceDriver')
    def test__check_persistence_error(self, mysql_driver):
        mysql_driver().get_persistence.side_effect = Exception
        check_result = self.cmd._check_persistence()
        self.assertEqual(
            Code.FAILURE, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'MysqlPersistenceDriver')
    def test__check_persistence(self, mysql_driver):
        pers_mock = mock.MagicMock()
        mysql_driver().get_persistence().__enter__.return_value = pers_mock
        check_result = self.cmd._check_persistence()
        self.assertEqual(pers_mock, check_result)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    def test__check_jobboard_error(self, redis_driver):
        pers_mock = mock.MagicMock()
        redis_driver().job_board.side_effect = Exception
        check_result = self.cmd._check_jobboard(pers_mock)
        self.assertEqual(Code.FAILURE, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    def test__check_jobboard_not_connected(self, redis_driver):
        jb_connected = mock.Mock(connected=False)
        redis_driver().job_board().__enter__.return_value = jb_connected
        check_result = self.cmd._check_jobboard(mock.MagicMock())
        self.assertEqual(Code.FAILURE, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    def test__check_jobboard(self, redis_driver):
        jb_connected = mock.Mock(connected=True)
        redis_driver().job_board().__enter__.return_value = jb_connected
        check_result = self.cmd._check_jobboard(mock.MagicMock())
        self.assertEqual(Code.SUCCESS, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'MysqlPersistenceDriver')
    def test__check_amphorav2_success(self, mysql_driver, redis_driver):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings',
                         default_provider_driver=constants.AMPHORA,
                         enabled_provider_drivers={constants.AMPHORAV2:
                                                   "Test"})
        jb_connected = mock.Mock(connected=True)
        redis_driver().job_board().__enter__.return_value = jb_connected
        check_result = self.cmd._check_amphorav2()
        self.assertEqual(
            Code.SUCCESS, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    def test__check_amphorav2_warning(self, redis_driver):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings',
                         default_provider_driver=constants.AMPHORA,
                         enabled_provider_drivers={constants.AMPHORAV2:
                                                   "Test"})
        check_result = self.cmd._check_amphorav2()
        self.assertEqual(
            Code.WARNING, check_result.code)

    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'RedisTaskFlowDriver')
    @mock.patch('octavia.controller.worker.v2.taskflow_jobboard_driver.'
                'MysqlPersistenceDriver')
    def test__check_amphorav2_failure(self, mysql_driver, redis_driver):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings',
                         default_provider_driver=constants.AMPHORAV2,
                         enabled_provider_drivers={constants.AMPHORA: "Test"})
        jb_connected = mock.Mock(connected=False)
        redis_driver().job_board().__enter__.return_value = jb_connected
        check_result = self.cmd._check_amphorav2()
        self.assertEqual(
            Code.FAILURE, check_result.code)

    def test__check_yaml_policy(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.conf(args=[], project='octavia')
        policy.Policy()

        self.conf.config(group='oslo_policy', policy_file='test.yaml')
        check_result = self.cmd._check_yaml_policy()
        self.assertEqual(Code.SUCCESS, check_result.code)

        self.conf.config(group='oslo_policy', policy_file='test.json')
        check_result = self.cmd._check_yaml_policy()
        self.assertEqual(Code.WARNING, check_result.code)

        self.conf.config(group='oslo_policy', policy_file='test')
        check_result = self.cmd._check_yaml_policy()
        self.assertEqual(Code.FAILURE, check_result.code)
