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

import threading

import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_db import exception as db_exc
from oslo_utils import uuidutils

from octavia.controller.healthmanager import health_manager as healthmanager
import octavia.tests.unit.base as base


CONF = cfg.CONF

AMPHORA_ID = uuidutils.generate_uuid()


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class TestHealthManager(base.TestCase):

    def setUp(self):
        super(TestHealthManager, self).setUp()

    @mock.patch('octavia.db.api.wait_for_connection')
    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora')
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_stale_amphora(self, session_mock, get_stale_amp_mock,
                                        failover_mock, db_wait_mock):
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="health_manager", heartbeat_timeout=5)
        amphora_health = mock.MagicMock()
        amphora_health.amphora_id = AMPHORA_ID

        get_stale_amp_mock.side_effect = [amphora_health, None]

        exit_event = threading.Event()
        hm = healthmanager.HealthManager(exit_event)

        hm.health_check()

        # Test DBDeadlock and RetryRequest exceptions
        session_mock.reset_mock()
        get_stale_amp_mock.reset_mock()
        mock_session = mock.MagicMock()
        session_mock.return_value = mock_session
        get_stale_amp_mock.side_effect = [
            db_exc.DBDeadlock,
            db_exc.RetryRequest(Exception('retry_test')),
            db_exc.DBConnectionError,
            TestException('test')]
        # Test that a DBDeadlock does not raise an exception
        self.assertIsNone(hm.health_check())
        # Test that a RetryRequest does not raise an exception
        self.assertIsNone(hm.health_check())
        # Test that a DBConnectionError does not raise an exception
        self.assertIsNone(hm.health_check())
        # ... and that it waits for DB reconnection
        db_wait_mock.assert_called_once()
        # Other exceptions should raise
        self.assertRaises(TestException, hm.health_check)
        self.assertEqual(4, mock_session.rollback.call_count)

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora', return_value=None)
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_nonstale_amphora(self, session_mock,
                                           get_stale_amp_mock, failover_mock):
        get_stale_amp_mock.side_effect = [None, TestException('test')]

        exit_event = threading.Event()
        hm = healthmanager.HealthManager(exit_event)

        hm.health_check()
        session_mock.assert_called_once_with(autocommit=False)
        self.assertFalse(failover_mock.called)

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora', return_value=None)
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_exit(self, session_mock, get_stale_amp_mock,
                               failover_mock):
        get_stale_amp_mock.return_value = None

        exit_event = threading.Event()
        hm = healthmanager.HealthManager(exit_event)
        hm.health_check()

        session_mock.assert_called_once_with(autocommit=False)
        self.assertFalse(failover_mock.called)

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.failover_amphora')
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.'
                'get_stale_amphora', return_value=None)
    @mock.patch('octavia.db.api.get_session')
    def test_health_check_db_error(self, session_mock, get_stale_amp_mock,
                                   failover_mock):
        get_stale_amp_mock.return_value = None

        mock_session = mock.MagicMock()
        session_mock.return_value = mock_session
        session_mock.side_effect = TestException('DB Error')
        exit_event = threading.Event()
        hm = healthmanager.HealthManager(exit_event)

        self.assertRaises(TestException, hm.health_check)
        self.assertEqual(0, mock_session.rollback.call_count)
