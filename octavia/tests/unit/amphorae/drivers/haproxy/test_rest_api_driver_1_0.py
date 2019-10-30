# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2015 Rackspace
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

import hashlib

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import requests
import requests_mock
import six

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.amphorae.drivers.haproxy import rest_api_driver as driver
from octavia.common import constants
from octavia.db import models
from octavia.network import data_models as network_models
from octavia.tests.common import sample_certs
from octavia.tests.unit import base
from octavia.tests.unit.common.sample_configs import sample_configs_combined

API_VERSION = '1.0'
FAKE_CIDR = '198.51.100.0/24'
FAKE_GATEWAY = '192.51.100.1'
FAKE_IP = '192.0.2.10'
FAKE_IPV6 = '2001:db8::cafe'
FAKE_IPV6_LLA = 'fe80::00ff:fe00:cafe'
FAKE_PEM_FILENAME = "file_name"
FAKE_UUID_1 = uuidutils.generate_uuid()
FAKE_VRRP_IP = '10.1.0.1'
FAKE_MAC_ADDRESS = '123'
FAKE_MTU = 1450
FAKE_MEMBER_IP_PORT_NAME_1 = "10.0.0.10:1003"
FAKE_MEMBER_IP_PORT_NAME_2 = "10.0.0.11:1004"


