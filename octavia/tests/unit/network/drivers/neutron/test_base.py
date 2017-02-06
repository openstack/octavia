#    Copyright 2015 Rackspace
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

import mock
from neutronclient.common import exceptions as neutron_client_exceptions

from octavia.common import clients
from octavia.common import data_models
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import base as neutron_base
from octavia.network.drivers.neutron import utils
from octavia.tests.common import constants as t_constants
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base


class TestBaseNeutronNetworkDriver(base.TestCase):

    def _instantiate_partial_abc(self, abclass):
        if "__abstractmethods__" not in abclass.__dict__:
            return abclass()
        new_dict = abclass.__dict__.copy()
        for abstractmethod in abclass.__abstractmethods__:
            new_dict[abstractmethod] = lambda x, *args, **kw: (x, args, kw)
        impl_class = type("partially_implemented_abc_%s" % abclass.__name__,
                          (abclass,), new_dict)
        return impl_class()

    def setUp(self):
        super(TestBaseNeutronNetworkDriver, self).setUp()
        with mock.patch('octavia.common.clients.neutron_client.Client',
                        autospec=True) as neutron_client:
            client = neutron_client(clients.NEUTRON_VERSION)
            client.list_extensions.return_value = {
                'extensions': [
                    {'alias': neutron_base.SEC_GRP_EXT_ALIAS}
                ]
            }
            self.k_session = mock.patch(
                'keystoneauth1.session.Session').start()
            self.driver = self._instantiate_partial_abc(
                neutron_base.BaseNeutronDriver)

    def test__check_extension_enabled(self):
        show_extension = self.driver.neutron_client.show_extension
        show_extension.side_effect = [None, neutron_client_exceptions.NotFound]

        self.assertTrue(self.driver._check_extension_enabled('TEST1'))
        self.assertFalse(self.driver._check_extension_enabled('TEST2'))

    def test__port_to_vip(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.subnet_id = t_constants.MOCK_SUBNET_ID
        port = utils.convert_port_dict_to_model(t_constants.MOCK_NEUTRON_PORT)
        vip = self.driver._port_to_vip(port, lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(lb.id, vip.load_balancer_id)

    def test__nova_interface_to_octavia_interface(self):
        nova_interface = t_constants.MockNovaInterface()
        nova_interface.net_id = '1'
        nova_interface.port_id = '2'
        nova_interface.fixed_ips = [{'ip_address': '10.0.0.1'}]
        interface = self.driver._nova_interface_to_octavia_interface(
            '3', nova_interface)
        self.assertEqual('1', interface.network_id)
        self.assertEqual('2', interface.port_id)
        ips = [fixed_ip.ip_address for fixed_ip in interface.fixed_ips]
        self.assertIn('10.0.0.1', ips)

    def test_get_plugged_networks(self):
        list_ports = self.driver.neutron_client.list_ports
        list_ports.side_effect = TypeError
        o_ifaces = self.driver.get_plugged_networks(
            t_constants.MOCK_COMPUTE_ID)
        self.assertEqual(0, len(o_ifaces))
        list_ports.side_effect = None
        list_ports.reset_mock()
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        plugged_networks = self.driver.get_plugged_networks(
            t_constants.MOCK_COMPUTE_ID)
        for pn in plugged_networks:
            self.assertIn(pn.port_id, [port1.get('id'), port2.get('id')])
            self.assertIn(pn.network_id, [port1.get('network_id'),
                                          port2.get('network_id')])
            for fixed_ip in pn.fixed_ips:
                self.assertIn(fixed_ip.ip_address,
                              [port1['fixed_ips'][0]['ip_address'],
                               port2['fixed_ips'][0]['ip_address']])

    def test_get_network(self):
        show_network = self.driver.neutron_client.show_network
        show_network.return_value = {'network': {
            'id': t_constants.MOCK_NETWORK_ID,
            'subnets': [t_constants.MOCK_SUBNET_ID]}}
        network = self.driver.get_network(t_constants.MOCK_NETWORK_ID)
        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(t_constants.MOCK_SUBNET_ID, network.subnets[0])

    def test_get_subnet(self):
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR}}
        subnet = self.driver.get_subnet(t_constants.MOCK_SUBNET_ID)
        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(t_constants.MOCK_CIDR, subnet.cidr)

    def test_get_port(self):
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'id': t_constants.MOCK_PORT_ID,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]}}
        port = self.driver.get_port(t_constants.MOCK_PORT_ID)
        self.assertIsInstance(port, network_models.Port)
        self.assertEqual(t_constants.MOCK_PORT_ID, port.id)
        self.assertEqual(t_constants.MOCK_MAC_ADDR, port.mac_address)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, port.network_id)
        self.assertEqual(1, len(port.fixed_ips))
        self.assertIsInstance(port.fixed_ips[0], network_models.FixedIP)
        self.assertEqual(t_constants.MOCK_SUBNET_ID,
                         port.fixed_ips[0].subnet_id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS,
                         port.fixed_ips[0].ip_address)

    def test_get_network_by_name(self):
        list_network = self.driver.neutron_client.list_networks
        list_network.return_value = {'networks': [{'network': {
            'id': t_constants.MOCK_NETWORK_ID,
            'name': t_constants.MOCK_NETWORK_NAME,
            'subnets': [t_constants.MOCK_SUBNET_ID]}}]}
        network = self.driver.get_network_by_name(
            t_constants.MOCK_NETWORK_NAME)
        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(t_constants.MOCK_NETWORK_NAME, network.name)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(t_constants.MOCK_SUBNET_ID, network.subnets[0])
        # Negative
        list_network.side_effect = neutron_client_exceptions.NotFound
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.get_network_by_name,
                          t_constants.MOCK_NETWORK_NAME)
        list_network.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_network_by_name,
                          t_constants.MOCK_NETWORK_NAME)

    def test_get_subnet_by_name(self):
        list_subnet = self.driver.neutron_client.list_subnets
        list_subnet.return_value = {'subnets': [{'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'name': t_constants.MOCK_SUBNET_NAME,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR}}]}
        subnet = self.driver.get_subnet_by_name(t_constants.MOCK_SUBNET_NAME)
        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(t_constants.MOCK_SUBNET_NAME, subnet.name)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(t_constants.MOCK_CIDR, subnet.cidr)
        # Negative
        list_subnet.side_effect = neutron_client_exceptions.NotFound
        self.assertRaises(network_base.SubnetNotFound,
                          self.driver.get_subnet_by_name,
                          t_constants.MOCK_SUBNET_NAME)
        list_subnet.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_subnet_by_name,
                          t_constants.MOCK_SUBNET_NAME)

    def test_get_port_by_name(self):
        list_port = self.driver.neutron_client.list_ports
        list_port.return_value = {'ports': [{'port': {
            'id': t_constants.MOCK_PORT_ID,
            'name': t_constants.MOCK_PORT_NAME,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]}}]}
        port = self.driver.get_port_by_name(t_constants.MOCK_PORT_NAME)
        self.assertIsInstance(port, network_models.Port)
        self.assertEqual(t_constants.MOCK_PORT_ID, port.id)
        self.assertEqual(t_constants.MOCK_PORT_NAME, port.name)
        self.assertEqual(t_constants.MOCK_MAC_ADDR, port.mac_address)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, port.network_id)
        self.assertEqual(1, len(port.fixed_ips))
        self.assertIsInstance(port.fixed_ips[0], network_models.FixedIP)
        self.assertEqual(t_constants.MOCK_SUBNET_ID,
                         port.fixed_ips[0].subnet_id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS,
                         port.fixed_ips[0].ip_address)
        # Negative
        list_port.side_effect = neutron_client_exceptions.NotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.get_port_by_name,
                          t_constants.MOCK_PORT_NAME)
        list_port.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_port_by_name,
                          t_constants.MOCK_PORT_NAME)

    def test_get_port_by_net_id_device_id(self):
        list_port = self.driver.neutron_client.list_ports
        list_port.return_value = {'ports': [{'port': {
            'id': t_constants.MOCK_PORT_ID,
            'name': t_constants.MOCK_PORT_NAME,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': t_constants.MOCK_DEVICE_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]}}]}
        port = self.driver.get_port_by_net_id_device_id(
            t_constants.MOCK_NETWORK_ID, t_constants.MOCK_DEVICE_ID)
        self.assertIsInstance(port, network_models.Port)
        self.assertEqual(t_constants.MOCK_PORT_ID, port.id)
        self.assertEqual(t_constants.MOCK_DEVICE_ID, port.device_id)
        self.assertEqual(t_constants.MOCK_PORT_NAME, port.name)
        self.assertEqual(t_constants.MOCK_MAC_ADDR, port.mac_address)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, port.network_id)
        self.assertEqual(1, len(port.fixed_ips))
        self.assertIsInstance(port.fixed_ips[0], network_models.FixedIP)
        self.assertEqual(t_constants.MOCK_SUBNET_ID,
                         port.fixed_ips[0].subnet_id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS,
                         port.fixed_ips[0].ip_address)
        # Negative
        list_port.side_effect = neutron_client_exceptions.NotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_PORT_NAME,
                          t_constants.MOCK_DEVICE_ID)
        list_port.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_NETWORK_ID,
                          t_constants.MOCK_DEVICE_ID)
