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
from neutronclient.common import exceptions as neutron_exceptions
from novaclient.client import exceptions as nova_exceptions

from octavia.common import constants
from octavia.common import data_models
from octavia.network import base as network_base
from octavia.network.drivers.neutron import allowed_address_pairs
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base


class MockNovaInterface(object):
    net_id = None
    port_id = None
    fixed_ips = []


MOCK_NOVA_INTERFACE = MockNovaInterface()
MOCK_NOVA_INTERFACE.net_id = '1'
MOCK_NOVA_INTERFACE.port_id = '2'
MOCK_NOVA_INTERFACE.fixed_ips = [{'ip_address': '10.0.0.1', 'subnet_id': '10'}]
MOCK_SUBNET = {'subnet': {'id': '10', 'network_id': '1'}}

MOCK_NEUTRON_PORT = {'port': {'network_id': '1',
                              'id': '2',
                              'fixed_ips': [{'ip_address': '10.0.0.1',
                                             'subnet_id': '10'}]}}


class TestAllowedAddressPairsDriver(base.TestCase):

    def setUp(self):
        super(TestAllowedAddressPairsDriver, self).setUp()
        neutron_patcher = mock.patch('neutronclient.neutron.client.Client',
                                     autospec=True)
        mock.patch('novaclient.client.Client', autospec=True).start()
        neutron_client = neutron_patcher.start()
        client = neutron_client(allowed_address_pairs.NEUTRON_VERSION)
        client.list_extensions.return_value = {
            'extensions': [{'alias': allowed_address_pairs.AAP_EXT_ALIAS},
                           {'alias': allowed_address_pairs.SEC_GRP_EXT_ALIAS}]}
        self.k_session = mock.patch(
            'octavia.common.keystone.get_session').start()
        self.driver = allowed_address_pairs.AllowedAddressPairsDriver()

    def test_check_extensions_loaded(self):
        list_extensions = self.driver.neutron_client.list_extensions
        list_extensions.return_value = {
            'extensions': [{'alias': 'blah'}]}
        self.assertRaises(network_base.NetworkException,
                          self.driver._check_extensions_loaded)

    def test_port_to_vip(self):
        fake_lb_id = '4'
        vip = self.driver._port_to_vip(MOCK_NEUTRON_PORT, fake_lb_id)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['ip_address'],
            vip.ip_address)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['subnet_id'],
            vip.subnet_id)
        self.assertEqual(MOCK_NEUTRON_PORT['port']['id'], vip.port_id)
        self.assertEqual(fake_lb_id, vip.load_balancer_id)

    def test_nova_interface_to_octavia_interface(self):
        nova_interface = MockNovaInterface()
        nova_interface.net_id = '1'
        nova_interface.port_id = '2'
        nova_interface.fixed_ips = [{'ip_address': '10.0.0.1'}]
        interface = self.driver._nova_interface_to_octavia_interface(
            '3', nova_interface)
        self.assertEqual('1', interface.network_id)
        self.assertEqual('2', interface.port_id)
        self.assertEqual('10.0.0.1', interface.ip_address)

    def test_get_interfaces_to_unplug(self):
        if1 = MockNovaInterface()
        if1.net_id = 'if1-net'
        if1.port_id = 'if1-port'
        if1.fixed_ips = [{'ip_address': '10.0.0.1'}]
        if2 = MockNovaInterface()
        if2.net_id = 'if2-net'
        if2.port_id = 'if2-port'
        if2.fixed_ips = [{'ip_address': '11.0.0.1'}]
        interfaces = [if1, if2]
        unpluggers = self.driver._get_interfaces_to_unplug(
            interfaces, 'if1-net')
        self.assertEqual([if1], unpluggers)
        unpluggers = self.driver._get_interfaces_to_unplug(
            interfaces, 'if1-net', ip_address='10.0.0.1')
        self.assertEqual([if1], unpluggers)
        unpluggers = self.driver._get_interfaces_to_unplug(
            interfaces, 'if1-net', ip_address='11.0.0.1')
        self.assertEqual([], unpluggers)
        unpluggers = self.driver._get_interfaces_to_unplug(
            interfaces, 'if3-net')
        self.assertEqual([], unpluggers)

    def test_deallocate_vip(self):
        vip = data_models.Vip(port_id='1')
        admin_tenant_id = 'octavia'
        session_mock = mock.MagicMock()
        session_mock.get_project_id.return_value = admin_tenant_id
        self.k_session.return_value = session_mock
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {'tenant_id': admin_tenant_id}}
        self.driver.deallocate_vip(vip)
        delete_port = self.driver.neutron_client.delete_port
        delete_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.VIPConfigurationNotFound,
                          self.driver.deallocate_vip, vip)
        delete_port.side_effect = TypeError
        self.assertRaises(network_base.DeallocateVIPException,
                          self.driver.deallocate_vip, vip)

    def test_deallocate_vip_when_port_not_owned_by_octavia(self):
        vip = data_models.Vip(port_id='1')
        session_mock = mock.MagicMock()
        session_mock.get_project_id.return_value = 'octavia'
        self.k_session.return_value = session_mock
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {'tenant_id': 'not-octavia'}}
        delete_port = self.driver.neutron_client.delete_port
        self.driver.deallocate_vip(vip)
        self.assertFalse(delete_port.called)

    def test_plug_vip(self):
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound
        lb = dmh.generate_load_balancer_tree()
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_vip, lb, lb.vip)
        interface_attach.side_effect = None
        interface_attach.return_value = MOCK_NOVA_INTERFACE
        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.PortNotFound,
                          self.driver.plug_vip, lb, lb.vip)
        update_port.side_effect = TypeError
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_vip, lb, lb.vip)
        update_port.side_effect = None
        update_port.reset_mock()
        list_security_groups = self.driver.neutron_client.list_security_groups
        list_security_groups.return_value = {
            'security_groups': [
                {'id': 'lb-sec-grp1'}
            ]
        }
        mock_ip = MOCK_NOVA_INTERFACE.fixed_ips[0].get('ip_address')
        expected_aap = {'port': {'allowed_address_pairs':
                                 [{'ip_address': lb.vip.ip_address}]}}
        interface_list = self.driver.nova_client.servers.interface_list
        if1 = MOCK_NOVA_INTERFACE
        if2 = MockNovaInterface()
        if2.net_id = '3'
        if2.port_id = '4'
        if2.fixed_ips = [{'ip_address': '10.0.0.2'}]
        interface_list.return_value = [if1, if2]
        amps = self.driver.plug_vip(lb, lb.vip)
        self.assertEqual(3, update_port.call_count)
        update_port.assert_any_call(if1.port_id, expected_aap)
        for amp in amps:
            self.assertEqual(mock_ip, amp.vrrp_ip)
            self.assertEqual(lb.vip.ip_address, amp.ha_ip)
            self.assertIn(amp.id, [lb.amphorae[0].id, lb.amphorae[1].id])

    def test_allocate_vip(self):
        fake_lb_vip = data_models.Vip()
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        self.assertRaises(network_base.AllocateVIPException,
                          self.driver.allocate_vip, fake_lb)
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = MOCK_NEUTRON_PORT
        fake_lb_vip = data_models.Vip(port_id=MOCK_NEUTRON_PORT['port']['id'])
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip = self.driver.allocate_vip(fake_lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['ip_address'],
            vip.ip_address)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['subnet_id'],
            vip.subnet_id)
        self.assertEqual(MOCK_NEUTRON_PORT['port']['id'], vip.port_id)
        self.assertIsNone(vip.load_balancer_id)

        create_port = self.driver.neutron_client.create_port
        create_port.return_value = MOCK_NEUTRON_PORT
        fake_lb_vip = data_models.Vip(
            subnet_id=MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['subnet_id'])
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip = self.driver.allocate_vip(fake_lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['ip_address'],
            vip.ip_address)
        self.assertEqual(
            MOCK_NEUTRON_PORT['port']['fixed_ips'][0]['subnet_id'],
            vip.subnet_id)
        self.assertEqual(MOCK_NEUTRON_PORT['port']['id'], vip.port_id)
        self.assertIsNone(vip.load_balancer_id)

    def test_unplug_vip(self):
        lb = dmh.generate_load_balancer_tree()
        interface_list = self.driver.nova_client.servers.interface_list
        interface_list.reset_mock()
        self.driver.neutron_client.show_subnet.return_value = MOCK_SUBNET
        if1 = MOCK_NOVA_INTERFACE
        if2 = MockNovaInterface()
        if2.net_id = '3'
        if2.port_id = '4'
        if2.fixed_ips = [{'ip_address': '10.0.0.2'}]
        interface_list.return_value = [if1, if2]
        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_vip, lb, lb.vip)
        update_port.side_effect = TypeError
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_vip, lb, lb.vip)
        update_port.side_effect = None
        update_port.reset_mock()
        self.driver.unplug_vip(lb, lb.vip)
        self.assertEqual(len(lb.amphorae), update_port.call_count)
        clear_aap = {'port': {'allowed_address_pairs': []}}
        update_port.assert_has_calls([mock.call(if1.port_id, clear_aap),
                                      mock.call(if1.port_id, clear_aap)])

    def test_plug_network(self):
        amp_id = '1'
        net_id = MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Instance not found')
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_network, amp_id, net_id)
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Network not found')
        self.assertRaises(network_base.NetworkException,
                          self.driver.plug_network, amp_id, net_id)
        interface_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_network, amp_id, net_id)
        interface_attach.side_effect = None
        interface_attach.return_value = MOCK_NOVA_INTERFACE
        oct_interface = self.driver.plug_network(amp_id, net_id)
        self.assertEqual(MOCK_NOVA_INTERFACE.fixed_ips[0].get('ip_address'),
                         oct_interface.ip_address)
        self.assertEqual(amp_id, oct_interface.amphora_id)
        self.assertEqual(net_id, oct_interface.network_id)

    def test_get_plugged_networks(self):
        amp_id = '1'
        interface_list = self.driver.nova_client.servers.interface_list
        interface_list.side_effect = TypeError
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_plugged_networks, amp_id)
        interface_list.side_effect = None
        interface_list.reset_mock()
        if1 = MOCK_NOVA_INTERFACE
        if2 = MockNovaInterface()
        if2.net_id = '3'
        if2.port_id = '4'
        if2.fixed_ips = [{'ip_address': '10.0.0.2'}]
        interface_list.return_value = [if1, if2]
        plugged_networks = self.driver.get_plugged_networks(amp_id)
        for pn in plugged_networks:
            self.assertIn(pn.port_id, [if1.port_id, if2.port_id])
            self.assertIn(pn.network_id, [if1.net_id, if2.net_id])
            self.assertIn(pn.ip_address, [if1.fixed_ips[0]['ip_address'],
                                          if2.fixed_ips[0]['ip_address']])

    def test_unplug_network(self):
        amp_id = '1'
        net_id = MOCK_NOVA_INTERFACE.net_id
        interface_list = self.driver.nova_client.servers.interface_list
        interface_list.side_effect = nova_exceptions.NotFound(404)
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.unplug_network, amp_id, net_id)
        interface_list.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.unplug_network, amp_id, net_id)
        interface_list.side_effect = None
        interface_list.reset_mock()
        if1 = MockNovaInterface()
        if1.net_id = 'if1-net'
        if1.port_id = 'if1-port'
        if1.fixed_ips = [{'ip_address': '10.0.0.1'}]
        if2 = MockNovaInterface()
        if2.net_id = 'if2-net'
        if2.port_id = 'if2-port'
        if2.fixed_ips = [{'ip_address': '11.0.0.1'}]
        interface_list.return_value = [if1, if2]
        interface_detach = self.driver.nova_client.servers.interface_detach
        interface_detach.side_effect = Exception
        self.assertRaises(network_base.UnplugNetworkException,
                          self.driver.unplug_network, amp_id, if2.net_id)
        interface_detach.side_effect = None
        interface_detach.reset_mock()
        self.driver.unplug_network(amp_id, if2.net_id)
        interface_detach.assert_called_once_with(server=amp_id,
                                                 port_id=if2.port_id)

    def test_update_vip(self):
        listeners = [data_models.Listener(protocol_port=80),
                     data_models.Listener(protocol_port=443)]
        lb = data_models.LoadBalancer(id='1', listeners=listeners)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'rule-80', 'port_range_max': 80},
                {'id': 'rule-22', 'port_range_max': 22}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        create_rule = self.driver.neutron_client.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')
        expected_create_rule = {
            'security_group_rule': {
                'security_group_id': 'secgrp-1',
                'direction': 'ingress',
                'protocol': 'TCP',
                'port_range_min': 443,
                'port_range_max': 443
            }
        }
        create_rule.assert_called_once_with(expected_create_rule)

    def test_update_vip_when_listener_deleted(self):
        listeners = [data_models.Listener(protocol_port=80),
                     data_models.Listener(
                         protocol_port=443,
                         provisioning_status=constants.PENDING_DELETE)]
        lb = data_models.LoadBalancer(id='1', listeners=listeners)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'rule-80', 'port_range_max': 80},
                {'id': 'rule-22', 'port_range_max': 443}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        create_rule = self.driver.neutron_client.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')
        self.assertFalse(create_rule.called)
