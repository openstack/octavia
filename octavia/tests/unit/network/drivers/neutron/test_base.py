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

from octavia.common import clients
from octavia.common import data_models
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import base as neutron_base
from octavia.network.drivers.neutron import utils
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base
from octavia.tests.unit.network.drivers.neutron import constants as n_constants


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
                'octavia.common.keystone.get_session').start()
            self.driver = self._instantiate_partial_abc(
                neutron_base.BaseNeutronDriver)

    def test__port_to_vip(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.subnet_id = n_constants.MOCK_SUBNET_ID
        port = utils.convert_port_dict_to_model(n_constants.MOCK_NEUTRON_PORT)
        vip = self.driver._port_to_vip(port, lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(n_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(n_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(n_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(lb.id, vip.load_balancer_id)

    def test__nova_interface_to_octavia_interface(self):
        nova_interface = n_constants.MockNovaInterface()
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
            n_constants.MOCK_COMPUTE_ID)
        self.assertEqual(0, len(o_ifaces))
        list_ports.side_effect = None
        list_ports.reset_mock()
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        plugged_networks = self.driver.get_plugged_networks(
            n_constants.MOCK_COMPUTE_ID)
        for pn in plugged_networks:
            self.assertIn(pn.port_id, [port1.get('id'), port2.get('id')])
            self.assertIn(pn.network_id, [port1.get('network_id'),
                                          port2.get('network_id')])
            for fixed_ip in pn.fixed_ips:
                self.assertIn(fixed_ip.ip_address,
                              [port1['fixed_ips'][0]['ip_address'],
                               port2['fixed_ips'][0]['ip_address']])

    def test_sec_grps_extension_check(self):
        self.driver._check_sec_grps()
        self.assertTrue(self.driver.sec_grp_enabled)
        self.driver._extensions = [{'alias': 'blah'}]
        self.driver._check_sec_grps()
        self.assertFalse(self.driver.sec_grp_enabled)

    def test_get_network(self):
        show_network = self.driver.neutron_client.show_network
        show_network.return_value = {'network': {
            'id': n_constants.MOCK_NETWORK_ID,
            'subnets': [n_constants.MOCK_SUBNET_ID]}}
        network = self.driver.get_network(n_constants.MOCK_NETWORK_ID)
        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(n_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(n_constants.MOCK_SUBNET_ID, network.subnets[0])

    def test_get_subnet(self):
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {'subnet': {
            'id': n_constants.MOCK_SUBNET_ID,
            'gateway_ip': n_constants.MOCK_IP_ADDRESS,
            'cidr': n_constants.MOCK_CIDR}}
        subnet = self.driver.get_subnet(n_constants.MOCK_SUBNET_ID)
        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(n_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(n_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(n_constants.MOCK_CIDR, subnet.cidr)

    def test_get_port(self):
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'id': n_constants.MOCK_PORT_ID,
            'mac_address': n_constants.MOCK_MAC_ADDR,
            'network_id': n_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': n_constants.MOCK_SUBNET_ID,
                'ip_address': n_constants.MOCK_IP_ADDRESS
            }]}}
        port = self.driver.get_port(n_constants.MOCK_PORT_ID)
        self.assertIsInstance(port, network_models.Port)
        self.assertEqual(n_constants.MOCK_PORT_ID, port.id)
        self.assertEqual(n_constants.MOCK_MAC_ADDR, port.mac_address)
        self.assertEqual(n_constants.MOCK_NETWORK_ID, port.network_id)
        self.assertEqual(1, len(port.fixed_ips))
        self.assertIsInstance(port.fixed_ips[0], network_models.FixedIP)
        self.assertEqual(n_constants.MOCK_SUBNET_ID,
                         port.fixed_ips[0].subnet_id)
        self.assertEqual(n_constants.MOCK_IP_ADDRESS,
                         port.fixed_ips[0].ip_address)
