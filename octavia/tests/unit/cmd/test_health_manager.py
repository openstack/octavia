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

import six

from octavia.cmd import health_manager
from octavia.tests.unit import base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestHealthManagerCMD(base.TestCase):

    def setUp(self):
        super(TestHealthManagerCMD, self).setUp()

    @mock.patch('octavia.controller.healthmanager.'
                'update_stats_mixin.UpdateStatsMixin')
    @mock.patch('octavia.controller.healthmanager.'
                'update_health_mixin.UpdateHealthMixin')
    @mock.patch('octavia.amphorae.drivers.health.'
                'heartbeat_udp.UDPStatusGetter')
    def test_hm_listener(self, mock_getter, mock_health, mock_stats):
        getter_mock = mock.MagicMock()
        check_mock = mock.MagicMock()
        getter_mock.check = check_mock
        getter_mock.check.side_effect = [None, Exception('break')]
        mock_getter.return_value = getter_mock
        self.assertRaisesRegexp(Exception, 'break',
                                health_manager.hm_listener)
        mock_getter.assert_called_once_with(mock_health(), mock_stats())
        self.assertEqual(getter_mock.check.call_count, 2)

    @mock.patch('octavia.controller.healthmanager.'
                'health_manager.HealthManager')
    def test_hm_health_check(self, mock_health):
        hm_mock = mock.MagicMock()
        health_check_mock = mock.MagicMock()
        hm_mock.health_check = health_check_mock
        hm_mock.health_check.side_effect = [None, Exception('break')]
        mock_health.return_value = hm_mock
        self.assertRaisesRegexp(Exception, 'break',
                                health_manager.hm_health_check)
        mock_health.assert_called_once_with()
        self.assertEqual(hm_mock.health_check.call_count, 2)

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

    @mock.patch('multiprocessing.Process')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main_keyboard_interrupt(self, mock_service, mock_process):
        mock_listener_proc = mock.MagicMock()
        mock_health_proc = mock.MagicMock()
        mock_join = mock.MagicMock()
        mock_join.side_effect = KeyboardInterrupt
        mock_listener_proc.join = mock_join

        mock_process.side_effect = [mock_listener_proc, mock_health_proc]

        health_manager.main()

        mock_listener_proc.start.assert_called_once_with()
        mock_health_proc.start.assert_called_once_with()
        mock_listener_proc.join.assert_called_once_with()
        self.assertFalse(mock_health_proc.join.called)
