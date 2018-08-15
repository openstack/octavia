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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import clients
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.network import base as network_base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import allowed_address_pairs
from octavia.network.drivers.neutron import base as neutron_base
from octavia.tests.common import constants as t_constants
from octavia.tests.common import data_model_helpers as dmh
from octavia.tests.unit import base


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
    PORT_ID = uuidutils.generate_uuid()
    DEVICE_ID = uuidutils.generate_uuid()

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
                    'keystoneauth1.session.Session').start()
                self.driver = allowed_address_pairs.AllowedAddressPairsDriver()

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=False)
    def test_check_aap_loaded(self, mock_check_ext):
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
        calls = [mock.call(vip.port_id)]
        for amp in lb.amphorae:
            calls.append(mock.call(amp.vrrp_port_id))
        delete_port.assert_has_calls(calls, any_order=True)
        delete_sec_grp.assert_called_once_with(sec_grp_id)

    def test_deallocate_vip_no_port(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.neutron_client.show_port
        port = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        show_port.side_effect = [port, Exception]
        list_security_groups = self.driver.neutron_client.list_security_groups
        security_groups = {
            'security_groups': [
                {'id': sec_grp_id}
            ]
        }
        list_security_groups.return_value = security_groups
        self.driver.deallocate_vip(vip)
        self.driver.neutron_client.update_port.assert_not_called()

    def test_deallocate_vip_port_deleted(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        delete_port.side_effect = neutron_exceptions.NotFound
        delete_sec_grp = self.driver.neutron_client.delete_security_group
        list_security_groups = self.driver.neutron_client.list_security_groups
        security_groups = {
            'security_groups': [
                {'id': sec_grp_id}
            ]
        }
        list_security_groups.return_value = security_groups
        self.driver.deallocate_vip(vip)
        calls = [mock.call(vip.port_id)]
        for amp in lb.amphorae:
            calls.append(mock.call(amp.vrrp_port_id))
        delete_port.assert_has_calls(calls, any_order=True)
        delete_sec_grp.assert_called_once_with(sec_grp_id)

    def test_deallocate_vip_no_sec_group(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        delete_sec_grp = self.driver.neutron_client.delete_security_group
        list_security_groups = self.driver.neutron_client.list_security_groups
        security_groups = {
            'security_groups': []
        }
        list_security_groups.return_value = security_groups
        self.driver.deallocate_vip(vip)
        delete_port.assert_called_with(vip.port_id)
        delete_sec_grp.assert_not_called()

    def test_deallocate_vip_when_delete_port_fails(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        delete_port.side_effect = [None, None, TypeError]
        self.assertRaises(network_base.DeallocateVIPException,
                          self.driver.deallocate_vip, vip)

    def test_deallocate_vip_when_secgrp_has_allocated_ports(self):
        max_retries = 1
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="networking", max_retries=max_retries)

        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        delete_port = self.driver.neutron_client.delete_port
        list_ports = self.driver.neutron_client.list_ports
        list_security_groups = self.driver.neutron_client.list_security_groups
        delete_sec_grp = self.driver.neutron_client.delete_security_group
        security_groups = {
            'security_groups': [
                {'id': t_constants.MOCK_SECURITY_GROUP_ID}
            ]
        }
        list_security_groups.return_value = security_groups
        delete_grp_results = [
            network_base.DeallocateVIPException
            for _ in range(max_retries + 1)]  # Total tries = max_retries + 1
        delete_grp_results.append(None)
        delete_sec_grp.side_effect = delete_grp_results
        list_ports.side_effect = [{
            "ports": [t_constants.MOCK_NEUTRON_PORT['port'],
                      t_constants.MOCK_NEUTRON_PORT2['port']]}]
        self.driver.deallocate_vip(vip)
        # First we expect the amp's ports to be deleted
        dp_calls = [mock.call(amp.vrrp_port_id) for amp in lb.amphorae]
        # Then after the SG delete fails, extra hanging-on ports are removed
        dp_calls.append(mock.call(t_constants.MOCK_PORT_ID))
        # Lastly we remove the vip port
        dp_calls.append(mock.call(vip.port_id))
        self.assertEqual(len(dp_calls), delete_port.call_count)
        delete_port.assert_has_calls(dp_calls)
        dsg_calls = [mock.call(t_constants.MOCK_SECURITY_GROUP_ID)
                     for _ in range(max_retries + 2)]  # Max fail + one success
        self.assertEqual(len(dsg_calls), delete_sec_grp.call_count)
        delete_sec_grp.assert_has_calls(dsg_calls)

    def test_deallocate_vip_when_port_not_found(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        show_port = self.driver.neutron_client.show_port
        show_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.driver.deallocate_vip(vip)

    def test_deallocate_vip_when_port_not_found_for_update(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = {'port': {
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER}}
        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.driver.deallocate_vip(vip)

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

    def test_deallocate_vip_when_vip_port_not_found(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        admin_project_id = 'octavia'
        session_mock = mock.MagicMock()
        session_mock.get_project_id.return_value = admin_project_id
        self.k_session.return_value = session_mock
        show_port = self.driver.neutron_client.show_port
        show_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.driver.deallocate_vip(vip)

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
        interface_attach.return_value = t_constants.MOCK_NOVA_INTERFACE

        update_port = self.driver.neutron_client.update_port
        update_port.side_effect = neutron_exceptions.PortNotFoundClient
        self.assertRaises(network_base.PortNotFound,
                          self.driver.plug_vip, lb, lb.vip)

    def test_plug_vip(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {
            'subnet': {
                'id': t_constants.MOCK_VIP_SUBNET_ID,
                'network_id': t_constants.MOCK_VIP_NET_ID
            }
        }
        list_ports = self.driver.neutron_client.list_ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1['port']
        port2 = t_constants.MOCK_MANAGEMENT_PORT2['port']
        list_ports.side_effect = [{'ports': [port1]}, {'ports': [port2]}]
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = [t_constants.MOCK_VRRP_INTERFACE1,
                                        t_constants.MOCK_VRRP_INTERFACE2]
        list_security_groups = self.driver.neutron_client.list_security_groups
        list_security_groups.return_value = {
            'security_groups': [
                {'id': 'lb-sec-grp1'}
            ]
        }
        update_port = self.driver.neutron_client.update_port
        expected_aap = {'port': {'allowed_address_pairs':
                                 [{'ip_address': lb.vip.ip_address}]}}
        amps = self.driver.plug_vip(lb, lb.vip)
        self.assertEqual(5, update_port.call_count)
        for amp in amps:
            update_port.assert_any_call(amp.vrrp_port_id, expected_aap)
            self.assertIn(amp.vrrp_ip, [t_constants.MOCK_VRRP_IP1,
                                        t_constants.MOCK_VRRP_IP2])
            self.assertEqual(lb.vip.ip_address, amp.ha_ip)

    def _set_safely(self, obj, name, value):
        if isinstance(obj, dict):
            current = obj.get(name)
            self.addCleanup(obj.update, {name: current})
            obj.update({name: value})
        else:
            current = getattr(obj, name)
            self.addCleanup(setattr, obj, name, current)
            setattr(obj, name, value)

    def test_plug_vip_on_mgmt_net(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.subnet_id = t_constants.MOCK_MANAGEMENT_SUBNET_ID
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {
            'subnet': {
                'id': t_constants.MOCK_MANAGEMENT_SUBNET_ID,
                'network_id': t_constants.MOCK_MANAGEMENT_NET_ID
            }
        }
        list_ports = self.driver.neutron_client.list_ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1['port']
        port2 = t_constants.MOCK_MANAGEMENT_PORT2['port']
        self._set_safely(t_constants.MOCK_MANAGEMENT_FIXED_IPS1[0],
                         'ip_address', lb.amphorae[0].lb_network_ip)
        self._set_safely(t_constants.MOCK_MANAGEMENT_FIXED_IPS2[0],
                         'ip_address', lb.amphorae[1].lb_network_ip)
        list_ports.side_effect = [{'ports': [port1]}, {'ports': [port2]}]
        interface_attach = self.driver.nova_client.servers.interface_attach
        self._set_safely(t_constants.MOCK_VRRP_INTERFACE1,
                         'net_id', t_constants.MOCK_MANAGEMENT_NET_ID)
        self._set_safely(t_constants.MOCK_VRRP_FIXED_IPS1[0],
                         'subnet_id', t_constants.MOCK_MANAGEMENT_SUBNET_ID)
        self._set_safely(t_constants.MOCK_VRRP_INTERFACE2,
                         'net_id', t_constants.MOCK_MANAGEMENT_NET_ID)
        self._set_safely(t_constants.MOCK_VRRP_FIXED_IPS2[0],
                         'subnet_id', t_constants.MOCK_MANAGEMENT_SUBNET_ID)
        interface_attach.side_effect = [t_constants.MOCK_VRRP_INTERFACE1,
                                        t_constants.MOCK_VRRP_INTERFACE2]
        list_security_groups = self.driver.neutron_client.list_security_groups
        list_security_groups.return_value = {
            'security_groups': [
                {'id': 'lb-sec-grp1'}
            ]
        }
        update_port = self.driver.neutron_client.update_port
        expected_aap = {'port': {'allowed_address_pairs':
                                 [{'ip_address': lb.vip.ip_address}]}}
        amps = self.driver.plug_vip(lb, lb.vip)
        self.assertEqual(5, update_port.call_count)
        for amp in amps:
            update_port.assert_any_call(amp.vrrp_port_id, expected_aap)
            self.assertIn(amp.vrrp_ip, [t_constants.MOCK_VRRP_IP1,
                                        t_constants.MOCK_VRRP_IP2])
            self.assertEqual(lb.vip.ip_address, amp.ha_ip)

    def test_allocate_vip_when_port_already_provided(self):
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = t_constants.MOCK_NEUTRON_PORT
        fake_lb_vip = data_models.Vip(
            port_id=t_constants.MOCK_PORT_ID,
            subnet_id=t_constants.MOCK_SUBNET_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip = self.driver.allocate_vip(fake_lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)

    def test_allocate_vip_when_port_creation_fails(self):
        fake_lb_vip = data_models.Vip(
            subnet_id=t_constants.MOCK_SUBNET_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        create_port = self.driver.neutron_client.create_port
        create_port.side_effect = Exception
        self.assertRaises(network_base.AllocateVIPException,
                          self.driver.allocate_vip, fake_lb)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_when_no_port_provided(self, mock_check_ext):
        port_create_dict = copy.deepcopy(t_constants.MOCK_NEUTRON_PORT)
        port_create_dict['port']['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['port']['device_id'] = 'lb-1'
        create_port = self.driver.neutron_client.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }}
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'port': {
                'name': 'octavia-lb-1',
                'network_id': t_constants.MOCK_NETWORK_ID,
                'device_id': 'lb-1',
                'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
                'admin_state_up': False,
                'project_id': 'test-project',
                'fixed_ips': [{'subnet_id': t_constants.MOCK_SUBNET_ID}]
            }
        }
        create_port.assert_called_once_with(exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=False)
    def test_allocate_vip_when_no_port_provided_tenant(self, mock_check_ext):
        port_create_dict = copy.deepcopy(t_constants.MOCK_NEUTRON_PORT)
        port_create_dict['port']['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['port']['device_id'] = 'lb-1'
        create_port = self.driver.neutron_client.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }}
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'port': {
                'name': 'octavia-lb-1',
                'network_id': t_constants.MOCK_NETWORK_ID,
                'device_id': 'lb-1',
                'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
                'admin_state_up': False,
                'tenant_id': 'test-project',
                'fixed_ips': [{'subnet_id': t_constants.MOCK_SUBNET_ID}]
            }
        }
        create_port.assert_called_once_with(exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)

    def test_unplug_vip_errors_when_update_port_cant_find_port(self):
        lb = dmh.generate_load_balancer_tree()
        list_ports = self.driver.neutron_client.list_ports
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = t_constants.MOCK_SUBNET
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
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
        show_subnet.return_value = t_constants.MOCK_SUBNET
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
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
        show_subnet.return_value = t_constants.MOCK_SUBNET
        update_port = self.driver.neutron_client.update_port
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports = self.driver.neutron_client.list_ports
        list_ports.return_value = {'ports': [port1, port2]}
        get_port = self.driver.neutron_client.get_port
        get_port.side_effect = neutron_exceptions.NotFound
        self.driver.unplug_vip(lb, lb.vip)
        self.assertEqual(len(lb.amphorae), update_port.call_count)
        clear_aap = {'port': {'allowed_address_pairs': []}}
        update_port.assert_has_calls([mock.call(port1.get('id'), clear_aap),
                                      mock.call(port1.get('id'), clear_aap)])

    def test_plug_network_when_compute_instance_cant_be_found(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Instance not found')
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_network_cant_be_found(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = nova_exceptions.NotFound(
            404, message='Network not found')
        self.assertRaises(network_base.NetworkException,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_interface_attach_fails(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        interface_attach = self.driver.nova_client.servers.interface_attach
        interface_attach.return_value = t_constants.MOCK_NOVA_INTERFACE
        oct_interface = self.driver.plug_network(
            t_constants.MOCK_COMPUTE_ID, net_id)
        exp_ips = [fixed_ip.get('ip_address')
                   for fixed_ip in t_constants.MOCK_NOVA_INTERFACE.fixed_ips]
        actual_ips = [fixed_ip.ip_address
                      for fixed_ip in oct_interface.fixed_ips]
        self.assertEqual(exp_ips, actual_ips)
        self.assertEqual(t_constants.MOCK_COMPUTE_ID,
                         oct_interface.compute_id)
        self.assertEqual(net_id, oct_interface.network_id)

    def test_unplug_network_when_compute_port_cant_be_found(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        list_ports = self.driver.neutron_client.list_ports
        list_ports.return_value = {'ports': []}
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.unplug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_unplug_network_when_list_ports_fails(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        list_ports = self.driver.neutron_client.list_ports
        list_ports.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.unplug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_unplug_network_when_interface_detach_fails(self):
        list_ports = self.driver.neutron_client.list_ports
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        interface_detach = self.driver.nova_client.servers.interface_detach
        interface_detach.side_effect = Exception
        self.driver.unplug_network(t_constants.MOCK_COMPUTE_ID,
                                   port2.get('network_id'))

    def test_unplug_network(self):
        list_ports = self.driver.neutron_client.list_ports
        port1 = t_constants.MOCK_NEUTRON_PORT['port']
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
            [{'ip_address': '10.0.0.2'}]
        }
        list_ports.return_value = {'ports': [port1, port2]}
        interface_detach = self.driver.nova_client.servers.interface_detach
        self.driver.unplug_network(t_constants.MOCK_COMPUTE_ID,
                                   port2.get('network_id'))
        interface_detach.assert_called_once_with(
            server=t_constants.MOCK_COMPUTE_ID, port_id=port2.get('id'))

    def test_update_vip(self):
        listeners = [data_models.Listener(protocol_port=80, peer_port=1024),
                     data_models.Listener(protocol_port=443, peer_port=1025)]
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'rule-80', 'port_range_max': 80, 'protocol': 'tcp'},
                {'id': 'rule-22', 'port_range_max': 22, 'protocol': 'tcp'}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        create_rule = self.driver.neutron_client.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')
        expected_create_rule_1 = {
            'security_group_rule': {
                'security_group_id': 'secgrp-1',
                'direction': 'ingress',
                'protocol': 'TCP',
                'port_range_min': 1024,
                'port_range_max': 1024,
                'ethertype': 'IPv4'
            }
        }
        expected_create_rule_2 = {
            'security_group_rule': {
                'security_group_id': 'secgrp-1',
                'direction': 'ingress',
                'protocol': 'TCP',
                'port_range_min': 1025,
                'port_range_max': 1025,
                'ethertype': 'IPv4'
            }
        }
        expected_create_rule_3 = {
            'security_group_rule': {
                'security_group_id': 'secgrp-1',
                'direction': 'ingress',
                'protocol': 'TCP',
                'port_range_min': 443,
                'port_range_max': 443,
                'ethertype': 'IPv4'
            }
        }
        create_rule.assert_has_calls([mock.call(expected_create_rule_1),
                                      mock.call(expected_create_rule_2),
                                      mock.call(expected_create_rule_3)])

    def test_update_vip_when_listener_deleted(self):
        listeners = [data_models.Listener(protocol_port=80),
                     data_models.Listener(
                         protocol_port=443,
                         provisioning_status=constants.PENDING_DELETE)]
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'rule-80', 'port_range_max': 80, 'protocol': 'tcp'},
                {'id': 'rule-22', 'port_range_max': 443, 'protocol': 'tcp'}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        create_rule = self.driver.neutron_client.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')
        self.assertTrue(create_rule.called)

    def test_update_vip_when_no_listeners(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'all-egress', 'protocol': None, 'direction': 'egress'},
                {'id': 'ssh-rule', 'protocol': 'tcp', 'port_range_max': 22}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('ssh-rule')

    def test_update_vip_when_security_group_rule_deleted(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': [{'id': 'secgrp-1'}]}
        fake_rules = {
            'security_group_rules': [
                {'id': 'all-egress', 'protocol': None, 'direction': 'egress'},
                {'id': 'ssh-rule', 'protocol': 'tcp', 'port_range_max': 22}
            ]
        }
        list_rules = self.driver.neutron_client.list_security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.neutron_client.delete_security_group_rule
        delete_rule.side_effect = neutron_exceptions.NotFound
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('ssh-rule')

    def test_update_vip_when_security_group_missing(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': []}
        self.assertRaises(exceptions.MissingVIPSecurityGroup,
                          self.driver.update_vip,
                          lb)

    @mock.patch('octavia.network.drivers.neutron.allowed_address_pairs.'
                'AllowedAddressPairsDriver._update_security_group_rules')
    def test_update_vip_for_delete_when_security_group_missing(self,
                                                               update_rules):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.neutron_client.list_security_groups
        list_sec_grps.return_value = {'security_groups': []}
        self.driver.update_vip(lb, for_delete=True)
        update_rules.assert_not_called()

    def test_failover_preparation(self):
        original_dns_integration_state = self.driver.dns_integration_enabled
        self.driver.dns_integration_enabled = False
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
        self.assertFalse(port_update.called)
        self.driver.dns_integration_enabled = original_dns_integration_state

    def test_failover_preparation_dns_integration(self):
        ports = {"ports": [
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                            "ip_address": self.IP_ADDRESS_1}],
             "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1},
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                            "ip_address": self.IP_ADDRESS_2}],
             "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}]}
        original_dns_integration_state = self.driver.dns_integration_enabled
        self.driver.dns_integration_enabled = True
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
        port_update.assert_called_once_with(ports['ports'][1].get('id'),
                                            {'port': {'dns_name': ''}})
        self.driver.dns_integration_enabled = original_dns_integration_state

    def _failover_show_port_side_effect(self, port_id):
        if port_id == self.LB_NET_PORT_ID:
            return {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                                   "ip_address": self.IP_ADDRESS_1}],
                    "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1}
        if port_id == self.HA_PORT_ID:
            return {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                                   "ip_address": self.IP_ADDRESS_2}],
                    "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}

    def test_plug_port(self):
        port = mock.MagicMock()
        port.id = self.PORT_ID
        interface_attach = self.driver.nova_client.servers.interface_attach
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)

        self.driver.plug_port(amphora, port)
        interface_attach.assert_called_once_with(server=amphora.compute_id,
                                                 net_id=None,
                                                 fixed_ip=None,
                                                 port_id=self.PORT_ID)

        # NotFound cases
        interface_attach.side_effect = nova_exceptions.NotFound(
            1, message='Instance')
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_port,
                          amphora,
                          port)
        interface_attach.side_effect = nova_exceptions.NotFound(
            1, message='Network')
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.plug_port,
                          amphora,
                          port)
        interface_attach.side_effect = nova_exceptions.NotFound(
            1, message='bogus')
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_port,
                          amphora,
                          port)

        # Already plugged case should not raise an exception
        interface_attach.side_effect = nova_exceptions.Conflict(1)
        self.driver.plug_port(amphora, port)

        # Unknown error case
        interface_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_port,
                          amphora,
                          port)

    def test_get_network_configs(self):
        amphora_mock = mock.MagicMock()
        load_balancer_mock = mock.MagicMock()
        vip_mock = mock.MagicMock()
        amphora_mock.status = constants.DELETED
        load_balancer_mock.amphorae = [amphora_mock]
        show_port = self.driver.neutron_client.show_port
        show_port.return_value = t_constants.MOCK_NEUTRON_PORT
        fake_subnet = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR}}
        show_subnet = self.driver.neutron_client.show_subnet
        show_subnet.return_value = fake_subnet
        configs = self.driver.get_network_configs(load_balancer_mock)
        self.assertEqual({}, configs)

        vip_mock.port_id = 1
        amphora_mock.id = 222
        amphora_mock.status = constants.ACTIVE
        amphora_mock.vrrp_port_id = 2
        amphora_mock.vrrp_ip = "10.0.0.1"
        amphora_mock.ha_port_id = 3
        amphora_mock.ha_ip = "10.0.0.2"
        load_balancer_mock.amphorae = [amphora_mock]

        configs = self.driver.get_network_configs(load_balancer_mock)
        self.assertEqual(1, len(configs))
        config = configs[222]
        # TODO(ptoohill): find a way to return different items for multiple
        # calls to the same method, right now each call to show subnet
        # will return the same values if a method happens to call it
        # multiple times for different subnets. We should be able to verify
        # different requests get different expected data.
        expected_port_id = t_constants.MOCK_NEUTRON_PORT['port']['id']
        self.assertEqual(expected_port_id, config.ha_port.id)
        self.assertEqual(expected_port_id, config.vrrp_port.id)
        expected_subnet_id = fake_subnet['subnet']['id']
        self.assertEqual(expected_subnet_id, config.ha_subnet.id)
        self.assertEqual(expected_subnet_id, config.vrrp_subnet.id)

    @mock.patch('time.sleep')
    def test_wait_for_port_detach(self, mock_sleep):
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)
        ports = {"ports": [
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                            "ip_address": self.IP_ADDRESS_1}],
             "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1},
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                            "ip_address": self.IP_ADDRESS_2}],
             "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}]}
        show_port_1_without_device_id = {"fixed_ips": [
            {"subnet_id": self.SUBNET_ID_1, "ip_address": self.IP_ADDRESS_1}],
            "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1,
            "device_id": ''}
        show_port_2_with_device_id = {"fixed_ips": [
            {"subnet_id": self.SUBNET_ID_2, "ip_address": self.IP_ADDRESS_2}],
            "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2,
            "device_id": self.DEVICE_ID}
        show_port_2_without_device_id = {"fixed_ips": [
            {"subnet_id": self.SUBNET_ID_2, "ip_address": self.IP_ADDRESS_2}],
            "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2,
            "device_id": None}
        self.driver.neutron_client.list_ports.return_value = ports
        port_mock = mock.MagicMock()
        port_mock.get = mock.Mock(
            side_effect=[show_port_1_without_device_id,
                         show_port_2_with_device_id,
                         show_port_2_with_device_id,
                         show_port_2_without_device_id])
        self.driver.neutron_client.show_port.return_value = port_mock
        self.driver.wait_for_port_detach(amphora)
        self.assertEqual(1, mock_sleep.call_count)

    @mock.patch('time.time')
    @mock.patch('time.sleep')
    def test_wait_for_port_detach_timeout(self, mock_sleep, mock_time):
        mock_time.side_effect = [1, 2, 6]
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="networking", port_detach_timeout=5)
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)
        ports = {"ports": [
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                            "ip_address": self.IP_ADDRESS_1}],
             "id": self.FIXED_IP_ID_1, "network_id": self.NETWORK_ID_1},
            {"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                            "ip_address": self.IP_ADDRESS_2}],
             "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2}]}
        show_port_1_with_device_id = {"fixed_ips": [
            {"subnet_id": self.SUBNET_ID_2, "ip_address": self.IP_ADDRESS_2}],
            "id": self.FIXED_IP_ID_2, "network_id": self.NETWORK_ID_2,
            "device_id": self.DEVICE_ID}
        self.driver.neutron_client.list_ports.return_value = ports
        port_mock = mock.MagicMock()
        port_mock.get = mock.Mock(
            return_value=show_port_1_with_device_id)
        self.driver.neutron_client.show_port.return_value = port_mock
        self.assertRaises(network_base.TimeoutException,
                          self.driver.wait_for_port_detach,
                          amphora)
