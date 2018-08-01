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
#    under the License.

import os
import subprocess

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


CONF = cfg.CONF


class TestUtil(base.TestCase):
    def setUp(self):
        super(TestUtil, self).setUp()
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.listener_id = uuidutils.generate_uuid()

    def test_keepalived_lvs_dir(self):
        fake_path = '/fake/path'
        self.CONF.config(group="haproxy_amphora", base_path=fake_path)

        result = util.keepalived_lvs_dir()
        fake_path = fake_path + '/lvs'
        self.assertEqual(fake_path, result)

    def test_keepalived_lvs_init_path(self):
        # Test systemd
        ref_path = (consts.SYSTEMD_DIR + '/' +
                    consts.KEEPALIVED_SYSTEMD_PREFIX % str(self.listener_id))
        result = util.keepalived_lvs_init_path(consts.INIT_SYSTEMD,
                                               self.listener_id)
        self.assertEqual(ref_path, result)

        # Test upstart
        ref_path = (consts.UPSTART_DIR + '/' +
                    consts.KEEPALIVED_UPSTART_PREFIX % str(self.listener_id))
        result = util.keepalived_lvs_init_path(consts.INIT_UPSTART,
                                               self.listener_id)
        self.assertEqual(ref_path, result)

        # Test sysvinit
        ref_path = (consts.SYSVINIT_DIR + '/' +
                    consts.KEEPALIVED_SYSVINIT_PREFIX % str(self.listener_id))
        result = util.keepalived_lvs_init_path(consts.INIT_SYSVINIT,
                                               self.listener_id)
        self.assertEqual(ref_path, result)

        # Test bad init system
        self.assertRaises(util.UnknownInitError, util.keepalived_lvs_init_path,
                          'bogus_init', self.listener_id)

    def test_keepalived_lvs_pids_path(self):
        fake_path = '/fake/path'
        self.CONF.config(group="haproxy_amphora", base_path=fake_path)

        pid_path = (fake_path + '/' + 'lvs/octavia-keepalivedlvs-' +
                    self.listener_id + '.' + 'pid')
        vrrp_pid_path = (fake_path + '/' + 'lvs/octavia-keepalivedlvs-' +
                         self.listener_id + '.' + 'vrrp.pid')
        check_pid_path = (fake_path + '/' + 'lvs/octavia-keepalivedlvs-' +
                          self.listener_id + '.' + 'check.pid')

        result1, result2, result3 = util.keepalived_lvs_pids_path(
            self.listener_id)

        self.assertEqual(pid_path, result1)
        self.assertEqual(vrrp_pid_path, result2)
        self.assertEqual(check_pid_path, result3)

    def test_keepalived_lvs_cfg_path(self):
        fake_path = '/fake/path'
        self.CONF.config(group="haproxy_amphora", base_path=fake_path)

        ref_path = (fake_path + '/lvs/octavia-keepalivedlvs-' +
                    self.listener_id + '.conf')
        result = util.keepalived_lvs_cfg_path(self.listener_id)

        self.assertEqual(ref_path, result)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'keepalived_lvs_pids_path')
    def test_get_keepalivedlvs_pid(self, mock_path):
        fake_path = '/fake/path'
        mock_path.return_value = [fake_path]
        self.useFixture(test_utils.OpenFixture(
            fake_path, ' space data   ')).mock_open
        result = util.get_keepalivedlvs_pid(self.listener_id)
        self.assertEqual(' space data', result)

    @mock.patch('jinja2.FileSystemLoader')
    @mock.patch('jinja2.Environment')
    @mock.patch('os.path')
    @mock.patch('octavia.amphorae.backends.agent.api_server.osutils.'
                'BaseOS.get_os_util')
    def test_install_netns_systemd_service(self, mock_get_os_util,
                                           mock_os_path, mock_jinja2_env,
                                           mock_fsloader):
        mock_os_util = mock.MagicMock()
        mock_os_util.has_ifup_all.return_value = True
        mock_get_os_util.return_value = mock_os_util

        mock_os_path.realpath.return_value = '/dir/file'
        mock_os_path.dirname.return_value = '/dir/'
        mock_os_path.exists.return_value = False
        mock_fsloader.return_value = 'fake_loader'
        mock_jinja_env = mock.MagicMock()
        mock_jinja2_env.return_value = mock_jinja_env
        mock_template = mock.MagicMock()
        mock_template.render.return_value = 'script'
        mock_jinja_env.get_template.return_value = mock_template

        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):

            util.install_netns_systemd_service()

        mock_jinja2_env.assert_called_with(autoescape=True,
                                           loader='fake_loader')

        mock_jinja_env.get_template.assert_called_once_with(
            consts.AMP_NETNS_SVC_PREFIX + '.systemd.j2')
        mock_template.render.assert_called_once_with(
            amphora_nsname=consts.AMPHORA_NAMESPACE, HasIFUPAll=True)
        handle = m()
        handle.write.assert_called_with('script')

        # Test file exists path we don't over write
        mock_jinja_env.get_template.reset_mock()
        mock_os_path.exists.return_value = True
        util.install_netns_systemd_service()
        self.assertFalse(mock_jinja_env.get_template.called)

    @mock.patch('subprocess.check_output')
    def test_run_systemctl_command(self, mock_check_output):

        util.run_systemctl_command('test', 'world')
        mock_check_output.assert_called_once_with(
            ['systemctl', 'test', 'world'], stderr=subprocess.STDOUT)

        mock_check_output.side_effect = subprocess.CalledProcessError(1,
                                                                      'boom')
        util.run_systemctl_command('test', 'world')

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.config_path')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'keepalived_lvs_cfg_path')
    @mock.patch('os.path.exists')
    def test_get_listener_protocol(self, mock_path_exists, mock_lvs_path,
                                   mock_cfg_path):
        mock_lvs_path.return_value = '/here'
        mock_cfg_path.return_value = '/there'
        mock_path_exists.side_effect = [True, False, True, False, False]

        result = util.get_listener_protocol('1')

        mock_cfg_path.assert_called_once_with('1')
        mock_path_exists.assert_called_once_with('/there')
        self.assertFalse(mock_lvs_path.called)
        self.assertEqual(consts.PROTOCOL_TCP, result)

        mock_cfg_path.reset_mock()

        result = util.get_listener_protocol('2')

        mock_cfg_path.assert_called_once_with('2')
        mock_lvs_path.assert_called_once_with('2')
        self.assertEqual(consts.PROTOCOL_UDP, result)

        mock_cfg_path.reset_mock()
        mock_lvs_path.reset_mock()

        result = util.get_listener_protocol('3')

        mock_cfg_path.assert_called_once_with('3')
        mock_lvs_path.assert_called_once_with('3')
        self.assertIsNone(result)
