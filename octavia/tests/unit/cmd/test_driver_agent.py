# Copyright 2018 Rackspace, US Inc.
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

import signal

import mock

import octavia.api.drivers.driver_agent.driver_listener
from octavia.cmd import driver_agent
from octavia.tests.unit import base


class TestDriverAgentCMD(base.TestCase):

    def setUp(self):
        super(TestDriverAgentCMD, self).setUp()

    @mock.patch('os.kill')
    @mock.patch('octavia.cmd.driver_agent.CONF')
    def test_handle_mutate_config(self, mock_conf, mock_os_kill):
        driver_agent._handle_mutate_config(1, 2)
        mock_conf.mutate_config_files.assert_called_once()
        os_calls = [mock.call(1, signal.SIGHUP), mock.call(2, signal.SIGHUP)]
        mock_os_kill.assert_has_calls(os_calls, any_order=True)

    @mock.patch('signal.signal')
    @mock.patch('octavia.cmd.driver_agent.multiprocessing')
    @mock.patch('oslo_reports.guru_meditation_report.TextGuruMeditation.'
                'setup_autorun')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main(self, mock_prep_srvc, mock_gmr, mock_multiprocessing,
                  mock_signal):
        mock_exit_event = mock.MagicMock()
        mock_multiprocessing.Event.return_value = mock_exit_event
        mock_status_listener_proc = mock.MagicMock()
        mock_stats_listener_proc = mock.MagicMock()
        mock_multiprocessing.Process.side_effect = [mock_status_listener_proc,
                                                    mock_stats_listener_proc,
                                                    mock_status_listener_proc,
                                                    mock_stats_listener_proc]
        driver_agent.main()
        mock_prep_srvc.assert_called_once()
        mock_gmr.assert_called_once()
        mock_status_listener_proc.start.assert_called_once()
        mock_stats_listener_proc.start.assert_called_once()
        process_calls = [mock.call(
            args=mock_exit_event, name='status_listener',
            target=(octavia.api.drivers.driver_agent.driver_listener.
                    status_listener)),
            mock.call(
                args=mock_exit_event, name='stats_listener',
                target=(octavia.api.drivers.driver_agent.driver_listener.
                        stats_listener))]
        mock_multiprocessing.Process.has_calls(process_calls, any_order=True)

        # Test keyboard interrupt path
        mock_stats_listener_proc.join.side_effect = [KeyboardInterrupt, None]
        driver_agent.main()
        mock_exit_event.set.assert_called_once()
