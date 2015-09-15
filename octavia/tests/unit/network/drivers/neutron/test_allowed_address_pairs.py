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

import copy

import mock
from neutronclient.common import exceptions as neutron_exceptions
from novaclient.client import exceptions as nova_exceptions

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import allowed_address_pairs
from octavia.network.drivers.neutron import base as neutron_base
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base
from octavia.tests.unit.network.drivers.neutron import constants as n_constants


class TestAllowedAddressPairsDriver(base.TestCase):
    k_session = None
    driver = None

    SUBNET_ID_1 = "5"
    SUBNET_ID_2 = "8"
    FIXED_IP_ID_1 = "6"
    FIXED_IP_ID_2 = "8"
    NETWORK_ID_1 = "7"
    NETWORK_ID_2 = "10"
    IP_ADDRESS_1 = "10.0.0.2"
    IP_ADDRESS_2 = "12.0.0.2"
    AMPHORA_ID = "1"
    LB_ID = "2"
    COMPUTE_ID = "3"
    ACTIVE = "ACTIVE"
    LB_NET_IP = "10.0.0.2"
    LB_NET_PORT_ID = "6"
    HA_PORT_ID = "8"
    HA_IP = "12.0.0.2"

    def setUp(self):
        super(TestAllowedAddressPairsDriver, self).setUp()
        with mock.patch('octavia.common.clients.neutron_client.Client',
                        autospec=True) as neutron_client:
            with mock.patch('octavia.common.clients.nova_client.Client',
                            autospec=True):
                client = neutron_client(clients.NEUTRON_VERSION)
                client.list_extensions.return_value = {
                    'extensions': [
                        {'alias': allowed_address_pairs.AAP_EXT_ALIAS},
                        {'alias': neutron_base.SEC_GRP_EXT_ALIAS}
                    ]
                }
                self.k_session = mock.patch(
                    'octavia.common.keystone.get_session').start()
                self.driver = allowed_address_pairs.AllowedAddressPairsDriver()

    def test_check_aap_loaded(self):
        self.driver._extensions = [{'alias': 'blah'}]
        self.assertRaises(network_base.NetworkException,
                          self.driver._check_aap_loaded)

    def test_get_interfaces_to_unplug(self):
        if1 = network_models.Interface()
        if1.network_id = 'if1-net'
        if1.port_id = 'if1-port'
        if1.fixed_ips = [network_models.FixedIP(ip_address='10.0.0.1')]
        if2 = network_models.Interface()
        if2.network_id = 'if2-net'
        if2.port_id = 'if2-port'
        if2.fixed_ips = [network_models.FixedIP(ip_address='11.0.0.1')]
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
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        delete_sec_grp = self.driver.neutron_client.delete_security_group
        list_security_groups = self.driver.neutron_client.list_security_groups
        security_groups = {
            'security_groups': [
                {'id': sec_grp_id}
            ]
        }
        list_security_groups.return_value = security_groups
        self.driver.deallocate_vip(vip)
        delete_port.assert_called_once_with(vip.port_id)
        delete_sec_grp.assert_called_once_with(sec_grp_id)

    def test_deallocate_vip_when_delete_port_fails(self):
        vip = data_models.Vip(port_id='1')
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        delete_port.side_effect = TypeError
        self.assertRaises(network_base.DeallocateVIPException,
                          self.driver.deallocate_vip, vip)

    def test_deallocate_vip_when_port_not_found(self):
        vip = data_models.Vip(port_id='1')
        show_port = self.driver.neutron_client.show_port
        show_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.VIPConfigurationNotFound,
                          self.driver.deallocate_vip, vip)

    def test_deallocate_vip_when_port_not_owned_by_octavia(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'id': vip.port_id,
            'device_owner': 'neutron:LOADBALANCERV2',
            'security_groups': [sec_grp_id]}}
        delete_port = self.driver.neutron_client.delete_port
        update_port = self.driver.neutron_client.update_port
        delete_sec_grp = self.driver.neutron_client.delete_security_group
        list_security_groups = self.driver.neutron_client.list_security_groups
        security_groups = {
            'security_groups': [
                {'id': sec_grp_id}
            ]
        }
        list_security_groups.return_value = security_groups
        self.driver.deallocate_vip(vip)
        expected_port_update = {'port': {'security_groups': []}}
        update_port.assert_called_once_with(vip.port_id, expected_port_update)
        delete_sec_grp.assert_called_once_with(sec_grp_id)
        self.assertFalse(delete_port.called)

    def test_deallocate_vip_when_vip_port_not_found(self):
        vip = data_models.Vip(port_id='1')
        admin_tenant_id = 'octavia'
        session_mock = mock.MagicMock()
        session_mock.get_project_id.return_value = admin_tenant_id
        self.k_session.return_value = session_mock
        show_port = self.driver.neutron_client.show_port
        show_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.VIPConfigurationNotFound,
                          self.driver.deallocate_vip, vip)

    def test_plug_vip_errors_when_nova_cant_find_network_to_attach(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {
            'subnet': {
                'id': lb.vip.subnet_id
            }
        }
        list_security_groups = self.driver.neutron_client.list_security_groups
        lsc_side_effect = [
            None, {
                'security_groups': [
                    {'id': 'lb-sec-grp1'}
                ]
            }
        ]
        list_security_groups.side_effect = lsc_side_effect

        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(404, "Network")
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_vip, lb, lb.vip)

    def test_plug_vip_errors_when_neutron_cant_find_port_to_update(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {
            'subnet': {
                'id': lb.vip.subnet_id
            }
        }
        list_security_groups = self.driver.neutron_client.list_security_groups
        lsc_side_effect = [
            None, {
                'security_groups': [
                    {'id': 'lb-sec-grp1'}
                ]
            }
        ]
        list_security_groups.side_effect = lsc_side_effect
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.return_value = n_constants.MOCK_NOVA_INTERFACE

        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.PortNotFound,
                          self.driver.plug_vip, lb, lb.vip)

    def test_plug_vip(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {
            'subnet': {
                'id': lb.vip.subnet_id
            }
        }
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.return_value = n_constants.MOCK_NOVA_INTERFACE
        list_security_groups = self.driver.neutron_client.list_security_groups
        list_security_groups.return_value = {
            'security_groups': [
                {'id': 'lb-sec-grp1'}
            ]
        }
        update_port = self.driver.neutron_client.update_port
        expected_aap = {'port': {'allowed_address_pairs':
                                 [{'ip_address': lb.vip.ip_address}]}}
        interface_list = self.driver.nova_client.servers.interface_list
        if1 = n_constants.MOCK_NOVA_INTERFACE
        if2 = n_constants.MockNovaInterface()
        if2.net_id = '3'
        if2.port_id = '4'
        if2.fixed_ips = [{'ip_address': '10.0.0.2'}]
        if1.fixed_ips = [{'ip_address': n_constants.MOCK_IP_ADDRESS,
                          'subnet_id': lb.vip.subnet_id}]
        interface_list.return_value = [if1, if2]
        amps = self.driver.plug_vip(lb, lb.vip)
        self.assertEqual(5, update_port.call_count)
        update_port.assert_any_call(if1.port_id, expected_aap)
        for amp in amps:
            self.assertEqual(n_constants.MOCK_IP_ADDRESS, amp.vrrp_ip)
            self.assertEqual(lb.vip.ip_address, amp.ha_ip)
            self.assertIn(amp.id, [lb.amphorae[0].id, lb.amphorae[1].id])

    def test_allocate_vip_when_port_already_provided(self):
        fake_lb_vip = data_models.Vip()
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        self.assertRaises(network_base.AllocateVIPException,
                          self.driver.allocate_vip, fake_lb)
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = n_constants.MOCK_NEUTRON_PORT
        fake_lb_vip = data_models.Vip(
            port_id=n_constants.MOCK_PORT_ID,
            subnet_id=n_constants.MOCK_SUBNET_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip = self.driver.allocate_vip(fake_lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(n_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(n_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(n_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)

    def test_allocate_vip_when_only_subnet_provided(self):
        port_create_dict = copy.copy(n_constants.MOCK_NEUTRON_PORT)
        port_create_dict['port']['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['port']['device_id'] = 'lb-1'
        create_port = self.driver.neutron_client.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {'subnet': {
            'id': n_constants.MOCK_SUBNET_ID,
            'network_id': n_constants.MOCK_NETWORK_ID
        }}
        fake_lb_vip = data_models.Vip(subnet_id=n_constants.MOCK_SUBNET_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'port': {
                'name': 'octavia-lb-1',
                'network_id': n_constants.MOCK_NETWORK_ID,
                'device_id': 'lb-1',
                'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
                'admin_state_up': False
            }
        }
        create_port.assert_called_once_with(exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(n_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(n_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(n_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)

    def test_unplug_vip_errors_when_update_port_cant_find_port(self):
        lb = dmh.generate_load_balancer_tree()
        list_ports = self.driver.neutron_client.list_ports
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = n_constants.MOCK_SUBNET
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_vip, lb, lb.vip)

    def test_unplug_vip_errors_when_update_port_fails(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = n_constants.MOCK_SUBNET
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports = self.driver.neutron_client.list_ports
        list_ports.return_value = {'ports': [port1, port2]}

        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = TypeError
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_vip, lb, lb.vip)

    def test_unplug_vip_errors_when_vip_subnet_not_found(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.side_effect = neutron_exceptions.NotFound
        self.assertRaises(network_base.PluggedVIPNotFound,
                          self.driver.unplug_vip, lb, lb.vip)

    def test_unplug_vip(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = n_constants.MOCK_SUBNET
        update_port = self.driver.neutron_client.update_port
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports = self.driver.neutron_client.list_ports
        list_ports.return_value = {'ports': [port1, port2]}
        self.driver.unplug_vip(lb, lb.vip)
        self.assertEqual(len(lb.amphorae), update_port.call_count)
        clear_aap = {'port': {'allowed_address_pairs': []}}
        update_port.assert_has_calls([mock.call(port1.get('id'), clear_aap),
                                      mock.call(port1.get('id'), clear_aap)])

    def test_plug_network_when_compute_instance_cant_be_found(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Instance not found')
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_network,
                          n_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_network_cant_be_found(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Network not found')
        self.assertRaises(network_base.NetworkException,
                          self.driver.plug_network,
                          n_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_interface_attach_fails(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_network,
                          n_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.return_value = n_constants.MOCK_NOVA_INTERFACE
        oct_interface = self.driver.plug_network(
            n_constants.MOCK_COMPUTE_ID, net_id)
        exp_ips = [fixed_ip.get('ip_address')
                   for fixed_ip in n_constants.MOCK_NOVA_INTERFACE.fixed_ips]
        actual_ips = [fixed_ip.ip_address
                      for fixed_ip in oct_interface.fixed_ips]
        self.assertEqual(exp_ips, actual_ips)
        self.assertEqual(n_constants.MOCK_COMPUTE_ID, oct_interface.compute_id)
        self.assertEqual(net_id, oct_interface.network_id)

    def test_unplug_network_when_compute_port_cant_be_found(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        list_ports = self.driver.neutron_client.list_ports
        list_ports.return_value = {'ports': []}
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.unplug_network,
                          n_constants.MOCK_COMPUTE_ID, net_id)

    def test_unplug_network_when_list_ports_fails(self):
        net_id = n_constants.MOCK_NOVA_INTERFACE.net_id
        list_ports = self.driver.neutron_client.list_ports
        list_ports.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.unplug_network,
                          n_constants.MOCK_COMPUTE_ID, net_id)

    def test_unplug_network_when_interface_detach_fails(self):
        list_ports = self.driver.neutron_client.list_ports
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        interface_detach = self.driver.nova_client.servers.interface_detach
        interface_detach.side_effect = Exception
        self.assertRaises(network_base.UnplugNetworkException,
                          self.driver.unplug_network,
                          n_constants.MOCK_COMPUTE_ID,
                          port2.get('network_id'))

    def test_unplug_network(self):
        list_ports = self.driver.neutron_client.list_ports
        port1 = n_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        interface_detach = self.driver.nova_client.servers.interface_detach
        self.driver.unplug_network(n_constants.MOCK_COMPUTE_ID,
                                   port2.get('network_id'))
        interface_detach.assert_called_once_with(
            server=n_constants.MOCK_COMPUTE_ID, port_id=port2.get('id'))

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

    def test_update_vip_when_no_listeners(self):
        listeners = []
        lb = data_models.LoadBalancer(id='1', listeners=listeners)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'all-egress', 'protocol': None, 'direction': 'egress'},
                {'id': 'ssh-rule', 'protocol': 'TCP', 'port_range_max': 22}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        create_rule = self.driver.neutron_client.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('ssh-rule')
        self.assertFalse(create_rule.called)

    def test_failover_preparation(self):
        ports = {"ports": [
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                            "ip_address": self.IP_ADDRESS_1}],
             "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1},
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                            "ip_address": self.IP_ADDRESS_2}],
             "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}]}
        self.driver.neutron_client.list_ports.return_value = ports
        self.driver.neutron_client.show_port = mock.Mock(
            side_effect=self._failover_show_port_side_effect)
        port_update = self.driver.neutron_client.update_port
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)
        self.driver.failover_preparation(amphora)
        port_update.assert_called_once_with(ports["ports"][1].get("id"),
                                            {'port': {'device_id': ''}})

    def _failover_show_port_side_effect(self, port_id):
        if port_id == self.LB_NET_PORT_ID:
            return {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                                   "ip_address": self.IP_ADDRESS_1}],
                    "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1}
        if port_id == self.HA_PORT_ID:
            return {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                                   "ip_address": self.IP_ADDRESS_2}],
                    "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}
