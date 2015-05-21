#    Copyright (c) 2015 Rackspace
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

from oslo_log import log
from oslo_utils import uuidutils
import paramiko
import six

from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.amphorae.drivers.haproxy import ssh_driver
from octavia.certificates.manager import barbican
from octavia.common import data_models
from octavia.common.tls_utils import cert_parser
from octavia.db import models as models
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs

if six.PY2:
    import mock
else:
    import unittest.mock as mock

LOG = log.getLogger(__name__)


class TestSshDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestSshDriver, self).setUp()
        self.driver = ssh_driver.HaproxyManager()
        self.listener = sample_configs.sample_listener_tuple()
        self.vip = sample_configs.sample_vip_tuple()
        self.amphora = models.Amphora()
        self.amphora.id = self.FAKE_UUID_1
        self.driver.barbican_client = mock.Mock(
            spec=barbican.BarbicanCertManager)
        self.driver.client = mock.Mock(spec=paramiko.SSHClient)
        self.driver.client.exec_command.return_value = (
            mock.Mock(), mock.Mock(), mock.Mock())
        self.driver.amp_config = mock.MagicMock()

    def test_update(self):
        with mock.patch.object(
                self.driver, '_process_tls_certificates') as process_tls_patch:
            with mock.patch.object(jinja_cfg.JinjaTemplater,
                                   'build_config') as build_conf:
                # Build sample Listener and VIP configs
                listener = sample_configs.sample_listener_tuple(tls=True,
                                                                sni=True)
                vip = sample_configs.sample_vip_tuple()

                process_tls_patch.return_value = {
                    'tls_cert': listener.default_tls_container,
                    'sni_certs': listener.sni_containers
                }
                build_conf.return_value = 'sampleConfig'

                # Execute driver method
                self.driver.update(listener, vip)

                # Verify calls
                process_tls_patch.assert_called_once_with(listener)
                build_conf.assert_called_once_with(
                    listener, listener.default_tls_container,
                    listener.sni_containers)
                self.driver.client.connect.assert_called_once()
                self.driver.client.open_sftp().assert_called_once()
                self.driver.client.open_sftp().put().assert_called_once()
                self.driver.client.exec_command.assert_called_once()
                self.driver.client.close.assert_called_once()

    def test_stop(self):
        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.start(listener, vip)
        self.driver.client.connect.assert_called_once()
        self.driver.client.exec_command.assert_called_once()
        self.driver.client.close.assert_called_once()

    def test_start(self):
        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.start(listener, vip)
        self.driver.client.connect.assert_called_once()
        self.driver.client.exec_command.assert_called_once()
        self.driver.client.close.assert_called_once()

    def test_delete(self):
        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.delete(listener, vip)

        # Verify call
        self.driver.client.connect.assert_called_once()
        self.driver.client.exec_command.assert_called_once()
        self.driver.client.close.assert_called_once()

    def test_get_info(self):
        pass

    def test_get_diagnostics(self):
        pass

    def test_finalize_amphora(self):
        pass

    def test_process_tls_certificates(self):
        listener = sample_configs.sample_listener_tuple(tls=True, sni=True)
        with mock.patch.object(self.driver, '_build_pem') as pem:
            with mock.patch.object(self.driver.barbican_client,
                                   'get_cert') as bbq:
                with mock.patch.object(cert_parser,
                                       'get_host_names') as cp:
                    cp.return_value = {'cn': 'fakeCN'}
                    pem.return_value = 'imapem'
                    self.driver._process_tls_certificates(listener)

                    # Ensure upload_cert is called three times
                    calls_bbq = [mock.call(listener.default_tls_container.id),
                                 mock.call().get_certificate(),
                                 mock.call().get_private_key(),
                                 mock.call().get_certificate(),
                                 mock.call().get_intermediates(),
                                 mock.call('cont_id_2'),
                                 mock.call().get_certificate(),
                                 mock.call().get_private_key(),
                                 mock.call().get_certificate(),
                                 mock.call().get_intermediates(),
                                 mock.call('cont_id_3'),
                                 mock.call().get_certificate(),
                                 mock.call().get_private_key(),
                                 mock.call().get_certificate(),
                                 mock.call().get_intermediates()]
                    bbq.assert_has_calls(calls_bbq)

                    self.driver.client.open_sftp().put(
                        mock.ANY, '{0}/{1}/certificates/{2}'.format(
                            self.driver.amp_config.base_path, listener.id,
                            pem)).assert_called_once()

    def test_get_primary_cn(self):
        cert = mock.MagicMock()

        with mock.patch.object(cert_parser, 'get_host_names') as cp:
            cp.return_value = {'cn': 'fakeCN'}
            cn = self.driver._get_primary_cn(cert)
            self.assertEqual('fakeCN', cn)

    def test_map_cert_tls_container(self):
        tls = data_models.TLSContainer(primary_cn='fakeCN',
                                       certificate='imaCert',
                                       private_key='imaPrivateKey',
                                       intermediates=['imainter1',
                                                      'imainter2'])
        cert = mock.MagicMock()
        cert.get_private_key.return_value = tls.private_key
        cert.get_certificate.return_value = tls.certificate
        cert.get_intermediates.return_value = tls.intermediates
        with mock.patch.object(cert_parser, 'get_host_names') as cp:
            cp.return_value = {'cn': 'fakeCN'}
            self.assertEqual(tls.primary_cn,
                             self.driver._map_cert_tls_container(
                                 cert).primary_cn)
            self.assertEqual(tls.certificate,
                             self.driver._map_cert_tls_container(
                                 cert).certificate)
            self.assertEqual(tls.private_key,
                             self.driver._map_cert_tls_container(
                                 cert).private_key)
            self.assertEqual(tls.intermediates,
                             self.driver._map_cert_tls_container(
                                 cert).intermediates)

    def test_build_pem(self):
        expected = 'imainter\nimainter2\nimacert\nimakey'
        tls_tupe = sample_configs.sample_tls_container_tuple(
            certificate='imacert', private_key='imakey',
            intermediates=['imainter', 'imainter2'])
        self.assertEqual(expected, self.driver._build_pem(tls_tupe))