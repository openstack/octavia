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
import concurrent.futures
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from taskflow import engines as tf_engines

from octavia.common import base_taskflow
import octavia.tests.unit.base as base


MAX_WORKERS = 1
ENGINE = 'parallel'

_engine_mock = mock.MagicMock()


class TestBaseTaskFlowEngine(base.TestCase):

    def setUp(self):

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="task_flow", max_workers=MAX_WORKERS)
        conf.config(group="task_flow", engine=ENGINE)
        conf.config(group="task_flow", disable_revert=True)
        super(TestBaseTaskFlowEngine, self).setUp()

    @mock.patch('concurrent.futures.ThreadPoolExecutor',
                return_value='TESTEXECUTOR')
    @mock.patch('taskflow.engines.load',
                return_value=_engine_mock)
    def test_taskflow_load(self,
                           mock_tf_engine_load,
                           mock_ThreadPoolExecutor):

        # Test __init__

        base_taskflow_engine = base_taskflow.BaseTaskFlowEngine()

        concurrent.futures.ThreadPoolExecutor.assert_called_once_with(
            max_workers=MAX_WORKERS)

        # Test _taskflow_load

        base_taskflow_engine._taskflow_load('TEST')

        tf_engines.load.assert_called_once_with(
            'TEST',
            engine=ENGINE,
            executor='TESTEXECUTOR',
            never_resolve=True)

        _engine_mock.compile.assert_called_once_with()
        _engine_mock.prepare.assert_called_once_with()


class TestTaskFlowServiceController(base.TestCase):

    _mock_uuid = '9a2ebc48-cd3e-429e-aa04-e32f5fc5442a'

    def setUp(self):
        self.conf = oslo_fixture.Config(cfg.CONF)
        self.conf.config(group="task_flow", engine='parallel')
        self.driver_mock = mock.MagicMock()
        self.persistence_mock = mock.MagicMock()
        self.jobboard_mock = mock.MagicMock()
        self.driver_mock.job_board.return_value = self.jobboard_mock
        self.driver_mock.persistence_driver.get_persistence.return_value = (
            self.persistence_mock)
        self.service_controller = base_taskflow.TaskFlowServiceController(
            self.driver_mock)
        super(TestTaskFlowServiceController, self).setUp()

    @mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=_mock_uuid)
    @mock.patch('taskflow.engines.save_factory_details')
    def test_run_poster(self, mock_engines, mockuuid):
        flow_factory = mock.MagicMock()
        flow_factory.__name__ = 'testname'
        job_name = 'testname-%s' % self._mock_uuid
        job_details = {'store': 'test'}
        with mock.patch.object(self.service_controller, '_wait_for_job'
                               ) as wait:
            uuid = self.service_controller.run_poster(flow_factory,
                                                      **job_details)
            save_logbook = self.persistence_mock.__enter__().get_connection(
            ).save_logbook
            save_logbook.assert_called()
            self.assertEqual(job_name, save_logbook.call_args[0][0].name)

            mock_engines.assert_called()
            save_args = mock_engines.call_args
            self.assertEqual(job_name, save_args[0][0].name)
            self.assertEqual(self._mock_uuid, save_args[0][0].uuid)
            self.assertEqual(flow_factory, save_args[0][1])
            self.assertEqual(self.persistence_mock.__enter__(),
                             save_args[1]['backend'])

            self.jobboard_mock.__enter__().post.assert_called()
            post_args = self.jobboard_mock.__enter__().post.call_args
            self.assertEqual(job_name, post_args[0][0])
            self.assertEqual(job_details, post_args[1]['details'])
            wait.assert_not_called()
            self.assertEqual(self._mock_uuid, uuid)

    @mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=_mock_uuid)
    @mock.patch('taskflow.engines.save_factory_details')
    def test_run_poster_wait(self, mock_engines, mockuuid):
        flow_factory = mock.MagicMock()
        flow_factory.__name__ = 'testname'
        job_details = {'store': 'test'}
        with mock.patch.object(self.service_controller, '_wait_for_job'
                               ) as wait:
            uuid = self.service_controller.run_poster(flow_factory, wait=True,
                                                      **job_details)
            self.persistence_mock.__enter__().get_connection(
            ).save_logbook.assert_called()
            mock_engines.assert_called()
            self.jobboard_mock.__enter__().post.assert_called()
            wait.assert_called_once_with(self.jobboard_mock.__enter__())
            self.assertEqual(self._mock_uuid, uuid)

    @mock.patch('octavia.common.base_taskflow.RedisDynamicLoggingConductor')
    @mock.patch('octavia.common.base_taskflow.DynamicLoggingConductor')
    def test_run_conductor(self, dynamiccond, rediscond):
        self.service_controller.run_conductor("test")
        rediscond.assert_called_once_with(
            "test", self.jobboard_mock.__enter__(),
            persistence=self.persistence_mock.__enter__(),
            engine='parallel')
        self.conf.config(group="task_flow",
                         jobboard_backend_driver='zookeeper_taskflow_driver')

        self.service_controller.run_conductor("test2")
        dynamiccond.assert_called_once_with(
            "test2", self.jobboard_mock.__enter__(),
            persistence=self.persistence_mock.__enter__(),
            engine='parallel')
