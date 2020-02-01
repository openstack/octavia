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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.common.jinja.haproxy.combined_listeners import jinja_cfg
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base
from octavia.tests.unit.common.sample_configs import sample_configs_combined

BASE_AMP_PATH = '/var/lib/octavia'
BASE_CRT_PATH = BASE_AMP_PATH + '/certs'
CONF = cfg.CONF
LISTENER_ID1 = uuidutils.generate_uuid()
LB_ID1 = uuidutils.generate_uuid()


class TestUtil(base.TestCase):
    def setUp(self):
        super(TestUtil, self).setUp()
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.listener_id = uuidutils.generate_uuid()
        self.jinja_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path=BASE_AMP_PATH,
            base_crt_dir=BASE_CRT_PATH)

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

        result = util.get_protocol_for_lb_object('1')

        mock_cfg_path.assert_called_once_with('1')
        mock_path_exists.assert_called_once_with('/there')
        self.assertFalse(mock_lvs_path.called)
        self.assertEqual(consts.PROTOCOL_TCP, result)

        mock_cfg_path.reset_mock()

        result = util.get_protocol_for_lb_object('2')

        mock_cfg_path.assert_called_once_with('2')
        mock_lvs_path.assert_called_once_with('2')
        self.assertEqual(consts.PROTOCOL_UDP, result)

        mock_cfg_path.reset_mock()
        mock_lvs_path.reset_mock()

        result = util.get_protocol_for_lb_object('3')

        mock_cfg_path.assert_called_once_with('3')
        mock_lvs_path.assert_called_once_with('3')
        self.assertIsNone(result)

    def test_parse_haproxy_config(self):
        self.CONF.config(group="haproxy_amphora",
                         base_cert_dir='/fake_cert_dir')
        FAKE_CRT_LIST_FILENAME = os.path.join(
            CONF.haproxy_amphora.base_cert_dir,
            'sample_loadbalancer_id_1/sample_listener_id_1.pem')
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True, sni=True)])

        path = util.config_path(LISTENER_ID1)
        self.useFixture(test_utils.OpenFixture(path, rendered_obj))

        res = util.parse_haproxy_file(LISTENER_ID1)
        listener_dict = res[1]['sample_listener_id_1']
        # NOTE: parse_haproxy_file makes mode TERMINATED_HTTPS even though
        #       the haproxy.cfg needs mode HTTP
        self.assertEqual('TERMINATED_HTTPS', listener_dict['mode'])
        self.assertEqual('/var/lib/octavia/sample_loadbalancer_id_1.sock',
                         res[0])
        self.assertEqual(FAKE_CRT_LIST_FILENAME, listener_dict['ssl_crt'])

        # render_template_tls_no_sni
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True)])
        self.useFixture(test_utils.OpenFixture(path, rendered_obj))

        res = util.parse_haproxy_file(LISTENER_ID1)
        listener_dict = res[1]['sample_listener_id_1']
        self.assertEqual('TERMINATED_HTTPS', listener_dict['mode'])
        self.assertEqual(BASE_AMP_PATH + '/sample_loadbalancer_id_1.sock',
                         res[0])
        self.assertEqual(FAKE_CRT_LIST_FILENAME, listener_dict['ssl_crt'])

        # render_template_http
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple()])

        self.useFixture(test_utils.OpenFixture(path, rendered_obj))

        res = util.parse_haproxy_file(LISTENER_ID1)
        listener_dict = res[1]['sample_listener_id_1']
        self.assertEqual('HTTP', listener_dict['mode'])
        self.assertEqual(BASE_AMP_PATH + '/sample_loadbalancer_id_1.sock',
                         res[0])
        self.assertIsNone(listener_dict.get('ssl_crt', None))

        # template_https
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs_combined.sample_amphora_tuple(),
            [sample_configs_combined.sample_listener_tuple(proto='HTTPS')])
        self.useFixture(test_utils.OpenFixture(path, rendered_obj))

        res = util.parse_haproxy_file(LISTENER_ID1)
        listener_dict = res[1]['sample_listener_id_1']
        self.assertEqual('TCP', listener_dict['mode'])
        self.assertEqual(BASE_AMP_PATH + '/sample_loadbalancer_id_1.sock',
                         res[0])
        self.assertIsNone(listener_dict.get('ssl_crt', None))

        # Bogus format
        self.useFixture(test_utils.OpenFixture(path, 'Bogus'))
        try:
            res = util.parse_haproxy_file(LISTENER_ID1)
            self.fail("No Exception?")
        except util.ParsingError:
            pass

        # Bad listener mode
        fake_cfg = 'stats socket foo\nfrontend {}\nmode\n'.format(LISTENER_ID1)
        self.useFixture(test_utils.OpenFixture(path, fake_cfg))
        self.assertRaises(util.ParsingError, util.parse_haproxy_file,
                          LISTENER_ID1)

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_udp_listeners')
    @mock.patch('os.makedirs')
    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    @mock.patch('os.path.join')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_loadbalancers')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util'
                '.haproxy_sock_path')
    def test_vrrp_check_script_update(self, mock_sock_path, mock_get_lbs,
                                      mock_join, mock_listdir, mock_exists,
                                      mock_makedirs, mock_get_listeners):
        mock_get_lbs.return_value = ['abc', LB_ID1]
        mock_sock_path.return_value = 'listener.sock'
        mock_exists.side_effect = [False, False, True]
        mock_get_lbs.side_effect = [['abc', LB_ID1], ['abc', LB_ID1], []]
        mock_get_listeners.return_value = []

        # Test the stop action path
        cmd = 'haproxy-vrrp-check ' + ' '.join(['listener.sock']) + '; exit $?'
        path = util.keepalived_dir()
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open

        util.vrrp_check_script_update(LB_ID1, 'stop')

        handle = m()
        handle.write.assert_called_once_with(cmd)

        # Test the start action path
        cmd = ('haproxy-vrrp-check ' + ' '.join(['listener.sock',
                                                 'listener.sock']) + '; exit '
                                                                     '$?')
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open
        util.vrrp_check_script_update(LB_ID1, 'start')
        handle = m()
        handle.write.assert_called_once_with(cmd)

        # Test the path with existing keepalived directory and no LBs
        mock_makedirs.reset_mock()
        cmd = 'exit 1'
        m = self.useFixture(test_utils.OpenFixture(path)).mock_open

        util.vrrp_check_script_update(LB_ID1, 'start')

        handle = m()
        handle.write.assert_called_once_with(cmd)
        mock_makedirs.assert_has_calls(
            [mock.call(util.keepalived_dir(), exist_ok=True),
             mock.call(util.keepalived_check_scripts_dir(), exist_ok=True)])

    @mock.patch('octavia.amphorae.backends.agent.api_server.util.config_path')
    def test_get_haproxy_vip_addresses(self, mock_cfg_path):
        FAKE_PATH = 'fake_path'
        mock_cfg_path.return_value = FAKE_PATH
        self.useFixture(
            test_utils.OpenFixture(FAKE_PATH, 'no match')).mock_open()

        # Test with no matching lines in the config file
        self.assertEqual([], util.get_haproxy_vip_addresses(LB_ID1))
        mock_cfg_path.assert_called_once_with(LB_ID1)

        # Test with a matching bind line
        mock_cfg_path.reset_mock()
        test_data = 'no match\nbind 203.0.113.43:1\nbogus line'
        self.useFixture(
            test_utils.OpenFixture(FAKE_PATH, test_data)).mock_open()
        expected_result = ['203.0.113.43']
        self.assertEqual(expected_result,
                         util.get_haproxy_vip_addresses(LB_ID1))
        mock_cfg_path.assert_called_once_with(LB_ID1)

        # Test with a matching bind line multiple binds
        mock_cfg_path.reset_mock()
        test_data = 'no match\nbind 203.0.113.44:1234, 203.0.113.45:4321'
        self.useFixture(
            test_utils.OpenFixture(FAKE_PATH, test_data)).mock_open()
        expected_result = ['203.0.113.44', '203.0.113.45']
        self.assertEqual(expected_result,
                         util.get_haproxy_vip_addresses(LB_ID1))
        mock_cfg_path.assert_called_once_with(LB_ID1)

        # Test with a bogus bind line
        mock_cfg_path.reset_mock()
        test_data = 'no match\nbind\nbogus line'
        self.useFixture(
            test_utils.OpenFixture(FAKE_PATH, test_data)).mock_open()
        self.assertEqual([], util.get_haproxy_vip_addresses(LB_ID1))
        mock_cfg_path.assert_called_once_with(LB_ID1)

    @mock.patch('octavia.amphorae.backends.utils.ip_advertisement.'
                'send_ip_advertisement')
    @mock.patch('octavia.amphorae.backends.utils.network_utils.'
                'get_interface_name')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_haproxy_vip_addresses')
    def test_send_vip_advertisements(self, mock_get_vip_addrs,
                                     mock_get_int_name, mock_send_advert):
        mock_get_vip_addrs.side_effect = [[], ['203.0.113.46'],
                                          Exception('boom')]
        mock_get_int_name.return_value = 'fake0'

        # Test no VIPs
        util.send_vip_advertisements(LB_ID1)
        mock_get_vip_addrs.assert_called_once_with(LB_ID1)
        mock_get_int_name.assert_not_called()
        mock_send_advert.assert_not_called()

        # Test with a VIP
        mock_get_vip_addrs.reset_mock()
        mock_get_int_name.reset_mock()
        mock_send_advert.reset_mock()
        util.send_vip_advertisements(LB_ID1)
        mock_get_vip_addrs.assert_called_once_with(LB_ID1)
        mock_get_int_name.assert_called_once_with(
            '203.0.113.46', net_ns=consts.AMPHORA_NAMESPACE)
        mock_send_advert.assert_called_once_with(
            'fake0', '203.0.113.46', net_ns=consts.AMPHORA_NAMESPACE)

        # Test with an exception (should not raise)
        mock_get_vip_addrs.reset_mock()
        mock_get_int_name.reset_mock()
        mock_send_advert.reset_mock()
        util.send_vip_advertisements(LB_ID1)
        mock_get_int_name.assert_not_called()
        mock_send_advert.assert_not_called()
