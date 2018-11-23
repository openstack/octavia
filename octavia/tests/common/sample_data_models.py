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
import datetime

from octavia_lib.api.drivers import data_models as driver_dm
from octavia_lib.common import constants as lib_consts
from oslo_utils import uuidutils

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
        self.lb_name = uuidutils.generate_uuid()
        self.lb_description = uuidutils.generate_uuid()
        self.flavor_id = uuidutils.generate_uuid()
        self.flavor_profile_id = uuidutils.generate_uuid()

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

        self.created_at = datetime.datetime.now()
        self.updated_at = (datetime.datetime.now() +
                           datetime.timedelta(minutes=1))

        self._common_test_dict = {
            lib_consts.PROVISIONING_STATUS: constants.ACTIVE,
            lib_consts.OPERATING_STATUS: constants.ONLINE,
            lib_consts.PROJECT_ID: self.project_id,
            constants.CREATED_AT: self.created_at,
            constants.UPDATED_AT: self.updated_at,
            constants.ENABLED: True}

        # Setup Health Monitors
        self.test_hm1_dict = {
            lib_consts.ID: self.hm1_id,
            lib_consts.TYPE: constants.HEALTH_MONITOR_PING,
            lib_consts.DELAY: 1, lib_consts.TIMEOUT: 3,
            lib_consts.FALL_THRESHOLD: 1, lib_consts.RISE_THRESHOLD: 2,
            lib_consts.HTTP_METHOD: lib_consts.HEALTH_MONITOR_HTTP_METHOD_GET,
            lib_consts.URL_PATH: '/', lib_consts.EXPECTED_CODES: '200',
            lib_consts.NAME: 'hm1', lib_consts.POOL_ID: self.pool1_id,
            lib_consts.HTTP_VERSION: 1.0, lib_consts.DOMAIN_NAME: None,
            lib_consts.PROJECT_ID: self.project_id}

        self.test_hm1_dict.update(self._common_test_dict)

        self.test_hm2_dict = copy.deepcopy(self.test_hm1_dict)
        self.test_hm2_dict[lib_consts.ID] = self.hm2_id
        self.test_hm2_dict[lib_consts.NAME] = 'hm2'
        self.test_hm2_dict.update(
            {lib_consts.HTTP_VERSION: 1.1,
             lib_consts.DOMAIN_NAME: 'testdomainname.com'})

        self.db_hm1 = data_models.HealthMonitor(**self.test_hm1_dict)
        self.db_hm2 = data_models.HealthMonitor(**self.test_hm2_dict)

        self.provider_hm1_dict = {
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.DELAY: 1, lib_consts.EXPECTED_CODES: '200',
            lib_consts.HEALTHMONITOR_ID: self.hm1_id,
            lib_consts.HTTP_METHOD: lib_consts.HEALTH_MONITOR_HTTP_METHOD_GET,
            lib_consts.MAX_RETRIES: 2,
            lib_consts.MAX_RETRIES_DOWN: 1,
            lib_consts.NAME: 'hm1',
            lib_consts.POOL_ID: self.pool1_id,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.TIMEOUT: 3,
            lib_consts.TYPE: constants.HEALTH_MONITOR_PING,
            lib_consts.URL_PATH: '/',
            lib_consts.HTTP_VERSION: 1.0,
            lib_consts.DOMAIN_NAME: None}

        self.provider_hm2_dict = copy.deepcopy(self.provider_hm1_dict)
        self.provider_hm2_dict[lib_consts.HEALTHMONITOR_ID] = self.hm2_id
        self.provider_hm2_dict[lib_consts.NAME] = 'hm2'
        self.provider_hm2_dict.update(
            {lib_consts.HTTP_VERSION: 1.1,
             lib_consts.DOMAIN_NAME: 'testdomainname.com'})

        self.provider_hm1 = driver_dm.HealthMonitor(**self.provider_hm1_dict)
        self.provider_hm2 = driver_dm.HealthMonitor(**self.provider_hm2_dict)

        # Setup Members
        self.test_member1_dict = {
            lib_consts.ID: self.member1_id,
            lib_consts.POOL_ID: self.pool1_id,
            constants.IP_ADDRESS: '192.0.2.16',
            lib_consts.PROTOCOL_PORT: 80, lib_consts.WEIGHT: 0,
            lib_consts.BACKUP: False,
            lib_consts.SUBNET_ID: self.subnet_id,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.NAME: 'member1',
            lib_consts.OPERATING_STATUS: lib_consts.ONLINE,
            lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
            constants.ENABLED: True,
            constants.CREATED_AT: self.created_at,
            constants.UPDATED_AT: self.updated_at,
            lib_consts.MONITOR_ADDRESS: '192.0.2.26',
            lib_consts.MONITOR_PORT: 81}

        self.test_member1_dict.update(self._common_test_dict)

        self.test_member2_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member2_dict[lib_consts.ID] = self.member2_id
        self.test_member2_dict[constants.IP_ADDRESS] = '192.0.2.17'
        self.test_member2_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.27'
        self.test_member2_dict[lib_consts.NAME] = 'member2'

        self.test_member3_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member3_dict[lib_consts.ID] = self.member3_id
        self.test_member3_dict[constants.IP_ADDRESS] = '192.0.2.18'
        self.test_member3_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.28'
        self.test_member3_dict[lib_consts.NAME] = 'member3'
        self.test_member3_dict[lib_consts.POOL_ID] = self.pool2_id

        self.test_member4_dict = copy.deepcopy(self.test_member1_dict)
        self.test_member4_dict[lib_consts.ID] = self.member4_id
        self.test_member4_dict[constants.IP_ADDRESS] = '192.0.2.19'
        self.test_member4_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.29'
        self.test_member4_dict[lib_consts.NAME] = 'member4'
        self.test_member4_dict[lib_consts.POOL_ID] = self.pool2_id

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

        self.provider_member1_dict = {lib_consts.ADDRESS: '192.0.2.16',
                                      lib_consts.ADMIN_STATE_UP: True,
                                      lib_consts.MEMBER_ID: self.member1_id,
                                      lib_consts.MONITOR_ADDRESS: '192.0.2.26',
                                      lib_consts.MONITOR_PORT: 81,
                                      lib_consts.NAME: 'member1',
                                      lib_consts.POOL_ID: self.pool1_id,
                                      lib_consts.PROJECT_ID: self.project_id,
                                      lib_consts.PROTOCOL_PORT: 80,
                                      lib_consts.SUBNET_ID: self.subnet_id,
                                      lib_consts.WEIGHT: 0,
                                      lib_consts.BACKUP: False}

        self.provider_member2_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member2_dict[lib_consts.MEMBER_ID] = self.member2_id
        self.provider_member2_dict[lib_consts.ADDRESS] = '192.0.2.17'
        self.provider_member2_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.27'
        self.provider_member2_dict[lib_consts.NAME] = 'member2'

        self.provider_member3_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member3_dict[lib_consts.MEMBER_ID] = self.member3_id
        self.provider_member3_dict[lib_consts.ADDRESS] = '192.0.2.18'
        self.provider_member3_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.28'
        self.provider_member3_dict[lib_consts.NAME] = 'member3'
        self.provider_member3_dict[lib_consts.POOL_ID] = self.pool2_id

        self.provider_member4_dict = copy.deepcopy(self.provider_member1_dict)
        self.provider_member4_dict[lib_consts.MEMBER_ID] = self.member4_id
        self.provider_member4_dict[lib_consts.ADDRESS] = '192.0.2.19'
        self.provider_member4_dict[lib_consts.MONITOR_ADDRESS] = '192.0.2.29'
        self.provider_member4_dict[lib_consts.NAME] = 'member4'
        self.provider_member4_dict[lib_consts.POOL_ID] = self.pool2_id

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
        self.test_pool1_dict = {
            lib_consts.ID: self.pool1_id,
            lib_consts.NAME: 'pool1', lib_consts.DESCRIPTION: 'Pool 1',
            constants.LOAD_BALANCER_ID: self.lb_id,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
            lib_consts.LB_ALGORITHM: lib_consts.LB_ALGORITHM_ROUND_ROBIN,
            lib_consts.MEMBERS: self.test_pool1_members_dict,
            constants.HEALTH_MONITOR: self.test_hm1_dict,
            lib_consts.SESSION_PERSISTENCE: {
                lib_consts.TYPE: lib_consts.LB_ALGORITHM_SOURCE_IP},
            lib_consts.LISTENERS: [],
            lib_consts.L7POLICIES: [],
            constants.TLS_CERTIFICATE_ID: self.pool_sni_container_ref,
            constants.CA_TLS_CERTIFICATE_ID: self.pool_ca_container_ref,
            constants.CRL_CONTAINER_ID: self.pool_crl_container_ref,
            lib_consts.TLS_ENABLED: True}

        self.test_pool1_dict.update(self._common_test_dict)

        self.test_pool2_dict = copy.deepcopy(self.test_pool1_dict)
        self.test_pool2_dict[lib_consts.ID] = self.pool2_id
        self.test_pool2_dict[lib_consts.NAME] = 'pool2'
        self.test_pool2_dict[lib_consts.DESCRIPTION] = 'Pool 2'
        self.test_pool2_dict[
            lib_consts.MEMBERS] = self.test_pool2_members_dict
        del self.test_pool2_dict[constants.TLS_CERTIFICATE_ID]
        del self.test_pool2_dict[constants.CA_TLS_CERTIFICATE_ID]
        del self.test_pool2_dict[constants.CRL_CONTAINER_ID]

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
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.DESCRIPTION: 'Pool 1',
            lib_consts.HEALTHMONITOR: self.provider_hm1_dict,
            lib_consts.LB_ALGORITHM: lib_consts.LB_ALGORITHM_ROUND_ROBIN,
            lib_consts.LOADBALANCER_ID: self.lb_id,
            lib_consts.MEMBERS: self.provider_pool1_members_dict,
            lib_consts.NAME: 'pool1',
            lib_consts.POOL_ID: self.pool1_id,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
            lib_consts.SESSION_PERSISTENCE: {
                lib_consts.TYPE: lib_consts.LB_ALGORITHM_SOURCE_IP},
            lib_consts.TLS_CONTAINER_REF: self.pool_sni_container_ref,
            lib_consts.TLS_CONTAINER_DATA: pool_cert.to_dict(),
            lib_consts.CA_TLS_CONTAINER_REF: self.pool_ca_container_ref,
            lib_consts.CA_TLS_CONTAINER_DATA: pool_ca_file_content,
            lib_consts.CRL_CONTAINER_REF: self.pool_crl_container_ref,
            lib_consts.CRL_CONTAINER_DATA: pool_crl_file_content,
            lib_consts.TLS_ENABLED: True
        }

        self.provider_pool2_dict = copy.deepcopy(self.provider_pool1_dict)
        self.provider_pool2_dict[lib_consts.POOL_ID] = self.pool2_id
        self.provider_pool2_dict[lib_consts.NAME] = 'pool2'
        self.provider_pool2_dict[lib_consts.DESCRIPTION] = 'Pool 2'
        self.provider_pool2_dict[
            lib_consts.MEMBERS] = self.provider_pool2_members_dict
        self.provider_pool2_dict[
            lib_consts.HEALTHMONITOR] = self.provider_hm2_dict
        self.provider_pool2_dict[lib_consts.TLS_CONTAINER_REF] = None
        del self.provider_pool2_dict[lib_consts.TLS_CONTAINER_DATA]
        self.provider_pool2_dict[lib_consts.CA_TLS_CONTAINER_REF] = None
        del self.provider_pool2_dict[lib_consts.CA_TLS_CONTAINER_DATA]
        self.provider_pool2_dict[lib_consts.CRL_CONTAINER_REF] = None
        del self.provider_pool2_dict[lib_consts.CRL_CONTAINER_DATA]

        self.provider_pool1 = driver_dm.Pool(**self.provider_pool1_dict)
        self.provider_pool1.members = self.provider_pool1_members
        self.provider_pool1.healthmonitor = self.provider_hm1
        self.provider_pool2 = driver_dm.Pool(**self.provider_pool2_dict)
        self.provider_pool2.members = self.provider_pool2_members
        self.provider_pool2.healthmonitor = self.provider_hm2

        self.provider_pools = [self.provider_pool1, self.provider_pool2]

        # Setup L7Rules
        self.test_l7rule1_dict = {
            lib_consts.ID: self.l7rule1_id,
            lib_consts.L7POLICY_ID: self.l7policy1_id,
            lib_consts.TYPE: lib_consts.L7RULE_TYPE_PATH,
            lib_consts.COMPARE_TYPE: lib_consts.L7RULE_COMPARE_TYPE_EQUAL_TO,
            lib_consts.KEY: 'fake_key',
            lib_consts.VALUE: 'fake_value',
            lib_consts.PROJECT_ID: self.project_id,
            constants.L7POLICY: None,
            lib_consts.INVERT: False}

        self.test_l7rule1_dict.update(self._common_test_dict)

        self.test_l7rule2_dict = copy.deepcopy(self.test_l7rule1_dict)
        self.test_l7rule2_dict[lib_consts.ID] = self.l7rule2_id

        self.test_l7rules = [self.test_l7rule1_dict, self.test_l7rule2_dict]

        self.db_l7Rule1 = data_models.L7Rule(**self.test_l7rule1_dict)
        self.db_l7Rule2 = data_models.L7Rule(**self.test_l7rule2_dict)

        self.db_l7Rules = [self.db_l7Rule1, self.db_l7Rule2]

        self.provider_l7rule1_dict = {
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.COMPARE_TYPE: lib_consts.L7RULE_COMPARE_TYPE_EQUAL_TO,
            lib_consts.INVERT: False,
            lib_consts.KEY: 'fake_key',
            lib_consts.L7POLICY_ID: self.l7policy1_id,
            lib_consts.L7RULE_ID: self.l7rule1_id,
            lib_consts.TYPE: lib_consts.L7RULE_TYPE_PATH,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.VALUE: 'fake_value'}

        self.provider_l7rule2_dict = copy.deepcopy(self.provider_l7rule1_dict)
        self.provider_l7rule2_dict[lib_consts.L7RULE_ID] = self.l7rule2_id
        self.provider_l7rules_dicts = [self.provider_l7rule1_dict,
                                       self.provider_l7rule2_dict]

        self.provider_l7rule1 = driver_dm.L7Rule(**self.provider_l7rule1_dict)
        self.provider_l7rule2 = driver_dm.L7Rule(**self.provider_l7rule2_dict)

        self.provider_rules = [self.provider_l7rule1, self.provider_l7rule2]

        # Setup L7Policies
        self.test_l7policy1_dict = {
            lib_consts.ID: self.l7policy1_id,
            lib_consts.NAME: 'l7policy_1',
            lib_consts.DESCRIPTION: 'L7policy 1',
            lib_consts.LISTENER_ID: self.listener1_id,
            lib_consts.ACTION: lib_consts.L7POLICY_ACTION_REDIRECT_TO_URL,
            lib_consts.REDIRECT_POOL_ID: None,
            lib_consts.REDIRECT_URL: 'http://example.com/index.html',
            lib_consts.REDIRECT_PREFIX: None,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.POSITION: 1,
            constants.LISTENER: None,
            constants.REDIRECT_POOL: None,
            lib_consts.L7RULES: self.test_l7rules,
            lib_consts.REDIRECT_HTTP_CODE: 302}

        self.test_l7policy1_dict.update(self._common_test_dict)

        self.test_l7policy2_dict = copy.deepcopy(self.test_l7policy1_dict)
        self.test_l7policy2_dict[lib_consts.ID] = self.l7policy2_id
        self.test_l7policy2_dict[lib_consts.NAME] = 'l7policy_2'
        self.test_l7policy2_dict[lib_consts.DESCRIPTION] = 'L7policy 2'

        self.test_l7policies = [self.test_l7policy1_dict,
                                self.test_l7policy2_dict]

        self.db_l7policy1 = data_models.L7Policy(**self.test_l7policy1_dict)
        self.db_l7policy2 = data_models.L7Policy(**self.test_l7policy2_dict)
        self.db_l7policy1.l7rules = self.db_l7Rules
        self.db_l7policy2.l7rules = self.db_l7Rules

        self.db_l7policies = [self.db_l7policy1, self.db_l7policy2]

        self.provider_l7policy1_dict = {
            lib_consts.ACTION: lib_consts.L7POLICY_ACTION_REDIRECT_TO_URL,
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.DESCRIPTION: 'L7policy 1',
            lib_consts.L7POLICY_ID: self.l7policy1_id,
            lib_consts.LISTENER_ID: self.listener1_id,
            lib_consts.NAME: 'l7policy_1',
            lib_consts.POSITION: 1,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.REDIRECT_POOL_ID: None,
            lib_consts.REDIRECT_URL: 'http://example.com/index.html',
            lib_consts.REDIRECT_PREFIX: None,
            lib_consts.RULES: self.provider_l7rules_dicts,
            lib_consts.REDIRECT_HTTP_CODE: 302
        }

        self.provider_l7policy2_dict = copy.deepcopy(
            self.provider_l7policy1_dict)
        self.provider_l7policy2_dict[
            lib_consts.L7POLICY_ID] = self.l7policy2_id
        self.provider_l7policy2_dict[lib_consts.NAME] = 'l7policy_2'
        self.provider_l7policy2_dict[lib_consts.DESCRIPTION] = 'L7policy 2'

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
            lib_consts.ID: self.listener1_id,
            lib_consts.NAME: 'listener_1',
            lib_consts.DESCRIPTION: 'Listener 1',
            lib_consts.DEFAULT_POOL_ID: self.pool1_id,
            constants.LOAD_BALANCER_ID: self.lb_id,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
            lib_consts.PROTOCOL_PORT: 90,
            lib_consts.CONNECTION_LIMIT: 10000,
            constants.TLS_CERTIFICATE_ID: self.default_tls_container_ref,
            lib_consts.DEFAULT_POOL: self.test_pool1_dict,
            constants.SNI_CONTAINERS: [
                {constants.TLS_CONTAINER_ID: self.sni_container_ref_1},
                {constants.TLS_CONTAINER_ID: self.sni_container_ref_2}],
            constants.PEER_PORT: 55,
            lib_consts.L7POLICIES: self.test_l7policies,
            lib_consts.INSERT_HEADERS: {},
            lib_consts.TIMEOUT_CLIENT_DATA: 1000,
            lib_consts.TIMEOUT_MEMBER_CONNECT: 2000,
            lib_consts.TIMEOUT_MEMBER_DATA: 3000,
            lib_consts.TIMEOUT_TCP_INSPECT: 4000,
            constants.CLIENT_CA_TLS_CERTIFICATE_ID:
                self.client_ca_tls_certificate_ref,
            lib_consts.CLIENT_AUTHENTICATION: constants.CLIENT_AUTH_NONE,
            constants.CLIENT_CRL_CONTAINER_ID: self.client_crl_container_ref,
            lib_consts.ALLOWED_CIDRS: ['192.0.2.0/24', '198.51.100.0/24']
        }

        self.test_listener1_dict.update(self._common_test_dict)

        self.test_listener2_dict = copy.deepcopy(self.test_listener1_dict)
        self.test_listener2_dict[lib_consts.ID] = self.listener2_id
        self.test_listener2_dict[lib_consts.NAME] = 'listener_2'
        self.test_listener2_dict[lib_consts.DESCRIPTION] = 'Listener 1'
        self.test_listener2_dict[lib_consts.DEFAULT_POOL_ID] = self.pool2_id
        self.test_listener2_dict[
            lib_consts.DEFAULT_POOL] = self.test_pool2_dict
        del self.test_listener2_dict[lib_consts.L7POLICIES]
        del self.test_listener2_dict[constants.SNI_CONTAINERS]
        del self.test_listener2_dict[constants.CLIENT_CA_TLS_CERTIFICATE_ID]
        del self.test_listener2_dict[constants.CLIENT_CRL_CONTAINER_ID]

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
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.ALLOWED_CIDRS: ['192.0.2.0/24', '198.51.100.0/24'],
            lib_consts.CONNECTION_LIMIT: 10000,
            lib_consts.DEFAULT_POOL: self.provider_pool1_dict,
            lib_consts.DEFAULT_POOL_ID: self.pool1_id,
            lib_consts.DEFAULT_TLS_CONTAINER_DATA: cert1.to_dict(),
            lib_consts.DEFAULT_TLS_CONTAINER_REF:
                self.default_tls_container_ref,
            lib_consts.DESCRIPTION: 'Listener 1',
            lib_consts.INSERT_HEADERS: {},
            lib_consts.L7POLICIES: self.provider_l7policies_dict,
            lib_consts.LISTENER_ID: self.listener1_id,
            lib_consts.LOADBALANCER_ID: self.lb_id,
            lib_consts.NAME: 'listener_1',
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
            lib_consts.PROTOCOL_PORT: 90,
            lib_consts.SNI_CONTAINER_DATA: [cert2.to_dict(), cert3.to_dict()],
            lib_consts.SNI_CONTAINER_REFS: [self.sni_container_ref_1,
                                            self.sni_container_ref_2],
            lib_consts.TIMEOUT_CLIENT_DATA: 1000,
            lib_consts.TIMEOUT_MEMBER_CONNECT: 2000,
            lib_consts.TIMEOUT_MEMBER_DATA: 3000,
            lib_consts.TIMEOUT_TCP_INSPECT: 4000,
            lib_consts.CLIENT_CA_TLS_CONTAINER_REF:
                self.client_ca_tls_certificate_ref,
            lib_consts.CLIENT_CA_TLS_CONTAINER_DATA: ca_cert,
            lib_consts.CLIENT_AUTHENTICATION: constants.CLIENT_AUTH_NONE,
            lib_consts.CLIENT_CRL_CONTAINER_REF: self.client_crl_container_ref,
            lib_consts.CLIENT_CRL_CONTAINER_DATA: crl_file_content
        }

        self.provider_listener2_dict = copy.deepcopy(
            self.provider_listener1_dict)
        self.provider_listener2_dict[
            lib_consts.LISTENER_ID] = self.listener2_id
        self.provider_listener2_dict[lib_consts.NAME] = 'listener_2'
        self.provider_listener2_dict[lib_consts.DESCRIPTION] = 'Listener 1'
        self.provider_listener2_dict[
            lib_consts.DEFAULT_POOL_ID] = self.pool2_id
        self.provider_listener2_dict[
            lib_consts.DEFAULT_POOL] = self.provider_pool2_dict
        del self.provider_listener2_dict[lib_consts.L7POLICIES]
        self.provider_listener2_dict[
            lib_consts.CLIENT_CA_TLS_CONTAINER_REF] = None
        del self.provider_listener2_dict[
            lib_consts.CLIENT_CA_TLS_CONTAINER_DATA]
        self.provider_listener2_dict[lib_consts.CLIENT_AUTHENTICATION] = (
            constants.CLIENT_AUTH_NONE)
        self.provider_listener2_dict[
            lib_consts.CLIENT_CRL_CONTAINER_REF] = None
        del self.provider_listener2_dict[lib_consts.CLIENT_CRL_CONTAINER_DATA]

        self.provider_listener1 = driver_dm.Listener(
            **self.provider_listener1_dict)
        self.provider_listener2 = driver_dm.Listener(
            **self.provider_listener2_dict)
        self.provider_listener1.default_pool = self.provider_pool1
        self.provider_listener2.default_pool = self.provider_pool2
        self.provider_listener1.l7policies = self.provider_l7policies

        self.provider_listeners = [self.provider_listener1,
                                   self.provider_listener2]

        self.test_vip_dict = {constants.IP_ADDRESS: self.ip_address,
                              constants.NETWORK_ID: self.network_id,
                              constants.PORT_ID: self.port_id,
                              lib_consts.SUBNET_ID: self.subnet_id,
                              constants.QOS_POLICY_ID: self.qos_policy_id}

        self.provider_vip_dict = {
            lib_consts.VIP_ADDRESS: self.ip_address,
            lib_consts.VIP_NETWORK_ID: self.network_id,
            lib_consts.VIP_PORT_ID: self.port_id,
            lib_consts.VIP_SUBNET_ID: self.subnet_id,
            lib_consts.VIP_QOS_POLICY_ID: self.qos_policy_id}

        self.db_vip = data_models.Vip(
            ip_address=self.ip_address,
            network_id=self.network_id,
            port_id=self.port_id,
            subnet_id=self.subnet_id,
            qos_policy_id=self.qos_policy_id)

        self.test_loadbalancer1_dict = {
            lib_consts.NAME: self.lb_name,
            lib_consts.DESCRIPTION: self.lb_description,
            constants.ENABLED: True,
            lib_consts.PROVISIONING_STATUS: lib_consts.PENDING_UPDATE,
            lib_consts.OPERATING_STATUS: lib_consts.OFFLINE,
            constants.TOPOLOGY: constants.TOPOLOGY_ACTIVE_STANDBY,
            constants.VRRP_GROUP: None,
            constants.PROVIDER: constants.AMPHORA,
            constants.SERVER_GROUP_ID: uuidutils.generate_uuid(),
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.ID: self.lb_id, constants.FLAVOR_ID: self.flavor_id,
            constants.TAGS: ['test_tag']}

        self.provider_loadbalancer_dict = {
            lib_consts.ADDITIONAL_VIPS: None,
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.DESCRIPTION: self.lb_description,
            lib_consts.FLAVOR: {"something": "else"},
            lib_consts.LISTENERS: None,
            lib_consts.LOADBALANCER_ID: self.lb_id,
            lib_consts.NAME: self.lb_name,
            lib_consts.POOLS: None,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.VIP_ADDRESS: self.ip_address,
            lib_consts.VIP_NETWORK_ID: self.network_id,
            lib_consts.VIP_PORT_ID: self.port_id,
            lib_consts.VIP_QOS_POLICY_ID: self.qos_policy_id,
            lib_consts.VIP_SUBNET_ID: self.subnet_id}

        self.provider_loadbalancer_tree_dict = {
            lib_consts.ADDITIONAL_VIPS: None,
            lib_consts.ADMIN_STATE_UP: True,
            lib_consts.DESCRIPTION: self.lb_description,
            lib_consts.FLAVOR: {"something": "else"},
            lib_consts.LISTENERS: None,
            lib_consts.LOADBALANCER_ID: self.lb_id,
            lib_consts.NAME: self.lb_name,
            lib_consts.POOLS: None,
            lib_consts.PROJECT_ID: self.project_id,
            lib_consts.VIP_ADDRESS: self.ip_address,
            lib_consts.VIP_NETWORK_ID: self.network_id,
            lib_consts.VIP_PORT_ID: self.port_id,
            lib_consts.VIP_QOS_POLICY_ID: self.qos_policy_id,
            lib_consts.VIP_SUBNET_ID: self.subnet_id}
