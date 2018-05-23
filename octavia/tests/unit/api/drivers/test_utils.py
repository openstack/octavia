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

from oslo_utils import uuidutils

from octavia.api.drivers import data_models as driver_dm
from octavia.api.drivers import exceptions as driver_exceptions
from octavia.api.drivers import utils
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.tests.unit import base


class TestUtils(base.TestCase):
    def setUp(self):
        super(TestUtils, self).setUp()

        hm1_id = uuidutils.generate_uuid()
        hm2_id = uuidutils.generate_uuid()
        l7policy1_id = uuidutils.generate_uuid()
        l7policy2_id = uuidutils.generate_uuid()
        l7rule1_id = uuidutils.generate_uuid()
        l7rule2_id = uuidutils.generate_uuid()
        listener1_id = uuidutils.generate_uuid()
        listener2_id = uuidutils.generate_uuid()
        member1_id = uuidutils.generate_uuid()
        member2_id = uuidutils.generate_uuid()
        member3_id = uuidutils.generate_uuid()
        member4_id = uuidutils.generate_uuid()
        pool1_id = uuidutils.generate_uuid()
        pool2_id = uuidutils.generate_uuid()
        self.lb_id = uuidutils.generate_uuid()
        self.project_id = uuidutils.generate_uuid()
        self.ip_address = '192.0.2.30'
        self.port_id = uuidutils.generate_uuid()
        self.network_id = uuidutils.generate_uuid()
        self.subnet_id = uuidutils.generate_uuid()
        self.qos_policy_id = uuidutils.generate_uuid()
        self.sni_containers = [{'tls_container_id': '2'},
                               {'tls_container_id': '3'}]

        _common_test_dict = {'provisioning_status': constants.ACTIVE,
                             'operating_status': constants.ONLINE,
                             'project_id': self.project_id,
                             'created_at': 'then',
                             'updated_at': 'now',
                             'enabled': True}

        # Setup Health Monitors
        self.test_hm1_dict = {'id': hm1_id,
                              'type': constants.HEALTH_MONITOR_PING,
                              'delay': 1, 'timeout': 3, 'fall_threshold': 1,
                              'rise_threshold': 2, 'http_method': 'GET',
                              'url_path': '/', 'expected_codes': '200',
                              'name': 'hm1', 'pool_id': pool1_id}

        self.test_hm1_dict.update(_common_test_dict)

        self.test_hm2_dict = copy.deepcopy(self.test_hm1_dict)
        self.test_hm2_dict['id'] = hm2_id
        self.test_hm2_dict['name'] = 'hm2'

        self.db_hm1 = data_models.HealthMonitor(**self.test_hm1_dict)
        self.db_hm2 = data_models.HealthMonitor(**self.test_hm2_dict)

        self.provider_hm1_dict = {'admin_state_up': True,
                                  'delay': 1, 'expected_codes': '200',
                                  'healthmonitor_id': hm1_id,
                                  'http_method': 'GET',
                                  'max_retries': 2,
                                  'max_retries_down': 1,
                                  'name': 'hm1',
                                  'pool_id': pool1_id,
                                  'timeout': 3,
                                  'type': constants.HEALTH_MONITOR_PING,
                                  'url_path': '/'}

        self.provider_hm2_dict = copy.deepcopy(self.provider_hm1_dict)
        self.provider_hm2_dict['healthmonitor_id'] = hm2_id
        self.provider_hm2_dict['name'] = 'hm2'

        self.provider_hm1 = driver_dm.HealthMonitor(**self.provider_hm1_dict)
        self.provider_hm2 = driver_dm.HealthMonitor(**self.provider_hm2_dict)

        # Setup Members
        self.test_member1_dict = {'id': member1_id,
                                  'pool_id': pool1_id,
                                  'ip_address': '192.0.2.16',
                                  'protocol_port': 80, 'weight': 0,
                                  'backup': False,
                                  'subnet_id': self.subnet_id,
                                  'pool': None,
                                  'name': 'member1',
                                  'monitor_address': '192.0.2.26',
                                  'monitor_port': 81}

        self.test_member1_dict.update(_common_test_dict)

        self.test_member2_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member2_dict['id'] = member2_id
        self.test_member2_dict['ip_address'] = '192.0.2.17'
        self.test_member2_dict['monitor_address'] = '192.0.2.27'
        self.test_member2_dict['name'] = 'member2'

        self.test_member3_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member3_dict['id'] = member3_id
        self.test_member3_dict['ip_address'] = '192.0.2.18'
        self.test_member3_dict['monitor_address'] = '192.0.2.28'
        self.test_member3_dict['name'] = 'member3'
        self.test_member3_dict['pool_id'] = pool2_id

        self.test_member4_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member4_dict['id'] = member4_id
        self.test_member4_dict['ip_address'] = '192.0.2.19'
        self.test_member4_dict['monitor_address'] = '192.0.2.29'
        self.test_member4_dict['name'] = 'member4'
        self.test_member4_dict['pool_id'] = pool2_id

        self.test_pool1_members_dict = [self.test_member1_dict,
                                        self.test_member2_dict]
        self.test_pool2_members_dict = [self.test_member3_dict,
                                        self.test_member4_dict]

        self.db_member1 = data_models.Member(**self.test_member1_dict)
        self.db_member2 = data_models.Member(**self.test_member2_dict)
        self.db_member3 = data_models.Member(**self.test_member3_dict)
        self.db_member4 = data_models.Member(**self.test_member4_dict)

        self.db_pool1_members = [self.db_member1, self.db_member2]
        self.db_pool2_members = [self.db_member3, self.db_member4]

        self.provider_member1_dict = {'address': '192.0.2.16',
                                      'admin_state_up': True,
                                      'member_id': member1_id,
                                      'monitor_address': '192.0.2.26',
                                      'monitor_port': 81,
                                      'name': 'member1',
                                      'pool_id': pool1_id,
                                      'protocol_port': 80,
                                      'subnet_id': self.subnet_id,
                                      'weight': 0,
                                      'backup': False}

        self.provider_member2_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member2_dict['member_id'] = member2_id
        self.provider_member2_dict['address'] = '192.0.2.17'
        self.provider_member2_dict['monitor_address'] = '192.0.2.27'
        self.provider_member2_dict['name'] = 'member2'

        self.provider_member3_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member3_dict['member_id'] = member3_id
        self.provider_member3_dict['address'] = '192.0.2.18'
        self.provider_member3_dict['monitor_address'] = '192.0.2.28'
        self.provider_member3_dict['name'] = 'member3'
        self.provider_member3_dict['pool_id'] = pool2_id

        self.provider_member4_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member4_dict['member_id'] = member4_id
        self.provider_member4_dict['address'] = '192.0.2.19'
        self.provider_member4_dict['monitor_address'] = '192.0.2.29'
        self.provider_member4_dict['name'] = 'member4'
        self.provider_member4_dict['pool_id'] = pool2_id

        self.provider_pool1_members_dict = [self.provider_member1_dict,
                                            self.provider_member2_dict]

        self.provider_pool2_members_dict = [self.provider_member3_dict,
                                            self.provider_member4_dict]

        self.provider_member1 = driver_dm.Member(**self.provider_member1_dict)
        self.provider_member2 = driver_dm.Member(**self.provider_member2_dict)
        self.provider_member3 = driver_dm.Member(**self.provider_member3_dict)
        self.provider_member4 = driver_dm.Member(**self.provider_member4_dict)

        self.provider_pool1_members = [self.provider_member1,
                                       self.provider_member2]
        self.provider_pool2_members = [self.provider_member3,
                                       self.provider_member4]

        # Setup test pools
        self.test_pool1_dict = {'id': pool1_id,
                                'name': 'pool1', 'description': 'Pool 1',
                                'load_balancer_id': self.lb_id,
                                'protocol': 'avian',
                                'lb_algorithm': 'round_robin',
                                'members': self.test_pool1_members_dict,
                                'health_monitor': self.test_hm1_dict,
                                'session_persistence': {'type': 'SOURCE'},
                                'listeners': [],
                                'l7policies': []}

        self.test_pool1_dict.update(_common_test_dict)

        self.test_pool2_dict = copy.deepcopy(self.test_pool1_dict)
        self.test_pool2_dict['id'] = pool2_id
        self.test_pool2_dict['name'] = 'pool2'
        self.test_pool2_dict['description'] = 'Pool 2'
        self.test_pool2_dict['members'] = self.test_pool2_members_dict

        self.test_pools = [self.test_pool1_dict, self.test_pool2_dict]

        self.db_pool1 = data_models.Pool(**self.test_pool1_dict)
        self.db_pool1.health_monitor = self.db_hm1
        self.db_pool1.members = self.db_pool1_members
        self.db_pool2 = data_models.Pool(**self.test_pool2_dict)
        self.db_pool2.health_monitor = self.db_hm2
        self.db_pool2.members = self.db_pool2_members

        self.test_db_pools = [self.db_pool1, self.db_pool2]

        self.provider_pool1_dict = {
            'admin_state_up': True,
            'description': 'Pool 1',
            'healthmonitor': self.provider_hm1_dict,
            'lb_algorithm': 'round_robin',
            'loadbalancer_id': self.lb_id,
            'members': self.provider_pool1_members_dict,
            'name': 'pool1',
            'pool_id': pool1_id,
            'protocol': 'avian',
            'session_persistence': {'type': 'SOURCE'}}

        self.provider_pool2_dict = copy.deepcopy(self.provider_pool1_dict)
        self.provider_pool2_dict['pool_id'] = pool2_id
        self.provider_pool2_dict['name'] = 'pool2'
        self.provider_pool2_dict['description'] = 'Pool 2'
        self.provider_pool2_dict['members'] = self.provider_pool2_members_dict
        self.provider_pool2_dict['healthmonitor'] = self.provider_hm2_dict

        self.provider_pool1 = driver_dm.Pool(**self.provider_pool1_dict)
        self.provider_pool1.members = self.provider_pool1_members
        self.provider_pool1.healthmonitor = self.provider_hm1
        self.provider_pool2 = driver_dm.Pool(**self.provider_pool2_dict)
        self.provider_pool2.members = self.provider_pool2_members
        self.provider_pool2.healthmonitor = self.provider_hm2

        self.provider_pools = [self.provider_pool1, self.provider_pool2]

        # Setup L7Rules
        self.test_l7rule1_dict = {'id': l7rule1_id,
                                  'l7policy_id': l7policy1_id,
                                  'type': 'o',
                                  'compare_type': 'fake_type',
                                  'key': 'fake_key',
                                  'value': 'fake_value',
                                  'l7policy': None,
                                  'invert': False}

        self.test_l7rule1_dict.update(_common_test_dict)

        self.test_l7rule2_dict = copy.deepcopy(self.test_l7rule1_dict)
        self.test_l7rule2_dict['id'] = l7rule2_id

        self.test_l7rules = [self.test_l7rule1_dict, self.test_l7rule2_dict]

        self.db_l7Rule1 = data_models.L7Rule(**self.test_l7rule1_dict)
        self.db_l7Rule2 = data_models.L7Rule(**self.test_l7rule2_dict)

        self.db_l7Rules = [self.db_l7Rule1, self.db_l7Rule2]

        self.provider_l7rule1_dict = {'admin_state_up': True,
                                      'compare_type': 'fake_type',
                                      'invert': False,
                                      'key': 'fake_key',
                                      'l7policy_id': l7policy1_id,
                                      'l7rule_id': l7rule1_id,
                                      'type': 'o',
                                      'value': 'fake_value'}

        self.provider_l7rule2_dict = copy.deepcopy(self.provider_l7rule1_dict)
        self.provider_l7rule2_dict['l7rule_id'] = l7rule2_id

        self.provider_l7rules_dicts = [self.provider_l7rule1_dict,
                                       self.provider_l7rule2_dict]

        self.provider_l7rule1 = driver_dm.L7Rule(**self.provider_l7rule1_dict)
        self.provider_l7rule2 = driver_dm.L7Rule(**self.provider_l7rule2_dict)

        self.provider_rules = [self.provider_l7rule1, self.provider_l7rule2]

        # Setup L7Policies
        self.test_l7policy1_dict = {'id': l7policy1_id,
                                    'name': 'l7policy_1',
                                    'description': 'L7policy 1',
                                    'listener_id': listener1_id,
                                    'action': 'go',
                                    'redirect_pool_id': pool1_id,
                                    'redirect_url': '/index.html',
                                    'position': 1,
                                    'listener': None,
                                    'redirect_pool': None,
                                    'l7rules': self.test_l7rules}

        self.test_l7policy1_dict.update(_common_test_dict)

        self.test_l7policy2_dict = copy.deepcopy(self.test_l7policy1_dict)
        self.test_l7policy2_dict['id'] = l7policy2_id
        self.test_l7policy2_dict['name'] = 'l7policy_2'
        self.test_l7policy2_dict['description'] = 'L7policy 2'

        self.test_l7policies = [self.test_l7policy1_dict,
                                self.test_l7policy2_dict]

        self.db_l7policy1 = data_models.L7Policy(**self.test_l7policy1_dict)
        self.db_l7policy2 = data_models.L7Policy(**self.test_l7policy2_dict)
        self.db_l7policy1.l7rules = self.db_l7Rules
        self.db_l7policy2.l7rules = self.db_l7Rules

        self.db_l7policies = [self.db_l7policy1, self.db_l7policy2]

        self.provider_l7policy1_dict = {'action': 'go',
                                        'admin_state_up': True,
                                        'description': 'L7policy 1',
                                        'l7policy_id': l7policy1_id,
                                        'listener_id': listener1_id,
                                        'name': 'l7policy_1',
                                        'position': 1,
                                        'redirect_pool_id': pool1_id,
                                        'redirect_url': '/index.html',
                                        'rules': self.provider_l7rules_dicts}

        self.provider_l7policy2_dict = copy.deepcopy(
            self.provider_l7policy1_dict)
        self.provider_l7policy2_dict['l7policy_id'] = l7policy2_id
        self.provider_l7policy2_dict['name'] = 'l7policy_2'
        self.provider_l7policy2_dict['description'] = 'L7policy 2'

        self.provider_l7policies_dict = [self.provider_l7policy1_dict,
                                         self.provider_l7policy2_dict]

        self.provider_l7policy1 = driver_dm.L7Policy(
            **self.provider_l7policy1_dict)
        self.provider_l7policy1.rules = self.provider_rules
        self.provider_l7policy2 = driver_dm.L7Policy(
            **self.provider_l7policy2_dict)
        self.provider_l7policy2.rules = self.provider_rules

        self.provider_l7policies = [self.provider_l7policy1,
                                    self.provider_l7policy2]

        # Setup Listeners
        self.test_listener1_dict = {'id': listener1_id,
                                    'name': 'listener_1',
                                    'description': 'Listener 1',
                                    'default_pool_id': pool1_id,
                                    'load_balancer_id': self.lb_id,
                                    'protocol': 'avian',
                                    'protocol_port': 90,
                                    'connection_limit': 10000,
                                    'tls_certificate_id': '1',
                                    'stats': None,
                                    'default_pool': self.test_pool1_dict,
                                    'load_balancer': None,
                                    'sni_containers': self.sni_containers,
                                    'peer_port': 55,
                                    'l7policies': self.test_l7policies,
                                    'insert_headers': {},
                                    'pools': None,
                                    'timeout_client_data': 1000,
                                    'timeout_member_connect': 2000,
                                    'timeout_member_data': 3000,
                                    'timeout_tcp_inspect': 4000}

        self.test_listener1_dict.update(_common_test_dict)

        self.test_listener2_dict = copy.deepcopy(self.test_listener1_dict)
        self.test_listener2_dict['id'] = listener2_id
        self.test_listener2_dict['name'] = 'listener_2'
        self.test_listener2_dict['description'] = 'Listener 1'
        self.test_listener2_dict['default_pool_id'] = pool2_id
        self.test_listener2_dict['default_pool'] = self.test_pool2_dict
        del self.test_listener2_dict['l7policies']
        del self.test_listener2_dict['sni_containers']

        self.test_listeners = [self.test_listener1_dict,
                               self.test_listener2_dict]

        self.db_listener1 = data_models.Listener(**self.test_listener1_dict)
        self.db_listener2 = data_models.Listener(**self.test_listener2_dict)
        self.db_listener1.default_pool = self.db_pool1
        self.db_listener2.default_pool = self.db_pool2
        self.db_listener1.l7policies = self.db_l7policies
        self.db_listener1.sni_containers = [
            data_models.SNI(tls_container_id='2'),
            data_models.SNI(tls_container_id='3')]

        self.test_db_listeners = [self.db_listener1, self.db_listener2]

        self.provider_listener1_dict = {
            'admin_state_up': True,
            'connection_limit': 10000,
            'default_pool': self.provider_pool1_dict,
            'default_pool_id': pool1_id,
            'default_tls_container': 'cert 1',
            'description': 'Listener 1',
            'insert_headers': {},
            'l7policies': self.provider_l7policies_dict,
            'listener_id': listener1_id,
            'loadbalancer_id': self.lb_id,
            'name': 'listener_1',
            'protocol': 'avian',
            'protocol_port': 90,
            'sni_containers': ['cert 2', 'cert 3'],
            'timeout_client_data': 1000,
            'timeout_member_connect': 2000,
            'timeout_member_data': 3000,
            'timeout_tcp_inspect': 4000}

        self.provider_listener2_dict = copy.deepcopy(
            self.provider_listener1_dict)
        self.provider_listener2_dict['listener_id'] = listener2_id
        self.provider_listener2_dict['name'] = 'listener_2'
        self.provider_listener2_dict['description'] = 'Listener 1'
        self.provider_listener2_dict['default_pool_id'] = pool2_id
        self.provider_listener2_dict['default_pool'] = self.provider_pool2_dict
        del self.provider_listener2_dict['l7policies']

        self.provider_listener1 = driver_dm.Listener(
            **self.provider_listener1_dict)
        self.provider_listener2 = driver_dm.Listener(
            **self.provider_listener2_dict)
        self.provider_listener1.default_pool = self.provider_pool1
        self.provider_listener2.default_pool = self.provider_pool2
        self.provider_listener1.l7policies = self.provider_l7policies

        self.provider_listeners = [self.provider_listener1,
                                   self.provider_listener2]

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

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_lb_dict_to_provider_dict(self, mock_load_cert):
        mock_load_cert.return_value = {'tls_cert': 'cert 1',
                                       'sni_certs': ['cert 2', 'cert 3']}

        test_lb_dict = {'name': 'lb1', 'project_id': self.project_id,
                        'vip_subnet_id': self.subnet_id,
                        'vip_port_id': self.port_id,
                        'vip_address': self.ip_address,
                        'vip_network_id': self.network_id,
                        'vip_qos_policy_id': self.qos_policy_id,
                        'provider': 'noop_driver',
                        'id': self.lb_id,
                        'listeners': [],
                        'pools': [],
                        'description': '', 'admin_state_up': True,
                        'provisioning_status': constants.PENDING_CREATE,
                        'operating_status': constants.OFFLINE,
                        'flavor_id': '',
                        'provider': 'noop_driver'}
        ref_prov_lb_dict = {'vip_address': self.ip_address,
                            'admin_state_up': True,
                            'loadbalancer_id': self.lb_id,
                            'vip_subnet_id': self.subnet_id,
                            'listeners': self.provider_listeners,
                            'description': '',
                            'project_id': self.project_id,
                            'flavor_id': '',
                            'vip_port_id': self.port_id,
                            'vip_qos_policy_id': self.qos_policy_id,
                            'vip_network_id': self.network_id,
                            'pools': self.provider_pools,
                            'name': 'lb1'}
        vip = data_models.Vip(ip_address=self.ip_address,
                              network_id=self.network_id,
                              port_id=self.port_id, subnet_id=self.subnet_id,
                              qos_policy_id=self.qos_policy_id)

        provider_lb_dict = utils.lb_dict_to_provider_dict(
            test_lb_dict, vip=vip, db_pools=self.test_db_pools,
            db_listeners=self.test_db_listeners)

        self.assertEqual(ref_prov_lb_dict, provider_lb_dict)

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_db_listeners_to_provider_listeners(self, mock_load_cert):
        mock_load_cert.return_value = {'tls_cert': 'cert 1',
                                       'sni_certs': ['cert 2', 'cert 3']}
        provider_listeners = utils.db_listeners_to_provider_listeners(
            self.test_db_listeners)
        self.assertEqual(self.provider_listeners, provider_listeners)

    @mock.patch('octavia.common.tls_utils.cert_parser.load_certificates_data')
    def test_listener_dict_to_provider_dict(self, mock_load_cert):
        mock_load_cert.return_value = {'tls_cert': 'cert 1',
                                       'sni_certs': ['cert 2', 'cert 3']}
        provider_listener = utils.listener_dict_to_provider_dict(
            self.test_listener1_dict)
        self.assertEqual(self.provider_listener1_dict, provider_listener)

    def test_db_pool_to_provider_pool(self):
        provider_pool = utils.db_pool_to_provider_pool(self.db_pool1)
        self.assertEqual(self.provider_pool1, provider_pool)

    def test_db_pools_to_provider_pools(self):
        provider_pools = utils.db_pools_to_provider_pools(self.test_db_pools)
        self.assertEqual(self.provider_pools, provider_pools)

    def test_pool_dict_to_provider_dict(self):
        provider_pool_dict = utils.pool_dict_to_provider_dict(
            self.test_pool1_dict)
        self.assertEqual(self.provider_pool1_dict, provider_pool_dict)

    def test_db_HM_to_provider_HM(self):
        provider_hm = utils.db_HM_to_provider_HM(self.db_hm1)
        self.assertEqual(self.provider_hm1, provider_hm)

    def test_hm_dict_to_provider_dict(self):
        provider_hm_dict = utils.hm_dict_to_provider_dict(self.test_hm1_dict)
        self.assertEqual(self.provider_hm1_dict, provider_hm_dict)

    def test_db_members_to_provider_members(self):
        provider_members = utils.db_members_to_provider_members(
            self.db_pool1_members)
        self.assertEqual(self.provider_pool1_members, provider_members)

    def test_member_dict_to_provider_dict(self):
        provider_member_dict = utils.member_dict_to_provider_dict(
            self.test_member1_dict)
        self.assertEqual(self.provider_member1_dict, provider_member_dict)

    def test_db_l7policies_to_provider_l7policies(self):
        provider_rules = utils.db_l7policies_to_provider_l7policies(
            self.db_l7policies)
        self.assertEqual(self.provider_l7policies, provider_rules)

    def test_l7policy_dict_to_provider_dict(self):
        provider_l7policy_dict = utils.l7policy_dict_to_provider_dict(
            self.test_l7policy1_dict)
        self.assertEqual(self.provider_l7policy1_dict, provider_l7policy_dict)

    def test_db_l7rules_to_provider_l7rules(self):
        provider_rules = utils.db_l7rules_to_provider_l7rules(self.db_l7Rules)
        self.assertEqual(self.provider_rules, provider_rules)

    def test_l7rule_dict_to_provider_dict(self):
        provider_rules_dict = utils.l7rule_dict_to_provider_dict(
            self.test_l7rule1_dict)
        self.assertEqual(self.provider_l7rule1_dict, provider_rules_dict)

    def test_vip_dict_to_provider_dict(self):
        test_vip_dict = {'ip_address': self.ip_address,
                         'network_id': self.network_id,
                         'port_id': self.port_id,
                         'subnet_id': self.subnet_id,
                         'qos_policy_id': self.qos_policy_id}

        provider_vip_dict = {'vip_address': self.ip_address,
                             'vip_network_id': self.network_id,
                             'vip_port_id': self.port_id,
                             'vip_subnet_id': self.subnet_id,
                             'vip_qos_policy_id': self.qos_policy_id}

        new_vip_dict = utils.vip_dict_to_provider_dict(test_vip_dict)
        self.assertEqual(provider_vip_dict, new_vip_dict)

    def test_provider_vip_dict_to_vip_obj(self):
        provider_vip_dict = {'vip_address': self.ip_address,
                             'vip_network_id': self.network_id,
                             'vip_port_id': self.port_id,
                             'vip_subnet_id': self.subnet_id,
                             'vip_qos_policy_id': self.qos_policy_id}

        ref_vip = data_models.Vip(ip_address=self.ip_address,
                                  network_id=self.network_id,
                                  port_id=self.port_id,
                                  subnet_id=self.subnet_id,
                                  qos_policy_id=self.qos_policy_id)

        new_provider_vip = utils.provider_vip_dict_to_vip_obj(
            provider_vip_dict)
        self.assertEqual(ref_vip, new_provider_vip)
