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

import mock
from oslo_utils import uuidutils
import six.moves.builtins as builtins

from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.backends.agent.api_server import util as agent_util
from octavia.common import constants as consts
from octavia.common.jinja.haproxy import jinja_cfg
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base
from octavia.tests.unit.common.sample_configs import sample_configs

BASE_AMP_PATH = '/var/lib/octavia'
BASE_CRT_PATH = BASE_AMP_PATH + '/certs'
LISTENER_ID1 = uuidutils.generate_uuid()


class ListenerTestCase(base.TestCase):
    def setUp(self):
        super(ListenerTestCase, self).setUp()
        self.jinja_cfg = jinja_cfg.JinjaTemplater(
            base_amp_path=BASE_AMP_PATH,
            base_crt_dir=BASE_CRT_PATH)

    def test_parse_haproxy_config(self):
        # template_tls
        tls_tupe = sample_configs.sample_tls_container_tuple(
            certificate='imaCert1', private_key='imaPrivateKey1',
            primary_cn='FakeCN')
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='TERMINATED_HTTPS',
                                                 tls=True, sni=True),
            tls_tupe)

        m = mock.mock_open(read_data=rendered_obj)

        with mock.patch.object(builtins, 'open', m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('TERMINATED_HTTPS', res['mode'])
            self.assertEqual('/var/lib/octavia/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertEqual(
                '/var/lib/octavia/certs/sample_listener_id_1/FakeCN.pem',
                res['ssl_crt'])

        # render_template_tls_no_sni
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(
                proto='TERMINATED_HTTPS', tls=True),
            tls_cert=sample_configs.sample_tls_container_tuple(
                certificate='ImAalsdkfjCert',
                private_key='ImAsdlfksdjPrivateKey',
                primary_cn="FakeCN"))

        m = mock.mock_open(read_data=rendered_obj)

        with mock.patch.object(builtins, 'open', m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('TERMINATED_HTTPS', res['mode'])
            self.assertEqual(BASE_AMP_PATH + '/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertEqual(
                BASE_CRT_PATH + '/sample_listener_id_1/FakeCN.pem',
                res['ssl_crt'])

        # render_template_http
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple())
        m = mock.mock_open(read_data=rendered_obj)

        with mock.patch.object(builtins, 'open', m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('HTTP', res['mode'])
            self.assertEqual(BASE_AMP_PATH + '/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertIsNone(res['ssl_crt'])

        # template_https
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTPS'))
        m = mock.mock_open(read_data=rendered_obj)

        with mock.patch.object(builtins, 'open', m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('TCP', res['mode'])
            self.assertEqual(BASE_AMP_PATH + '/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertIsNone(res['ssl_crt'])

        # Bogus format
        m = mock.mock_open(read_data='Bogus')

        with mock.patch.object(builtins, 'open', m, create=True):
            try:
                res = listener._parse_haproxy_file('123')
                self.fail("No Exception?")
            except listener.ParsingError:
                pass

    @mock.patch('os.path.exists')
    @mock.patch('octavia.amphorae.backends.agent.api_server'
                + '.util.get_haproxy_pid')
    def test_check_listener_status(self, mock_pid, mock_exists):
        mock_pid.return_value = '1245'
        mock_exists.side_effect = [True, True]
        config_path = agent_util.config_path(LISTENER_ID1)
        file_contents = 'frontend {}'.format(LISTENER_ID1)
        self.useFixture(test_utils.OpenFixture(config_path, file_contents))
        self.assertEqual(
            consts.ACTIVE,
            listener._check_listener_status(LISTENER_ID1))

        mock_exists.side_effect = [True, False]
        self.assertEqual(
            consts.ERROR,
            listener._check_listener_status(LISTENER_ID1))

        mock_exists.side_effect = [False]
        self.assertEqual(
            consts.OFFLINE,
            listener._check_listener_status(LISTENER_ID1))

    @mock.patch('os.makedirs')
    @mock.patch('os.path.exists')
    @mock.patch('os.listdir')
    @mock.patch('os.path.join')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util.'
                'get_listeners')
    @mock.patch('octavia.amphorae.backends.agent.api_server.util'
                '.haproxy_sock_path')
    def test_vrrp_check_script_update(self, mock_sock_path, mock_get_listeners,
                                      mock_join, mock_listdir, mock_exists,
                                      mock_makedirs):
        mock_get_listeners.return_value = ['abc', '123']
        mock_sock_path.return_value = 'listener.sock'
        mock_exists.return_value = False
        cmd = 'haproxy-vrrp-check ' + ' '.join(['listener.sock']) + '; exit $?'
        m = mock.mock_open()
        with mock.patch.object(builtins, 'open', m, create=True):
            listener.vrrp_check_script_update('123', 'stop')
        handle = m()
        handle.write.assert_called_once_with(cmd)

        mock_get_listeners.return_value = ['abc', '123']
        cmd = ('haproxy-vrrp-check ' + ' '.join(['listener.sock',
                                                 'listener.sock']) + '; exit '
                                                                     '$?')
        m = mock.mock_open()
        with mock.patch.object(builtins, 'open', m, create=True):
            listener.vrrp_check_script_update('123', 'start')
        handle = m()
        handle.write.assert_called_once_with(cmd)
