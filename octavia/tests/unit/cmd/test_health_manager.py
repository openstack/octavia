#    Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import signal

import mock

from octavia.cmd import health_manager
from octavia.tests.unit import base


class TestHealthManagerCMD(base.TestCase):

    def setUp(self):
        super(TestHealthManagerCMD, self).setUp()

    @mock.patch('multiprocessing.Event')
    @mock.patch('octavia.amphorae.drivers.health.'
                'heartbeat_udp.UDPStatusGetter')
    def test_hm_listener(self, mock_getter,
                         mock_event):
        mock_event.is_set.side_effect = [False, False, True]
        getter_mock = mock.MagicMock()
        check_mock = mock.MagicMock()
        getter_mock.check = check_mock
        getter_mock.check.side_effect = [None, Exception('break')]
        mock_getter.return_value = getter_mock
        health_manager.hm_listener(mock_event)
        mock_getter.assert_called_once()
        self.assertEqual(2, getter_mock.check.call_count)

    @mock.patch('multiprocessing.Event')
    @mock.patch('futurist.periodics.PeriodicWorker.start')
    @mock.patch('futurist.periodics.PeriodicWorker.__init__')
    @mock.patch('signal.signal')
    @mock.patch('octavia.controller.healthmanager.'
                'health_manager.HealthManager')
    def test_hm_health_check(self, mock_health, mock_signal, mock_worker,
                             mock_start, mock_event):
        mock_event.is_set.side_effect = [False, True]
        hm_mock = mock.MagicMock()
        mock_worker.return_value = None
        health_check_mock = mock.MagicMock()
        hm_mock.health_check = health_check_mock
        mock_health.return_value = hm_mock
        health_manager.hm_health_check(mock_event)
        mock_health.assert_called_once_with(mock_event)

    @mock.patch('multiprocessing.Process')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main(self, mock_service, mock_process):
        mock_listener_proc = mock.MagicMock()
        mock_health_proc = mock.MagicMock()

        mock_process.side_effect = [mock_listener_proc, mock_health_proc]

        health_manager.main()

        mock_listener_proc.start.assert_called_once_with()
        mock_health_proc.start.assert_called_once_with()
        mock_listener_proc.join.assert_called_once_with()
        mock_health_proc.join.assert_called_once_with()

    @mock.patch('os.kill')
    @mock.patch('multiprocessing.Process')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main_keyboard_interrupt(self, mock_service, mock_process,
                                     mock_kill):
        mock_listener_proc = mock.MagicMock()
        mock_health_proc = mock.MagicMock()
        mock_join = mock.MagicMock()
        mock_join.side_effect = [KeyboardInterrupt, None]
        mock_listener_proc.join = mock_join

        mock_process.side_effect = [mock_listener_proc, mock_health_proc]

        health_manager.main()

        mock_listener_proc.start.assert_called_once_with()
        mock_health_proc.start.assert_called_once_with()
        self.assertEqual(2, mock_listener_proc.join.call_count)
        mock_health_proc.join.assert_called_once_with()
        mock_kill.assert_called_once_with(mock_health_proc.pid,
                                          signal.SIGINT)

    @mock.patch('os.kill')
    @mock.patch('oslo_config.cfg.CONF.mutate_config_files')
    def test_handle_mutate_config(self, mock_mutate, mock_kill):
        health_manager._handle_mutate_config(1, 2)

        mock_mutate.assert_called_once()

        calls = [mock.call(1, signal.SIGHUP), mock.call(2, signal.SIGHUP)]
        mock_kill.assert_has_calls(calls)
