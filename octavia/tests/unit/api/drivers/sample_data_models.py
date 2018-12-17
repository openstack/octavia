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

from oslo_utils import uuidutils

from octavia.api.drivers import data_models as driver_dm
from octavia.common import constants
from octavia.common import data_models


class SampleDriverDataModels(object):

    def __init__(self):
        self.project_id = uuidutils.generate_uuid()
        self.lb_id = uuidutils.generate_uuid()
        self.ip_address = '192.0.2.30'
        self.port_id = uuidutils.generate_uuid()
        self.network_id = uuidutils.generate_uuid()
        self.subnet_id = uuidutils.generate_uuid()
        self.qos_policy_id = uuidutils.generate_uuid()

        self.listener1_id = uuidutils.generate_uuid()
        self.listener2_id = uuidutils.generate_uuid()
        self.default_tls_container_ref = uuidutils.generate_uuid()
        self.sni_container_ref_1 = uuidutils.generate_uuid()
        self.sni_container_ref_2 = uuidutils.generate_uuid()
        self.client_ca_tls_certificate_ref = uuidutils.generate_uuid()
        self.client_crl_container_ref = uuidutils.generate_uuid()
        self.pool_sni_container_ref = uuidutils.generate_uuid()
        self.pool_ca_container_ref = uuidutils.generate_uuid()
        self.pool_crl_container_ref = uuidutils.generate_uuid()

        self.pool1_id = uuidutils.generate_uuid()
        self.pool2_id = uuidutils.generate_uuid()

        self.hm1_id = uuidutils.generate_uuid()
        self.hm2_id = uuidutils.generate_uuid()

        self.member1_id = uuidutils.generate_uuid()
        self.member2_id = uuidutils.generate_uuid()
        self.member3_id = uuidutils.generate_uuid()
        self.member4_id = uuidutils.generate_uuid()

        self.l7policy1_id = uuidutils.generate_uuid()
        self.l7policy2_id = uuidutils.generate_uuid()

        self.l7rule1_id = uuidutils.generate_uuid()
        self.l7rule2_id = uuidutils.generate_uuid()

        self._common_test_dict = {'provisioning_status': constants.ACTIVE,
                                  'operating_status': constants.ONLINE,
                                  'project_id': self.project_id,
                                  'created_at': 'then',
                                  'updated_at': 'now',
                                  'enabled': True}

        # Setup Health Monitors
        self.test_hm1_dict = {'id': self.hm1_id,
                              'type': constants.HEALTH_MONITOR_PING,
                              'delay': 1, 'timeout': 3, 'fall_threshold': 1,
                              'rise_threshold': 2, 'http_method': 'GET',
                              'url_path': '/', 'expected_codes': '200',
                              'name': 'hm1', 'pool_id': self.pool1_id,
                              'http_version': 1.0, 'domain_name': None}

        self.test_hm1_dict.update(self._common_test_dict)

        self.test_hm2_dict = copy.deepcopy(self.test_hm1_dict)
        self.test_hm2_dict['id'] = self.hm2_id
        self.test_hm2_dict['name'] = 'hm2'
        self.test_hm2_dict.update({'http_version': 1.1,
                                   'domain_name': 'testdomainname.com'})

        self.db_hm1 = data_models.HealthMonitor(**self.test_hm1_dict)
        self.db_hm2 = data_models.HealthMonitor(**self.test_hm2_dict)

        self.provider_hm1_dict = {'admin_state_up': True,
                                  'delay': 1, 'expected_codes': '200',
                                  'healthmonitor_id': self.hm1_id,
                                  'http_method': 'GET',
                                  'max_retries': 2,
                                  'max_retries_down': 1,
                                  'name': 'hm1',
                                  'pool_id': self.pool1_id,
                                  'timeout': 3,
                                  'type': constants.HEALTH_MONITOR_PING,
                                  'url_path': '/',
                                  'http_version': 1.0,
                                  'domain_name': None}

        self.provider_hm2_dict = copy.deepcopy(self.provider_hm1_dict)
        self.provider_hm2_dict['healthmonitor_id'] = self.hm2_id
        self.provider_hm2_dict['name'] = 'hm2'
        self.provider_hm2_dict.update({'http_version': 1.1,
                                       'domain_name': 'testdomainname.com'})

        self.provider_hm1 = driver_dm.HealthMonitor(**self.provider_hm1_dict)
        self.provider_hm2 = driver_dm.HealthMonitor(**self.provider_hm2_dict)

        # Setup Members
        self.test_member1_dict = {'id': self.member1_id,
                                  'pool_id': self.pool1_id,
                                  'ip_address': '192.0.2.16',
                                  'protocol_port': 80, 'weight': 0,
                                  'backup': False,
                                  'subnet_id': self.subnet_id,
                                  'pool': None,
                                  'name': 'member1',
                                  'monitor_address': '192.0.2.26',
                                  'monitor_port': 81}

        self.test_member1_dict.update(self._common_test_dict)

        self.test_member2_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member2_dict['id'] = self.member2_id
        self.test_member2_dict['ip_address'] = '192.0.2.17'
        self.test_member2_dict['monitor_address'] = '192.0.2.27'
        self.test_member2_dict['name'] = 'member2'

        self.test_member3_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member3_dict['id'] = self.member3_id
        self.test_member3_dict['ip_address'] = '192.0.2.18'
        self.test_member3_dict['monitor_address'] = '192.0.2.28'
        self.test_member3_dict['name'] = 'member3'
        self.test_member3_dict['pool_id'] = self.pool2_id

        self.test_member4_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member4_dict['id'] = self.member4_id
        self.test_member4_dict['ip_address'] = '192.0.2.19'
        self.test_member4_dict['monitor_address'] = '192.0.2.29'
        self.test_member4_dict['name'] = 'member4'
        self.test_member4_dict['pool_id'] = self.pool2_id

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
                                      'member_id': self.member1_id,
                                      'monitor_address': '192.0.2.26',
                                      'monitor_port': 81,
                                      'name': 'member1',
                                      'pool_id': self.pool1_id,
                                      'protocol_port': 80,
                                      'subnet_id': self.subnet_id,
                                      'weight': 0,
                                      'backup': False}

        self.provider_member2_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member2_dict['member_id'] = self.member2_id
        self.provider_member2_dict['address'] = '192.0.2.17'
        self.provider_member2_dict['monitor_address'] = '192.0.2.27'
        self.provider_member2_dict['name'] = 'member2'

        self.provider_member3_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member3_dict['member_id'] = self.member3_id
        self.provider_member3_dict['address'] = '192.0.2.18'
        self.provider_member3_dict['monitor_address'] = '192.0.2.28'
        self.provider_member3_dict['name'] = 'member3'
        self.provider_member3_dict['pool_id'] = self.pool2_id

        self.provider_member4_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member4_dict['member_id'] = self.member4_id
        self.provider_member4_dict['address'] = '192.0.2.19'
        self.provider_member4_dict['monitor_address'] = '192.0.2.29'
        self.provider_member4_dict['name'] = 'member4'
        self.provider_member4_dict['pool_id'] = self.pool2_id

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
        self.test_pool1_dict = {'id': self.pool1_id,
                                'name': 'pool1', 'description': 'Pool 1',
                                'load_balancer_id': self.lb_id,
                                'protocol': 'avian',
                                'lb_algorithm': 'round_robin',
                                'members': self.test_pool1_members_dict,
                                'health_monitor': self.test_hm1_dict,
                                'session_persistence': {'type': 'SOURCE'},
                                'listeners': [],
                                'l7policies': [],
                                'tls_certificate_id':
                                    self.pool_sni_container_ref,
                                'ca_tls_certificate_id':
                                    self.pool_ca_container_ref,
                                'crl_container_id':
                                    self.pool_crl_container_ref,
                                'tls_enabled': True}

        self.test_pool1_dict.update(self._common_test_dict)

        self.test_pool2_dict = copy.deepcopy(self.test_pool1_dict)
        self.test_pool2_dict['id'] = self.pool2_id
        self.test_pool2_dict['name'] = 'pool2'
        self.test_pool2_dict['description'] = 'Pool 2'
        self.test_pool2_dict['members'] = self.test_pool2_members_dict
        del self.test_pool2_dict['tls_certificate_id']
        del self.test_pool2_dict['ca_tls_certificate_id']
        del self.test_pool2_dict['crl_container_id']

        self.test_pools = [self.test_pool1_dict, self.test_pool2_dict]

        self.db_pool1 = data_models.Pool(**self.test_pool1_dict)
        self.db_pool1.health_monitor = self.db_hm1
        self.db_pool1.members = self.db_pool1_members
        self.db_pool2 = data_models.Pool(**self.test_pool2_dict)
        self.db_pool2.health_monitor = self.db_hm2
        self.db_pool2.members = self.db_pool2_members

        self.test_db_pools = [self.db_pool1, self.db_pool2]
        pool_cert = data_models.TLSContainer(certificate='pool cert')
        pool_ca_file_content = 'X509 POOL CA CERT FILE'
        pool_crl_file_content = 'X509 POOL CRL FILE'

        self.provider_pool1_dict = {
            'admin_state_up': True,
            'description': 'Pool 1',
            'healthmonitor': self.provider_hm1_dict,
            'lb_algorithm': 'round_robin',
            'loadbalancer_id': self.lb_id,
            'members': self.provider_pool1_members_dict,
            'name': 'pool1',
            'pool_id': self.pool1_id,
            'protocol': 'avian',
            'session_persistence': {'type': 'SOURCE'},
            'tls_container_ref': self.pool_sni_container_ref,
            'tls_container_data': pool_cert.to_dict(),
            'ca_tls_container_ref': self.pool_ca_container_ref,
            'ca_tls_container_data': pool_ca_file_content,
            'crl_container_ref': self.pool_crl_container_ref,
            'crl_container_data': pool_crl_file_content,
            'tls_enabled': True
        }

        self.provider_pool2_dict = copy.deepcopy(self.provider_pool1_dict)
        self.provider_pool2_dict['pool_id'] = self.pool2_id
        self.provider_pool2_dict['name'] = 'pool2'
        self.provider_pool2_dict['description'] = 'Pool 2'
        self.provider_pool2_dict['members'] = self.provider_pool2_members_dict
        self.provider_pool2_dict['healthmonitor'] = self.provider_hm2_dict
        self.provider_pool2_dict['tls_container_ref'] = None
        del self.provider_pool2_dict['tls_container_data']
        self.provider_pool2_dict['ca_tls_container_ref'] = None
        del self.provider_pool2_dict['ca_tls_container_data']
        self.provider_pool2_dict['crl_container_ref'] = None
        del self.provider_pool2_dict['crl_container_data']

        self.provider_pool1 = driver_dm.Pool(**self.provider_pool1_dict)
        self.provider_pool1.members = self.provider_pool1_members
        self.provider_pool1.healthmonitor = self.provider_hm1
        self.provider_pool2 = driver_dm.Pool(**self.provider_pool2_dict)
        self.provider_pool2.members = self.provider_pool2_members
        self.provider_pool2.healthmonitor = self.provider_hm2

        self.provider_pools = [self.provider_pool1, self.provider_pool2]

        # Setup L7Rules
        self.test_l7rule1_dict = {'id': self.l7rule1_id,
                                  'l7policy_id': self.l7policy1_id,
                                  'type': 'o',
                                  'compare_type': 'fake_type',
                                  'key': 'fake_key',
                                  'value': 'fake_value',
                                  'l7policy': None,
                                  'invert': False}

        self.test_l7rule1_dict.update(self._common_test_dict)

        self.test_l7rule2_dict = copy.deepcopy(self.test_l7rule1_dict)
        self.test_l7rule2_dict['id'] = self.l7rule2_id

        self.test_l7rules = [self.test_l7rule1_dict, self.test_l7rule2_dict]

        self.db_l7Rule1 = data_models.L7Rule(**self.test_l7rule1_dict)
        self.db_l7Rule2 = data_models.L7Rule(**self.test_l7rule2_dict)

        self.db_l7Rules = [self.db_l7Rule1, self.db_l7Rule2]

        self.provider_l7rule1_dict = {'admin_state_up': True,
                                      'compare_type': 'fake_type',
                                      'invert': False,
                                      'key': 'fake_key',
                                      'l7policy_id': self.l7policy1_id,
                                      'l7rule_id': self.l7rule1_id,
                                      'type': 'o',
                                      'value': 'fake_value'}

        self.provider_l7rule2_dict = copy.deepcopy(self.provider_l7rule1_dict)
        self.provider_l7rule2_dict['l7rule_id'] = self.l7rule2_id
        self.provider_l7rules_dicts = [self.provider_l7rule1_dict,
                                       self.provider_l7rule2_dict]

        self.provider_l7rule1 = driver_dm.L7Rule(**self.provider_l7rule1_dict)
        self.provider_l7rule2 = driver_dm.L7Rule(**self.provider_l7rule2_dict)

        self.provider_rules = [self.provider_l7rule1, self.provider_l7rule2]

        # Setup L7Policies
        self.test_l7policy1_dict = {'id': self.l7policy1_id,
                                    'name': 'l7policy_1',
                                    'description': 'L7policy 1',
                                    'listener_id': self.listener1_id,
                                    'action': 'go',
                                    'redirect_pool_id': self.pool1_id,
                                    'redirect_url': '/index.html',
                                    'redirect_prefix': 'https://example.com/',
                                    'position': 1,
                                    'listener': None,
                                    'redirect_pool': None,
                                    'l7rules': self.test_l7rules,
                                    'redirect_http_code': 302}

        self.test_l7policy1_dict.update(self._common_test_dict)

        self.test_l7policy2_dict = copy.deepcopy(self.test_l7policy1_dict)
        self.test_l7policy2_dict['id'] = self.l7policy2_id
        self.test_l7policy2_dict['name'] = 'l7policy_2'
        self.test_l7policy2_dict['description'] = 'L7policy 2'

        self.test_l7policies = [self.test_l7policy1_dict,
                                self.test_l7policy2_dict]

        self.db_l7policy1 = data_models.L7Policy(**self.test_l7policy1_dict)
        self.db_l7policy2 = data_models.L7Policy(**self.test_l7policy2_dict)
        self.db_l7policy1.l7rules = self.db_l7Rules
        self.db_l7policy2.l7rules = self.db_l7Rules

        self.db_l7policies = [self.db_l7policy1, self.db_l7policy2]

        self.provider_l7policy1_dict = {
            'action': 'go',
            'admin_state_up': True,
            'description': 'L7policy 1',
            'l7policy_id': self.l7policy1_id,
            'listener_id': self.listener1_id,
            'name': 'l7policy_1',
            'position': 1,
            'redirect_pool_id': self.pool1_id,
            'redirect_url': '/index.html',
            'redirect_prefix': 'https://example.com/',
            'rules': self.provider_l7rules_dicts,
            'redirect_http_code': 302
        }

        self.provider_l7policy2_dict = copy.deepcopy(
            self.provider_l7policy1_dict)
        self.provider_l7policy2_dict['l7policy_id'] = self.l7policy2_id
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
        self.test_listener1_dict = {
            'id': self.listener1_id,
            'name': 'listener_1',
            'description': 'Listener 1',
            'default_pool_id': self.pool1_id,
            'load_balancer_id': self.lb_id,
            'protocol': 'avian',
            'protocol_port': 90,
            'connection_limit': 10000,
            'tls_certificate_id': self.default_tls_container_ref,
            'stats': None,
            'default_pool': self.test_pool1_dict,
            'load_balancer': None,
            'sni_containers': [self.sni_container_ref_1,
                               self.sni_container_ref_2],
            'peer_port': 55,
            'l7policies': self.test_l7policies,
            'insert_headers': {},
            'pools': None,
            'timeout_client_data': 1000,
            'timeout_member_connect': 2000,
            'timeout_member_data': 3000,
            'timeout_tcp_inspect': 4000,
            'client_ca_tls_certificate_id': self.client_ca_tls_certificate_ref,
            'client_authentication': constants.CLIENT_AUTH_NONE,
            'client_crl_container_id': self.client_crl_container_ref
        }

        self.test_listener1_dict.update(self._common_test_dict)

        self.test_listener2_dict = copy.deepcopy(self.test_listener1_dict)
        self.test_listener2_dict['id'] = self.listener2_id
        self.test_listener2_dict['name'] = 'listener_2'
        self.test_listener2_dict['description'] = 'Listener 1'
        self.test_listener2_dict['default_pool_id'] = self.pool2_id
        self.test_listener2_dict['default_pool'] = self.test_pool2_dict
        del self.test_listener2_dict['l7policies']
        del self.test_listener2_dict['sni_containers']
        del self.test_listener2_dict['client_ca_tls_certificate_id']
        del self.test_listener2_dict['client_crl_container_id']

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

        cert1 = data_models.TLSContainer(certificate='cert 1')
        cert2 = data_models.TLSContainer(certificate='cert 2')
        cert3 = data_models.TLSContainer(certificate='cert 3')
        ca_cert = 'ca cert'
        crl_file_content = 'X509 CRL FILE'

        self.provider_listener1_dict = {
            'admin_state_up': True,
            'connection_limit': 10000,
            'default_pool': self.provider_pool1_dict,
            'default_pool_id': self.pool1_id,
            'default_tls_container_data': cert1.to_dict(),
            'default_tls_container_ref': self.default_tls_container_ref,
            'description': 'Listener 1',
            'insert_headers': {},
            'l7policies': self.provider_l7policies_dict,
            'listener_id': self.listener1_id,
            'loadbalancer_id': self.lb_id,
            'name': 'listener_1',
            'protocol': 'avian',
            'protocol_port': 90,
            'sni_container_data': [cert2.to_dict(), cert3.to_dict()],
            'sni_container_refs': [self.sni_container_ref_1,
                                   self.sni_container_ref_2],
            'timeout_client_data': 1000,
            'timeout_member_connect': 2000,
            'timeout_member_data': 3000,
            'timeout_tcp_inspect': 4000,
            'client_ca_tls_container_ref': self.client_ca_tls_certificate_ref,
            'client_ca_tls_container_data': ca_cert,
            'client_authentication': constants.CLIENT_AUTH_NONE,
            'client_crl_container_ref': self.client_crl_container_ref,
            'client_crl_container_data': crl_file_content
        }

        self.provider_listener2_dict = copy.deepcopy(
            self.provider_listener1_dict)
        self.provider_listener2_dict['listener_id'] = self.listener2_id
        self.provider_listener2_dict['name'] = 'listener_2'
        self.provider_listener2_dict['description'] = 'Listener 1'
        self.provider_listener2_dict['default_pool_id'] = self.pool2_id
        self.provider_listener2_dict['default_pool'] = self.provider_pool2_dict
        del self.provider_listener2_dict['l7policies']
        self.provider_listener2_dict['client_ca_tls_container_ref'] = None
        del self.provider_listener2_dict['client_ca_tls_container_data']
        self.provider_listener2_dict['client_authentication'] = (
            constants.CLIENT_AUTH_NONE)
        self.provider_listener2_dict['client_crl_container_ref'] = None
        del self.provider_listener2_dict['client_crl_container_data']

        self.provider_listener1 = driver_dm.Listener(
            **self.provider_listener1_dict)
        self.provider_listener2 = driver_dm.Listener(
            **self.provider_listener2_dict)
        self.provider_listener1.default_pool = self.provider_pool1
        self.provider_listener2.default_pool = self.provider_pool2
        self.provider_listener1.l7policies = self.provider_l7policies

        self.provider_listeners = [self.provider_listener1,
                                   self.provider_listener2]

        self.test_vip_dict = {'ip_address': self.ip_address,
                              'network_id': self.network_id,
                              'port_id': self.port_id,
                              'subnet_id': self.subnet_id,
                              'qos_policy_id': self.qos_policy_id}

        self.provider_vip_dict = {
            'vip_address': self.ip_address,
            'vip_network_id': self.network_id,
            'vip_port_id': self.port_id,
            'vip_subnet_id': self.subnet_id,
            'vip_qos_policy_id': self.qos_policy_id}

        self.db_vip = data_models.Vip(
            ip_address=self.ip_address,
            network_id=self.network_id,
            port_id=self.port_id,
            subnet_id=self.subnet_id,
            qos_policy_id=self.qos_policy_id)
