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
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import subprocess
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import loadbalancer
from octavia.amphorae.backends.agent.api_server import util as agent_util
from octavia.common import constants as consts
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base

CONF = cfg.CONF
LISTENER_ID1 = uuidutils.generate_uuid()
LB_ID1 = uuidutils.generate_uuid()


class ListenerTestCase(base.TestCase):
    def setUp(self):
        super().setUp()
        self.mock_platform = mock.patch("distro.id").start()
        self.mock_platform.return_value = "ubuntu"
        self.test_loadbalancer = loadbalancer.Loadbalancer()

    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server' +
                '.util.get_haproxy_pid')
    def test_check_haproxy_status(self, mock_pid, mock_exists):
        mock_pid.return_value = '1245'
        mock_exists.side_effect = [True, True]
        self.assertEqual(
            consts.ACTIVE,
            self.test_loadbalancer._check_haproxy_status(LISTENER_ID1))

        mock_exists.side_effect = [True, False]
        self.assertEqual(
            consts.OFFLINE,
            self.test_loadbalancer._check_haproxy_status(LISTENER_ID1))

        mock_exists.side_effect = [False]
        self.assertEqual(
            consts.OFFLINE,
            self.test_loadbalancer._check_haproxy_status(LISTENER_ID1))

    @mock.patch('time.sleep')
    @mock.patch('octavia.amphorae.backends.agent.api_server.loadbalancer.LOG')
    @mock.patch('octavia.amphorae.backends.agent.api_server.loadbalancer.'
                'Loadbalancer._check_haproxy_status')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'vrrp_check_script_update')
    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server.loadbalancer.'
                'Loadbalancer._check_lb_exists')
    @mock.patch('subprocess.check_output')
    @mock.patch('octavia.amphorae.backends.utils.haproxy_query.HAProxyQuery')
    def test_start_stop_lb(self, mock_haproxy_query, mock_check_output,
                           mock_lb_exists, mock_path_exists, mock_vrrp_update,
                           mock_check_status, mock_LOG, mock_time_sleep):
        listener_id = uuidutils.generate_uuid()

        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        mock_path_exists.side_effect = [False, True, True, False, False]
        mock_check_status.side_effect = ['bogus', consts.OFFLINE]

        # Happy path - No VRRP
        cmd = "systemctl {action} haproxy-{listener_id}.service".format(
            action=consts.AMP_ACTION_START, listener_id=listener_id)

        result = self.test_loadbalancer.start_stop_lb(
            listener_id, consts.AMP_ACTION_START)

        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT,
                                                  encoding='utf-8')
        mock_lb_exists.assert_called_once_with(listener_id)
        mock_vrrp_update.assert_not_called()
        self.assertEqual(202, result.status_code)
        self.assertEqual('OK', result.json['message'])
        ref_details = ('Configuration file is valid\n'
                       'haproxy daemon for {} started'.format(listener_id))
        self.assertEqual(ref_details, result.json['details'])

        # Happy path - VRRP - RELOAD
        conf.config(group="controller_worker",
                    loadbalancer_topology=consts.TOPOLOGY_ACTIVE_STANDBY)

        mock_lb_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_output.reset_mock()

        cmd = "systemctl {action} haproxy-{listener_id}.service".format(
            action=consts.AMP_ACTION_RELOAD, listener_id=listener_id)

        result = self.test_loadbalancer.start_stop_lb(
            listener_id, consts.AMP_ACTION_RELOAD)

        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT,
                                                  encoding='utf-8')
        mock_lb_exists.assert_called_once_with(listener_id)
        mock_vrrp_update.assert_called_once_with(listener_id,
                                                 consts.AMP_ACTION_RELOAD)
        self.assertEqual(202, result.status_code)
        self.assertEqual('OK', result.json['message'])
        ref_details = f'Listener {listener_id} {consts.AMP_ACTION_RELOAD}ed'
        self.assertEqual(ref_details, result.json['details'])

        # Happy path - VRRP - RELOAD - OFFLINE
        mock_lb_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_output.reset_mock()

        cmd = "systemctl {action} haproxy-{listener_id}.service".format(
            action=consts.AMP_ACTION_START, listener_id=listener_id)

        result = self.test_loadbalancer.start_stop_lb(
            listener_id, consts.AMP_ACTION_RELOAD)

        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT,
                                                  encoding='utf-8')
        mock_lb_exists.assert_called_once_with(listener_id)
        mock_vrrp_update.assert_called_once_with(listener_id,
                                                 consts.AMP_ACTION_RELOAD)
        self.assertEqual(202, result.status_code)
        self.assertEqual('OK', result.json['message'])
        ref_details = ('Configuration file is valid\n'
                       'haproxy daemon for {} started'.format(listener_id))
        self.assertEqual(ref_details, result.json['details'])

        # Unhappy path - Not already running
        conf.config(group="controller_worker",
                    loadbalancer_topology=consts.TOPOLOGY_SINGLE)

        mock_lb_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_output.reset_mock()

        cmd = "systemctl {action} haproxy-{listener_id}.service".format(
            action=consts.AMP_ACTION_START, listener_id=listener_id)

        mock_check_output.side_effect = subprocess.CalledProcessError(
            output='bogus', returncode=-2, cmd='sit')

        result = self.test_loadbalancer.start_stop_lb(
            listener_id, consts.AMP_ACTION_START)

        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT,
                                                  encoding='utf-8')
        mock_lb_exists.assert_called_once_with(listener_id)
        mock_vrrp_update.assert_not_called()
        self.assertEqual(500, result.status_code)
        self.assertEqual(f'Error {consts.AMP_ACTION_START}ing haproxy',
                         result.json['message'])
        self.assertEqual('bogus', result.json['details'])

        # Unhappy path - Already running
        mock_lb_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_output.reset_mock()

        cmd = "systemctl {action} haproxy-{listener_id}.service".format(
            action=consts.AMP_ACTION_START, listener_id=listener_id)

        mock_check_output.side_effect = subprocess.CalledProcessError(
            output='Job is already running', returncode=-2, cmd='sit')

        result = self.test_loadbalancer.start_stop_lb(
            listener_id, consts.AMP_ACTION_START)

        mock_check_output.assert_called_once_with(cmd.split(),
                                                  stderr=subprocess.STDOUT,
                                                  encoding='utf-8')
        mock_lb_exists.assert_called_once_with(listener_id)
        mock_vrrp_update.assert_not_called()
        self.assertEqual(202, result.status_code)
        self.assertEqual('OK', result.json['message'])
        ref_details = ('Configuration file is valid\n'
                       'haproxy daemon for {} started'.format(listener_id))
        self.assertEqual(ref_details, result.json['details'])

        # Invalid action
        mock_check_output.reset_mock()
        mock_lb_exists.reset_mock()
        mock_path_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        result = self.test_loadbalancer.start_stop_lb(listener_id, 'bogus')
        self.assertEqual(400, result.status_code)
        self.assertEqual('Invalid Request', result.json['message'])
        self.assertEqual('Unknown action: bogus', result.json['details'])
        mock_lb_exists.assert_not_called()
        mock_path_exists.assert_not_called()
        mock_vrrp_update.assert_not_called()
        mock_check_output.assert_not_called()

        # haproxy error on reload
        mock_check_output.reset_mock()
        mock_lb_exists.reset_mock()
        mock_path_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_status.reset_mock()
        mock_LOG.reset_mock()

        mock_check_output.side_effect = [
            subprocess.CalledProcessError(
                output='haproxy.service is not active, cannot reload.',
                returncode=-2, cmd='service'),
            None]
        mock_check_status.return_value = 'ACTIVE'
        mock_check_status.side_effect = None

        mock_query = mock.Mock()
        mock_haproxy_query.return_value = mock_query
        mock_query.show_info.side_effect = [Exception("error"),
                                            {'Uptime_sec': 5}]

        result = self.test_loadbalancer.start_stop_lb(listener_id, 'reload')
        self.assertEqual(202, result.status_code)

        LOG_last_call = mock_LOG.mock_calls[-1]
        self.assertIn('An error occured with haproxy', LOG_last_call[1][0])

        # haproxy error on reload - retry limit
        print("--")
        mock_check_output.reset_mock()
        mock_lb_exists.reset_mock()
        mock_path_exists.reset_mock()
        mock_vrrp_update.reset_mock()
        mock_check_status.reset_mock()
        mock_LOG.reset_mock()

        mock_check_output.side_effect = [
            subprocess.CalledProcessError(
                output='haproxy.service is not active, cannot reload.',
                returncode=-2, cmd='service'),
            subprocess.CalledProcessError(
                output='haproxy.service is not active, cannot reload.',
                returncode=-2, cmd='service'),
            subprocess.CalledProcessError(
                output='haproxy.service is not active, cannot reload.',
                returncode=-2, cmd='service')]
        mock_check_status.return_value = 'ACTIVE'
        mock_check_status.side_effect = None

        mock_query = mock.Mock()
        mock_haproxy_query.return_value = mock_query
        mock_query.show_info.side_effect = Exception("error")

        result = self.test_loadbalancer.start_stop_lb(listener_id, 'reload')
        self.assertEqual(500, result.status_code)
        self.assertEqual('Error reloading haproxy', result.json['message'])
        self.assertEqual('haproxy.service is not active, cannot reload.',
                         result.json['details'])

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'config_path')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_haproxy_pid')
    @mock.patch('os.path.exists')
    def test_get_listeners_on_lb(self, mock_exists, mock_get_haproxy_pid,
                                 mock_config_path):

        fake_cfg_path = '/some/fake/cfg/file.cfg'
        mock_config_path.return_value = fake_cfg_path
        mock_get_haproxy_pid.return_value = 'fake_pid'

        # Finds two listeners
        mock_exists.side_effect = [True, True]
        fake_cfg_data = 'frontend list1\nbackend foo\nfrontend list2'
        self.useFixture(
            test_utils.OpenFixture(fake_cfg_path, fake_cfg_data)).mock_open
        result = self.test_loadbalancer._get_listeners_on_lb(LB_ID1)
        self.assertEqual(['list1', 'list2'], result)
        mock_exists.assert_has_calls([mock.call(agent_util.pid_path(LB_ID1)),
                                     mock.call('/proc/fake_pid')])

        # No PID file, no listeners
        mock_exists.reset_mock()
        mock_exists.side_effect = [False]
        result = self.test_loadbalancer._get_listeners_on_lb(LB_ID1)
        self.assertEqual([], result)
        mock_exists.assert_called_once_with(agent_util.pid_path(LB_ID1))

        # PID file, no running process, no listeners
        mock_exists.reset_mock()
        mock_exists.side_effect = [True, False]
        result = self.test_loadbalancer._get_listeners_on_lb(LB_ID1)
        self.assertEqual([], result)
        mock_exists.assert_has_calls([mock.call(agent_util.pid_path(LB_ID1)),
                                     mock.call('/proc/fake_pid')])

        # PID file, running process, no listeners
        mock_exists.reset_mock()
        mock_exists.side_effect = [True, True]
        fake_cfg_data = 'backend only'
        self.useFixture(
            test_utils.OpenFixture(fake_cfg_path, fake_cfg_data)).mock_open
        result = self.test_loadbalancer._get_listeners_on_lb(LB_ID1)
        self.assertEqual([], result)
        mock_exists.assert_has_calls([mock.call(agent_util.pid_path(LB_ID1)),
                                     mock.call('/proc/fake_pid')])
