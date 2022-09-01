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
from unittest import mock

from octavia_lib.api.drivers import data_models as driver_dm
from octavia_lib.api.drivers import exceptions
from octavia_lib.common import constants as lib_consts
from oslo_utils import uuidutils

from octavia.api.drivers.amphora_driver.v2 import driver
from octavia.common import constants as consts
from octavia.network import base as network_base
from octavia.tests.common import sample_data_models
from octavia.tests.unit import base


class TestAmphoraDriver(base.TestRpc):
    def setUp(self):
        super().setUp()
        self.amp_driver = driver.AmphoraProviderDriver()
        self.sample_data = sample_data_models.SampleDriverDataModels()

    @mock.patch('octavia.common.utils.get_network_driver')
    def test_create_vip_port(self, mock_get_net_driver):
        mock_net_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_net_driver
        mock_net_driver.allocate_vip.return_value = self.sample_data.db_vip, []

        provider_vip_dict, add_vip_dicts = self.amp_driver.create_vip_port(
            self.sample_data.lb_id, self.sample_data.project_id,
            self.sample_data.provider_vip_dict,
            [self.sample_data.provider_additional_vip_dict])

        self.assertEqual(self.sample_data.provider_vip_dict, provider_vip_dict)
        self.assertFalse(add_vip_dicts)

    @mock.patch('octavia.common.utils.get_network_driver')
    def test_create_vip_port_without_port_security_enabled(
            self, mock_get_net_driver):
        mock_net_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_net_driver
        network = mock.MagicMock()
        network.port_security_enabled = False
        mock_net_driver.get_network.return_value = network
        mock_net_driver.allocate_vip.return_value = self.sample_data.db_vip

        self.assertRaises(exceptions.DriverError,
                          self.amp_driver.create_vip_port,
                          self.sample_data.lb_id, self.sample_data.project_id,
                          self.sample_data.provider_vip_dict,
                          [self.sample_data.provider_additional_vip_dict])

    @mock.patch('octavia.common.utils.get_network_driver')
    def test_create_vip_port_failed(self, mock_get_net_driver):
        mock_net_driver = mock.MagicMock()
        mock_get_net_driver.return_value = mock_net_driver
        mock_net_driver.allocate_vip.side_effect = (
            network_base.AllocateVIPException())

        self.assertRaises(exceptions.DriverError,
                          self.amp_driver.create_vip_port,
                          self.sample_data.lb_id, self.sample_data.project_id,
                          self.sample_data.provider_vip_dict,
                          [self.sample_data.provider_additional_vip_dict])

    # Load Balancer
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_create(self, mock_cast):
        provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id)
        self.amp_driver.loadbalancer_create(provider_lb)
        payload = {consts.LOADBALANCER: provider_lb.to_dict(),
                   consts.FLAVOR: None,
                   consts.AVAILABILITY_ZONE: None}
        mock_cast.assert_called_with({}, 'create_load_balancer', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_delete(self, mock_cast):
        provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id)
        self.amp_driver.loadbalancer_delete(provider_lb)
        payload = {consts.LOADBALANCER: provider_lb.to_dict(),
                   'cascade': False}
        mock_cast.assert_called_with({}, 'delete_load_balancer', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_failover(self, mock_cast):
        self.amp_driver.loadbalancer_failover(self.sample_data.lb_id)
        payload = {consts.LOAD_BALANCER_ID: self.sample_data.lb_id}
        mock_cast.assert_called_with({}, 'failover_load_balancer', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_update(self, mock_cast):
        old_provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id)
        provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id, admin_state_up=True)
        lb_dict = {'enabled': True}
        self.amp_driver.loadbalancer_update(old_provider_lb, provider_lb)
        payload = {consts.ORIGINAL_LOADBALANCER: old_provider_lb.to_dict(),
                   consts.LOAD_BALANCER_UPDATES: lb_dict}
        mock_cast.assert_called_with({}, 'update_load_balancer', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_update_name(self, mock_cast):
        old_provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id)
        provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id, name='Great LB')
        lb_dict = {'name': 'Great LB'}
        self.amp_driver.loadbalancer_update(old_provider_lb, provider_lb)
        payload = {consts.ORIGINAL_LOADBALANCER: old_provider_lb.to_dict(),
                   consts.LOAD_BALANCER_UPDATES: lb_dict}
        mock_cast.assert_called_with({}, 'update_load_balancer', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_loadbalancer_update_qos(self, mock_cast):
        qos_policy_id = uuidutils.generate_uuid()
        old_provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id)
        provider_lb = driver_dm.LoadBalancer(
            loadbalancer_id=self.sample_data.lb_id,
            vip_qos_policy_id=qos_policy_id)
        lb_dict = {'vip': {'qos_policy_id': qos_policy_id}}
        self.amp_driver.loadbalancer_update(old_provider_lb, provider_lb)
        payload = {consts.ORIGINAL_LOADBALANCER: old_provider_lb.to_dict(),
                   consts.LOAD_BALANCER_UPDATES: lb_dict}
        mock_cast.assert_called_with({}, 'update_load_balancer', **payload)

    # Listener
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_create(self, mock_cast):
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id,
            protocol=consts.PROTOCOL_HTTPS,
            alpn_protocols=consts.AMPHORA_SUPPORTED_ALPN_PROTOCOLS)
        self.amp_driver.listener_create(provider_listener)
        payload = {consts.LISTENER: provider_listener.to_dict()}
        mock_cast.assert_called_with({}, 'create_listener', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_create_unsupported_alpn(self, mock_cast):
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id,
            protocol=consts.PROTOCOL_HTTPS)
        provider_listener.alpn_protocols = ['http/1.1', 'eureka']
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.listener_create,
            provider_listener)
        mock_cast.assert_not_called()

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_create_unsupported_protocol(self, mock_cast):
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id,
            protocol='UNSUPPORTED_PROTO')
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.listener_create,
            provider_listener)
        mock_cast.assert_not_called()

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_delete(self, mock_cast):
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id)
        self.amp_driver.listener_delete(provider_listener)
        payload = {consts.LISTENER: provider_listener.to_dict()}
        mock_cast.assert_called_with({}, 'delete_listener', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_update(self, mock_cast):
        old_provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id)
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id, admin_state_up=False)
        listener_dict = provider_listener.to_dict()
        listener_dict['admin_state_up'] = False
        self.amp_driver.listener_update(old_provider_listener,
                                        provider_listener)
        payload = {consts.ORIGINAL_LISTENER: old_provider_listener.to_dict(),
                   consts.LISTENER_UPDATES: listener_dict}
        mock_cast.assert_called_with({}, 'update_listener', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_update_name(self, mock_cast):
        old_provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id)
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id, name='Great Listener')
        listener_dict = provider_listener.to_dict()
        listener_dict['name'] = 'Great Listener'
        self.amp_driver.listener_update(old_provider_listener,
                                        provider_listener)
        payload = {consts.ORIGINAL_LISTENER: old_provider_listener.to_dict(),
                   consts.LISTENER_UPDATES: listener_dict}
        mock_cast.assert_called_with({}, 'update_listener', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_listener_update_unsupported_alpn(self, mock_cast):
        old_provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id)
        provider_listener = driver_dm.Listener(
            listener_id=self.sample_data.listener1_id,
            alpn_protocols=['http/1.1', 'eureka'])
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.listener_update,
            old_provider_listener,
            provider_listener)

    # Pool
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_create(self, mock_cast):
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id,
            lb_algorithm=consts.LB_ALGORITHM_ROUND_ROBIN,
            alpn_protocols=consts.AMPHORA_SUPPORTED_ALPN_PROTOCOLS)
        self.amp_driver.pool_create(provider_pool)
        payload = {consts.POOL: provider_pool.to_dict(recurse=True)}
        mock_cast.assert_called_with({}, 'create_pool', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_create_unsupported_algorithm(self, mock_cast):
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        provider_pool.lb_algorithm = 'foo'
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.pool_create,
            provider_pool)
        mock_cast.assert_not_called()

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_create_unsupported_alpn(self, mock_cast):
        provider_pool = driver_dm.Pool(pool_id=self.sample_data.pool1_id)
        provider_pool.alpn_protocols = ['http/1.1', 'eureka']
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.pool_create,
            provider_pool)
        mock_cast.assert_not_called()

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_delete(self, mock_cast):
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        self.amp_driver.pool_delete(provider_pool)
        payload = {consts.POOL: provider_pool.to_dict()}
        mock_cast.assert_called_with({}, 'delete_pool', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_update(self, mock_cast):
        old_provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id, admin_state_up=True,
            ca_tls_container_data='CA DATA', ca_tls_container_ref='CA REF',
            crl_container_data='CRL DATA', crl_container_ref='CRL REF',
            description='TEST DESCRIPTION', name='TEST NAME',
            lb_algorithm=consts.LB_ALGORITHM_SOURCE_IP,
            session_persistence='FAKE SP', tls_container_data='TLS DATA',
            tls_container_ref='TLS REF', tls_enabled=False)
        pool_dict = {'description': 'TEST DESCRIPTION',
                     'lb_algorithm': 'SOURCE_IP', 'name': 'TEST NAME',
                     'session_persistence': 'FAKE SP', 'tls_enabled': False,
                     'enabled': True, 'tls_certificate_id': 'TLS REF',
                     'ca_tls_certificate_id': 'CA REF',
                     'crl_container_id': 'CRL REF'}
        self.amp_driver.pool_update(old_provider_pool, provider_pool)
        payload = {consts.ORIGINAL_POOL: old_provider_pool.to_dict(),
                   consts.POOL_UPDATES: pool_dict}
        mock_cast.assert_called_with({}, 'update_pool', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_update_name(self, mock_cast):
        old_provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id, name='Great pool',
            admin_state_up=True, tls_enabled=True)
        pool_dict = {'name': 'Great pool',
                     'enabled': True,
                     'tls_enabled': True}
        self.amp_driver.pool_update(old_provider_pool, provider_pool)
        payload = {consts.ORIGINAL_POOL: old_provider_pool.to_dict(),
                   consts.POOL_UPDATES: pool_dict}
        mock_cast.assert_called_with({}, 'update_pool', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_update_unsupported_algorithm(self, mock_cast):
        old_provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        provider_pool = driver_dm.Pool(
            pool_id=self.sample_data.pool1_id)
        provider_pool.lb_algorithm = 'foo'
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.pool_update,
            old_provider_pool,
            provider_pool)
        mock_cast.assert_not_called()

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_pool_update_unsupported_alpn(self, mock_cast):
        old_provider_pool = driver_dm.Pool(pool_id=self.sample_data.pool1_id)
        provider_pool = driver_dm.Pool(
            listener_id=self.sample_data.pool1_id,
            alpn_protocols=['http/1.1', 'eureka'])
        self.assertRaises(
            exceptions.UnsupportedOptionError,
            self.amp_driver.pool_update,
            old_provider_pool,
            provider_pool)

    # Member
    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_create(self, mock_cast, mock_pool_get, mock_session):
        provider_member = driver_dm.Member(
            member_id=self.sample_data)
        self.amp_driver.member_create(provider_member)
        payload = {consts.MEMBER: provider_member.to_dict()}
        mock_cast.assert_called_with({}, 'create_member', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_create_udp_ipv4(self, mock_cast, mock_pool_get,
                                    mock_session):
        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "192.0.1.1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = consts.PROTOCOL_UDP
        mock_pool.listeners = [mock_listener]
        mock_pool_get.return_value = mock_pool

        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id,
            address="192.0.2.1")
        self.amp_driver.member_create(provider_member)
        payload = {consts.MEMBER: provider_member.to_dict()}
        mock_cast.assert_called_with({}, 'create_member', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_create_udp_ipv4_ipv6(self, mock_cast, mock_pool_get,
                                         mock_session):
        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "fe80::1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = consts.PROTOCOL_UDP
        mock_pool.listeners = [mock_listener]
        mock_pool_get.return_value = mock_pool

        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id,
            address="192.0.2.1")
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.member_create,
                          provider_member)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_create_sctp_ipv4(self, mock_cast, mock_pool_get,
                                     mock_session):
        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "192.0.1.1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = lib_consts.PROTOCOL_SCTP
        mock_pool.listeners = [mock_listener]
        mock_pool_get.return_value = mock_pool

        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id,
            address="192.0.2.1")
        self.amp_driver.member_create(provider_member)
        payload = {consts.MEMBER: provider_member.to_dict()}
        mock_cast.assert_called_with({}, 'create_member', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_create_sctp_ipv4_ipv6(self, mock_cast, mock_pool_get,
                                          mock_session):
        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "fe80::1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = lib_consts.PROTOCOL_SCTP
        mock_pool.listeners = [mock_listener]
        mock_pool_get.return_value = mock_pool

        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id,
            address="192.0.2.1")
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.member_create,
                          provider_member)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_delete(self, mock_cast):
        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id)
        self.amp_driver.member_delete(provider_member)
        payload = {consts.MEMBER: provider_member.to_dict()}
        mock_cast.assert_called_with({}, 'delete_member', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_update(self, mock_cast):
        old_provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id)
        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id, admin_state_up=True)
        member_dict = provider_member.to_dict()
        member_dict.pop(consts.MEMBER_ID)
        member_dict['enabled'] = member_dict.pop('admin_state_up')
        self.amp_driver.member_update(old_provider_member,
                                      provider_member)
        payload = {consts.ORIGINAL_MEMBER: old_provider_member.to_dict(),
                   consts.MEMBER_UPDATES: member_dict}
        mock_cast.assert_called_with({}, 'update_member', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_update_name(self, mock_cast):
        old_provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id)
        provider_member = driver_dm.Member(
            member_id=self.sample_data.member1_id, name='Great member')
        member_dict = provider_member.to_dict()
        member_dict.pop(consts.MEMBER_ID)
        self.amp_driver.member_update(old_provider_member,
                                      provider_member)
        payload = {consts.ORIGINAL_MEMBER: old_provider_member.to_dict(),
                   consts.MEMBER_UPDATES: member_dict}
        mock_cast.assert_called_with({}, 'update_member', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_batch_update(self, mock_cast, mock_pool_get, mock_session):
        mock_pool = mock.MagicMock()
        mock_pool.members = self.sample_data.db_pool1_members
        mock_pool_get.return_value = mock_pool

        prov_mem_update = driver_dm.Member(
            member_id=self.sample_data.member2_id,
            pool_id=self.sample_data.pool1_id, admin_state_up=False,
            address='192.0.2.17', monitor_address='192.0.2.77',
            protocol_port=80, name='updated-member2')
        prov_new_member = driver_dm.Member(
            member_id=self.sample_data.member3_id,
            pool_id=self.sample_data.pool1_id,
            address='192.0.2.18', monitor_address='192.0.2.28',
            protocol_port=80, name='member3')
        prov_members = [prov_mem_update, prov_new_member]

        update_mem_dict = {'ip_address': '192.0.2.17',
                           'name': 'updated-member2',
                           'monitor_address': '192.0.2.77',
                           'id': self.sample_data.member2_id,
                           'enabled': False,
                           'protocol_port': 80,
                           'pool_id': self.sample_data.pool1_id}

        self.amp_driver.member_batch_update(
            self.sample_data.pool1_id, prov_members)

        payload = {
            'old_members': [self.sample_data.db_pool1_members[0].to_dict()],
            'new_members': [prov_new_member.to_dict()],
            'updated_members': [update_mem_dict]}
        mock_cast.assert_called_with({}, 'batch_update_members', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_batch_update_no_admin_addr(self, mock_cast,
                                               mock_pool_get, mock_session):
        mock_pool = mock.MagicMock()
        mock_pool.members = self.sample_data.db_pool1_members
        mock_pool_get.return_value = mock_pool

        prov_mem_update = driver_dm.Member(
            member_id=self.sample_data.member2_id,
            pool_id=self.sample_data.pool1_id,
            monitor_address='192.0.2.77',
            protocol_port=80, name='updated-member2')
        prov_new_member = driver_dm.Member(
            member_id=self.sample_data.member3_id,
            pool_id=self.sample_data.pool1_id,
            address='192.0.2.18', monitor_address='192.0.2.28',
            protocol_port=80, name='member3')
        prov_members = [prov_mem_update, prov_new_member]

        update_mem_dict = {'name': 'updated-member2',
                           'monitor_address': '192.0.2.77',
                           'id': self.sample_data.member2_id,
                           'protocol_port': 80,
                           'pool_id': self.sample_data.pool1_id}

        self.amp_driver.member_batch_update(
            self.sample_data.pool1_id, prov_members)

        payload = {
            'old_members': [self.sample_data.db_pool1_members[0].to_dict()],
            'new_members': [prov_new_member.to_dict()],
            'updated_members': [update_mem_dict]}
        mock_cast.assert_called_with({}, 'batch_update_members', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_batch_update_clear_already_empty(
            self, mock_cast, mock_pool_get, mock_session):
        """Expect that we will pass an empty payload if directed.

        Logic for whether or not to attempt this will be done above the driver
        layer, so our driver is responsible to forward the request even if it
        is a perceived no-op.
        """
        mock_pool = mock.MagicMock()
        mock_pool_get.return_value = mock_pool

        self.amp_driver.member_batch_update(
            self.sample_data.pool1_id, [])

        payload = {'old_members': [],
                   'new_members': [],
                   'updated_members': []}
        mock_cast.assert_called_with({}, 'batch_update_members', **payload)

    # Health Monitor
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_health_monitor_create(self, mock_cast):
        provider_HM = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id)
        self.amp_driver.health_monitor_create(provider_HM)
        payload = {consts.HEALTH_MONITOR: provider_HM.to_dict()}
        mock_cast.assert_called_with({}, 'create_health_monitor', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_health_monitor_delete(self, mock_cast):
        provider_HM = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id)
        self.amp_driver.health_monitor_delete(provider_HM)
        payload = {consts.HEALTH_MONITOR: provider_HM.to_dict()}
        mock_cast.assert_called_with({}, 'delete_health_monitor', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_batch_update_udp_ipv4(self, mock_cast, mock_pool_get,
                                          mock_session):

        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "192.0.1.1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = consts.PROTOCOL_UDP
        mock_pool.listeners = [mock_listener]
        mock_pool.members = self.sample_data.db_pool1_members
        mock_pool_get.return_value = mock_pool

        prov_mem_update = driver_dm.Member(
            member_id=self.sample_data.member2_id,
            pool_id=self.sample_data.pool1_id, admin_state_up=False,
            address='192.0.2.17', monitor_address='192.0.2.77',
            protocol_port=80, name='updated-member2')
        prov_new_member = driver_dm.Member(
            member_id=self.sample_data.member3_id,
            pool_id=self.sample_data.pool1_id,
            address='192.0.2.18', monitor_address='192.0.2.28',
            protocol_port=80, name='member3')
        prov_members = [prov_mem_update, prov_new_member]

        update_mem_dict = {'ip_address': '192.0.2.17',
                           'name': 'updated-member2',
                           'monitor_address': '192.0.2.77',
                           'id': self.sample_data.member2_id,
                           'enabled': False,
                           'protocol_port': 80,
                           'pool_id': self.sample_data.pool1_id}

        self.amp_driver.member_batch_update(
            self.sample_data.pool1_id, prov_members)

        payload = {'old_members':
                   [self.sample_data.db_pool1_members[0].to_dict()],
                   'new_members': [prov_new_member.to_dict()],
                   'updated_members': [update_mem_dict]}
        mock_cast.assert_called_with({}, 'batch_update_members', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_member_batch_update_udp_ipv4_ipv6(self, mock_cast, mock_pool_get,
                                               mock_session):

        mock_lb = mock.MagicMock()
        mock_lb.vip = mock.MagicMock()
        mock_lb.vip.ip_address = "192.0.1.1"
        mock_listener = mock.MagicMock()
        mock_listener.load_balancer = mock_lb
        mock_pool = mock.MagicMock()
        mock_pool.protocol = consts.PROTOCOL_UDP
        mock_pool.listeners = [mock_listener]
        mock_pool.members = self.sample_data.db_pool1_members
        mock_pool_get.return_value = mock_pool

        prov_mem_update = driver_dm.Member(
            member_id=self.sample_data.member2_id,
            pool_id=self.sample_data.pool1_id, admin_state_up=False,
            address='fe80::1', monitor_address='fe80::2',
            protocol_port=80, name='updated-member2')
        prov_new_member = driver_dm.Member(
            member_id=self.sample_data.member3_id,
            pool_id=self.sample_data.pool1_id,
            address='192.0.2.18', monitor_address='192.0.2.28',
            protocol_port=80, name='member3')
        prov_members = [prov_mem_update, prov_new_member]

        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.member_batch_update,
                          self.sample_data.pool1_id, prov_members)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_health_monitor_update(self, mock_cast):
        old_provider_hm = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id)
        provider_hm = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id, admin_state_up=True,
            max_retries=1, max_retries_down=2)
        hm_dict = {'enabled': True, 'rise_threshold': 1, 'fall_threshold': 2}
        self.amp_driver.health_monitor_update(old_provider_hm, provider_hm)
        payload = {consts.ORIGINAL_HEALTH_MONITOR: old_provider_hm.to_dict(),
                   consts.HEALTH_MONITOR_UPDATES: hm_dict}
        mock_cast.assert_called_with({}, 'update_health_monitor', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_health_monitor_update_name(self, mock_cast):
        old_provider_hm = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id)
        provider_hm = driver_dm.HealthMonitor(
            healthmonitor_id=self.sample_data.hm1_id, name='Great HM')
        hm_dict = {'name': 'Great HM'}
        self.amp_driver.health_monitor_update(old_provider_hm, provider_hm)
        payload = {consts.ORIGINAL_HEALTH_MONITOR: old_provider_hm.to_dict(),
                   consts.HEALTH_MONITOR_UPDATES: hm_dict}
        mock_cast.assert_called_with({}, 'update_health_monitor', **payload)

    # L7 Policy
    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.ListenerRepository.get')
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7policy_create(self, mock_cast, mock_listener_get, mock_session):
        mock_listener = mock.MagicMock()
        mock_listener.protocol = consts.PROTOCOL_HTTP
        mock_listener_get.return_value = mock_listener
        provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id)
        self.amp_driver.l7policy_create(provider_l7policy)
        payload = {consts.L7POLICY: provider_l7policy.to_dict()}
        mock_cast.assert_called_with({}, 'create_l7policy', **payload)

    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.ListenerRepository.get')
    def test_l7policy_create_invalid_listener_protocol(self, mock_listener_get,
                                                       mock_session):
        mock_listener = mock.MagicMock()
        mock_listener.protocol = consts.PROTOCOL_UDP
        mock_listener_get.return_value = mock_listener
        provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id)
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.l7policy_create,
                          provider_l7policy)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7policy_delete(self, mock_cast):
        provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id)
        self.amp_driver.l7policy_delete(provider_l7policy)
        payload = {consts.L7POLICY: provider_l7policy.to_dict()}
        mock_cast.assert_called_with({}, 'delete_l7policy', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7policy_update(self, mock_cast):
        old_provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id)
        provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id, admin_state_up=True)
        l7policy_dict = {'enabled': True}
        self.amp_driver.l7policy_update(old_provider_l7policy,
                                        provider_l7policy)
        payload = {consts.ORIGINAL_L7POLICY: old_provider_l7policy.to_dict(),
                   consts.L7POLICY_UPDATES: l7policy_dict}
        mock_cast.assert_called_with({}, 'update_l7policy', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7policy_update_name(self, mock_cast):
        old_provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id)
        provider_l7policy = driver_dm.L7Policy(
            l7policy_id=self.sample_data.l7policy1_id, name='Great L7Policy')
        l7policy_dict = {'name': 'Great L7Policy'}
        self.amp_driver.l7policy_update(old_provider_l7policy,
                                        provider_l7policy)
        payload = {consts.ORIGINAL_L7POLICY: old_provider_l7policy.to_dict(),
                   consts.L7POLICY_UPDATES: l7policy_dict}
        mock_cast.assert_called_with({}, 'update_l7policy', **payload)

    # L7 Rules
    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7rule_create(self, mock_cast):
        provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id)
        self.amp_driver.l7rule_create(provider_l7rule)
        payload = {consts.L7RULE: provider_l7rule.to_dict()}
        mock_cast.assert_called_with({}, 'create_l7rule', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7rule_delete(self, mock_cast):
        provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id)
        self.amp_driver.l7rule_delete(provider_l7rule)
        payload = {consts.L7RULE: provider_l7rule.to_dict()}
        mock_cast.assert_called_with({}, 'delete_l7rule', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7rule_update(self, mock_cast):
        old_provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id)
        provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id, admin_state_up=True)
        l7rule_dict = {'enabled': True}
        self.amp_driver.l7rule_update(old_provider_l7rule,
                                      provider_l7rule)
        payload = {consts.ORIGINAL_L7RULE: old_provider_l7rule.to_dict(),
                   consts.L7RULE_UPDATES: l7rule_dict}
        mock_cast.assert_called_with({}, 'update_l7rule', **payload)

    @mock.patch('oslo_messaging.RPCClient.cast')
    def test_l7rule_update_invert(self, mock_cast):
        old_provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id)
        provider_l7rule = driver_dm.L7Rule(
            l7rule_id=self.sample_data.l7rule1_id, invert=True)
        l7rule_dict = {'invert': True}
        self.amp_driver.l7rule_update(old_provider_l7rule, provider_l7rule)
        payload = {consts.ORIGINAL_L7RULE: old_provider_l7rule.to_dict(),
                   consts.L7RULE_UPDATES: l7rule_dict}
        mock_cast.assert_called_with({}, 'update_l7rule', **payload)

    # Flavor
    def test_get_supported_flavor_metadata(self):
        test_schema = {
            "properties": {
                "test_name": {"description": "Test description"},
                "test_name2": {"description": "Another description"}}}
        ref_dict = {"test_name": "Test description",
                    "test_name2": "Another description"}

        # mock out the supported_flavor_metadata
        with mock.patch('octavia.api.drivers.amphora_driver.flavor_schema.'
                        'SUPPORTED_FLAVOR_SCHEMA', test_schema):
            result = self.amp_driver.get_supported_flavor_metadata()
        self.assertEqual(ref_dict, result)

        # Test for bad schema
        with mock.patch('octavia.api.drivers.amphora_driver.flavor_schema.'
                        'SUPPORTED_FLAVOR_SCHEMA', 'bogus'):
            self.assertRaises(exceptions.DriverError,
                              self.amp_driver.get_supported_flavor_metadata)

    def test_validate_flavor(self):
        ref_dict = {consts.LOADBALANCER_TOPOLOGY: consts.TOPOLOGY_SINGLE}
        self.amp_driver.validate_flavor(ref_dict)

        # Test bad flavor metadata value is bad
        ref_dict = {consts.LOADBALANCER_TOPOLOGY: 'bogus'}
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.validate_flavor,
                          ref_dict)

        # Test bad flavor metadata key
        ref_dict = {'bogus': 'bogus'}
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.validate_flavor,
                          ref_dict)

        # Test for bad schema
        with mock.patch('octavia.api.drivers.amphora_driver.flavor_schema.'
                        'SUPPORTED_FLAVOR_SCHEMA', 'bogus'):
            self.assertRaises(exceptions.DriverError,
                              self.amp_driver.validate_flavor, 'bogus')

    # Availability Zone
    def test_get_supported_availability_zone_metadata(self):
        test_schema = {
            "properties": {
                "test_name": {"description": "Test description"},
                "test_name2": {"description": "Another description"}}}
        ref_dict = {"test_name": "Test description",
                    "test_name2": "Another description"}

        # mock out the supported_availability_zone_metadata
        with mock.patch('octavia.api.drivers.amphora_driver.'
                        'availability_zone_schema.'
                        'SUPPORTED_AVAILABILITY_ZONE_SCHEMA', test_schema):
            result = self.amp_driver.get_supported_availability_zone_metadata()
        self.assertEqual(ref_dict, result)

        # Test for bad schema
        with mock.patch('octavia.api.drivers.amphora_driver.'
                        'availability_zone_schema.'
                        'SUPPORTED_AVAILABILITY_ZONE_SCHEMA', 'bogus'):
            self.assertRaises(
                exceptions.DriverError,
                self.amp_driver.get_supported_availability_zone_metadata)

    def test_validate_availability_zone(self):
        # Test compute zone
        with mock.patch('stevedore.driver.DriverManager.driver') as m_driver:
            m_driver.validate_availability_zone.return_value = None
            ref_dict = {consts.COMPUTE_ZONE: 'my_compute_zone'}
            self.amp_driver.validate_availability_zone(ref_dict)

        with mock.patch('octavia.common.utils.get_network_driver') as m_driver:
            # Test vip networks
            m_driver.get_network.return_value = None
            ref_dict = {consts.VALID_VIP_NETWORKS: ['my_vip_net']}
            self.amp_driver.validate_availability_zone(ref_dict)

            # Test management network
            ref_dict = {consts.MANAGEMENT_NETWORK: 'my_management_net'}
            self.amp_driver.validate_availability_zone(ref_dict)

        # Test bad availability zone metadata key
        ref_dict = {'bogus': 'bogus'}
        self.assertRaises(exceptions.UnsupportedOptionError,
                          self.amp_driver.validate_availability_zone,
                          ref_dict)

        # Test for bad schema
        with mock.patch('octavia.api.drivers.amphora_driver.'
                        'availability_zone_schema.'
                        'SUPPORTED_AVAILABILITY_ZONE_SCHEMA', 'bogus'):
            self.assertRaises(exceptions.DriverError,
                              self.amp_driver.validate_availability_zone,
                              'bogus')

    @mock.patch('cryptography.fernet.Fernet')
    def test_encrypt_listener_dict(self, mock_fernet):
        mock_fern = mock.MagicMock()
        mock_fernet.return_value = mock_fern
        TEST_DATA = {'cert': b'some data'}
        TEST_DATA2 = {'test': 'more data'}
        FAKE_ENCRYPTED_DATA = b'alqwkhjetrhth'
        mock_fern.encrypt.return_value = FAKE_ENCRYPTED_DATA

        # We need a class instance with the mock
        amp_driver = driver.AmphoraProviderDriver()

        # Test just default_tls_container_data
        list_dict = {consts.DEFAULT_TLS_CONTAINER_DATA: TEST_DATA}

        amp_driver._encrypt_listener_dict(list_dict)

        mock_fern.encrypt.assert_called_once_with(b'some data')

        self.assertEqual({'cert': FAKE_ENCRYPTED_DATA},
                         list_dict[consts.DEFAULT_TLS_CONTAINER_DATA])

        mock_fern.reset_mock()

        # Test just sni_container_data
        TEST_DATA = {'cert': b'some data'}
        sni_dict = {consts.SNI_CONTAINER_DATA: [TEST_DATA, TEST_DATA2]}

        amp_driver._encrypt_listener_dict(sni_dict)

        mock_fern.encrypt.assert_called_once_with(b'some data')

        encrypted_sni = [{'cert': FAKE_ENCRYPTED_DATA},
                         TEST_DATA2]
        self.assertEqual(encrypted_sni, sni_dict[consts.SNI_CONTAINER_DATA])
