# Copyright 2019 Red Hat, Inc. All rights reserved.
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

import copy
import multiprocessing
from unittest import mock

from octavia_lib.api.drivers import driver_lib as octavia_driver_lib
from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from stevedore import driver as stevedore_driver

from octavia.api.drivers.driver_agent import driver_listener
from octavia.common import config
from octavia.common import constants
from octavia.db import repositories
from octavia.tests.common import sample_certs
from octavia.tests.common import sample_data_models
from octavia.tests.functional.db import base

from oslo_log import log as logging
LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class DriverAgentTest(base.OctaviaDBTestBase):

    def _process_cleanup(self):
        self.exit_event.set()
        self.status_listener_proc.join(5)
        self.stats_listener_proc.join(5)
        self.get_listener_proc.join(5)

    def setUp(self):
        status_socket_file = '/tmp/octavia-{}.status.sock'.format(
            uuidutils.generate_uuid())
        stats_socket_file = '/tmp/octavia-{}.stats.sock'.format(
            uuidutils.generate_uuid())
        get_socket_file = '/tmp/octavia-{}.get.sock'.format(
            uuidutils.generate_uuid())
        sqlite_db_file = '/tmp/octavia-{}.sqlite.db'.format(
            uuidutils.generate_uuid())
        sqlite_db_connection = 'sqlite:///{}'.format(sqlite_db_file)

        # Note that because the driver agent is a multi-process
        # agent we must use a sqlite file rather than an
        # in-memory instance.
        super().setUp(
            connection_string=sqlite_db_connection)

        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))
        conf.config(group="driver_agent",
                    status_socket_path=status_socket_file)
        conf.config(group="driver_agent",
                    stats_socket_path=stats_socket_file)
        conf.config(group="driver_agent", status_request_timeout=1)
        conf.config(group="driver_agent", get_socket_path=get_socket_file)
        conf.config(group="certificates", cert_manager='local_cert_manager')
        conf.config(group="certificates", storage_path='/tmp')

        # Set up the certificate
        cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver
        self.cert_ref = cert_manager.store_cert(
            None,
            sample_certs.X509_CERT,
            sample_certs.X509_CERT_KEY_ENCRYPTED,
            sample_certs.X509_IMDS,
            private_key_passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE)
        self.addCleanup(cert_manager.delete_cert, None, self.cert_ref)

        self.exit_event = multiprocessing.Event()

        self.status_listener_proc = multiprocessing.Process(
            name='status_listener', target=driver_listener.status_listener,
            args=(self.exit_event,))
        # TODO(johnsom) Remove once https://bugs.python.org/issue6721
        #               is resolved.
        self.status_listener_proc.daemon = True

        self.status_listener_proc.start()

        self.stats_listener_proc = multiprocessing.Process(
            name='stats_listener', target=driver_listener.stats_listener,
            args=(self.exit_event,))
        # TODO(johnsom) Remove once https://bugs.python.org/issue6721
        #               is resolved.
        self.stats_listener_proc.daemon = True

        self.stats_listener_proc.start()

        self.get_listener_proc = multiprocessing.Process(
            name='get_listener', target=driver_listener.get_listener,
            args=(self.exit_event,))
        # TODO(johnsom) Remove once https://bugs.python.org/issue6721
        #               is resolved.
        self.get_listener_proc.daemon = True

        self.get_listener_proc.start()

        self.addCleanup(self._process_cleanup)

        self.driver_lib = octavia_driver_lib.DriverLibrary(
            status_socket=status_socket_file,
            stats_socket=stats_socket_file,
            get_socket=get_socket_file)

        self.sample_data = sample_data_models.SampleDriverDataModels()
        self.repos = repositories.Repositories()

        # Create the full load balancer in the database
        self.tls_container_dict = {
            lib_consts.CERTIFICATE: sample_certs.X509_CERT.decode('utf-8'),
            lib_consts.ID: sample_certs.X509_CERT_SHA1,
            lib_consts.INTERMEDIATES: [
                i.decode('utf-8') for i in sample_certs.X509_IMDS_LIST],
            lib_consts.PASSPHRASE: None,
            lib_consts.PRIMARY_CN: sample_certs.X509_CERT_CN,
            lib_consts.PRIVATE_KEY: sample_certs.X509_CERT_KEY.decode('utf-8')}

        # ### Create load balancer
        self.repos.flavor_profile.create(
            self.session, id=self.sample_data.flavor_profile_id,
            provider_name=constants.AMPHORA,
            flavor_data='{"something": "else"}')
        self.repos.flavor.create(
            self.session, id=self.sample_data.flavor_id,
            enabled=True, flavor_profile_id=self.sample_data.flavor_profile_id)
        self.repos.create_load_balancer_and_vip(
            self.session, self.sample_data.test_loadbalancer1_dict,
            self.sample_data.test_vip_dict)

        # ### Create Pool
        pool_dict = copy.deepcopy(self.sample_data.test_pool1_dict)

        pool_dict[constants.LOAD_BALANCER_ID] = self.sample_data.lb_id

        # Use a live certificate
        pool_dict[constants.TLS_CERTIFICATE_ID] = self.cert_ref
        pool_dict[constants.CA_TLS_CERTIFICATE_ID] = self.cert_ref
        pool_dict[constants.CRL_CONTAINER_ID] = self.cert_ref

        # Remove items that are linked in the DB
        del pool_dict[lib_consts.MEMBERS]
        del pool_dict[constants.HEALTH_MONITOR]
        del pool_dict[lib_consts.SESSION_PERSISTENCE]
        del pool_dict[lib_consts.LISTENERS]
        del pool_dict[lib_consts.L7POLICIES]

        self.repos.pool.create(self.session, **pool_dict)

        self.repos.session_persistence.create(
            self.session, pool_id=self.sample_data.pool1_id,
            type=lib_consts.SESSION_PERSISTENCE_SOURCE_IP)

        self.provider_pool_dict = copy.deepcopy(
            self.sample_data.provider_pool1_dict)
        self.provider_pool_dict[
            constants.LISTENER_ID] = self.sample_data.listener1_id

        # Fix for render_unsets = True
        self.provider_pool_dict[
            lib_consts.SESSION_PERSISTENCE][lib_consts.COOKIE_NAME] = None
        self.provider_pool_dict[lib_consts.SESSION_PERSISTENCE][
            lib_consts.PERSISTENCE_GRANULARITY] = None
        self.provider_pool_dict[lib_consts.SESSION_PERSISTENCE][
            lib_consts.PERSISTENCE_TIMEOUT] = None

        # Use a live certificate
        self.provider_pool_dict[
            lib_consts.TLS_CONTAINER_DATA] = self.tls_container_dict
        self.provider_pool_dict[lib_consts.TLS_CONTAINER_REF] = self.cert_ref
        self.provider_pool_dict[
            lib_consts.CA_TLS_CONTAINER_DATA] = (
                sample_certs.X509_CERT.decode('utf-8'))
        self.provider_pool_dict[
            lib_consts.CA_TLS_CONTAINER_REF] = self.cert_ref
        self.provider_pool_dict[
            lib_consts.CRL_CONTAINER_DATA] = (
                sample_certs.X509_CERT.decode('utf-8'))
        self.provider_pool_dict[lib_consts.CRL_CONTAINER_REF] = self.cert_ref

        # ### Create Member
        member_dict = copy.deepcopy(self.sample_data.test_member1_dict)
        self.repos.member.create(self.session, **member_dict)
        self.provider_pool_dict[lib_consts.MEMBERS] = [
            self.sample_data.provider_member1_dict]

        # ### Create Health Monitor
        hm_dict = copy.deepcopy(self.sample_data.test_hm1_dict)
        self.repos.health_monitor.create(self.session, **hm_dict)
        self.provider_pool_dict[
            lib_consts.HEALTHMONITOR] = self.sample_data.provider_hm1_dict

        # ### Create Listener
        listener_dict = copy.deepcopy(self.sample_data.test_listener1_dict)
        listener_dict[lib_consts.DEFAULT_POOL_ID] = self.sample_data.pool1_id

        # Remove items that are linked in the DB
        del listener_dict[lib_consts.L7POLICIES]
        del listener_dict[lib_consts.DEFAULT_POOL]
        del listener_dict[constants.SNI_CONTAINERS]

        # Use a live certificate
        listener_dict[constants.TLS_CERTIFICATE_ID] = self.cert_ref
        listener_dict[constants.CLIENT_CA_TLS_CERTIFICATE_ID] = self.cert_ref
        listener_dict[constants.CLIENT_CRL_CONTAINER_ID] = self.cert_ref

        self.repos.listener.create(self.session,
                                   **listener_dict)
        self.repos.sni.create(self.session,
                              listener_id=self.sample_data.listener1_id,
                              tls_container_id=self.cert_ref, position=1)

        # Add our live certs in that differ from the fake certs in sample_data
        self.provider_listener_dict = copy.deepcopy(
            self.sample_data.provider_listener1_dict)
        self.provider_listener_dict[
            lib_consts.DEFAULT_TLS_CONTAINER_REF] = self.cert_ref
        self.provider_listener_dict[
            lib_consts.DEFAULT_TLS_CONTAINER_DATA] = self.tls_container_dict
        self.provider_listener_dict[
            lib_consts.CLIENT_CA_TLS_CONTAINER_REF] = self.cert_ref
        self.provider_listener_dict[
            lib_consts.CLIENT_CA_TLS_CONTAINER_DATA] = (
                sample_certs.X509_CERT.decode('utf-8'))
        self.provider_listener_dict[
            lib_consts.CLIENT_CRL_CONTAINER_REF] = self.cert_ref
        self.provider_listener_dict[
            lib_consts.CLIENT_CRL_CONTAINER_DATA] = (
                sample_certs.X509_CERT.decode('utf-8'))
        self.provider_listener_dict[
            lib_consts.SNI_CONTAINER_DATA] = [self.tls_container_dict]
        self.provider_listener_dict[
            lib_consts.SNI_CONTAINER_REFS] = [self.cert_ref]

        self.provider_listener_dict[
            lib_consts.DEFAULT_POOL] = self.provider_pool_dict
        self.provider_listener_dict[
            lib_consts.DEFAULT_POOL_ID] = self.sample_data.pool1_id

        self.provider_listener_dict[lib_consts.L7POLICIES] = [
            self.sample_data.provider_l7policy1_dict]

        # ### Create L7 Policy
        l7policy_dict = copy.deepcopy(self.sample_data.test_l7policy1_dict)
        del l7policy_dict[lib_consts.L7RULES]
        self.repos.l7policy.create(self.session, **l7policy_dict)

        # ### Create L7 Rules
        l7rule_dict = copy.deepcopy(self.sample_data.test_l7rule1_dict)
        self.repos.l7rule.create(self.session, **l7rule_dict)
        l7rule2_dict = copy.deepcopy(self.sample_data.test_l7rule2_dict)
        self.repos.l7rule.create(self.session, **l7rule2_dict)

        self.session.commit()

        self.provider_lb_dict = copy.deepcopy(
            self.sample_data.provider_loadbalancer_tree_dict)
        self.provider_lb_dict[lib_consts.POOLS] = [self.provider_pool_dict]
        self.provider_lb_dict[
            lib_consts.LISTENERS] = [self.provider_listener_dict]

    def _compare_load_balancer_dicts(self,
                                     provider_lb_dict,
                                     result_dict):
        for key in (lib_consts.LOADBALANCER_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.VIP_ADDRESS,
                    lib_consts.VIP_NETWORK_ID,
                    lib_consts.VIP_SUBNET_ID,
                    lib_consts.VIP_PORT_ID,
                    lib_consts.VIP_QOS_POLICY_ID,
                    lib_consts.FLAVOR,
                    lib_consts.AVAILABILITY_ZONE,
                    lib_consts.ADDITIONAL_VIPS):
            self.assertEqual(provider_lb_dict.get(key),
                             result_dict.get(key))

        provider_listener_dicts = provider_lb_dict[lib_consts.LISTENERS]
        result_listener_dicts = result_dict[lib_consts.LISTENERS]

        self.assertEqual(len(provider_listener_dicts),
                         len(result_listener_dicts))

        for listener_dicts in zip(provider_listener_dicts,
                                  result_listener_dicts):
            provider_listener_dict = listener_dicts[0]
            result_listener_dict = listener_dicts[1]
            self._compare_listener_dicts(provider_listener_dict,
                                         result_listener_dict)

        self.assertEqual(len(provider_lb_dict[lib_consts.POOLS]),
                         len(result_dict[lib_consts.POOLS]))

        for pool_dicts in zip(provider_lb_dict[lib_consts.POOLS],
                              result_dict[lib_consts.POOLS]):
            provider_pool_dict = pool_dicts[0]
            result_pool_dict = pool_dicts[1]
            self._compare_pool_dicts(provider_pool_dict,
                                     result_pool_dict)

    def _compare_listener_dicts(self,
                                provider_listener_dict,
                                result_listener_dict):
        for key in (lib_consts.LISTENER_ID,
                    lib_consts.LOADBALANCER_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.PROTOCOL,
                    lib_consts.PROTOCOL_PORT,
                    lib_consts.CONNECTION_LIMIT,
                    lib_consts.DEFAULT_POOL_ID,
                    lib_consts.TIMEOUT_CLIENT_DATA,
                    lib_consts.TIMEOUT_MEMBER_CONNECT,
                    lib_consts.TIMEOUT_MEMBER_DATA,
                    lib_consts.TIMEOUT_TCP_INSPECT,
                    lib_consts.INSERT_HEADERS,
                    lib_consts.ALLOWED_CIDRS,
                    lib_consts.DEFAULT_TLS_CONTAINER_REF,
                    lib_consts.DEFAULT_TLS_CONTAINER_DATA,
                    lib_consts.SNI_CONTAINER_REFS,
                    lib_consts.SNI_CONTAINER_DATA,
                    lib_consts.CLIENT_CA_TLS_CONTAINER_REF,
                    lib_consts.CLIENT_CA_TLS_CONTAINER_DATA,
                    lib_consts.CLIENT_AUTHENTICATION,
                    lib_consts.CLIENT_CRL_CONTAINER_REF,
                    lib_consts.CLIENT_CRL_CONTAINER_DATA,
                    lib_consts.TLS_CIPHERS,
                    lib_consts.TLS_VERSIONS):
            self.assertEqual(provider_listener_dict.get(key),
                             result_listener_dict.get(key))

        provider_l7policy_dicts = provider_listener_dict.get(
            lib_consts.L7POLICIES)
        result_l7policy_dicts = result_listener_dict.get(
            lib_consts.L7POLICIES)

        self.assertEqual(len(provider_l7policy_dicts),
                         len(result_l7policy_dicts))

        for l7policy_dicts in zip(provider_l7policy_dicts,
                                  result_l7policy_dicts):
            provider_l7policy_dict = l7policy_dicts[0]
            result_l7policy_dict = l7policy_dicts[1]
            self._compare_l7policy_dicts(provider_l7policy_dict,
                                         result_l7policy_dict)

    def _compare_l7policy_dicts(self,
                                provider_l7policy_dict,
                                result_l7policy_dict):
        for key in (lib_consts.L7POLICY_ID,
                    lib_consts.LISTENER_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.ACTION,
                    lib_consts.POSITION,
                    lib_consts.REDIRECT_POOL_ID,
                    lib_consts.REDIRECT_URL,
                    lib_consts.REDIRECT_PREFIX,
                    lib_consts.REDIRECT_HTTP_CODE):
            self.assertEqual(provider_l7policy_dict.get(key),
                             result_l7policy_dict.get(key))

        provider_l7rule_dicts = provider_l7policy_dict.get(lib_consts.L7RULES)
        result_l7rule_dicts = result_l7policy_dict.get(lib_consts.L7RULES)

        if provider_l7rule_dicts or result_l7rule_dicts:
            self.assertIsNotNone(provider_l7rule_dicts)
            self.assertIsNotNone(result_l7rule_dicts)

            self.assertEqual(len(provider_l7rule_dicts),
                             len(result_l7rule_dicts))

            for l7rule_dicts in zip(provider_l7rule_dicts,
                                    result_l7rule_dicts):
                provider_l7rule_dict = l7rule_dicts[0]
                result_l7rule_dict = l7rule_dicts[1]
                self._compare_l7rule_dicts(provider_l7rule_dict,
                                           result_l7rule_dict)

    def _compare_l7rule_dicts(self,
                              provider_l7rule_dict,
                              result_l7rule_dict):
        for key in (lib_consts.L7RULE_ID,
                    lib_consts.L7POLICY_ID,
                    lib_consts.LISTENER_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.TYPE,
                    lib_consts.COMPARE_TYPE,
                    lib_consts.KEY,
                    lib_consts.VALUE,
                    lib_consts.INVERT):
            self.assertEqual(provider_l7rule_dict.get(key),
                             result_l7rule_dict.get(key))

    def _compare_pool_dicts(self,
                            provider_pool_dict,
                            result_pool_dict):
        for key in (lib_consts.POOL_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.LB_ALGORITHM,
                    lib_consts.LOADBALANCER_ID,
                    lib_consts.PROTOCOL,
                    lib_consts.SESSION_PERSISTENCE,
                    lib_consts.TLS_ENABLED,
                    lib_consts.TLS_CONTAINER_REF,
                    lib_consts.TLS_CONTAINER_DATA,
                    lib_consts.CA_TLS_CONTAINER_REF,
                    lib_consts.CA_TLS_CONTAINER_DATA,
                    lib_consts.CRL_CONTAINER_REF,
                    lib_consts.CRL_CONTAINER_DATA,
                    lib_consts.TLS_CIPHERS,
                    lib_consts.TLS_VERSIONS,
                    lib_consts.ALPN_PROTOCOLS):
            self.assertEqual(provider_pool_dict.get(key),
                             result_pool_dict.get(key))

        provider_hm_dict = provider_pool_dict.get(
            lib_consts.HEALTHMONITOR)
        result_hm_dict = result_pool_dict.get(
            lib_consts.HEALTHMONITOR)
        if provider_hm_dict or result_hm_dict:
            self._compare_hm_dicts(provider_hm_dict,
                                   result_hm_dict)

        provider_member_dicts = provider_pool_dict.get(
            lib_consts.MEMBERS)
        result_member_dicts = result_pool_dict.get(
            lib_consts.MEMBERS)
        self.assertEqual(len(provider_member_dicts),
                         len(result_member_dicts))

        for member_dicts in zip(provider_member_dicts,
                                result_member_dicts):
            provider_member_dict = member_dicts[0]
            result_member_dict = member_dicts[1]
            self._compare_member_dicts(provider_member_dict,
                                       result_member_dict)

    def _compare_hm_dicts(self,
                          provider_hm_dict,
                          result_hm_dict):
        for key in (lib_consts.HEALTHMONITOR_ID,
                    lib_consts.POOL_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.TYPE,
                    lib_consts.DELAY,
                    lib_consts.TIMEOUT,
                    lib_consts.MAX_RETRIES,
                    lib_consts.MAX_RETRIES_DOWN,
                    lib_consts.DOMAIN_NAME,
                    lib_consts.EXPECTED_CODES,
                    lib_consts.HTTP_METHOD,
                    lib_consts.HTTP_VERSION,
                    lib_consts.URL_PATH):
            self.assertEqual(provider_hm_dict.get(key),
                             result_hm_dict.get(key))

    def _compare_member_dicts(self,
                              provider_member_dict,
                              result_member_dict):
        for key in (lib_consts.MEMBER_ID,
                    lib_consts.POOL_ID,
                    lib_consts.NAME,
                    lib_consts.DESCRIPTION,
                    lib_consts.PROJECT_ID,
                    lib_consts.ADMIN_STATE_UP,
                    lib_consts.ADDRESS,
                    lib_consts.PROTOCOL_PORT,
                    lib_consts.MONITOR_ADDRESS,
                    lib_consts.MONITOR_PORT,
                    lib_consts.SUBNET_ID,
                    lib_consts.WEIGHT,
                    lib_consts.BACKUP):
            self.assertEqual(provider_member_dict.get(key),
                             result_member_dict.get(key))

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_loadbalancer(self):
        result = self.driver_lib.get_loadbalancer(self.sample_data.lb_id)
        result_dict = result.to_dict(render_unsets=True, recurse=True)

        self._compare_load_balancer_dicts(self.provider_lb_dict,
                                          result_dict)

        # Test non-existent load balancer
        result = self.driver_lib.get_loadbalancer('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_listener(self):
        result = self.driver_lib.get_listener(self.sample_data.listener1_id)
        result_dict = result.to_dict(render_unsets=True, recurse=True)

        self._compare_listener_dicts(self.provider_listener_dict,
                                     result_dict)

        # Test non-existent listener
        result = self.driver_lib.get_listener('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_pool(self):
        result = self.driver_lib.get_pool(self.sample_data.pool1_id)
        result_dict = result.to_dict(render_unsets=True, recurse=True)

        self._compare_pool_dicts(self.provider_pool_dict,
                                 result_dict)

        # Test non-existent pool
        result = self.driver_lib.get_pool('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_member(self):
        result = self.driver_lib.get_member(self.sample_data.member1_id)
        result_dict = result.to_dict(render_unsets=True)

        self._compare_member_dicts(self.sample_data.provider_member1_dict,
                                   result_dict)

        # Test non-existent member
        result = self.driver_lib.get_member('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_healthmonitor(self):
        result = self.driver_lib.get_healthmonitor(self.sample_data.hm1_id)
        result_dict = result.to_dict(render_unsets=True)

        self._compare_hm_dicts(self.sample_data.provider_hm1_dict,
                               result_dict)

        # Test non-existent health monitor
        result = self.driver_lib.get_healthmonitor('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_l7policy(self):
        result = self.driver_lib.get_l7policy(self.sample_data.l7policy1_id)
        result_dict = result.to_dict(render_unsets=True, recurse=True)

        self._compare_l7policy_dicts(
            self.sample_data.provider_l7policy1_dict,
            result_dict)

        # Test non-existent L7 policy
        result = self.driver_lib.get_l7policy('bogus')
        self.assertIsNone(result)

    @mock.patch('octavia_lib.api.drivers.driver_lib.SOCKET_TIMEOUT', 30)
    def test_get_l7rule(self):
        result = self.driver_lib.get_l7rule(self.sample_data.l7rule1_id)
        result_dict = result.to_dict(render_unsets=True)

        self._compare_l7rule_dicts(
            self.sample_data.provider_l7rule1_dict,
            result_dict)

        # Test non-existent L7 rule
        result = self.driver_lib.get_l7rule('bogus')
        self.assertIsNone(result)

    def test_update_load_balancer_status(self):
        # Add a new member
        member_dict = copy.deepcopy(self.sample_data.test_member2_dict)
        self.repos.member.create(self.session, **member_dict)
        self.session.commit()

        result = self.driver_lib.get_member(member_dict[lib_consts.ID])
        self.assertEqual(self.sample_data.provider_member2_dict,
                         result.to_dict(render_unsets=True))

        # Test deleting a member
        status = {
            "loadbalancers": [
                {"id": self.sample_data.lb_id,
                 "provisioning_status": "ACTIVE",
                 "operating_status": "ONLINE"}
            ],
            "healthmonitors": [],
            "l7policies": [],
            "l7rules": [],
            "listeners": [],
            "members": [
                {"id": member_dict[lib_consts.ID],
                 "provisioning_status": "DELETED"}
            ],
            "pools": []
        }

        self.driver_lib.update_loadbalancer_status(status)
        result = self.driver_lib.get_member(member_dict[lib_consts.ID])
        self.assertIsNone(result)

        # Test deleting an already deleted member
        # It should be silently ignored
        self.driver_lib.update_loadbalancer_status(status)
        result = self.driver_lib.get_member(member_dict[lib_consts.ID])
        self.assertIsNone(result)
