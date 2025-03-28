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
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from unittest import mock

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.db import models
from octavia.network import data_models as network_models
from octavia.network.drivers.noop_driver import driver
import octavia.tests.unit.base as base


class TestNoopNetworkDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()
    FAKE_UUID_3 = uuidutils.generate_uuid()
    FAKE_UUID_4 = uuidutils.generate_uuid()
    FAKE_UUID_5 = uuidutils.generate_uuid()
    FAKE_UUID_6 = uuidutils.generate_uuid()
    FAKE_UUID_7 = uuidutils.generate_uuid()

    def setUp(self):
        super().setUp()
        self.mock_engine = mock.MagicMock()
        with mock.patch('octavia.network.drivers.noop_driver.driver.'
                        'create_engine') as mock_create_engine:
            mock_create_engine.return_value = self.mock_engine
            with mock.patch('octavia.network.drivers.noop_driver.'
                            'driver.event'):
                self.driver = driver.NoopNetworkDriver()
            mock_create_engine.assert_called_once_with(
                'sqlite:////tmp/octavia-network-noop.db')

        self.port = mock.MagicMock()
        self.port_id = 88
        self.port_name = 'port1'
        self.port.id = self.port_id
        self.network_id = self.FAKE_UUID_3
        self.network_name = 'net1'
        self.device_id = self.FAKE_UUID_4
        self.ip_address = "192.0.2.2"
        self.load_balancer = models.LoadBalancer()
        self.load_balancer.id = self.FAKE_UUID_2

        self.vip = models.Vip()
        self.vip.ip_address = "192.0.2.1"
        self.vip.subnet_id = uuidutils.generate_uuid()
        self.vip.port_id = uuidutils.generate_uuid()
        self.amphora_id = self.FAKE_UUID_1
        self.compute_id = self.FAKE_UUID_2
        self.compute2_id = self.FAKE_UUID_2
        self.subnet_id = self.FAKE_UUID_3
        self.subnet_name = 'subnet1'
        self.qos_policy_id = self.FAKE_UUID_5
        self.vrrp_port_id = self.FAKE_UUID_6

        self.amphora1 = models.Amphora()
        self.amphora1.id = uuidutils.generate_uuid()
        self.amphora1.compute_id = self.compute_id
        self.amphora1.vrrp_port_id = uuidutils.generate_uuid()
        self.amphora1.ha_port_id = uuidutils.generate_uuid()
        self.amphora1.vrrp_ip = '192.0.2.10'
        self.amphora1.ha_ip = '192.0.2.11'
        self.amphora2 = models.Amphora()
        self.amphora2.id = uuidutils.generate_uuid()
        self.amphora2.compute_id = self.compute2_id
        self.amphora2.vrrp_port_id = uuidutils.generate_uuid()
        self.amphora2.ha_port_id = uuidutils.generate_uuid()
        self.amphora2.vrrp_ip = '192.0.2.20'
        self.amphora2.ha_ip = '192.0.2.21'
        self.load_balancer.amphorae = [self.amphora1, self.amphora2]
        self.load_balancer.vip = self.vip
        self.subnet = mock.MagicMock()
        self.subnet.id = self.subnet_id

    def test_allocate_vip(self):
        self.driver.allocate_vip(self.load_balancer)
        self.assertEqual(
            (self.load_balancer, 'allocate_vip'),
            self.driver.driver.networkconfigconfig[self.load_balancer.id])

    def test_deallocate_vip(self):
        self.driver.deallocate_vip(self.vip)
        self.assertEqual((self.vip,
                          'deallocate_vip'),
                         self.driver.driver.networkconfigconfig[
                             self.vip.ip_address])

    def test_update_vip_sg(self):
        self.driver.update_vip_sg(self.load_balancer, self.vip)
        self.assertEqual((self.load_balancer, self.vip,
                          'update_vip_sg'),
                         self.driver.driver.networkconfigconfig[(
                             self.load_balancer.id, self.vip.ip_address)])

    def test_update_aap_port_sg(self):
        self.driver.update_aap_port_sg(self.load_balancer, self.amphora1,
                                       self.vip)
        self.assertEqual((self.load_balancer, self.vip, self.amphora1,
                          'update_aap_port_sg'),
                         self.driver.driver.networkconfigconfig[(
                             self.amphora1.id, self.vip.ip_address)])

    def test_unplug_vip(self):
        self.driver.unplug_vip(self.load_balancer, self.vip)
        self.assertEqual((self.load_balancer, self.vip,
                          'unplug_vip'),
                         self.driver.driver.networkconfigconfig[(
                             self.load_balancer.id, self.vip.ip_address)])

    def test_unplug_network(self):
        self.driver.unplug_network(self.compute_id, self.network_id)
        self.assertEqual((self.compute_id, self.network_id, 'unplug_network'),
                         self.driver.driver.networkconfigconfig[(
                             self.compute_id, self.network_id)])

    def test_get_plugged_networks(self):
        interface_db_mock = mock.MagicMock()
        interface_db_mock.port_id = self.port_id
        interface_db_mock.network_id = self.network_id
        interface_db_mock.compute_id = self.compute_id
        interface_db_mock.vnic_type = constants.VNIC_TYPE_NORMAL

        fixed_ips_db_mock = mock.MagicMock()
        fixed_ips_db_mock.port_id = self.port_id
        fixed_ips_db_mock.subnet_id = self.subnet_id
        fixed_ips_db_mock.ip_address = self.ip_address

        # mock out the sqlite db calls
        connect_mock = mock.MagicMock()
        connection_mock = mock.MagicMock()
        self.mock_engine.connect.return_value = connect_mock
        connect_mock.__enter__.return_value = connection_mock

        connection_mock.execute.side_effect = [[interface_db_mock],
                                               [fixed_ips_db_mock]]

        result = self.driver.get_plugged_networks(self.compute_id)

        self.assertEqual((self.compute_id, 'get_plugged_networks'),
                         self.driver.driver.networkconfigconfig[(
                             self.compute_id)])

        expected_fixed_ips = [network_models.FixedIP(
            subnet_id=self.subnet_id, ip_address=self.ip_address)]
        expected_interfaces = [network_models.Interface(
            compute_id=self.compute_id, network_id=self.network_id,
            port_id=self.port_id, fixed_ips=expected_fixed_ips,
            vnic_type=constants.VNIC_TYPE_NORMAL)]

        self.assertEqual(expected_interfaces, result)

    def test_update_vip(self):
        self.driver.update_vip(self.load_balancer)
        self.assertEqual((self.load_balancer, False, 'update_vip'),
                         self.driver.driver.networkconfigconfig[(
                             self.load_balancer.id
                         )])

    def test_get_network(self):
        network = self.driver.get_network(self.network_id)
        self.assertEqual(
            (self.network_id, 'get_network'),
            self.driver.driver.networkconfigconfig[self.network_id]
        )
        self.assertEqual(self.network_id, network.id)
        network_again = self.driver.get_network(self.network_id)
        self.assertEqual(network, network_again)

    def test_get_subnet(self):
        subnet = self.driver.get_subnet(self.subnet_id)
        self.assertEqual(
            (self.subnet_id, 'get_subnet'),
            self.driver.driver.networkconfigconfig[self.subnet_id]
        )
        self.assertEqual(self.subnet_id, subnet.id)
        subnet_again = self.driver.get_subnet(self.subnet_id)
        self.assertEqual(subnet, subnet_again)

    def test_get_port(self):
        port = self.driver.get_port(self.port_id)
        self.assertEqual(
            (self.port_id, 'get_port'),
            self.driver.driver.networkconfigconfig[self.port_id]
        )
        self.assertEqual(self.port_id, port.id)
        port_again = self.driver.get_port(self.port_id)
        self.assertEqual(port, port_again)

    def test_get_network_by_name(self):
        network = self.driver.get_network_by_name(self.network_name)
        self.assertEqual(
            (self.network_name, 'get_network_by_name'),
            self.driver.driver.networkconfigconfig[self.network_name]
        )
        self.assertEqual(self.network_name, network.name)
        network_again = self.driver.get_network_by_name(self.network_name)
        self.assertEqual(network, network_again)

    def test_get_subnet_by_name(self):
        subnet = self.driver.get_subnet_by_name(self.subnet_name)
        self.assertEqual(
            (self.subnet_name, 'get_subnet_by_name'),
            self.driver.driver.networkconfigconfig[self.subnet_name]
        )
        self.assertEqual(self.subnet_name, subnet.name)
        subnet_again = self.driver.get_subnet_by_name(self.subnet_name)
        self.assertEqual(subnet, subnet_again)

    def test_get_port_by_name(self):
        port = self.driver.get_port_by_name(self.port_name)
        self.assertEqual(
            (self.port_name, 'get_port_by_name'),
            self.driver.driver.networkconfigconfig[self.port_name]
        )
        self.assertEqual(self.port_name, port.name)
        port_again = self.driver.get_port_by_name(self.port_name)
        self.assertEqual(port, port_again)

    def test_get_port_by_net_id_device_id(self):
        port = self.driver.get_port_by_net_id_device_id(
            self.network_id, self.device_id)
        self.assertEqual(
            (self.network_id, self.device_id,
             'get_port_by_net_id_device_id'),
            self.driver.driver.networkconfigconfig[(self.network_id,
                                                    self.device_id)]
        )
        self.assertEqual(self.network_id, port.network_id)
        self.assertEqual(self.device_id, port.device_id)
        port_again = self.driver.get_port_by_net_id_device_id(
            self.network_id, self.device_id)
        self.assertEqual(port, port_again)

    def test_get_security_group(self):
        FAKE_SG_NAME = 'fake_sg_name'
        result = self.driver.get_security_group(FAKE_SG_NAME)

        self.assertEqual((FAKE_SG_NAME, 'get_security_group'),
                         self.driver.driver.networkconfigconfig[FAKE_SG_NAME])
        self.assertTrue(uuidutils.is_uuid_like(result.id))

    def test_plug_port(self):
        self.driver.plug_port(self.amphora1, self.port)
        self.assertEqual(
            (self.amphora1, self.port, 'plug_port'),
            self.driver.driver.networkconfigconfig[self.amphora1.id,
                                                   self.port.id]
        )

    def test_get_network_configs(self):
        amp_config = self.driver.get_network_configs(self.load_balancer)
        self.assertEqual(
            (self.load_balancer, 'get_network_configs'),
            self.driver.driver.networkconfigconfig[self.load_balancer.id]
        )
        self.assertEqual(2, len(amp_config))
        self.assertEqual(self.amphora1, amp_config[self.amphora1.id].amphora)
        self.assertEqual(self.amphora2, amp_config[self.amphora2.id].amphora)

    def test_get_qos_policy(self):
        self.driver.get_qos_policy(self.qos_policy_id)
        self.assertEqual(
            (self.qos_policy_id, 'get_qos_policy'),
            self.driver.driver.networkconfigconfig[self.qos_policy_id]
        )

    def test_apply_qos_on_port(self):
        self.driver.apply_qos_on_port(self.qos_policy_id, self.vrrp_port_id)
        self.assertEqual(
            (self.qos_policy_id, self.vrrp_port_id, 'apply_qos_on_port'),
            self.driver.driver.networkconfigconfig[self.qos_policy_id,
                                                   self.vrrp_port_id]
        )

    def test_plug_aap_port(self):
        self.driver.plug_aap_port(self.load_balancer, self.vip, self.amphora1,
                                  self.subnet)
        self.assertEqual(
            (self.load_balancer, self.vip, self.amphora1, self.subnet,
             'plug_aap_port'),
            self.driver.driver.networkconfigconfig[self.amphora1.id,
                                                   self.vip.ip_address]
        )

    def test_unplug_aap(self):
        self.driver.unplug_aap_port(self.vip, self.amphora1, self.subnet)
        self.assertEqual(
            (self.vip, self.amphora1, self.subnet,
             'unplug_aap_port'),
            self.driver.driver.networkconfigconfig[self.amphora1.id,
                                                   self.vip.ip_address]
        )

    def test_delete_port(self):
        PORT_ID = uuidutils.generate_uuid()

        self.driver.delete_port(PORT_ID)

        self.assertEqual((PORT_ID, 'delete_port'),
                         self.driver.driver.networkconfigconfig[PORT_ID])

    def test_set_port_admin_state_up(self):
        PORT_ID = uuidutils.generate_uuid()

        self.driver.set_port_admin_state_up(PORT_ID, False)

        self.assertEqual(
            (PORT_ID, False, 'admin_down_port'),
            self.driver.driver.networkconfigconfig[(PORT_ID, False)])

    def test_create_port(self):
        FAKE_NAME = 'fake_name'
        IP_ADDRESS = '2001:db8::77'
        NETWORK_ID = uuidutils.generate_uuid()
        QOS_POLICY_ID = uuidutils.generate_uuid()
        SUBNET_ID = uuidutils.generate_uuid()
        FIXED_IPS = [{'ip_address': IP_ADDRESS, 'subnet_id': SUBNET_ID},
                     {'subnet_id': SUBNET_ID}]

        # Test minimum
        result = self.driver.create_port(NETWORK_ID)

        self.assertIsInstance(result, network_models.Port)
        self.assertEqual(NETWORK_ID, result.network_id)

        # Test full parameters
        result = self.driver.create_port(
            NETWORK_ID, name=FAKE_NAME, fixed_ips=FIXED_IPS,
            admin_state_up=False, qos_policy_id=QOS_POLICY_ID)

        self.assertIsInstance(result, network_models.Port)
        self.assertEqual(NETWORK_ID, result.network_id)
        self.assertEqual(FAKE_NAME, result.name)
        self.assertEqual(IP_ADDRESS, result.fixed_ips[0].ip_address)
        self.assertEqual(SUBNET_ID, result.fixed_ips[0].subnet_id)
        self.assertEqual('198.51.100.56', result.fixed_ips[1].ip_address)
        self.assertEqual(SUBNET_ID, result.fixed_ips[1].subnet_id)
        self.assertEqual(QOS_POLICY_ID, result.qos_policy_id)
        self.assertFalse(result.admin_state_up)

    def test_plug_fixed_ip(self):
        self.driver.plug_fixed_ip(self.port_id, self.subnet_id,
                                  self.ip_address)
        self.assertEqual(
            (self.port_id, self.subnet_id, self.ip_address, 'plug_fixed_ip'),
            self.driver.driver.networkconfigconfig[
                self.port_id, self.subnet_id]
        )
