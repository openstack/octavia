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
from octavia.network import data_models as network_models
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs

if six.PY2:
    import mock
else:
    import unittest.mock as mock

LOG = log.getLogger(__name__)

MOCK_NETWORK_ID = '1'
MOCK_SUBNET_ID = '2'
MOCK_PORT_ID = '3'
MOCK_COMPUTE_ID = '4'
MOCK_AMP_ID = '5'
MOCK_IP_ADDRESS = '10.0.0.1'
MOCK_CIDR = '10.0.0.0/24'


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
                self.driver.client.connect.assert_called_once_with(
                    hostname=listener.load_balancer.amphorae[0].lb_network_ip,
                    key_filename=self.driver.amp_config.key_path,
                    username=self.driver.amp_config.username)
                self.driver.client.open_sftp.assert_called_once_with()
                self.driver.client.open_sftp().put.assert_called_once_with(
                    mock.ANY, mock.ANY
                )
                self.driver.client.exec_command.assert_has_calls([
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY),
                    mock.call(mock.ANY)
                ])
                self.driver.client.close.assert_called_once_with()

    def test_stop(self):
        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.start(listener, vip)
        self.driver.client.connect.assert_called_once_with(
            hostname=listener.load_balancer.amphorae[0].lb_network_ip,
            key_filename=self.driver.amp_config.key_path,
            username=self.driver.amp_config.username)
        self.driver.client.exec_command.assert_called_once_with(
            'sudo haproxy -f {0}/{1}/haproxy.cfg -p {0}/{1}/{1}.pid'.format(
                self.driver.amp_config.base_path, listener.id))
        self.driver.client.close.assert_called_once_with()

    def test_start(self):
        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.start(listener, vip)
        self.driver.client.connect.assert_called_once_with(
            hostname=listener.load_balancer.amphorae[0].lb_network_ip,
            key_filename=self.driver.amp_config.key_path,
            username=self.driver.amp_config.username)
        self.driver.client.exec_command.assert_called_once_with(
            'sudo haproxy -f {0}/{1}/haproxy.cfg -p {0}/{1}/{1}.pid'.format(
                self.driver.amp_config.base_path, listener.id))
        self.driver.client.close.assert_called_once_with()

    def test_delete(self):

        # Build sample Listener and VIP configs
        listener = sample_configs.sample_listener_tuple(
            tls=True, sni=True)
        vip = sample_configs.sample_vip_tuple()

        # Execute driver method
        self.driver.delete(listener, vip)

        # Verify call
        self.driver.client.connect.assert_called_once_with(
            hostname=listener.load_balancer.amphorae[0].lb_network_ip,
            key_filename=self.driver.amp_config.key_path,
            username=self.driver.amp_config.username)
        exec_command_calls = [
            mock.call('sudo kill -9 $(cat {0}/sample_listener_id_1'
                      '/sample_listener_id_1.pid)'
                      .format(self.driver.amp_config.base_path)),
            mock.call('sudo rm -rf {0}/sample_listener_id_1'.format(
                      self.driver.amp_config.base_path))]
        self.driver.client.exec_command.assert_has_calls(exec_command_calls)
        self.driver.client.close.assert_called_once_with()

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

                    self.driver.client.open_sftp().put.assert_has_calls([
                        mock.call(mock.ANY, mock.ANY),
                        mock.call(mock.ANY, mock.ANY),
                        mock.call(mock.ANY, mock.ANY),
                    ])

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

    @mock.patch.object(ssh_driver.HaproxyManager, '_execute_command')
    def test_post_vip_plug_no_down_links(self, exec_command):
        amps = [data_models.Amphora(id=MOCK_AMP_ID, compute_id=MOCK_COMPUTE_ID,
                                    lb_network_ip=MOCK_IP_ADDRESS)]
        vip = data_models.Vip(ip_address=MOCK_IP_ADDRESS)
        lb = data_models.LoadBalancer(amphorae=amps, vip=vip)
        vip_network = network_models.Network(id=MOCK_NETWORK_ID)
        exec_command.return_value = ('', '')
        self.driver.post_vip_plug(lb, vip_network)
        exec_command.assert_called_once_with(ssh_driver.CMD_GREP_DOWN_LINKS)

    @mock.patch.object(ssh_driver.HaproxyManager, '_execute_command')
    def test_post_vip_plug(self, exec_command):
        amps = [data_models.Amphora(id=MOCK_AMP_ID, compute_id=MOCK_COMPUTE_ID,
                                    lb_network_ip=MOCK_IP_ADDRESS)]
        vip = data_models.Vip(ip_address=MOCK_IP_ADDRESS)
        lb = data_models.LoadBalancer(amphorae=amps, vip=vip)
        vip_subnet = network_models.Subnet(id=MOCK_SUBNET_ID,
                                           gateway_ip=MOCK_IP_ADDRESS,
                                           cidr=MOCK_CIDR)
        vip_port = network_models.Port(id=MOCK_PORT_ID,
                                       device_id=MOCK_COMPUTE_ID)
        amphorae_net_config = {amps[0].id: network_models.AmphoraNetworkConfig(
            amphora=amps[0],
            vip_subnet=vip_subnet,
            vip_port=vip_port
        )}
        iface = 'eth1'
        exec_command.return_value = ('{0}: '.format(iface), '')
        self.driver.post_vip_plug(lb, amphorae_net_config)
        grep_call = mock.call(ssh_driver.CMD_GREP_DOWN_LINKS)
        dhclient_call = mock.call(ssh_driver.CMD_DHCLIENT.format(iface),
                                  run_as_root=True)
        add_ip_call = mock.call(ssh_driver.CMD_ADD_IP_ADDR.format(
            MOCK_IP_ADDRESS, iface), run_as_root=True)
        show_ip_call = mock.call(ssh_driver.CMD_SHOW_IP_ADDR.format(iface))
        create_vip_table_call = mock.call(
            ssh_driver.CMD_CREATE_VIP_ROUTE_TABLE.format(
                ssh_driver.VIP_ROUTE_TABLE),
            run_as_root=True
        )
        add_route_call = mock.call(
            ssh_driver.CMD_ADD_ROUTE_TO_TABLE.format(
                MOCK_CIDR, iface, ssh_driver.VIP_ROUTE_TABLE),
            run_as_root=True
        )
        add_default_route_call = mock.call(
            ssh_driver.CMD_ADD_DEFAULT_ROUTE_TO_TABLE.format(
                MOCK_IP_ADDRESS, iface, ssh_driver.VIP_ROUTE_TABLE),
            run_as_root=True
        )
        add_rule_from_call = mock.call(
            ssh_driver.CMD_ADD_RULE_FROM_NET_TO_TABLE.format(
                MOCK_CIDR, ssh_driver.VIP_ROUTE_TABLE),
            run_as_root=True
        )
        add_rule_to_call = mock.call(
            ssh_driver.CMD_ADD_RULE_TO_NET_TO_TABLE.format(
                MOCK_CIDR, ssh_driver.VIP_ROUTE_TABLE),
            run_as_root=True
        )
        exec_command.assert_has_calls([grep_call, dhclient_call, add_ip_call,
                                       show_ip_call, create_vip_table_call,
                                       add_route_call, add_default_route_call,
                                       add_rule_from_call, add_rule_to_call])
        self.assertEqual(9, exec_command.call_count)

    @mock.patch.object(ssh_driver.HaproxyManager, '_execute_command')
    def test_post_network_plug_no_down_links(self, exec_command):
        amp = data_models.Amphora(id=MOCK_AMP_ID, compute_id=MOCK_COMPUTE_ID,
                                  lb_network_ip=MOCK_IP_ADDRESS)
        exec_command.return_value = ('', '')
        self.driver.post_network_plug(amp)
        exec_command.assert_called_once_with(ssh_driver.CMD_GREP_DOWN_LINKS)

    @mock.patch.object(ssh_driver.HaproxyManager, '_execute_command')
    def test_post_network_plug(self, exec_command):
        amp = data_models.Amphora(id=MOCK_AMP_ID, compute_id=MOCK_COMPUTE_ID,
                                  lb_network_ip=MOCK_IP_ADDRESS)
        iface = 'eth1'
        exec_command.return_value = ('{0}: '.format(iface), '')
        self.driver.post_network_plug(amp)
        grep_call = mock.call(ssh_driver.CMD_GREP_DOWN_LINKS)
        dhclient_call = mock.call(ssh_driver.CMD_DHCLIENT.format(iface),
                                  run_as_root=True)
        show_ip_call = mock.call(ssh_driver.CMD_SHOW_IP_ADDR.format(iface))
        exec_command.assert_has_calls([grep_call, dhclient_call, show_ip_call])
        self.assertEqual(3, exec_command.call_count)
