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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.common import data_models
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import base as neutron_base
from octavia.network.drivers.neutron import utils
from octavia.tests.common import constants as t_constants
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base
import openstack.exceptions as os_exceptions
from openstack.network.v2.network import Network
from openstack.network.v2.network_ip_availability import NetworkIPAvailability
from openstack.network.v2.port import Port
from openstack.network.v2.qos_policy import QoSPolicy
from openstack.network.v2.subnet import Subnet


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
        super().setUp()
        with mock.patch('octavia.common.clients.openstack.connection.'
                        'Connection', autospec=True) as os_connection:
            self._original_find_extension = (
                os_connection.return_value.network.find_extension)
            os_connection.return_value.network.find_extension = (
                lambda x: 'alias' if x == neutron_base.SEC_GRP_EXT_ALIAS else
                None)
            self.k_session = mock.patch(
                'keystoneauth1.session.Session').start()
            self.driver = self._instantiate_partial_abc(
                neutron_base.BaseNeutronDriver)

    def test__check_extension_enabled(self):
        with mock.patch.object(self.driver.network_proxy, "find_extension",
                               side_effect=[True, False]) as show_extension:
            self.assertTrue(self.driver._check_extension_enabled('TEST1'))
            self.assertFalse(self.driver._check_extension_enabled('TEST2'))
            show_extension.assert_has_calls(
                [mock.call('TEST1'), mock.call('TEST2')])

    def test__check_extension_enabled_cached(self):
        with mock.patch.object(self.driver.network_proxy, "find_extension",
                               ) as show_extension:
            self.driver._check_extension_cache = {'TEST1': True,
                                                  'TEST2': False}
            self.assertTrue(self.driver._check_extension_enabled('TEST1'))
            self.assertFalse(self.driver._check_extension_enabled('TEST2'))
            self.assertNotIn(mock.call('TEST1'), show_extension.mock_calls)
            self.assertNotIn(mock.call('TEST2'), show_extension.mock_calls)

    def test__add_allowed_address_pair_to_port(self):
        self.driver._add_allowed_address_pairs_to_port(
            t_constants.MOCK_PORT_ID, [t_constants.MOCK_IP_ADDRESS])
        expected_aap_dict = {
            'allowed_address_pairs': [
                {'ip_address': t_constants.MOCK_IP_ADDRESS}]}
        self.driver.network_proxy.update_port.assert_has_calls([
            mock.call(t_constants.MOCK_PORT_ID, **expected_aap_dict)])

    def test__add_security_group_to_port(self):
        self.driver._add_security_group_to_port(
            t_constants.MOCK_SECURITY_GROUP_ID, t_constants.MOCK_PORT_ID)
        expected_sg_dict = {
            'security_groups': [
                t_constants.MOCK_SECURITY_GROUP_ID]}
        self.driver.network_proxy.update_port.assert_has_calls([
            mock.call(t_constants.MOCK_PORT_ID, **expected_sg_dict)])

    def test__add_security_group_to_port_with_port_not_found(self):
        self.driver.network_proxy.update_port.side_effect = (
            os_exceptions.ResourceNotFound)
        self.assertRaises(
            network_base.PortNotFound,
            self.driver._add_security_group_to_port,
            t_constants.MOCK_SECURITY_GROUP_ID, t_constants.MOCK_PORT_ID)

    def test__add_security_group_to_port_with_other_exception(self):
        self.driver.network_proxy.update_port.side_effect = IOError
        self.assertRaises(
            network_base.NetworkException,
            self.driver._add_security_group_to_port,
            t_constants.MOCK_SECURITY_GROUP_ID, t_constants.MOCK_PORT_ID)

    def test__get_ports_by_security_group(self):
        self.driver.network_proxy.ports.return_value = [
            t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT2]
        ports = self.driver._get_ports_by_security_group(
            t_constants.MOCK_SECURITY_GROUP_ID)
        self.assertEqual(1, len(ports))
        self.assertIn(t_constants.MOCK_NEUTRON_PORT, ports)

    def test__create_security_group(self):
        sg_return = self.driver._create_security_group(
            t_constants.MOCK_SECURITY_GROUP_NAME)
        expected_sec_grp_dict = {
            'name': t_constants.MOCK_SECURITY_GROUP_NAME}
        self.driver.network_proxy.create_security_group.assert_has_calls([
            mock.call(**expected_sec_grp_dict)])
        self.assertEqual(
            sg_return,
            self.driver.network_proxy.create_security_group())

    def test__create_security_group_rule(self):
        self.driver._create_security_group_rule(
            sec_grp_id=t_constants.MOCK_SECURITY_GROUP_ID,
            direction=1,
            protocol=2,
            port_min=3,
            port_max=4,
            ethertype=5,
            cidr="10.0.0.0/24")
        expected_sec_grp_rule_dict = {
            'security_group_id': t_constants.MOCK_SECURITY_GROUP_ID,
            'direction': 1,
            'protocol': 2,
            'port_range_min': 3,
            'port_range_max': 4,
            'ethertype': 5,
            'remote_ip_prefix': '10.0.0.0/24'}
        self.driver.network_proxy.create_security_group_rule.assert_has_calls(
            [mock.call(**expected_sec_grp_rule_dict)])

    def test__port_to_vip(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.subnet_id = t_constants.MOCK_SUBNET_ID
        lb.vip.ip_address = t_constants.MOCK_IP_ADDRESS
        port = utils.convert_port_to_model(t_constants.MOCK_NEUTRON_PORT)
        vip, additional_vips = self.driver._port_to_vip(port, lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertIsInstance(additional_vips, list)
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
        list_ports = self.driver.network_proxy.ports
        list_ports.side_effect = TypeError
        o_ifaces = self.driver.get_plugged_networks(
            t_constants.MOCK_DEVICE_ID)
        self.assertEqual(0, len(o_ifaces))
        list_ports.side_effect = None
        list_ports.reset_mock()
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = [port1, port2]
        plugged_networks = self.driver.get_plugged_networks(
            t_constants.MOCK_DEVICE_ID)
        for pn in plugged_networks:
            self.assertIn(pn.port_id, [port1.get('id'), port2.get('id')])
            self.assertIn(pn.network_id, [port1.get('network_id'),
                                          port2.get('network_id')])
            for fixed_ip in pn.fixed_ips:
                self.assertIn(fixed_ip.ip_address,
                              [port1['fixed_ips'][0]['ip_address'],
                               port2['fixed_ips'][0]['ip_address']])

    def test_get_network(self):
        config = self.useFixture(oslo_fixture.Config(cfg.CONF))
        config.config(group="networking", allow_invisible_resource_usage=True)

        show_network = self.driver.network_proxy.get_network
        show_network.return_value = Network(**{
            'id': t_constants.MOCK_NETWORK_ID,
            'subnets': [t_constants.MOCK_SUBNET_ID]})
        network = self.driver.get_network(t_constants.MOCK_NETWORK_ID)
        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(t_constants.MOCK_SUBNET_ID, network.subnets[0])

    @mock.patch("octavia.common.clients.NeutronAuth.get_user_neutron_client")
    def test_get_user_network(self, neutron_client_mock):
        show_network = neutron_client_mock.return_value.get_network
        show_network.return_value = Network(**{
            'id': t_constants.MOCK_NETWORK_ID,
            'subnets': [t_constants.MOCK_SUBNET_ID]})

        network = self.driver.get_network(t_constants.MOCK_NETWORK_ID,
                                          context=mock.ANY)

        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(t_constants.MOCK_SUBNET_ID, network.subnets[0])

    def test_get_subnet(self):
        config = self.useFixture(oslo_fixture.Config(cfg.CONF))
        config.config(group="networking", allow_invisible_resource_usage=True)

        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR})
        subnet = self.driver.get_subnet(t_constants.MOCK_SUBNET_ID)
        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(t_constants.MOCK_CIDR, subnet.cidr)

    @mock.patch("octavia.common.clients.NeutronAuth.get_user_neutron_client")
    def test_get_user_subnet(self, neutron_client_mock):
        show_subnet = neutron_client_mock.return_value.get_subnet
        show_subnet.return_value = Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR})

        subnet = self.driver.get_subnet(t_constants.MOCK_SUBNET_ID,
                                        context=mock.ANY)

        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(t_constants.MOCK_CIDR, subnet.cidr)

    def test_get_port(self):
        config = self.useFixture(oslo_fixture.Config(cfg.CONF))
        config.config(group="networking", allow_invisible_resource_usage=True)

        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]})
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

    @mock.patch("octavia.common.clients.NeutronAuth.get_user_neutron_client")
    def test_get_user_port(self, neutron_client_mock):
        show_port = neutron_client_mock.return_value.get_port
        show_port.return_value = Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]})

        port = self.driver.get_port(t_constants.MOCK_PORT_ID, context=mock.ANY)

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
        list_network = self.driver.network_proxy.networks
        list_network.return_value = iter([Network(**{
            'id': t_constants.MOCK_NETWORK_ID,
            'name': t_constants.MOCK_NETWORK_NAME,
            'subnets': [t_constants.MOCK_SUBNET_ID]})])
        network = self.driver.get_network_by_name(
            t_constants.MOCK_NETWORK_NAME)
        self.assertIsInstance(network, network_models.Network)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, network.id)
        self.assertEqual(t_constants.MOCK_NETWORK_NAME, network.name)
        self.assertEqual(1, len(network.subnets))
        self.assertEqual(t_constants.MOCK_SUBNET_ID, network.subnets[0])
        # Negative
        list_network.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.get_network_by_name,
                          t_constants.MOCK_NETWORK_NAME)
        list_network.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_network_by_name,
                          t_constants.MOCK_NETWORK_NAME)

    def test_get_subnet_by_name(self):
        list_subnet = self.driver.network_proxy.subnets
        list_subnet.return_value = iter([Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID,
            'name': t_constants.MOCK_SUBNET_NAME,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR})])
        subnet = self.driver.get_subnet_by_name(t_constants.MOCK_SUBNET_NAME)
        self.assertIsInstance(subnet, network_models.Subnet)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, subnet.id)
        self.assertEqual(t_constants.MOCK_SUBNET_NAME, subnet.name)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, subnet.gateway_ip)
        self.assertEqual(t_constants.MOCK_CIDR, subnet.cidr)
        # Negative
        list_subnet.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.SubnetNotFound,
                          self.driver.get_subnet_by_name,
                          t_constants.MOCK_SUBNET_NAME)
        list_subnet.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_subnet_by_name,
                          t_constants.MOCK_SUBNET_NAME)

    def test_get_port_by_name(self):
        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'name': t_constants.MOCK_PORT_NAME,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]})])
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
        list_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.get_port_by_name,
                          t_constants.MOCK_PORT_NAME)
        list_port.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_port_by_name,
                          t_constants.MOCK_PORT_NAME)

    def test_get_port_by_net_id_device_id(self):
        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'name': t_constants.MOCK_PORT_NAME,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': t_constants.MOCK_DEVICE_ID,
            'fixed_ips': [{
                'subnet_id': t_constants.MOCK_SUBNET_ID,
                'ip_address': t_constants.MOCK_IP_ADDRESS
            }]})])
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
        list_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_PORT_NAME,
                          t_constants.MOCK_DEVICE_ID)
        list_port.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_NETWORK_ID,
                          t_constants.MOCK_DEVICE_ID)

    def test_get_ports_by_net_id_device_id(self):
        """Test get_port_by_net_id_device_id, when port is not unique.

        The expected result is: only the first port is returned.
        """

        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([t_constants.MOCK_NEUTRON_PORT,
                                       t_constants.MOCK_NEUTRON_PORT2,
                                       ])

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
        list_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_PORT_NAME,
                          t_constants.MOCK_DEVICE_ID)
        list_port.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_port_by_net_id_device_id,
                          t_constants.MOCK_NETWORK_ID,
                          t_constants.MOCK_DEVICE_ID)

    def test_get_multiple_ports_by_net_id_device_id(self):
        """Test _get_resources_by_filters, when result is not unique"""
        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([t_constants.MOCK_NEUTRON_PORT,
                                       t_constants.MOCK_NEUTRON_PORT2,
                                       ])

        ports = self.driver._get_resources_by_filters(
            'port',
            network_id=t_constants.MOCK_NETWORK_ID,
            device_id=t_constants.MOCK_DEVICE_ID,
        )
        self.assertIsInstance(ports, list)
        port1, port2 = ports

        self.assertEqual(t_constants.MOCK_PORT_ID, port1.id)
        self.assertEqual(t_constants.MOCK_PORT_ID2, port2.id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS,
                         port1.fixed_ips[0].ip_address)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS2,
                         port2.fixed_ips[0].ip_address)

    def test_get_unique_port_by_name(self):
        """Test _get_resources_by_filters, when result is unique"""
        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([t_constants.MOCK_NEUTRON_PORT])

        port = self.driver._get_resources_by_filters(
            'port', unique_item=True, name=t_constants.MOCK_PORT_NAME)

        self.assertIsInstance(port, network_models.Port)
        self.assertEqual(t_constants.MOCK_PORT_ID, port.id)

    def test_get_non_existing_port_by_name(self):
        """Test _get_resources_by_filters, when result is empty"""
        list_port = self.driver.network_proxy.ports
        list_port.return_value = iter([])

        self.assertRaises(network_base.PortNotFound,
                          self.driver._get_resources_by_filters,
                          'port', unique_item=True, name='port1')

    def test_get_qos_policy(self):
        get_qos = self.driver.network_proxy.get_qos_policy
        get_qos.return_value = QoSPolicy(**{
            'id': t_constants.MOCK_NEUTRON_QOS_POLICY_ID})
        qos = self.driver.get_qos_policy(
            t_constants.MOCK_NEUTRON_QOS_POLICY_ID)
        self.assertIsInstance(qos, network_models.QosPolicy)
        self.assertEqual(t_constants.MOCK_NEUTRON_QOS_POLICY_ID,
                         qos.id)

        get_qos.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.QosPolicyNotFound,
                          self.driver.get_qos_policy,
                          t_constants.MOCK_NEUTRON_QOS_POLICY_ID)

        get_qos.side_effect = os_exceptions.SDKException
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_qos_policy,
                          t_constants.MOCK_NEUTRON_QOS_POLICY_ID)

    def test_apply_qos_on_port(self):
        update_port = self.driver.network_proxy.update_port
        self.driver.apply_qos_on_port(
            t_constants.MOCK_NEUTRON_QOS_POLICY_ID,
            t_constants.MOCK_PORT_ID
        )
        update_port.assert_called_once_with(
            t_constants.MOCK_PORT_ID,
            qos_policy_id=t_constants.MOCK_NEUTRON_QOS_POLICY_ID)

    def test_apply_or_undo_qos_on_port(self):
        # The apply and undo qos function use the same "update_port" with
        # neutron client. So testing them in one Uts.
        update_port = self.driver.network_proxy.update_port
        update_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.apply_qos_on_port,
                          t_constants.MOCK_PORT_ID,
                          t_constants.MOCK_NEUTRON_QOS_POLICY_ID)

        update_port.side_effect = os_exceptions.SDKException
        self.assertRaises(network_base.NetworkException,
                          self.driver.apply_qos_on_port,
                          t_constants.MOCK_PORT_ID,
                          t_constants.MOCK_NEUTRON_QOS_POLICY_ID)

    def test_get_network_ip_availability(self):
        show_network_ip_availability = (
            self.driver.network_proxy.get_network_ip_availability)
        show_network_ip_availability.return_value = (
            NetworkIPAvailability(**{
                'network_id': t_constants.MOCK_NETWORK_ID,
                'subnet_ip_availability':
                    t_constants.MOCK_SUBNET_IP_AVAILABILITY
            }))
        ip_avail = self.driver.get_network_ip_availability(
            network_models.Network(t_constants.MOCK_NETWORK_ID))
        self.assertIsInstance(ip_avail, network_models.Network_IP_Availability)
        self.assertEqual(t_constants.MOCK_NETWORK_ID, ip_avail.network_id)
        self.assertEqual(t_constants.MOCK_SUBNET_IP_AVAILABILITY,
                         ip_avail.subnet_ip_availability)

    def test_plug_fixed_ip(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }]
        })

        self.driver.plug_fixed_ip(t_constants.MOCK_PORT_ID,
                                  t_constants.MOCK_SUBNET_ID2,
                                  t_constants.MOCK_IP_ADDRESS2)

        expected_body = {
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }, {
                    'subnet_id': t_constants.MOCK_SUBNET_ID2,
                    'ip_address': t_constants.MOCK_IP_ADDRESS2
                }
            ]
        }
        self.driver.network_proxy.update_port.assert_called_once_with(
            t_constants.MOCK_PORT_ID,
            **expected_body)

    def test_plug_fixed_ip_no_ip_address(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }]
        })

        self.driver.plug_fixed_ip(t_constants.MOCK_PORT_ID,
                                  t_constants.MOCK_SUBNET_ID2)

        expected_body = {
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }, {
                    'subnet_id': t_constants.MOCK_SUBNET_ID2,
                }
            ]
        }
        self.driver.network_proxy.update_port.assert_called_once_with(
            t_constants.MOCK_PORT_ID, **expected_body)

    def test_plug_fixed_ip_exception(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = {
            'id': t_constants.MOCK_PORT_ID,
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }]
        }

        self.driver.network_proxy.update_port.side_effect = Exception

        self.assertRaises(network_base.NetworkException,
                          self.driver.plug_fixed_ip,
                          t_constants.MOCK_PORT_ID,
                          t_constants.MOCK_SUBNET_ID2)

    def test_unplug_fixed_ip(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(**{
            'id': t_constants.MOCK_PORT_ID,
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID,
                    'ip_address': t_constants.MOCK_IP_ADDRESS,
                    'subnet': None
                }, {
                    'subnet_id': t_constants.MOCK_SUBNET_ID2,
                    'ip_address': t_constants.MOCK_IP_ADDRESS2,
                    'subnet': None
                }]
        })

        self.driver.unplug_fixed_ip(t_constants.MOCK_PORT_ID,
                                    t_constants.MOCK_SUBNET_ID)

        expected_body = {
            'fixed_ips': [
                {
                    'subnet_id': t_constants.MOCK_SUBNET_ID2,
                    'ip_address': t_constants.MOCK_IP_ADDRESS2,
                    'subnet': None
                }
            ]
        }
        self.driver.network_proxy.update_port.assert_called_once_with(
            t_constants.MOCK_PORT_ID,
            **expected_body)

    def test_unplug_fixed_ip_exception(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_id=t_constants.MOCK_PORT_ID,
            fixed_ips=[(t_constants.MOCK_IP_ADDRESS,
                        t_constants.MOCK_SUBNET_ID)],
        )

        self.driver.network_proxy.update_port.side_effect = Exception

        self.assertRaises(network_base.NetworkException,
                          self.driver.unplug_fixed_ip,
                          t_constants.MOCK_PORT_ID,
                          t_constants.MOCK_SUBNET_ID)