class TestHaproxyAmphoraLoadBalancerDriverTest(base.TestCase):

    def setUp(self):
        super(TestHaproxyAmphoraLoadBalancerDriverTest, self).setUp()

        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        NEXTHOP = '192.0.2.1'

        self.driver = driver.HaproxyAmphoraLoadBalancerDriver()

        self.driver.cert_manager = mock.MagicMock()
        self.driver.cert_parser = mock.MagicMock()
        self.driver.clients = {
            'base': mock.MagicMock(),
            API_VERSION: mock.MagicMock()}
        self.driver.clients['base'].get_api_version.return_value = {
            'api_version': API_VERSION}
        self.driver.clients[
            API_VERSION].get_info.return_value = {
            'haproxy_version': u'1.6.3-1ubuntu0.1',
            'api_version': API_VERSION}
        self.driver.jinja_combo = mock.MagicMock()
        self.driver.udp_jinja = mock.MagicMock()

        # Build sample Listener and VIP configs
        self.sl = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True, client_crl_cert=True,
            recursive_nest=True)
        self.sl_udp = sample_configs_combined.sample_listener_tuple(
            proto=constants.PROTOCOL_UDP,
            persistence_type=constants.SESSION_PERSISTENCE_SOURCE_IP,
            persistence_timeout=33,
            persistence_granularity='255.255.0.0',
            monitor_proto=constants.HEALTH_MONITOR_UDP_CONNECT)
        self.pool_has_cert = sample_configs_combined.sample_pool_tuple(
            pool_cert=True, pool_ca_cert=True, pool_crl=True)
        self.amp = self.sl.load_balancer.amphorae[0]
        self.sv = sample_configs_combined.sample_vip_tuple()
        self.lb = self.sl.load_balancer
        self.lb_udp = (
            sample_configs_combined.sample_lb_with_udp_listener_tuple())
        self.fixed_ip = mock.MagicMock()
        self.fixed_ip.ip_address = '198.51.100.5'
        self.fixed_ip.subnet.cidr = '198.51.100.0/24'
        self.network = network_models.Network(mtu=FAKE_MTU)
        self.port = network_models.Port(mac_address=FAKE_MAC_ADDRESS,
                                        fixed_ips=[self.fixed_ip],
                                        network=self.network)

        self.host_routes = [network_models.HostRoute(destination=DEST1,
                                                     nexthop=NEXTHOP),
                            network_models.HostRoute(destination=DEST2,
                                                     nexthop=NEXTHOP)]
        host_routes_data = [{'destination': DEST1, 'nexthop': NEXTHOP},
                            {'destination': DEST2, 'nexthop': NEXTHOP}]
        self.subnet_info = {'subnet_cidr': FAKE_CIDR,
                            'gateway': FAKE_GATEWAY,
                            'mac_address': FAKE_MAC_ADDRESS,
                            'vrrp_ip': self.amp.vrrp_ip,
                            'mtu': FAKE_MTU,
                            'host_routes': host_routes_data}

        self.timeout_dict = {constants.REQ_CONN_TIMEOUT: 1,
                             constants.REQ_READ_TIMEOUT: 2,
                             constants.CONN_MAX_RETRIES: 3,
                             constants.CONN_RETRY_INTERVAL: 4}

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_secret')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_amphora_listeners(self, mock_load_cert, mock_secret):
        mock_amphora = mock.MagicMock()
        mock_amphora.id = 'mock_amphora_id'
        mock_amphora.api_version = API_VERSION
        mock_secret.return_value = 'filename.pem'
        mock_load_cert.return_value = {
            'tls_cert': self.sl.default_tls_container, 'sni_certs': [],
            'client_ca_cert': None}
        self.driver.jinja_combo.build_config.return_value = 'the_config'

        mock_empty_lb = mock.MagicMock()
        mock_empty_lb.listeners = []
        self.driver.update_amphora_listeners(mock_empty_lb, mock_amphora,
                                             self.timeout_dict)
        mock_load_cert.assert_not_called()
        self.driver.jinja_combo.build_config.assert_not_called()
        self.driver.clients[API_VERSION].upload_config.assert_not_called()
        self.driver.clients[API_VERSION].reload_listener.assert_not_called()

        self.driver.update_amphora_listeners(self.lb,
                                             mock_amphora, self.timeout_dict)
        self.driver.clients[API_VERSION].upload_config.assert_called_once_with(
            mock_amphora, self.lb.id, 'the_config',
            timeout_dict=self.timeout_dict)
        self.driver.clients[API_VERSION].reload_listener(
            mock_amphora, self.lb.id, timeout_dict=self.timeout_dict)

        mock_load_cert.reset_mock()
        self.driver.jinja_combo.build_config.reset_mock()
        self.driver.clients[API_VERSION].upload_config.reset_mock()
        self.driver.clients[API_VERSION].reload_listener.reset_mock()
        mock_amphora.status = constants.DELETED
        self.driver.update_amphora_listeners(self.lb,
                                             mock_amphora, self.timeout_dict)
        mock_load_cert.assert_not_called()
        self.driver.jinja_combo.build_config.assert_not_called()
        self.driver.clients[API_VERSION].upload_config.assert_not_called()
        self.driver.clients[API_VERSION].reload_listener.assert_not_called()

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.ListenerRepository.update')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_update_amphora_listeners_bad_cert(
            self, mock_load_cert, mock_list_update, mock_get_session):
        mock_amphora = mock.MagicMock()
        mock_amphora.id = 'mock_amphora_id'
        mock_amphora.api_version = API_VERSION

        mock_get_session.return_value = 'fake_session'
        mock_load_cert.side_effect = [Exception]
        self.driver.update_amphora_listeners(self.lb,
                                             mock_amphora, self.timeout_dict)
        mock_list_update.assert_called_once_with(
            'fake_session', self.lb.listeners[0].id,
            provisioning_status=constants.ERROR,
            operating_status=constants.ERROR)
        self.driver.jinja_combo.build_config.assert_not_called()
        (self.driver.clients[API_VERSION].delete_listener.
         assert_called_once_with)(mock_amphora, self.lb.id)

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_secret')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.get_host_names')
    def test_update(self, mock_cert, mock_load_crt, mock_secret):
        mock_cert.return_value = {'cn': sample_certs.X509_CERT_CN}
        mock_secret.side_effect = ['filename.pem', 'crl-filename.pem']
        sconts = []
        for sni_container in self.sl.sni_containers:
            sconts.append(sni_container.tls_container)
        mock_load_crt.side_effect = [{
            'tls_cert': self.sl.default_tls_container, 'sni_certs': sconts},
            {'tls_cert': None, 'sni_certs': []}]
        self.driver.clients[API_VERSION].get_cert_md5sum.side_effect = [
            exc.NotFound, 'Fake_MD5', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            'CA_CERT_MD5']
        self.driver.jinja_combo.build_config.side_effect = ['fake_config']

        # Execute driver method
        self.driver.update(self.lb)

        # verify result
        gcm_calls = [
            mock.call(self.amp, self.lb.id,
                      self.sl.default_tls_container.id + '.pem',
                      ignore=(404,)),
            mock.call(self.amp, self.lb.id,
                      sconts[0].id + '.pem', ignore=(404,)),
            mock.call(self.amp, self.lb.id,
                      sconts[1].id + '.pem', ignore=(404,)),
        ]

        self.driver.clients[API_VERSION].get_cert_md5sum.assert_has_calls(
            gcm_calls, any_order=True)

        # this is called three times (last MD5 matches)
        fp1 = b'\n'.join([sample_certs.X509_CERT,
                          sample_certs.X509_CERT_KEY,
                          sample_certs.X509_IMDS]) + b'\n'
        fp2 = b'\n'.join([sample_certs.X509_CERT_2,
                          sample_certs.X509_CERT_KEY_2,
                          sample_certs.X509_IMDS]) + b'\n'
        fp3 = b'\n'.join([sample_certs.X509_CERT_3,
                          sample_certs.X509_CERT_KEY_3,
                          sample_certs.X509_IMDS]) + b'\n'

        ucp_calls = [
            mock.call(self.amp, self.lb.id,
                      self.sl.default_tls_container.id + '.pem', fp1),
            mock.call(self.amp, self.lb.id,
                      sconts[0].id + '.pem', fp2),
            mock.call(self.amp, self.lb.id,
                      sconts[1].id + '.pem', fp3),
        ]

        self.driver.clients[API_VERSION].upload_cert_pem.assert_has_calls(
            ucp_calls, any_order=True)

        # upload only one config file
        self.driver.clients[API_VERSION].upload_config.assert_called_once_with(
            self.amp, self.lb.id, 'fake_config', timeout_dict=None)
        # start should be called once
        self.driver.clients[
            API_VERSION].reload_listener.assert_called_once_with(
            self.amp, self.lb.id, timeout_dict=None)
        secret_calls = [
            mock.call(self.sl, self.sl.client_ca_tls_certificate_id, self.amp,
                      self.lb.id),
            mock.call(self.sl, self.sl.client_crl_container_id, self.amp,
                      self.lb.id)
        ]
        mock_secret.assert_has_calls(secret_calls)

    def test_udp_update(self):
        self.driver.udp_jinja.build_config.side_effect = ['fake_udp_config']

        # Execute driver method
        self.driver.update(self.lb_udp)

        # upload only one config file
        self.driver.clients[
            API_VERSION].upload_udp_config.assert_called_once_with(
            self.amp, self.sl_udp.id, 'fake_udp_config', timeout_dict=None)

        # start should be called once
        self.driver.clients[
            API_VERSION].reload_listener.assert_called_once_with(
            self.amp, self.sl_udp.id, timeout_dict=None)

    def test_upload_cert_amp(self):
        self.driver.upload_cert_amp(self.amp, six.b('test'))
        self.driver.clients[
            API_VERSION].update_cert_for_rotation.assert_called_once_with(
            self.amp, six.b('test'))

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test__process_tls_certificates_no_ca_cert(self, mock_load_crt):
        sample_listener = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True)
        sconts = []
        for sni_container in sample_listener.sni_containers:
            sconts.append(sni_container.tls_container)
        mock_load_crt.return_value = {
            'tls_cert': self.sl.default_tls_container,
            'sni_certs': sconts
        }
        self.driver.clients[API_VERSION].get_cert_md5sum.side_effect = [
            exc.NotFound, 'Fake_MD5', 'aaaaa', 'aaaaa']
        self.driver._process_tls_certificates(
            sample_listener, self.amp, sample_listener.load_balancer.id)
        gcm_calls = [
            mock.call(self.amp, self.lb.id,
                      self.sl.default_tls_container.id + '.pem',
                      ignore=(404,)),
            mock.call(self.amp, self.lb.id,
                      sconts[0].id + '.pem', ignore=(404,)),
            mock.call(self.amp, self.lb.id,
                      sconts[1].id + '.pem', ignore=(404,))
        ]
        self.driver.clients[API_VERSION].get_cert_md5sum.assert_has_calls(
            gcm_calls, any_order=True)
        fp1 = b'\n'.join([sample_certs.X509_CERT,
                          sample_certs.X509_CERT_KEY,
                          sample_certs.X509_IMDS]) + b'\n'
        fp2 = b'\n'.join([sample_certs.X509_CERT_2,
                          sample_certs.X509_CERT_KEY_2,
                          sample_certs.X509_IMDS]) + b'\n'
        fp3 = b'\n'.join([sample_certs.X509_CERT_3,
                          sample_certs.X509_CERT_KEY_3,
                          sample_certs.X509_IMDS]) + b'\n'
        ucp_calls = [
            mock.call(self.amp, self.lb.id,
                      self.sl.default_tls_container.id + '.pem', fp1),
            mock.call(self.amp, self.lb.id,
                      sconts[0].id + '.pem', fp2),
            mock.call(self.amp, self.lb.id,
                      sconts[1].id + '.pem', fp3)
        ]
        self.driver.clients[API_VERSION].upload_cert_pem.assert_has_calls(
            ucp_calls, any_order=True)
        self.assertEqual(
            4, self.driver.clients[API_VERSION].upload_cert_pem.call_count)

    @mock.patch('oslo_context.context.RequestContext')
    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._upload_cert')
    def test_process_secret(self, mock_upload_cert, mock_oslo):
        # Test bypass if no secret_ref
        sample_listener = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True)

        result = self.driver._process_secret(sample_listener, None)

        self.assertIsNone(result)
        self.driver.cert_manager.get_secret.assert_not_called()

        # Test the secret process
        sample_listener = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True)
        fake_context = 'fake context'
        fake_secret = b'fake cert'
        mock_oslo.return_value = fake_context
        self.driver.cert_manager.get_secret.reset_mock()
        self.driver.cert_manager.get_secret.return_value = fake_secret
        ref_md5 = hashlib.md5(fake_secret).hexdigest()  # nosec
        ref_id = hashlib.sha1(fake_secret).hexdigest()  # nosec
        ref_name = '{id}.pem'.format(id=ref_id)

        result = self.driver._process_secret(
            sample_listener, sample_listener.client_ca_tls_certificate_id,
            self.amp, sample_listener.id)

        mock_oslo.assert_called_once_with(
            project_id=sample_listener.project_id)
        self.driver.cert_manager.get_secret.assert_called_once_with(
            fake_context, sample_listener.client_ca_tls_certificate_id)
        mock_upload_cert.assert_called_once_with(
            self.amp, sample_listener.id, pem=fake_secret,
            md5=ref_md5, name=ref_name)
        self.assertEqual(ref_name, result)

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_pool_certs')
    def test__process_listener_pool_certs(self, mock_pool_cert):
        sample_listener = sample_configs_combined.sample_listener_tuple(
            l7=True)

        ref_pool_cert_1 = {'client_cert': '/some/fake/cert-1.pem'}
        ref_pool_cert_2 = {'client_cert': '/some/fake/cert-2.pem'}

        mock_pool_cert.side_effect = [ref_pool_cert_1, ref_pool_cert_2]

        ref_cert_dict = {'sample_pool_id_1': ref_pool_cert_1,
                         'sample_pool_id_2': ref_pool_cert_2}

        result = self.driver._process_listener_pool_certs(
            sample_listener, self.amp, sample_listener.load_balancer.id)

        pool_certs_calls = [
            mock.call(sample_listener, sample_listener.default_pool,
                      self.amp, sample_listener.load_balancer.id),
            mock.call(sample_listener, sample_listener.pools[1],
                      self.amp, sample_listener.load_balancer.id)
        ]

        mock_pool_cert.assert_has_calls(pool_certs_calls, any_order=True)

        self.assertEqual(ref_cert_dict, result)

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_secret')
    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._upload_cert')
    @mock.patch('octavia.common.tls_utils.cert_parser.build_pem')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test__process_pool_certs(self, mock_load_certs, mock_build_pem,
                                 mock_upload_cert, mock_secret):
        fake_cert_dir = '/fake/cert/dir'
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="haproxy_amphora", base_cert_dir=fake_cert_dir)
        sample_listener = sample_configs_combined.sample_listener_tuple(
            pool_cert=True, pool_ca_cert=True, pool_crl=True)
        cert_data_mock = mock.MagicMock()
        cert_data_mock.id = uuidutils.generate_uuid()
        mock_load_certs.return_value = cert_data_mock
        fake_pem = b'fake pem'
        mock_build_pem.return_value = fake_pem
        ref_md5 = hashlib.md5(fake_pem).hexdigest()  # nosec
        ref_name = '{id}.pem'.format(id=cert_data_mock.id)
        ref_path = '{cert_dir}/{list_id}/{name}'.format(
            cert_dir=fake_cert_dir, list_id=sample_listener.id, name=ref_name)
        ref_ca_name = 'fake_ca.pem'
        ref_ca_path = '{cert_dir}/{list_id}/{name}'.format(
            cert_dir=fake_cert_dir, list_id=sample_listener.id,
            name=ref_ca_name)
        ref_crl_name = 'fake_crl.pem'
        ref_crl_path = '{cert_dir}/{list_id}/{name}'.format(
            cert_dir=fake_cert_dir, list_id=sample_listener.id,
            name=ref_crl_name)
        ref_result = {'client_cert': ref_path, 'ca_cert': ref_ca_path,
                      'crl': ref_crl_path}
        mock_secret.side_effect = [ref_ca_name, ref_crl_name]

        result = self.driver._process_pool_certs(
            sample_listener, sample_listener.default_pool, self.amp,
            sample_listener.load_balancer.id)

        secret_calls = [
            mock.call(sample_listener,
                      sample_listener.default_pool.ca_tls_certificate_id,
                      self.amp, sample_listener.load_balancer.id),
            mock.call(sample_listener,
                      sample_listener.default_pool.crl_container_id,
                      self.amp, sample_listener.load_balancer.id)]

        mock_build_pem.assert_called_once_with(cert_data_mock)
        mock_upload_cert.assert_called_once_with(
            self.amp, sample_listener.load_balancer.id, pem=fake_pem,
            md5=ref_md5, name=ref_name)
        mock_secret.assert_has_calls(secret_calls)
        self.assertEqual(ref_result, result)

    def test_start(self):
        amp1 = mock.MagicMock()
        amp1.api_version = API_VERSION
        amp2 = mock.MagicMock()
        amp2.api_version = API_VERSION
        amp2.status = constants.DELETED
        loadbalancer = mock.MagicMock()
        loadbalancer.id = uuidutils.generate_uuid()
        loadbalancer.amphorae = [amp1, amp2]
        loadbalancer.vip = self.sv
        listener = mock.MagicMock()
        listener.id = uuidutils.generate_uuid()
        listener.protocol = constants.PROTOCOL_HTTP
        loadbalancer.listeners = [listener]
        listener.load_balancer = loadbalancer
        self.driver.clients[
            API_VERSION].start_listener.__name__ = 'start_listener'
        # Execute driver method
        self.driver.start(loadbalancer)
        self.driver.clients[
            API_VERSION].start_listener.assert_called_once_with(
            amp1, loadbalancer.id)

    def test_start_with_amphora(self):
        # Execute driver method
        amp = mock.MagicMock()
        self.driver.clients[
            API_VERSION].start_listener.__name__ = 'start_listener'
        self.driver.start(self.lb, self.amp)
        self.driver.clients[
            API_VERSION].start_listener.assert_called_once_with(
            self.amp, self.lb.id)

        self.driver.clients[API_VERSION].start_listener.reset_mock()
        amp.status = constants.DELETED
        self.driver.start(self.lb, amp)
        self.driver.clients[API_VERSION].start_listener.assert_not_called()

    def test_udp_start(self):
        self.driver.clients[
            API_VERSION].start_listener.__name__ = 'start_listener'
        # Execute driver method
        self.driver.start(self.lb_udp)
        self.driver.clients[
            API_VERSION].start_listener.assert_called_once_with(
            self.amp, self.sl_udp.id)

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_secret')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.get_host_names')
    def test_delete_second_listener(self, mock_cert, mock_load_crt,
                                    mock_secret):
        self.driver.clients[
            API_VERSION].delete_listener.__name__ = 'delete_listener'
        sl = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True, client_crl_cert=True,
            recursive_nest=True)
        sl2 = sample_configs_combined.sample_listener_tuple(
            id='sample_listener_id_2')
        sl.load_balancer.listeners.append(sl2)
        mock_cert.return_value = {'cn': sample_certs.X509_CERT_CN}
        mock_secret.side_effect = ['filename.pem', 'crl-filename.pem']
        sconts = []
        for sni_container in self.sl.sni_containers:
            sconts.append(sni_container.tls_container)
        mock_load_crt.side_effect = [{
            'tls_cert': self.sl.default_tls_container, 'sni_certs': sconts},
            {'tls_cert': None, 'sni_certs': []}]
        self.driver.jinja_combo.build_config.side_effect = ['fake_config']
        # Execute driver method
        self.driver.delete(sl)

        # All of the pem files should be removed
        dcp_calls = [
            mock.call(self.amp, sl.load_balancer.id,
                      self.sl.default_tls_container.id + '.pem'),
            mock.call(self.amp, sl.load_balancer.id, sconts[0].id + '.pem'),
            mock.call(self.amp, sl.load_balancer.id, sconts[1].id + '.pem'),
        ]
        self.driver.clients[API_VERSION].delete_cert_pem.assert_has_calls(
            dcp_calls, any_order=True)

        # Now just make sure we did an update and not a delete
        self.driver.clients[API_VERSION].delete_listener.assert_not_called()
        self.driver.clients[API_VERSION].upload_config.assert_called_once_with(
            self.amp, sl.load_balancer.id, 'fake_config', timeout_dict=None)
        # start should be called once
        self.driver.clients[
            API_VERSION].reload_listener.assert_called_once_with(
            self.amp, sl.load_balancer.id, timeout_dict=None)

    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.'
                'HaproxyAmphoraLoadBalancerDriver._process_secret')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.get_host_names')
    def test_delete_second_listener_active_standby(self, mock_cert,
                                                   mock_load_crt,
                                                   mock_secret):
        self.driver.clients[
            API_VERSION].delete_listener.__name__ = 'delete_listener'
        sl = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True, client_crl_cert=True,
            recursive_nest=True, topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        sl2 = sample_configs_combined.sample_listener_tuple(
            id='sample_listener_id_2',
            topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        sl.load_balancer.listeners.append(sl2)
        mock_cert.return_value = {'cn': sample_certs.X509_CERT_CN}
        mock_secret.side_effect = ['filename.pem', 'crl-filename.pem',
                                   'filename.pem', 'crl-filename.pem']
        sconts = []
        for sni_container in self.sl.sni_containers:
            sconts.append(sni_container.tls_container)
        mock_load_crt.side_effect = [{
            'tls_cert': self.sl.default_tls_container, 'sni_certs': sconts},
            {'tls_cert': None, 'sni_certs': []},
            {'tls_cert': None, 'sni_certs': []},
            {'tls_cert': None, 'sni_certs': []}]
        self.driver.jinja_combo.build_config.side_effect = [
            'fake_config', 'fake_config']
        # Execute driver method
        self.driver.delete(sl)

        amp1 = sl.load_balancer.amphorae[0]
        amp2 = sl.load_balancer.amphorae[1]

        # All of the pem files should be removed (using amp1 or amp2)
        dcp_calls_list = [
            [
                mock.call(amp1, sl.load_balancer.id,
                          sl.default_tls_container.id + '.pem'),
                mock.call(amp2, sl.load_balancer.id,
                          sl.default_tls_container.id + '.pem')
            ],
            [
                mock.call(amp1, sl.load_balancer.id, sconts[0].id + '.pem'),
                mock.call(amp2, sl.load_balancer.id, sconts[0].id + '.pem')
            ],
            [
                mock.call(amp1, sl.load_balancer.id, sconts[1].id + '.pem'),
                mock.call(amp2, sl.load_balancer.id, sconts[1].id + '.pem')
            ]
        ]
        mock_calls = (
            self.driver.clients[API_VERSION].delete_cert_pem.mock_calls)
        for dcp_calls in dcp_calls_list:
            # Ensure that at least one call in each pair has been seen
            if (dcp_calls[0] not in mock_calls and
                    dcp_calls[1] not in mock_calls):
                raise Exception("%s not found in %s" % (dcp_calls, mock_calls))

        # Now just make sure we did an update and not a delete
        self.driver.clients[API_VERSION].delete_listener.assert_not_called()
        upload_config_calls = [
            mock.call(amp1, sl.load_balancer.id, 'fake_config',
                      timeout_dict=None),
            mock.call(amp2, sl.load_balancer.id, 'fake_config',
                      timeout_dict=None)
        ]
        self.driver.clients[API_VERSION].upload_config.assert_has_calls(
            upload_config_calls, any_order=True)

        # start should be called once per amp
        reload_listener_calls = [
            mock.call(amp1, sl.load_balancer.id, timeout_dict=None),
            mock.call(amp2, sl.load_balancer.id, timeout_dict=None)
        ]
        self.driver.clients[
            API_VERSION].reload_listener.assert_has_calls(
                reload_listener_calls, any_order=True)

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_delete_last_listener(self, mock_load_crt):
        self.driver.clients[
            API_VERSION].delete_listener.__name__ = 'delete_listener'
        sl = sample_configs_combined.sample_listener_tuple(
            tls=True, sni=True, client_ca_cert=True, client_crl_cert=True,
            recursive_nest=True)
        mock_load_crt.side_effect = [{
            'tls_cert': sl.default_tls_container, 'sni_certs': None}]
        # Execute driver method
        self.driver.delete(sl)
        self.driver.clients[
            API_VERSION].delete_listener.assert_called_once_with(
            self.amp, sl.load_balancer.id)

    def test_udp_delete(self):
        self.driver.clients[
            API_VERSION].delete_listener.__name__ = 'delete_listener'
        # Execute driver method
        self.driver.delete(self.sl_udp)
        self.driver.clients[
            API_VERSION].delete_listener.assert_called_once_with(
            self.amp, self.sl_udp.id)

    def test_get_info(self):
        expected_info = {'haproxy_version': '1.6.3-1ubuntu0.1',
                         'api_version': '1.0'}
        result = self.driver.get_info(self.amp)
        self.assertEqual(expected_info, result)

    def test_get_diagnostics(self):
        # TODO(johnsom) Implement once this exists on the amphora agent.
        result = self.driver.get_diagnostics(self.amp)
        self.assertIsNone(result)

    def test_finalize_amphora(self):
        # TODO(johnsom) Implement once this exists on the amphora agent.
        result = self.driver.finalize_amphora(self.amp)
        self.assertIsNone(result)

    def test_post_vip_plug(self):
        amphorae_network_config = mock.MagicMock()
        amphorae_network_config.get().vip_subnet.cidr = FAKE_CIDR
        amphorae_network_config.get().vip_subnet.gateway_ip = FAKE_GATEWAY
        amphorae_network_config.get().vip_subnet.host_routes = self.host_routes
        amphorae_network_config.get().vrrp_port = self.port
        self.driver.post_vip_plug(self.amp, self.lb, amphorae_network_config)
        self.driver.clients[API_VERSION].plug_vip.assert_called_once_with(
            self.amp, self.lb.vip.ip_address, self.subnet_info)

    def test_post_network_plug(self):
        # Test dhcp path
        port = network_models.Port(mac_address=FAKE_MAC_ADDRESS,
                                   fixed_ips=[],
                                   network=self.network)
        self.driver.post_network_plug(self.amp, port)
        self.driver.clients[API_VERSION].plug_network.assert_called_once_with(
            self.amp, dict(mac_address=FAKE_MAC_ADDRESS,
                           fixed_ips=[],
                           mtu=FAKE_MTU))

        self.driver.clients[API_VERSION].plug_network.reset_mock()

        # Test fixed IP path
        self.driver.post_network_plug(self.amp, self.port)
        self.driver.clients[API_VERSION].plug_network.assert_called_once_with(
            self.amp, dict(mac_address=FAKE_MAC_ADDRESS,
                           fixed_ips=[dict(ip_address='198.51.100.5',
                                           subnet_cidr='198.51.100.0/24',
                                           host_routes=[])],
                           mtu=FAKE_MTU))

    def test_post_network_plug_with_host_routes(self):
        SUBNET_ID = 'SUBNET_ID'
        FIXED_IP1 = '192.0.2.2'
        FIXED_IP2 = '192.0.2.3'
        SUBNET_CIDR = '192.0.2.0/24'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        NEXTHOP = '192.0.2.1'
        host_routes = [network_models.HostRoute(destination=DEST1,
                                                nexthop=NEXTHOP),
                       network_models.HostRoute(destination=DEST2,
                                                nexthop=NEXTHOP)]
        subnet = network_models.Subnet(id=SUBNET_ID, cidr=SUBNET_CIDR,
                                       ip_version=4, host_routes=host_routes)
        fixed_ips = [
            network_models.FixedIP(subnet_id=subnet.id, ip_address=FIXED_IP1,
                                   subnet=subnet),
            network_models.FixedIP(subnet_id=subnet.id, ip_address=FIXED_IP2,
                                   subnet=subnet)
        ]
        port = network_models.Port(mac_address=FAKE_MAC_ADDRESS,
                                   fixed_ips=fixed_ips,
                                   network=self.network)
        self.driver.post_network_plug(self.amp, port)
        expected_fixed_ips = [
            {'ip_address': FIXED_IP1, 'subnet_cidr': SUBNET_CIDR,
             'host_routes': [{'destination': DEST1, 'nexthop': NEXTHOP},
                             {'destination': DEST2, 'nexthop': NEXTHOP}]},
            {'ip_address': FIXED_IP2, 'subnet_cidr': SUBNET_CIDR,
             'host_routes': [{'destination': DEST1, 'nexthop': NEXTHOP},
                             {'destination': DEST2, 'nexthop': NEXTHOP}]}
        ]
        self.driver.clients[API_VERSION].plug_network.assert_called_once_with(
            self.amp, dict(mac_address=FAKE_MAC_ADDRESS,
                           fixed_ips=expected_fixed_ips,
                           mtu=FAKE_MTU))

    def test_get_vrrp_interface(self):
        self.driver.get_vrrp_interface(self.amp)
        self.driver.clients[API_VERSION].get_interface.assert_called_once_with(
            self.amp, self.amp.vrrp_ip, timeout_dict=None)

    def test_get_haproxy_versions(self):
        ref_haproxy_versions = ['1', '6']
        result = self.driver._get_haproxy_versions(self.amp)
        self.driver.clients[API_VERSION].get_info.assert_called_once_with(
            self.amp)
        self.assertEqual(ref_haproxy_versions, result)

    def test_populate_amphora_api_version(self):

        # Normal path, populate the version
        # clear out any previous values
        ref_haproxy_version = list(map(int, API_VERSION.split('.')))
        mock_amp = mock.MagicMock()
        mock_amp.api_version = None
        result = self.driver._populate_amphora_api_version(mock_amp)
        self.assertEqual(API_VERSION, mock_amp.api_version)
        self.assertEqual(ref_haproxy_version, result)

        # Existing version passed in
        fake_version = '9999.9999'
        ref_haproxy_version = list(map(int, fake_version.split('.')))
        mock_amp = mock.MagicMock()
        mock_amp.api_version = fake_version
        result = self.driver._populate_amphora_api_version(mock_amp)
        self.assertEqual(fake_version, mock_amp.api_version)
        self.assertEqual(ref_haproxy_version, result)

    def test_update_amphora_agent_config(self):
        self.driver.update_amphora_agent_config(self.amp, six.b('test'))
        self.driver.clients[
            API_VERSION].update_agent_config.assert_called_once_with(
            self.amp, six.b('test'), timeout_dict=None)


class TestAmphoraAPIClientTest(base.TestCase):

    def setUp(self):
        super(TestAmphoraAPIClientTest, self).setUp()
        self.driver = driver.AmphoraAPIClient1_0()
        self.base_url = "https://192.0.2.77:9443/"
        self.base_url_ver = self.base_url + "1.0"
        self.amp = models.Amphora(lb_network_ip='192.0.2.77', compute_id='123')
        self.amp.api_version = API_VERSION
        self.port_info = dict(mac_address=FAKE_MAC_ADDRESS)
        # Override with much lower values for testing purposes..
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="haproxy_amphora", connection_max_retries=2)

        self.subnet_info = {'subnet_cidr': FAKE_CIDR,
                            'gateway': FAKE_GATEWAY,
                            'mac_address': FAKE_MAC_ADDRESS,
                            'vrrp_ip': self.amp.vrrp_ip}
        patcher = mock.patch('time.sleep').start()
        self.addCleanup(patcher.stop)
        self.timeout_dict = {constants.REQ_CONN_TIMEOUT: 1,
                             constants.REQ_READ_TIMEOUT: 2,
                             constants.CONN_MAX_RETRIES: 3,
                             constants.CONN_RETRY_INTERVAL: 4}

    def test_base_url(self):
        url = self.driver._base_url(FAKE_IP)
        self.assertEqual('https://192.0.2.10:9443/', url)
        url = self.driver._base_url(FAKE_IPV6, self.amp.api_version)
        self.assertEqual('https://[2001:db8::cafe]:9443/1.0/', url)
        url = self.driver._base_url(FAKE_IPV6_LLA, self.amp.api_version)
        self.assertEqual('https://[fe80::00ff:fe00:cafe%o-hm0]:9443/1.0/', url)

    @mock.patch('requests.Session.get', side_effect=requests.ConnectionError)
    @mock.patch('octavia.amphorae.drivers.haproxy.rest_api_driver.time.sleep')
    def test_request(self, mock_sleep, mock_get):
        self.assertRaises(driver_except.TimeOutException,
                          self.driver.request, 'get', self.amp,
                          'unavailableURL', self.timeout_dict)

    @requests_mock.mock()
    def test_get_api_version(self, mock_requests):
        ref_api_version = {'api_version': '0.1'}
        mock_requests.get('{base}/'.format(base=self.base_url),
                          json=ref_api_version)
        result = self.driver.get_api_version(self.amp)
        self.assertEqual(ref_api_version, result)

    @requests_mock.mock()
    def test_get_info(self, m):
        info = {"hostname": "some_hostname", "version": "some_version",
                "api_version": "0.5", "uuid": FAKE_UUID_1}
        m.get("{base}/info".format(base=self.base_url_ver),
              json=info)
        information = self.driver.get_info(self.amp)
        self.assertEqual(info, information)

    @requests_mock.mock()
    def test_get_info_unauthorized(self, m):
        m.get("{base}/info".format(base=self.base_url_ver),
              status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_info, self.amp)

    @requests_mock.mock()
    def test_get_info_missing(self, m):
        m.get("{base}/info".format(base=self.base_url_ver),
              status_code=404,
              headers={'content-type': 'application/json'})
        self.assertRaises(exc.NotFound, self.driver.get_info, self.amp)

    @requests_mock.mock()
    def test_get_info_server_error(self, m):
        m.get("{base}/info".format(base=self.base_url_ver),
              status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.get_info,
                          self.amp)

    @requests_mock.mock()
    def test_get_info_service_unavailable(self, m):
        m.get("{base}/info".format(base=self.base_url_ver),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.get_info,
                          self.amp)

    @requests_mock.mock()
    def test_get_details(self, m):
        details = {"hostname": "some_hostname", "version": "some_version",
                   "api_version": "0.5", "uuid": FAKE_UUID_1,
                   "network_tx": "some_tx", "network_rx": "some_rx",
                   "active": True, "haproxy_count": 10}
        m.get("{base}/details".format(base=self.base_url_ver),
              json=details)
        amp_details = self.driver.get_details(self.amp)
        self.assertEqual(details, amp_details)

    @requests_mock.mock()
    def test_get_details_unauthorized(self, m):
        m.get("{base}/details".format(base=self.base_url_ver),
              status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_details, self.amp)

    @requests_mock.mock()
    def test_get_details_missing(self, m):
        m.get("{base}/details".format(base=self.base_url_ver),
              status_code=404,
              headers={'content-type': 'application/json'})
        self.assertRaises(exc.NotFound, self.driver.get_details, self.amp)

    @requests_mock.mock()
    def test_get_details_server_error(self, m):
        m.get("{base}/details".format(base=self.base_url_ver),
              status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.get_details,
                          self.amp)

    @requests_mock.mock()
    def test_get_details_service_unavailable(self, m):
        m.get("{base}/details".format(base=self.base_url_ver),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.get_details,
                          self.amp)

    @requests_mock.mock()
    def test_get_all_listeners(self, m):
        listeners = [{"status": "ONLINE", "provisioning_status": "ACTIVE",
                      "type": "PASSIVE", "uuid": FAKE_UUID_1}]
        m.get("{base}/listeners".format(base=self.base_url_ver),
              json=listeners)
        all_listeners = self.driver.get_all_listeners(self.amp)
        self.assertEqual(listeners, all_listeners)

    @requests_mock.mock()
    def test_get_all_listeners_unauthorized(self, m):
        m.get("{base}/listeners".format(base=self.base_url_ver),
              status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_all_listeners,
                          self.amp)

    @requests_mock.mock()
    def test_get_all_listeners_missing(self, m):
        m.get("{base}/listeners".format(base=self.base_url_ver),
              status_code=404,
              headers={'content-type': 'application/json'})
        self.assertRaises(exc.NotFound, self.driver.get_all_listeners,
                          self.amp)

    @requests_mock.mock()
    def test_get_all_listeners_server_error(self, m):
        m.get("{base}/listeners".format(base=self.base_url_ver),
              status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.get_all_listeners, self.amp)

    @requests_mock.mock()
    def test_get_all_listeners_service_unavailable(self, m):
        m.get("{base}/listeners".format(base=self.base_url_ver),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable,
                          self.driver.get_all_listeners, self.amp)

    @requests_mock.mock()
    def test_start_loadbalancer(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/start".format(
            base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1))
        self.driver.start_listener(self.amp, FAKE_UUID_1)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_start_loadbalancer_missing(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/start".format(
            base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1),
            status_code=404,
            headers={'content-type': 'application/json'})
        self.assertRaises(exc.NotFound, self.driver.start_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_start_loadbalancer_unauthorized(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/start".format(
            base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1),
            status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.start_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_start_loadbalancer_server_error(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/start".format(
            base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1),
            status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.start_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_start_loadbalancer_service_unavailable(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/start".format(
            base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1),
            status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.start_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_delete_listener(self, m):
        m.delete("{base}/listeners/{listener_id}".format(
            base=self.base_url_ver, listener_id=FAKE_UUID_1), json={})
        self.driver.delete_listener(self.amp, FAKE_UUID_1)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_delete_listener_missing(self, m):
        m.delete("{base}/listeners/{listener_id}".format(
            base=self.base_url_ver, listener_id=FAKE_UUID_1),
            status_code=404,
            headers={'content-type': 'application/json'})
        self.driver.delete_listener(self.amp, FAKE_UUID_1)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_delete_listener_unauthorized(self, m):
        m.delete("{base}/listeners/{listener_id}".format(
            base=self.base_url_ver, listener_id=FAKE_UUID_1),
            status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.delete_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_delete_listener_server_error(self, m):
        m.delete("{base}/listeners/{listener_id}".format(
            base=self.base_url_ver, listener_id=FAKE_UUID_1),
            status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.delete_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_delete_listener_service_unavailable(self, m):
        m.delete("{base}/listeners/{listener_id}".format(
            base=self.base_url_ver, listener_id=FAKE_UUID_1),
            status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.delete_listener,
                          self.amp, FAKE_UUID_1)

    @requests_mock.mock()
    def test_upload_cert_pem(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME))
        self.driver.upload_cert_pem(self.amp, FAKE_UUID_1,
                                    FAKE_PEM_FILENAME,
                                    "some_file")
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_upload_invalid_cert_pem(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.upload_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME,
                          "some_file")

    @requests_mock.mock()
    def test_upload_cert_pem_unauthorized(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.upload_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME,
                          "some_file")

    @requests_mock.mock()
    def test_upload_cert_pem_server_error(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.upload_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME,
                          "some_file")

    @requests_mock.mock()
    def test_upload_cert_pem_service_unavailable(self, m):
        m.put("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.upload_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME,
                          "some_file")

    @requests_mock.mock()
    def test_update_cert_for_rotation(self, m):
        m.put("{base}/certificate".format(base=self.base_url_ver))
        resp_body = self.driver.update_cert_for_rotation(self.amp,
                                                         "some_file")
        self.assertEqual(200, resp_body.status_code)

    @requests_mock.mock()
    def test_update_invalid_cert_for_rotation(self, m):
        m.put("{base}/certificate".format(base=self.base_url_ver),
              status_code=400)
        self.assertRaises(exc.InvalidRequest,
                          self.driver.update_cert_for_rotation, self.amp,
                          "some_file")

    @requests_mock.mock()
    def test_update_cert_for_rotation_unauthorized(self, m):
        m.put("{base}/certificate".format(base=self.base_url_ver),
              status_code=401)
        self.assertRaises(exc.Unauthorized,
                          self.driver.update_cert_for_rotation, self.amp,
                          "some_file")

    @requests_mock.mock()
    def test_update_cert_for_rotation_error(self, m):
        m.put("{base}/certificate".format(base=self.base_url_ver),
              status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.update_cert_for_rotation, self.amp,
                          "some_file")

    @requests_mock.mock()
    def test_update_cert_for_rotation_unavailable(self, m):
        m.put("{base}/certificate".format(base=self.base_url_ver),
              status_code=503)
        self.assertRaises(exc.ServiceUnavailable,
                          self.driver.update_cert_for_rotation, self.amp,
                          "some_file")

    @requests_mock.mock()
    def test_get_cert_5sum(self, m):
        md5sum = {"md5sum": "some_real_sum"}
        m.get("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), json=md5sum)
        sum_test = self.driver.get_cert_md5sum(self.amp, FAKE_UUID_1,
                                               FAKE_PEM_FILENAME)
        self.assertIsNotNone(sum_test)

    @requests_mock.mock()
    def test_get_cert_5sum_missing(self, m):
        m.get("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=404,
              headers={'content-type': 'application/json'})
        self.assertRaises(exc.NotFound, self.driver.get_cert_md5sum,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_get_cert_5sum_unauthorized(self, m):
        m.get("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.get_cert_md5sum,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_get_cert_5sum_server_error(self, m):
        m.get("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.get_cert_md5sum,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_get_cert_5sum_service_unavailable(self, m):
        m.get("{base}/loadbalancer/{loadbalancer_id}/certificates/"
              "{filename}".format(
                  base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                  filename=FAKE_PEM_FILENAME), status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.get_cert_md5sum,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_delete_cert_pem(self, m):
        m.delete(
            "{base}/loadbalancer/{loadbalancer_id}/certificates/"
            "{filename}".format(
                base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                filename=FAKE_PEM_FILENAME))
        self.driver.delete_cert_pem(self.amp, FAKE_UUID_1,
                                    FAKE_PEM_FILENAME)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_delete_cert_pem_missing(self, m):
        m.delete(
            "{base}/loadbalancer/{loadbalancer_id}/certificates/"
            "{filename}".format(
                base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                filename=FAKE_PEM_FILENAME), status_code=404,
            headers={'content-type': 'application/json'})
        self.driver.delete_cert_pem(self.amp, FAKE_UUID_1,
                                    FAKE_PEM_FILENAME)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_delete_cert_pem_unauthorized(self, m):
        m.delete(
            "{base}/loadbalancer/{loadbalancer_id}/certificates/"
            "{filename}".format(
                base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                filename=FAKE_PEM_FILENAME), status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.delete_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_delete_cert_pem_server_error(self, m):
        m.delete(
            "{base}/loadbalancer/{loadbalancer_id}/certificates/"
            "{filename}".format(
                base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                filename=FAKE_PEM_FILENAME), status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.delete_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_delete_cert_pem_service_unavailable(self, m):
        m.delete(
            "{base}/loadbalancer/{loadbalancer_id}/certificates/"
            "{filename}".format(
                base=self.base_url_ver, loadbalancer_id=FAKE_UUID_1,
                filename=FAKE_PEM_FILENAME), status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.delete_cert_pem,
                          self.amp, FAKE_UUID_1, FAKE_PEM_FILENAME)

    @requests_mock.mock()
    def test_upload_config(self, m):
        config = {"name": "fake_config"}
        m.put(
            "{base}/loadbalancer/{"
            "amphora_id}/{loadbalancer_id}/haproxy".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                loadbalancer_id=FAKE_UUID_1),
            json=config)
        self.driver.upload_config(self.amp, FAKE_UUID_1,
                                  config)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_upload_invalid_config(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/loadbalancer/{"
            "amphora_id}/{loadbalancer_id}/haproxy".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                loadbalancer_id=FAKE_UUID_1),
            status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.upload_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_config_unauthorized(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/loadbalancer/{"
            "amphora_id}/{loadbalancer_id}/haproxy".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                loadbalancer_id=FAKE_UUID_1),
            status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.upload_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_config_server_error(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/loadbalancer/{"
            "amphora_id}/{loadbalancer_id}/haproxy".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                loadbalancer_id=FAKE_UUID_1),
            status_code=500)
        self.assertRaises(exc.InternalServerError, self.driver.upload_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_config_service_unavailable(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/loadbalancer/{"
            "amphora_id}/{loadbalancer_id}/haproxy".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                loadbalancer_id=FAKE_UUID_1),
            status_code=503)
        self.assertRaises(exc.ServiceUnavailable, self.driver.upload_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_udp_config(self, m):
        config = {"name": "fake_config"}
        m.put(
            "{base}/listeners/"
            "{amphora_id}/{listener_id}/udp_listener".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                listener_id=FAKE_UUID_1),
            json=config)
        self.driver.upload_udp_config(self.amp, FAKE_UUID_1, config)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_upload_udp_invalid_config(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/listeners/"
            "{amphora_id}/{listener_id}/udp_listener".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                listener_id=FAKE_UUID_1),
            status_code=400)
        self.assertRaises(exc.InvalidRequest, self.driver.upload_udp_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_udp_config_unauthorized(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/listeners/"
            "{amphora_id}/{listener_id}/udp_listener".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                listener_id=FAKE_UUID_1),
            status_code=401)
        self.assertRaises(exc.Unauthorized, self.driver.upload_udp_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_udp_config_server_error(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/listeners/"
            "{amphora_id}/{listener_id}/udp_listener".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                listener_id=FAKE_UUID_1),
            status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.upload_udp_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_upload_udp_config_service_unavailable(self, m):
        config = '{"name": "bad_config"}'
        m.put(
            "{base}/listeners/"
            "{amphora_id}/{listener_id}/udp_listener".format(
                amphora_id=self.amp.id, base=self.base_url_ver,
                listener_id=FAKE_UUID_1),
            status_code=503)
        self.assertRaises(exc.ServiceUnavailable,
                          self.driver.upload_udp_config,
                          self.amp, FAKE_UUID_1, config)

    @requests_mock.mock()
    def test_plug_vip(self, m):
        m.post("{base}/plug/vip/{vip}".format(
            base=self.base_url_ver, vip=FAKE_IP)
        )
        self.driver.plug_vip(self.amp, FAKE_IP, self.subnet_info)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_plug_vip_api_not_ready(self, m):
        m.post("{base}/plug/vip/{vip}".format(
            base=self.base_url_ver, vip=FAKE_IP),
            status_code=404, headers={'content-type': 'text/html'}
        )
        self.assertRaises(driver_except.TimeOutException,
                          self.driver.plug_vip,
                          self.amp, FAKE_IP, self.subnet_info)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_plug_network(self, m):
        m.post("{base}/plug/network".format(
            base=self.base_url_ver)
        )
        self.driver.plug_network(self.amp, self.port_info)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_upload_vrrp_config(self, m):
        config = '{"name": "bad_config"}'
        m.put("{base}/vrrp/upload".format(
            base=self.base_url_ver)
        )
        self.driver.upload_vrrp_config(self.amp, config)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_vrrp_action(self, m):
        action = 'start'
        m.put("{base}/vrrp/{action}".format(base=self.base_url_ver,
              action=action))
        self.driver._vrrp_action(action, self.amp)
        self.assertTrue(m.called)

    @requests_mock.mock()
    def test_get_interface(self, m):
        interface = [{"interface": "eth1"}]
        ip_addr = '192.51.100.1'
        m.get("{base}/interface/{ip_addr}".format(base=self.base_url_ver,
                                                  ip_addr=ip_addr),
              json=interface)
        self.driver.get_interface(self.amp, ip_addr)
        self.assertTrue(m.called)

        m.register_uri('GET',
                       self.base_url_ver + '/interface/' + ip_addr,
                       status_code=500, reason='FAIL', json='FAIL')
        self.assertRaises(exc.InternalServerError,
                          self.driver.get_interface,
                          self.amp, ip_addr)

    @requests_mock.mock()
    def test_update_agent_config(self, m):
        m.put("{base}/config".format(base=self.base_url_ver))
        resp_body = self.driver.update_agent_config(self.amp, "some_file")
        self.assertEqual(200, resp_body.status_code)

    @requests_mock.mock()
    def test_update_agent_config_error(self, m):
        m.put("{base}/config".format(base=self.base_url_ver), status_code=500)
        self.assertRaises(exc.InternalServerError,
                          self.driver.update_agent_config, self.amp,
                          "some_file")
