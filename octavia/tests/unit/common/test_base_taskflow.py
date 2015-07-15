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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import six
from taskflow import engines as tf_engines

from octavia.common import base_taskflow
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

MAX_WORKERS = 1

_engine_mock = mock.MagicMock()


class TestBaseTaskFlowEngine(base.TestCase):

    def setUp(self):

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="task_flow", max_workers=MAX_WORKERS)
        conf.config(group="task_flow", engine='TESTENGINE')
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
            engine_conf='TESTENGINE',
            executor='TESTEXECUTOR')

        _engine_mock.compile.assert_called_once_with()
        _engine_mock.prepare.assert_called_once_with()
