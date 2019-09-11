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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

import octavia.api.drivers.driver_agent.driver_listener
from octavia.cmd import driver_agent
from octavia.tests.unit import base

CONF = cfg.CONF


class TestDriverAgentCMD(base.TestCase):

    def setUp(self):
        super(TestDriverAgentCMD, self).setUp()
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))

    @mock.patch('os.kill')
    @mock.patch('octavia.cmd.driver_agent.CONF')
    def test_handle_mutate_config(self, mock_conf, mock_os_kill):
        driver_agent._handle_mutate_config(1, 2)
        mock_conf.mutate_config_files.assert_called_once()
        os_calls = [mock.call(1, signal.SIGHUP), mock.call(2, signal.SIGHUP)]
        mock_os_kill.assert_has_calls(os_calls, any_order=True)

    def test_check_if_provider_agent_enabled(self):
        mock_extension = mock.MagicMock()
        self.CONF.config(group="driver_agent",
                         enabled_provider_agents=[
                             'spiffy_agent', 'super_agent'])
        mock_extension.name = 'super_agent'
        self.assertTrue(
            driver_agent._check_if_provider_agent_enabled(mock_extension))
        mock_extension.name = 'bogus_agent'
        self.assertFalse(
            driver_agent._check_if_provider_agent_enabled(mock_extension))

    @mock.patch('setproctitle.setproctitle')
    @mock.patch('signal.signal')
    def test_process_wrapper(self, mock_signal, mock_setproctitle):
        mock_exit_event = mock.MagicMock()
        mock_function = mock.MagicMock()
        mock_function.side_effect = [
            mock.DEFAULT, Exception('boom'), mock.DEFAULT, Exception('boom'),
            mock.DEFAULT]
        mock_exit_event.is_set.side_effect = [False, False, True,
                                              False, False, True]

        signal_calls = [mock.call(signal.SIGINT, signal.SIG_IGN),
                        mock.call(signal.SIGHUP, driver_agent._mutate_config)]
        # With agent_name
        driver_agent._process_wrapper(
            mock_exit_event, 'test_proc_name', mock_function,
            agent_name='test_agent_name')
        mock_signal.assert_has_calls(signal_calls)
        mock_setproctitle.assert_called_once_with(
            'octavia-driver-agent - test_proc_name -- test_agent_name')
        mock_function.assert_called_once_with(mock_exit_event)

        # With agent_name - With function exception
        mock_signal.reset_mock()
        mock_setproctitle.reset_mock()
        mock_function.reset_mock()
        driver_agent._process_wrapper(
            mock_exit_event, 'test_proc_name', mock_function,
            agent_name='test_agent_name')
        mock_signal.assert_has_calls(signal_calls)
        mock_setproctitle.assert_called_once_with(
            'octavia-driver-agent - test_proc_name -- test_agent_name')
        mock_function.assert_called_once_with(mock_exit_event)

        # Without agent_name
        mock_signal.reset_mock()
        mock_setproctitle.reset_mock()
        mock_function.reset_mock()
        driver_agent._process_wrapper(
            mock_exit_event, 'test_proc_name', mock_function)
        mock_signal.assert_has_calls(signal_calls)
        mock_setproctitle.assert_called_once_with(
            'octavia-driver-agent - test_proc_name')
        mock_function.assert_called_once_with(mock_exit_event)

        # Without agent_name - With function exception
        mock_signal.reset_mock()
        mock_setproctitle.reset_mock()
        mock_function.reset_mock()
        driver_agent._process_wrapper(
            mock_exit_event, 'test_proc_name', mock_function)
        mock_signal.assert_has_calls(signal_calls)
        mock_setproctitle.assert_called_once_with(
            'octavia-driver-agent - test_proc_name')
        mock_function.assert_called_once_with(mock_exit_event)

    @mock.patch('octavia.cmd.driver_agent.multiprocessing')
    @mock.patch('stevedore.enabled.EnabledExtensionManager')
    def test_start_provider_agents(self, mock_stevedore, mock_multiprocessing):
        mock_extension = mock.MagicMock()
        mock_extension.name = 'test_extension'
        mock_exit_event = mock.MagicMock()
        mock_stevedore.return_value = [mock_extension]
        mock_ext_proc = mock.MagicMock()
        mock_multiprocessing.Process.return_value = mock_ext_proc

        driver_agent._start_provider_agents(mock_exit_event)

        mock_stevedore.assert_called_once_with(
            namespace='octavia.driver_agent.provider_agents',
            check_func=driver_agent._check_if_provider_agent_enabled)
        mock_multiprocessing.Process.assert_called_once_with(
            name='test_extension', target=driver_agent._process_wrapper,
            args=(mock_exit_event, 'provider_agent', mock_extension.plugin),
            kwargs={'agent_name': 'test_extension'})
        mock_ext_proc.start.assert_called_once_with()

    @mock.patch('os.kill')
    @mock.patch('octavia.cmd.driver_agent.multiprocessing')
    @mock.patch('oslo_reports.guru_meditation_report.TextGuruMeditation.'
                'setup_autorun')
    @mock.patch('octavia.common.service.prepare_service')
    def test_main(self, mock_prep_srvc, mock_gmr, mock_multiprocessing,
                  mock_kill):
        mock_exit_event = mock.MagicMock()
        mock_multiprocessing.Event.return_value = mock_exit_event
        mock_status_listener_proc = mock.MagicMock()
        mock_stats_listener_proc = mock.MagicMock()
        mock_get_listener_proc = mock.MagicMock()
        mock_multiprocessing.Process.side_effect = [
            mock_status_listener_proc, mock_stats_listener_proc,
            mock_get_listener_proc,
            mock_status_listener_proc, mock_stats_listener_proc,
            mock_get_listener_proc,
            mock_status_listener_proc, mock_stats_listener_proc,
            mock_get_listener_proc,
            mock_status_listener_proc, mock_stats_listener_proc,
            mock_get_listener_proc,
            mock_status_listener_proc, mock_stats_listener_proc,
            mock_get_listener_proc]
        driver_agent.main()
        mock_prep_srvc.assert_called_once()
        mock_gmr.assert_called_once()
        mock_status_listener_proc.start.assert_called_once()
        mock_stats_listener_proc.start.assert_called_once()
        mock_get_listener_proc.start.assert_called_once()
        process_calls = [mock.call(
            args=mock_exit_event, name='status_listener',
            target=(octavia.api.drivers.driver_agent.driver_listener.
                    status_listener)),
            mock.call(
                args=mock_exit_event, name='stats_listener',
                target=(octavia.api.drivers.driver_agent.driver_listener.
                        stats_listener)),
            mock.call(
                args=mock_exit_event, name='get_listener',
                target=(octavia.api.drivers.driver_agent.driver_listener.
                        get_listener))]
        mock_multiprocessing.Process.has_calls(process_calls, any_order=True)

        # Test keyboard interrupt path
        mock_stats_listener_proc.join.side_effect = [KeyboardInterrupt, None]
        driver_agent.main()
        mock_exit_event.set.assert_called_once()

        # Test keyboard interrupt with provider agents
        mock_exit_event.reset_mock()
        mock_stats_listener_proc.join.side_effect = [KeyboardInterrupt, None]
        mock_provider_proc = mock.MagicMock()
        mock_provider_proc.pid = 'not-valid-pid'
        mock_provider_proc.exitcode = 1
        driver_agent.PROVIDER_AGENT_PROCESSES = [mock_provider_proc]
        driver_agent.main()
        mock_exit_event.set.assert_called_once()
        mock_provider_proc.join.assert_called_once_with(
            CONF.driver_agent.provider_agent_shutdown_timeout)

        # Test keyboard interrupt with provider agents fails to stop
        mock_exit_event.reset_mock()
        mock_stats_listener_proc.join.side_effect = [KeyboardInterrupt, None]
        mock_provider_proc = mock.MagicMock()
        mock_provider_proc.pid = 'not-valid-pid'
        mock_provider_proc.exitcode = None
        driver_agent.PROVIDER_AGENT_PROCESSES = [mock_provider_proc]
        driver_agent.main()
        mock_exit_event.set.assert_called_once()
        mock_provider_proc.join.assert_called_once_with(
            CONF.driver_agent.provider_agent_shutdown_timeout)
        mock_kill.assert_called_once_with('not-valid-pid', signal.SIGKILL)

        # Test keyboard interrupt with provider agents join exception
        mock_exit_event.reset_mock()
        mock_stats_listener_proc.join.side_effect = [KeyboardInterrupt, None]
        mock_provider_proc = mock.MagicMock()
        mock_provider_proc.pid = 'not-valid-pid'
        mock_provider_proc.join.side_effect = Exception('boom')
        driver_agent.PROVIDER_AGENT_PROCESSES = [mock_provider_proc]
        driver_agent.main()
        mock_exit_event.set.assert_called_once()
        mock_provider_proc.join.assert_called_once_with(
            CONF.driver_agent.provider_agent_shutdown_timeout)
