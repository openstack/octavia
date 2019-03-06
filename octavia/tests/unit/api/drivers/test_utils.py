#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy

import mock

from octavia.api.drivers import data_models as driver_dm
from octavia.api.drivers import exceptions as driver_exceptions
from octavia.api.drivers import utils
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.tests.unit.api.drivers import sample_data_models
from octavia.tests.unit import base


class TestUtils(base.TestCase):
    def setUp(self):
        super(TestUtils, self).setUp()
        self.sample_data = sample_data_models.SampleDriverDataModels()

    def test_call_provider(self):
        mock_driver_method = mock.MagicMock()

        # Test happy path
        utils.call_provider("provider_name", mock_driver_method,
                            "arg1", foo="arg2")
        mock_driver_method.assert_called_with("arg1", foo="arg2")

        # Test driver raising DriverError
        mock_driver_method.side_effect = driver_exceptions.DriverError
        self.assertRaises(exceptions.ProviderDriverError,
                          utils.call_provider, "provider_name",
                          mock_driver_method)

        # Test driver raising NotImplementedError
        mock_driver_method.side_effect = driver_exceptions.NotImplementedError
        self.assertRaises(exceptions.ProviderNotImplementedError,
                          utils.call_provider, "provider_name",
                          mock_driver_method)

        # Test driver raising UnsupportedOptionError
        mock_driver_method.side_effect = (
            driver_exceptions.UnsupportedOptionError)
        self.assertRaises(exceptions.ProviderUnsupportedOptionError,
                          utils.call_provider, "provider_name",
                          mock_driver_method)

        # Test driver raising DriverError
        mock_driver_method.side_effect = Exception
        self.assertRaises(exceptions.ProviderDriverError,
                          utils.call_provider, "provider_name",
                          mock_driver_method)

    def test_base_to_provider_dict(self):

        test_dict = {'provisioning_status': constants.ACTIVE,
                     'operating_status': constants.ONLINE,
                     'provider': 'octavia',
                     'created_at': 'now',
                     'updated_at': 'then',
                     'enabled': True,
                     'project_id': 1}

        result_dict = utils._base_to_provider_dict(test_dict,
                                                   include_project_id=True)
        self.assertEqual({'admin_state_up': True, 'project_id': 1},
                         result_dict)

        result_dict = utils._base_to_provider_dict(test_dict,
                                                   include_project_id=False)
        self.assertEqual({'admin_state_up': True},
                         result_dict)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_lb_dict_to_provider_dict(self, mock_load_cert, mock_secret):
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_secret.side_effect = ['X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE', 'ca cert',
                                   'X509 CRL FILE', 'ca cert', 'X509 CRL FILE',
                                   'X509 POOL CA CERT FILE',
                                   'X509 CRL FILE']
        listener_certs = {'tls_cert': cert1, 'sni_certs': [cert2, cert3]}
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        pool_certs = {'tls_cert': pool_cert, 'sni_certs': []}
        mock_load_cert.side_effect = [pool_certs, listener_certs,
                                      listener_certs, listener_certs,
                                      listener_certs]
        test_lb_dict = {'name': 'lb1',
                        'project_id': self.sample_data.project_id,
                        'vip_subnet_id': self.sample_data.subnet_id,
                        'vip_port_id': self.sample_data.port_id,
                        'vip_address': self.sample_data.ip_address,
                        'vip_network_id': self.sample_data.network_id,
                        'vip_qos_policy_id': self.sample_data.qos_policy_id,
                        'id': self.sample_data.lb_id,
                        'listeners': [],
                        'pools': [],
                        'description': '', 'admin_state_up': True,
                        'provisioning_status': constants.PENDING_CREATE,
                        'operating_status': constants.OFFLINE,
                        'flavor_id': '',
                        'provider': 'noop_driver'}
        ref_prov_lb_dict = {
            'vip_address': self.sample_data.ip_address,
            'admin_state_up': True,
            'loadbalancer_id': self.sample_data.lb_id,
            'vip_subnet_id': self.sample_data.subnet_id,
            'listeners': self.sample_data.provider_listeners,
            'description': '',
            'project_id': self.sample_data.project_id,
            'vip_port_id': self.sample_data.port_id,
            'vip_qos_policy_id': self.sample_data.qos_policy_id,
            'vip_network_id': self.sample_data.network_id,
            'pools': self.sample_data.provider_pools,
            'name': 'lb1'}
        vip = data_models.Vip(ip_address=self.sample_data.ip_address,
                              network_id=self.sample_data.network_id,
                              port_id=self.sample_data.port_id,
                              subnet_id=self.sample_data.subnet_id,
                              qos_policy_id=self.sample_data.qos_policy_id)

        provider_lb_dict = utils.lb_dict_to_provider_dict(
            test_lb_dict, vip=vip, db_pools=self.sample_data.test_db_pools,
            db_listeners=self.sample_data.test_db_listeners)

        self.assertEqual(ref_prov_lb_dict, provider_lb_dict)

    def test_db_loadbalancer_to_provider_loadbalancer(self):
        vip = data_models.Vip(ip_address=self.sample_data.ip_address,
                              network_id=self.sample_data.network_id,
                              port_id=self.sample_data.port_id,
                              subnet_id=self.sample_data.subnet_id)
        test_db_lb = data_models.LoadBalancer(id=1, vip=vip)
        provider_lb = utils.db_loadbalancer_to_provider_loadbalancer(
            test_db_lb)
        ref_provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=1,
            vip_address=self.sample_data.ip_address,
            vip_network_id=self.sample_data.network_id,
            vip_port_id=self.sample_data.port_id,
            vip_subnet_id=self.sample_data.subnet_id)
        self.assertEqual(ref_provider_lb.to_dict(render_unsets=True),
                         provider_lb.to_dict(render_unsets=True))

    def test_db_listener_to_provider_listener(self):
        test_db_list = data_models.Listener(id=1)
        provider_list = utils.db_listener_to_provider_listener(test_db_list)
        ref_provider_list = driver_dm.Listener(listener_id=1,
                                               insert_headers={})
        self.assertEqual(ref_provider_list.to_dict(render_unsets=True),
                         provider_list.to_dict(render_unsets=True))

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_db_listeners_to_provider_listeners(self, mock_load_cert,
                                                mock_secret):
        mock_secret.side_effect = ['ca cert', 'X509 CRL FILE',
                                   'ca cert', 'X509 CRL FILE',
                                   'ca cert', 'X509 CRL FILE']
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_load_cert.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        provider_listeners = utils.db_listeners_to_provider_listeners(
            self.sample_data.test_db_listeners)
        self.assertEqual(self.sample_data.provider_listeners,
                         provider_listeners)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_listener_dict_to_provider_dict(self, mock_load_cert, mock_secret):
        mock_secret.side_effect = ['ca cert', 'X509 CRL FILE',
                                   'X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE']
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        listener_certs = {'tls_cert': cert1, 'sni_certs': [cert2, cert3]}
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        pool_certs = {'tls_cert': pool_cert, 'sni_certs': []}
        mock_load_cert.side_effect = [listener_certs, pool_certs]
        # The reason to do this, as before the logic arrives the test func,
        # there are two data sources, one is from db_dict, the other is from
        # the api layer model_dict, actually, they are different and contain
        # different fields. That's why the test_listener1_dict from sample data
        # just contain the client_ca_tls_certificate_id for client certificate,
        # not any other related fields. So we need to delete them.
        expect_prov = copy.deepcopy(self.sample_data.provider_listener1_dict)
        expect_pool_prov = copy.deepcopy(self.sample_data.provider_pool1_dict)
        expect_prov['default_pool'] = expect_pool_prov
        provider_listener = utils.listener_dict_to_provider_dict(
            self.sample_data.test_listener1_dict)
        self.assertEqual(expect_prov, provider_listener)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_listener_dict_to_provider_dict_SNI(self, mock_load_cert,
                                                mock_secret):
        mock_secret.return_value = 'ca cert'
        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        mock_load_cert.return_value = {'tls_cert': cert1,
                                       'sni_certs': [cert2, cert3]}
        # Test with bad SNI content
        test_listener = copy.deepcopy(self.sample_data.test_listener1_dict)
        test_listener['sni_containers'] = [[]]
        self.assertRaises(exceptions.ValidationException,
                          utils.listener_dict_to_provider_dict,
                          test_listener)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_db_pool_to_provider_pool(self, mock_load_cert, mock_secret):
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        mock_load_cert.return_value = {'tls_cert': pool_cert,
                                       'sni_certs': None,
                                       'client_ca_cert': None}
        mock_secret.side_effect = ['X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE']
        provider_pool = utils.db_pool_to_provider_pool(
            self.sample_data.db_pool1)
        self.assertEqual(self.sample_data.provider_pool1, provider_pool)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_db_pool_to_provider_pool_partial(self, mock_load_cert,
                                              mock_secret):
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        mock_load_cert.return_value = {'tls_cert': pool_cert,
                                       'sni_certs': None,
                                       'client_ca_cert': None}
        mock_secret.side_effect = ['X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE']
        test_db_pool = self.sample_data.db_pool1
        test_db_pool.members = [self.sample_data.db_member1]
        provider_pool = utils.db_pool_to_provider_pool(test_db_pool)
        self.assertEqual(self.sample_data.provider_pool1, provider_pool)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_db_pools_to_provider_pools(self, mock_load_cert, mock_secret):
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        mock_load_cert.return_value = {'tls_cert': pool_cert,
                                       'sni_certs': None,
                                       'client_ca_cert': None}
        mock_secret.side_effect = ['X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE']
        provider_pools = utils.db_pools_to_provider_pools(
            self.sample_data.test_db_pools)
        self.assertEqual(self.sample_data.provider_pools, provider_pools)

    @mock.patch('octavia.api.drivers.utils._get_secret_data')
    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_pool_dict_to_provider_dict(self, mock_load_cert, mock_secret):
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        mock_load_cert.return_value = {'tls_cert': pool_cert,
                                       'sni_certs': None,
                                       'client_ca_cert': None}
        mock_secret.side_effect = ['X509 POOL CA CERT FILE',
                                   'X509 POOL CRL FILE']
        expect_prov = copy.deepcopy(self.sample_data.provider_pool1_dict)
        expect_prov.pop('crl_container_ref')
        provider_pool_dict = utils.pool_dict_to_provider_dict(
            self.sample_data.test_pool1_dict)
        provider_pool_dict.pop('crl_container_ref')
        self.assertEqual(expect_prov, provider_pool_dict)

    def test_db_HM_to_provider_HM(self):
        provider_hm = utils.db_HM_to_provider_HM(self.sample_data.db_hm1)
        self.assertEqual(self.sample_data.provider_hm1, provider_hm)

    def test_hm_dict_to_provider_dict(self):
        provider_hm_dict = utils.hm_dict_to_provider_dict(
            self.sample_data.test_hm1_dict)
        self.assertEqual(self.sample_data.provider_hm1_dict, provider_hm_dict)

    def test_HM_to_provider_HM_with_http_version_and_domain_name(self):
        provider_hm = utils.db_HM_to_provider_HM(self.sample_data.db_hm2)
        self.assertEqual(self.sample_data.provider_hm2, provider_hm)

        provider_hm_dict = utils.hm_dict_to_provider_dict(
            self.sample_data.test_hm2_dict)
        self.assertEqual(self.sample_data.provider_hm2_dict, provider_hm_dict)

    def test_hm_dict_to_provider_dict_partial(self):
        provider_hm_dict = utils.hm_dict_to_provider_dict({'id': 1})
        self.assertEqual({'healthmonitor_id': 1}, provider_hm_dict)

    def test_db_members_to_provider_members(self):
        provider_members = utils.db_members_to_provider_members(
            self.sample_data.db_pool1_members)
        self.assertEqual(self.sample_data.provider_pool1_members,
                         provider_members)

    def test_member_dict_to_provider_dict(self):
        provider_member_dict = utils.member_dict_to_provider_dict(
            self.sample_data.test_member1_dict)
        self.assertEqual(self.sample_data.provider_member1_dict,
                         provider_member_dict)

    def test_db_l7policies_to_provider_l7policies(self):
        provider_rules = utils.db_l7policies_to_provider_l7policies(
            self.sample_data.db_l7policies)
        self.assertEqual(self.sample_data.provider_l7policies, provider_rules)

    def test_l7policy_dict_to_provider_dict(self):
        provider_l7policy_dict = utils.l7policy_dict_to_provider_dict(
            self.sample_data.test_l7policy1_dict)
        self.assertEqual(self.sample_data.provider_l7policy1_dict,
                         provider_l7policy_dict)

    def test_db_l7rules_to_provider_l7rules(self):
        provider_rules = utils.db_l7rules_to_provider_l7rules(
            self.sample_data.db_l7Rules)
        self.assertEqual(self.sample_data.provider_rules, provider_rules)

    def test_l7rule_dict_to_provider_dict(self):
        provider_rules_dict = utils.l7rule_dict_to_provider_dict(
            self.sample_data.test_l7rule1_dict)
        self.assertEqual(self.sample_data.provider_l7rule1_dict,
                         provider_rules_dict)

    def test_vip_dict_to_provider_dict(self):
        new_vip_dict = utils.vip_dict_to_provider_dict(
            self.sample_data.test_vip_dict)
        self.assertEqual(self.sample_data.provider_vip_dict, new_vip_dict)

    def test_vip_dict_to_provider_dict_partial(self):
        new_vip_dict = utils.vip_dict_to_provider_dict(
            {'ip_address': '192.0.2.44'})
        self.assertEqual({'vip_address': '192.0.2.44'}, new_vip_dict)

    def test_provider_vip_dict_to_vip_obj(self):
        new_provider_vip = utils.provider_vip_dict_to_vip_obj(
            self.sample_data.provider_vip_dict)
        self.assertEqual(self.sample_data.db_vip, new_provider_vip)
