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
import six

from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.common import constants as consts
import octavia.tests.unit.base as base
from octavia.tests.unit.common.sample_configs import sample_configs

BUILTINS = '__builtin__'
if six.PY3:
    BUILTINS = 'builtins'

BASE_AMP_PATH = '/var/lib/octavia'
BASE_CRT_PATH = BASE_AMP_PATH + '/certs'


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

        with mock.patch('%s.open' % BUILTINS, m, create=True):
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

        with mock.patch('%s.open' % BUILTINS, m, create=True):
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

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('HTTP', res['mode'])
            self.assertEqual(BASE_AMP_PATH + '/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertIsNone(res['ssl_crt'])

        # template_https
        rendered_obj = self.jinja_cfg.render_loadbalancer_obj(
            sample_configs.sample_listener_tuple(proto='HTTPS'))
        m = mock.mock_open(read_data=rendered_obj)

        with mock.patch('%s.open' % BUILTINS, m, create=True):
            res = listener._parse_haproxy_file('123')
            self.assertEqual('TCP', res['mode'])
            self.assertEqual(BASE_AMP_PATH + '/sample_listener_id_1.sock',
                             res['stats_socket'])
            self.assertIsNone(res['ssl_crt'])

        # Bogus format
        m = mock.mock_open(read_data='Bogus')

        with mock.patch('%s.open' % BUILTINS, m, create=True):
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
        self.assertEqual(
            consts.ACTIVE,
            listener._check_listener_status('123'))

        mock_exists.side_effect = [True, False]
        self.assertEqual(
            consts.ERROR,
            listener._check_listener_status('123'))

        mock_exists.side_effect = [False]
        self.assertEqual(
            consts.OFFLINE,
            listener._check_listener_status('123'))
