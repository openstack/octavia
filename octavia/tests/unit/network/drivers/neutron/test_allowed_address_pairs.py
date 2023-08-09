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

from novaclient.client import exceptions as nova_exceptions
import openstack.exceptions as os_exceptions
from openstack.network.v2.port import Port
from openstack.network.v2.security_group import SecurityGroup
from openstack.network.v2.subnet import Subnet
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

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
    IPV6_ADDRESS_1 = "2001:db8::1234"
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
        super().setUp()
        with mock.patch('octavia.common.clients.openstack.connection'
                        '.Connection', autospec=True) as os_connection:
            with mock.patch('stevedore.driver.DriverManager.driver',
                            autospec=True):
                network_proxy = os_connection().network
                network_proxy.find_extension = (
                    lambda x: 'alias' if x in (
                        allowed_address_pairs.AAP_EXT_ALIAS,
                        neutron_base.SEC_GRP_EXT_ALIAS)
                    else None)
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
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        delete_port = self.driver.network_proxy.delete_port
        delete_sec_grp = self.driver.network_proxy.delete_security_group
        list_security_groups = self.driver.network_proxy.find_security_group
        list_security_groups.return_value = SecurityGroup(id=sec_grp_id)
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
        show_port = self.driver.network_proxy.get_port
        port = Port(device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        show_port.side_effect = [port, Exception]
        list_security_groups = self.driver.network_proxy.find_security_group
        list_security_groups.return_value = SecurityGroup(id=sec_grp_id)
        self.driver.deallocate_vip(vip)
        self.driver.network_proxy.update_port.assert_not_called()

    def test_deallocate_vip_port_deleted(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        delete_port = self.driver.network_proxy.delete_port
        delete_port.side_effect = os_exceptions.ResourceNotFound
        delete_sec_grp = self.driver.network_proxy.delete_security_group
        find_security_group = self.driver.network_proxy.find_security_group
        find_security_group.return_value = SecurityGroup(id=sec_grp_id)
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
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        delete_port = self.driver.network_proxy.delete_port
        delete_sec_grp = self.driver.network_proxy.delete_security_group
        list_security_groups = self.driver.network_proxy.find_security_group
        list_security_groups.return_value = None
        self.driver.deallocate_vip(vip)
        delete_port.assert_called_with(vip.port_id)
        delete_sec_grp.assert_not_called()

    def test_deallocate_vip_when_delete_port_fails(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        delete_port = self.driver.network_proxy.delete_port
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
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        delete_port = self.driver.network_proxy.delete_port
        list_ports = self.driver.network_proxy.ports
        find_security_group = self.driver.network_proxy.find_security_group
        delete_sec_grp = self.driver.network_proxy.delete_security_group
        security_group = SecurityGroup(id=t_constants.MOCK_SECURITY_GROUP_ID)
        find_security_group.return_value = security_group
        delete_grp_results = [
            network_base.DeallocateVIPException
            for _ in range(max_retries + 1)]  # Total tries = max_retries + 1
        delete_grp_results.append(None)
        delete_sec_grp.side_effect = delete_grp_results
        list_ports.return_value = iter([t_constants.MOCK_NEUTRON_PORT,
                                        t_constants.MOCK_NEUTRON_PORT2])
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
        show_port = self.driver.network_proxy.get_port
        show_port.side_effect = os_exceptions.ResourceNotFound
        self.driver.deallocate_vip(vip)

    def test_deallocate_vip_when_port_not_found_for_update(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(
            device_owner=allowed_address_pairs.OCTAVIA_OWNER)
        update_port = self.driver.network_proxy.update_port
        update_port.side_effect = os_exceptions.ResourceNotFound
        self.driver.deallocate_vip(vip)

    def test_deallocate_vip_when_port_not_owned_by_octavia(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.load_balancer = lb
        vip = lb.vip
        sec_grp_id = 'lb-sec-grp1'
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = Port(**{
            'id': vip.port_id,
            'device_owner': 'neutron:LOADBALANCERV2',
            'security_groups': [sec_grp_id]})
        update_port = self.driver.network_proxy.update_port
        delete_sec_grp = self.driver.network_proxy.delete_security_group
        list_security_groups = self.driver.network_proxy.find_security_group
        list_security_groups.return_value = SecurityGroup(id=sec_grp_id)
        self.driver.deallocate_vip(vip)
        expected_port_update = {'security_group_ids': []}
        update_port.assert_called_once_with(vip.port_id,
                                            **expected_port_update)
        delete_sec_grp.assert_called_once_with(sec_grp_id)

    def test_deallocate_vip_when_vip_port_not_found(self):
        lb = dmh.generate_load_balancer_tree()
        vip = data_models.Vip(port_id='1')
        vip.load_balancer = lb
        admin_project_id = 'octavia'
        session_mock = mock.MagicMock()
        session_mock.get_project_id.return_value = admin_project_id
        self.k_session.return_value = session_mock
        show_port = self.driver.network_proxy.get_port
        show_port.side_effect = os_exceptions.ResourceNotFound
        self.driver.deallocate_vip(vip)

    def test_plug_aap_errors_when_nova_cant_find_network_to_attach(self):
        lb = dmh.generate_load_balancer_tree()
        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)

        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = nova_exceptions.NotFound(404, "Network")
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_aap_port, lb, lb.vip,
                          lb.amphorae[0], subnet)

    def test_plug_aap_errors_when_neutron_cant_find_port_to_update(self):
        lb = dmh.generate_load_balancer_tree()
        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.return_value = t_constants.MOCK_NOVA_INTERFACE

        update_port = self.driver.network_proxy.update_port
        update_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.plug_aap_port, lb, lb.vip,
                          lb.amphorae[0], subnet)

    @mock.patch('octavia.network.drivers.neutron.allowed_address_pairs.'
                'AllowedAddressPairsDriver.update_vip_sg')
    @mock.patch('octavia.network.drivers.neutron.allowed_address_pairs.'
                'AllowedAddressPairsDriver.get_subnet')
    @mock.patch('octavia.network.drivers.neutron.allowed_address_pairs.'
                'AllowedAddressPairsDriver.plug_aap_port')
    def test_plug_vip(self, mock_plug_aap, mock_get_subnet,
                      mock_update_vip_sg):
        lb = dmh.generate_load_balancer_tree()
        subnet = mock.MagicMock()
        mock_get_subnet.return_value = subnet
        mock_plug_aap.side_effect = lb.amphorae
        amps = self.driver.plug_vip(lb, lb.vip)

        mock_update_vip_sg.assert_called_with(lb, lb.vip)
        mock_get_subnet.assert_called_with(lb.vip.subnet_id)
        for amp in amps:
            mock_plug_aap.assert_any_call(lb, lb.vip, amp, subnet)

    @mock.patch('octavia.common.utils.get_vip_security_group_name')
    def test_update_vip_sg(self, mock_get_sg_name):
        LB_ID = uuidutils.generate_uuid()
        SG_ID = uuidutils.generate_uuid()
        VIP_PORT_ID = uuidutils.generate_uuid()
        TEST_SG_NAME = 'test_SG_name'
        lb_mock = mock.MagicMock()
        lb_mock.id = LB_ID
        vip_mock = mock.MagicMock()
        vip_mock.port_id = VIP_PORT_ID
        security_group_dict = {'id': SG_ID}
        mock_get_sg_name.return_value = TEST_SG_NAME

        test_driver = allowed_address_pairs.AllowedAddressPairsDriver()

        test_driver._add_vip_security_group_to_port = mock.MagicMock()
        test_driver._create_security_group = mock.MagicMock()
        test_driver._get_lb_security_group = mock.MagicMock()
        test_driver._update_security_group_rules = mock.MagicMock()
        test_driver._get_lb_security_group.side_effect = [security_group_dict,
                                                          None]
        test_driver._create_security_group.return_value = security_group_dict

        # Test security groups disabled
        test_driver.sec_grp_enabled = False

        result = test_driver.update_vip_sg(lb_mock, vip_mock)

        self.assertIsNone(result)
        test_driver._add_vip_security_group_to_port.assert_not_called()
        test_driver._get_lb_security_group.assert_not_called()
        test_driver._update_security_group_rules.assert_not_called()

        # Test by security group ID
        test_driver.sec_grp_enabled = True

        result = test_driver.update_vip_sg(lb_mock, vip_mock)

        self.assertEqual(SG_ID, result)
        test_driver._update_security_group_rules.assert_called_once_with(
            lb_mock, SG_ID)
        test_driver._add_vip_security_group_to_port.assert_called_once_with(
            LB_ID, VIP_PORT_ID, SG_ID)

        # Test by security group name
        test_driver._add_vip_security_group_to_port.reset_mock()
        test_driver._get_lb_security_group.reset_mock()
        test_driver._update_security_group_rules.reset_mock()

        result = test_driver.update_vip_sg(lb_mock, vip_mock)

        self.assertEqual(SG_ID, result)
        mock_get_sg_name.assert_called_once_with(LB_ID)
        test_driver._create_security_group.assert_called_once_with(
            TEST_SG_NAME)
        test_driver._update_security_group_rules.assert_called_once_with(
            lb_mock, SG_ID)
        test_driver._add_vip_security_group_to_port.assert_called_once_with(
            LB_ID, VIP_PORT_ID, SG_ID)

    def test_plug_aap_port(self):
        lb = dmh.generate_load_balancer_tree()

        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)

        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1
        port2 = t_constants.MOCK_MANAGEMENT_PORT2
        list_ports.return_value = iter([port1, port2])
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = [t_constants.MOCK_VRRP_INTERFACE1]
        update_port = self.driver.network_proxy.update_port
        expected_aap = {
            'allowed_address_pairs': [{'ip_address': lb.vip.ip_address}]}
        amp = self.driver.plug_aap_port(lb, lb.vip, lb.amphorae[0], subnet)
        update_port.assert_any_call(amp.vrrp_port_id, **expected_aap)
        self.assertIn(amp.vrrp_ip, [t_constants.MOCK_VRRP_IP1,
                                    t_constants.MOCK_VRRP_IP2])
        self.assertEqual(lb.vip.ip_address, amp.ha_ip)

    @mock.patch('octavia.network.drivers.neutron.utils.'
                'convert_port_to_model')
    def test_plug_aap_port_create_fails(self, mock_convert):
        lb = dmh.generate_load_balancer_tree()

        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)

        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1
        port2 = t_constants.MOCK_MANAGEMENT_PORT2
        list_ports.return_value = iter([port1, port2])
        port_create = self.driver.network_proxy.create_port
        port_create.side_effect = [Exception('Create failure')]
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_aap_port,
                          lb, lb.vip, lb.amphorae[0], subnet)
        mock_convert.assert_not_called()
        self.driver.network_proxy.delete_port.assert_not_called()

    def test_plug_aap_port_attach_fails(self):
        lb = dmh.generate_load_balancer_tree()

        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)

        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1
        port2 = t_constants.MOCK_MANAGEMENT_PORT2
        list_ports.return_value = iter([port1, port2])
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = [Exception('Attach failure')]
        self.assertRaises(network_base.PlugVIPException,
                          self.driver.plug_aap_port,
                          lb, lb.vip, lb.amphorae[0], subnet)
        self.driver.network_proxy.delete_port.assert_called_once()

    def test_plug_aap_port_with_add_vips(self):
        additional_vips = [
            {'ip_address': t_constants.MOCK_IP_ADDRESS2,
             'subnet_id': t_constants.MOCK_VIP_SUBNET_ID2}
        ]
        lb = dmh.generate_load_balancer_tree(additional_vips=additional_vips)

        subnet = network_models.Subnet(id=t_constants.MOCK_VIP_SUBNET_ID,
                                       network_id=t_constants.MOCK_VIP_NET_ID)

        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1
        port2 = t_constants.MOCK_MANAGEMENT_PORT2
        list_ports.return_value = iter([port1, port2])
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = [t_constants.MOCK_VRRP_INTERFACE1]
        update_port = self.driver.network_proxy.update_port
        amp = self.driver.plug_aap_port(lb, lb.vip, lb.amphorae[0], subnet)
        expected_aap = {
            'allowed_address_pairs':
                [{'ip_address': lb.vip.ip_address},
                 {'ip_address': lb.additional_vips[0].ip_address}]}

        update_port.assert_any_call(amp.vrrp_port_id, **expected_aap)
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

    def test_plug_aap_on_mgmt_net(self):
        lb = dmh.generate_load_balancer_tree()
        lb.vip.subnet_id = t_constants.MOCK_MANAGEMENT_SUBNET_ID
        subnet = network_models.Subnet(
            id=t_constants.MOCK_MANAGEMENT_SUBNET_ID,
            network_id=t_constants.MOCK_MANAGEMENT_NET_ID)
        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_MANAGEMENT_PORT1
        port2 = t_constants.MOCK_MANAGEMENT_PORT2
        self._set_safely(t_constants.MOCK_MANAGEMENT_FIXED_IPS1[0],
                         'ip_address', lb.amphorae[0].lb_network_ip)
        self._set_safely(t_constants.MOCK_MANAGEMENT_FIXED_IPS2[0],
                         'ip_address', lb.amphorae[1].lb_network_ip)
        list_ports.side_effect = [iter([port1]), iter([port2])]
        network_attach = self.driver.compute.attach_network_or_port
        self._set_safely(t_constants.MOCK_VRRP_INTERFACE1,
                         'net_id', t_constants.MOCK_MANAGEMENT_NET_ID)
        self._set_safely(t_constants.MOCK_VRRP_FIXED_IPS1[0],
                         'subnet_id', t_constants.MOCK_MANAGEMENT_SUBNET_ID)
        self._set_safely(t_constants.MOCK_VRRP_INTERFACE2,
                         'net_id', t_constants.MOCK_MANAGEMENT_NET_ID)
        self._set_safely(t_constants.MOCK_VRRP_FIXED_IPS2[0],
                         'subnet_id', t_constants.MOCK_MANAGEMENT_SUBNET_ID)
        network_attach.side_effect = [t_constants.MOCK_VRRP_INTERFACE1]
        update_port = self.driver.network_proxy.update_port
        expected_aap = {
            'allowed_address_pairs': [{'ip_address': lb.vip.ip_address}]}
        amp = self.driver.plug_aap_port(lb, lb.vip, lb.amphorae[0], subnet)
        update_port.assert_any_call(amp.vrrp_port_id, **expected_aap)
        self.assertIn(amp.vrrp_ip, [t_constants.MOCK_VRRP_IP1,
                                    t_constants.MOCK_VRRP_IP2])
        self.assertEqual(lb.vip.ip_address, amp.ha_ip)

    def test_validate_fixed_ip(self):
        IP_ADDRESS = '203.0.113.61'
        OTHER_IP_ADDRESS = '203.0.113.62'
        SUBNET_ID = uuidutils.generate_uuid()
        OTHER_SUBNET_ID = uuidutils.generate_uuid()
        fixed_ip_mock = mock.MagicMock()
        fixed_ip_mock.subnet_id = SUBNET_ID
        fixed_ip_mock.ip_address = IP_ADDRESS

        # valid
        result = self.driver._validate_fixed_ip([fixed_ip_mock], SUBNET_ID,
                                                IP_ADDRESS)
        self.assertTrue(result)

        # no subnet match
        result = self.driver._validate_fixed_ip(
            [fixed_ip_mock], OTHER_SUBNET_ID, IP_ADDRESS)
        self.assertFalse(result)

        # no IP match
        result = self.driver._validate_fixed_ip([fixed_ip_mock], SUBNET_ID,
                                                OTHER_IP_ADDRESS)
        self.assertFalse(result)

    def test_allocate_vip_when_port_already_provided(self):
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = t_constants.MOCK_NEUTRON_PORT
        fake_lb_vip = data_models.Vip(
            port_id=t_constants.MOCK_PORT_ID,
            subnet_id=t_constants.MOCK_SUBNET_ID,
            network_id=t_constants.MOCK_NETWORK_ID,
            ip_address=t_constants.MOCK_IP_ADDRESS)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_with_port_mismatch(self, mock_check_ext):
        bad_existing_port = mock.MagicMock()
        bad_existing_port.port_id = uuidutils.generate_uuid()
        bad_existing_port.network_id = uuidutils.generate_uuid()
        bad_existing_port.subnet_id = uuidutils.generate_uuid()
        show_port = self.driver.network_proxy.get_port
        show_port.return_value = bad_existing_port
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }}
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      port_id=t_constants.MOCK_PORT_ID,
                                      octavia_owned=True)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'project_id': 'test-project',
            'fixed_ips': [{'subnet_id': t_constants.MOCK_SUBNET_ID}]
        }
        self.driver.network_proxy.delete_port.assert_called_once_with(
            t_constants.MOCK_PORT_ID)
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                'get_port', side_effect=network_base.PortNotFound)
    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_when_port_not_found(self, mock_check_ext,
                                              mock_get_port):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {'subnet': {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }}
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      port_id=t_constants.MOCK_PORT_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'project_id': 'test-project',
            'fixed_ips': [{'subnet_id': t_constants.MOCK_SUBNET_ID}]
        }
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                'get_port', side_effect=Exception('boom'))
    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_unkown_exception(self, mock_check_ext,
                                           mock_get_port):
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      port_id=t_constants.MOCK_PORT_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        self.assertRaises(network_base.AllocateVIPException,
                          self.driver.allocate_vip, fake_lb)

    def test_allocate_vip_when_port_creation_fails(self):
        fake_lb_vip = data_models.Vip(
            subnet_id=t_constants.MOCK_SUBNET_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip)
        create_port = self.driver.network_proxy.create_port
        create_port.side_effect = Exception
        self.assertRaises(network_base.AllocateVIPException,
                          self.driver.allocate_vip, fake_lb)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_when_no_port_provided(self, mock_check_ext):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      ip_address=t_constants.MOCK_IP_ADDRESS)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'project_id': 'test-project',
            'fixed_ips': [{'ip_address': t_constants.MOCK_IP_ADDRESS,
                           'subnet_id': t_constants.MOCK_SUBNET_ID}]
        }
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_when_no_port_fixed_ip(self, mock_check_ext):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        })
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      ip_address=t_constants.MOCK_IP_ADDRESS)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'project_id': 'test-project',
            'fixed_ips': [{'subnet_id': t_constants.MOCK_SUBNET_ID,
                           'ip_address': t_constants.MOCK_IP_ADDRESS}]
        }
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=True)
    def test_allocate_vip_when_no_port_no_fixed_ip(self, mock_check_ext):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }
        fake_lb_vip = data_models.Vip(network_id=t_constants.MOCK_NETWORK_ID)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'project_id': 'test-project'}
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertTrue(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=False)
    def test_allocate_vip_when_no_port_provided_tenant(self, mock_check_ext):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      ip_address=t_constants.MOCK_IP_ADDRESS)
        fake_lb = data_models.LoadBalancer(id='1', vip=fake_lb_vip,
                                           project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'tenant_id': 'test-project',
            'fixed_ips': [{'ip_address': t_constants.MOCK_IP_ADDRESS,
                           'subnet_id': t_constants.MOCK_SUBNET_ID}]
        }
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch('octavia.network.drivers.neutron.base.BaseNeutronDriver.'
                '_check_extension_enabled', return_value=False)
    def test_allocate_vip_with_additional_vips(self, mock_check_ext):
        port_create_dict = Port(**t_constants.MOCK_NEUTRON_PORT.to_dict())
        port_create_dict['device_owner'] = (
            allowed_address_pairs.OCTAVIA_OWNER)
        port_create_dict['device_id'] = 'lb-1'
        create_port = self.driver.network_proxy.create_port
        create_port.return_value = port_create_dict
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = {
            'id': t_constants.MOCK_SUBNET_ID,
            'network_id': t_constants.MOCK_NETWORK_ID
        }
        fake_lb_vip = data_models.Vip(subnet_id=t_constants.MOCK_SUBNET_ID,
                                      network_id=t_constants.MOCK_NETWORK_ID,
                                      ip_address=t_constants.MOCK_IP_ADDRESS)
        fake_additional_vips = [
            data_models.AdditionalVip(ip_address=t_constants.MOCK_IP_ADDRESS2),
            data_models.AdditionalVip(subnet_id=t_constants.MOCK_SUBNET_ID3)]
        fake_lb = data_models.LoadBalancer(
            id='1', vip=fake_lb_vip,
            additional_vips=fake_additional_vips,
            project_id='test-project')
        vip, additional_vips = self.driver.allocate_vip(fake_lb)
        exp_create_port_call = {
            'name': 'octavia-lb-1',
            'network_id': t_constants.MOCK_NETWORK_ID,
            'device_id': 'lb-1',
            'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
            'admin_state_up': False,
            'tenant_id': 'test-project',
            'fixed_ips': [
                {'ip_address': t_constants.MOCK_IP_ADDRESS,
                 'subnet_id': t_constants.MOCK_SUBNET_ID},
                {'ip_address': t_constants.MOCK_IP_ADDRESS2},
                {'subnet_id': t_constants.MOCK_SUBNET_ID3}]
        }
        create_port.assert_called_once_with(**exp_create_port_call)
        self.assertIsInstance(vip, data_models.Vip)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS, vip.ip_address)
        self.assertEqual(t_constants.MOCK_SUBNET_ID, vip.subnet_id)
        self.assertEqual(t_constants.MOCK_PORT_ID, vip.port_id)
        self.assertEqual(fake_lb.id, vip.load_balancer_id)
        self.assertFalse(additional_vips)

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    def test_unplug_aap_port_errors_when_update_port_cant_find_port(
            self, mock_time_sleep, mock_time_time):
        lb = dmh.generate_load_balancer_tree()
        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        }
        subnet = network_models.Subnet(
            id=t_constants.MOCK_MANAGEMENT_SUBNET_ID,
            network_id='3')
        list_ports.side_effect = [
            iter([port1, port2]),
            iter([port1, port2]),
            iter([port1]),
        ]
        update_port = self.driver.network_proxy.update_port
        update_port.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_aap_port, lb.vip, lb.amphorae[0],
                          subnet)

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    def test_unplug_aap_errors_when_update_port_fails(
            self, mock_time_sleep, mock_time_time):
        lb = dmh.generate_load_balancer_tree()
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        }

        subnet = network_models.Subnet(
            id=t_constants.MOCK_MANAGEMENT_SUBNET_ID,
            network_id='3')

        list_ports = self.driver.network_proxy.ports
        list_ports.side_effect = [
            iter([port1, port2]),
            iter([port1, port2]),
            iter([port1]),
        ]
        mock_time_time.side_effect = [1, 1, 2]

        update_port = self.driver.network_proxy.update_port
        update_port.side_effect = TypeError
        self.assertRaises(network_base.UnplugVIPException,
                          self.driver.unplug_aap_port, lb.vip,
                          lb.amphorae[0], subnet)

    def test_unplug_vip_errors_when_vip_subnet_not_found(self):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.side_effect = os_exceptions.ResourceNotFound
        self.assertRaises(network_base.PluggedVIPNotFound,
                          self.driver.unplug_vip, lb, lb.vip)

    @mock.patch('octavia.network.drivers.neutron.allowed_address_pairs.'
                'AllowedAddressPairsDriver.unplug_aap_port')
    def test_unplug_vip(self, mock):
        lb = dmh.generate_load_balancer_tree()
        show_subnet = self.driver.network_proxy.get_subnet
        show_subnet.return_value = t_constants.MOCK_SUBNET
        self.driver.unplug_vip(lb, lb.vip)
        self.assertEqual(len(lb.amphorae), mock.call_count)

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    @mock.patch("octavia.network.drivers.neutron.allowed_address_pairs."
                "AllowedAddressPairsDriver.unplug_network")
    def test_unplug_aap_port(self, mock_unplug_network,
                             mock_time_sleep, mock_time_time):
        lb = dmh.generate_load_balancer_tree()
        update_port = self.driver.network_proxy.update_port
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        }
        subnet = network_models.Subnet(
            id=t_constants.MOCK_MANAGEMENT_SUBNET_ID,
            network_id='3')
        list_ports = self.driver.network_proxy.ports
        list_ports.side_effect = [
            iter([port1, port2]),
            iter([port1, port2]),
            iter([port1]),
        ]
        mock_time_time.side_effect = [1, 1, 2]
        get_port = self.driver.network_proxy.get_port
        get_port.side_effect = os_exceptions.ResourceNotFound
        self.driver.unplug_aap_port(lb.vip, lb.amphorae[0], subnet)
        clear_aap = {'allowed_address_pairs': []}
        update_port.assert_called_once_with(port2.get('id'), **clear_aap)
        mock_unplug_network.assert_called_once_with(
            lb.amphorae[0].compute_id, subnet.network_id)

    def test_plug_network_when_compute_instance_cant_be_found(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = exceptions.NotFound(
            resource='Instance not found', id=1)
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_network_cant_be_found(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = nova_exceptions.NotFound(
            404, message='Network not found')
        self.assertRaises(network_base.NetworkException,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network_when_interface_attach_fails(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_plug_network(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.return_value = t_constants.MOCK_NOVA_INTERFACE
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
        list_ports = self.driver.network_proxy.ports
        list_ports.return_value = iter([])
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.unplug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    def test_unplug_network_when_list_ports_fails(self):
        net_id = t_constants.MOCK_NOVA_INTERFACE.net_id
        list_ports = self.driver.network_proxy.ports
        list_ports.side_effect = Exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.unplug_network,
                          t_constants.MOCK_COMPUTE_ID, net_id)

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    def test_unplug_network(self, mock_time_sleep, mock_time_time):
        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = {
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        }
        list_ports.side_effect = [
            iter([port1, port2]),
            iter([port1, port2]),
            iter([port1]),
        ]
        port_detach = self.driver.compute.detach_port

        mock_time_time.side_effect = [1, 1, 2]

        self.driver.unplug_network(t_constants.MOCK_COMPUTE_ID,
                                   port2.get('network_id'))
        port_detach.assert_called_once_with(
            compute_id=t_constants.MOCK_COMPUTE_ID, port_id=port2.get('id'))

        mock_time_sleep.assert_called_once()

    @mock.patch("time.time")
    @mock.patch("time.sleep")
    @mock.patch("octavia.network.drivers.neutron.allowed_address_pairs.LOG")
    def test_unplug_network_timeout(self, mock_log,
                                    mock_time_sleep, mock_time_time):
        list_ports = self.driver.network_proxy.ports
        port1 = t_constants.MOCK_NEUTRON_PORT
        port2 = Port(**{
            'id': '4', 'network_id': '3', 'fixed_ips':
                [{'ip_address': '10.0.0.2'}]
        })

        list_ports.side_effect = [iter([port1, port2]) for _ in range(7)]
        port_detach = self.driver.compute.detach_port

        mock_time_time.side_effect = [0, 0, 1, 2, 10, 20, 100, 300]

        self.driver.unplug_network(t_constants.MOCK_COMPUTE_ID,
                                   port2.get('network_id'))
        port_detach.assert_called_once_with(
            compute_id=t_constants.MOCK_COMPUTE_ID, port_id=port2.get('id'))

        self.assertEqual(6, len(mock_time_sleep.mock_calls))
        mock_log.warning.assert_called_once()

    def test_update_vip(self):
        lc_1 = data_models.ListenerCidr('l1', '10.0.101.0/24')
        lc_2 = data_models.ListenerCidr('l2', '10.0.102.0/24')
        lc_3 = data_models.ListenerCidr('l2', '10.0.103.0/24')
        lc_4 = data_models.ListenerCidr('l2', '2001:0DB8::/32')
        listeners = [data_models.Listener(protocol_port=80, peer_port=1024,
                                          protocol=constants.PROTOCOL_TCP,
                                          allowed_cidrs=[lc_1]),
                     data_models.Listener(protocol_port=443, peer_port=1025,
                                          protocol=constants.PROTOCOL_TCP,
                                          allowed_cidrs=[lc_2, lc_3, lc_4]),
                     data_models.Listener(protocol_port=50, peer_port=1026,
                                          protocol=constants.PROTOCOL_UDP)]
        vip = data_models.Vip(ip_address='10.0.0.2')

        additional_vip = data_models.AdditionalVip(
            ip_address=self.IPV6_ADDRESS_1)
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip,
                                      additional_vips=[additional_vip])
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = {'id': 'secgrp-1'}
        fake_rules = [
            {'id': 'rule-80', 'port_range_max': 80, 'protocol': 'tcp',
             'remote_ip_prefix': '10.0.101.0/24'},
            {'id': 'rule-22', 'port_range_max': 22, 'protocol': 'tcp'}
        ]
        list_rules = self.driver.network_proxy.security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.network_proxy.delete_security_group_rule
        create_rule = self.driver.network_proxy.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')
        expected_create_rule_1 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 1024,
            'port_range_max': 1024,
            'ethertype': 'IPv4',
            'remote_ip_prefix': None
        }
        expected_create_rule_udp_peer = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 1026,
            'port_range_max': 1026,
            'ethertype': 'IPv4',
            'remote_ip_prefix': None
        }
        expected_create_rule_2 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 1025,
            'port_range_max': 1025,
            'ethertype': 'IPv4',
            'remote_ip_prefix': None
        }
        expected_create_rule_3 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 443,
            'port_range_max': 443,
            'ethertype': 'IPv4',
            'remote_ip_prefix': '10.0.102.0/24'
        }
        expected_create_rule_4 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 443,
            'port_range_max': 443,
            'ethertype': 'IPv4',
            'remote_ip_prefix': '10.0.103.0/24'
        }
        expected_create_rule_5 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': 443,
            'port_range_max': 443,
            'ethertype': 'IPv6',
            'remote_ip_prefix': '2001:0DB8::/32'
        }
        expected_create_rule_udp_1 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'udp',
            'port_range_min': 50,
            'port_range_max': 50,
            'ethertype': 'IPv4',
            'remote_ip_prefix': None
        }
        expected_create_rule_udp_2 = {
            'security_group_id': 'secgrp-1',
            'direction': 'ingress',
            'protocol': 'udp',
            'port_range_min': 50,
            'port_range_max': 50,
            'ethertype': 'IPv6',
            'remote_ip_prefix': None
        }

        create_rule.assert_has_calls([mock.call(**expected_create_rule_1),
                                      mock.call(
                                          **expected_create_rule_udp_peer),
                                      mock.call(**expected_create_rule_2),
                                      mock.call(**expected_create_rule_3),
                                      mock.call(**expected_create_rule_4),
                                      mock.call(**expected_create_rule_5),
                                      mock.call(**expected_create_rule_udp_1),
                                      mock.call(**expected_create_rule_udp_2)],
                                     any_order=True)

    def test_update_vip_when_protocol_and_peer_ports_overlap(self):
        lc_1 = data_models.ListenerCidr('l1', '0.0.0.0/0')
        listeners = [data_models.Listener(protocol_port=80, peer_port=1024,
                                          protocol=constants.PROTOCOL_TCP),
                     data_models.Listener(protocol_port=443, peer_port=1025,
                                          protocol=constants.PROTOCOL_TCP),
                     data_models.Listener(protocol_port=1025, peer_port=1026,
                                          protocol=constants.PROTOCOL_TCP,
                                          allowed_cidrs=[lc_1])]
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = {'id': 'secgrp-1'}
        fake_rules = [
            {'id': 'rule-80', 'port_range_max': 80, 'protocol': 'tcp'},
            {'id': 'rule-22', 'port_range_max': 22, 'protocol': 'tcp'}
        ]
        list_rules = self.driver.network_proxy.security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.network_proxy.delete_security_group_rule
        create_rule = self.driver.network_proxy.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('rule-22')

        # Create SG rule calls should be 4, each for port 1024/1025/1026/443
        # No duplicate SG creation for overlap port 1025
        self.assertEqual(4, create_rule.call_count)

    def test_update_vip_when_listener_deleted(self):
        listeners = [data_models.Listener(protocol_port=80,
                                          protocol=constants.PROTOCOL_TCP),
                     data_models.Listener(
                         protocol_port=443,
                         protocol=constants.PROTOCOL_TCP,
                         provisioning_status=constants.PENDING_DELETE),
                     data_models.Listener(
                         protocol_port=50, protocol=constants.PROTOCOL_UDP,
                         provisioning_status=constants.PENDING_DELETE)]
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = {'id': 'secgrp-1'}
        fake_rules = [
            {'id': 'rule-80', 'port_range_max': 80, 'protocol': 'tcp'},
            {'id': 'rule-22', 'port_range_max': 443, 'protocol': 'tcp'},
            {'id': 'rule-udp-50', 'port_range_max': 50, 'protocol': 'tcp'}
        ]
        list_rules = self.driver.network_proxy.security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.network_proxy.delete_security_group_rule
        create_rule = self.driver.network_proxy.create_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_has_calls(
            [mock.call('rule-22'), mock.call('rule-udp-50')])
        self.assertTrue(create_rule.called)

    def test_update_vip_when_no_listeners(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = {'id': 'secgrp-1'}
        fake_rules = [
            {'id': 'all-egress', 'protocol': None, 'direction': 'egress'},
            {'id': 'ssh-rule', 'protocol': 'tcp', 'port_range_max': 22}
        ]
        list_rules = self.driver.network_proxy.security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.network_proxy.delete_security_group_rule
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('ssh-rule')

    def test_update_vip_when_security_group_rule_deleted(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = {'id': 'secgrp-1'}
        fake_rules = [
            {'id': 'all-egress', 'protocol': None, 'direction': 'egress'},
            {'id': 'ssh-rule', 'protocol': 'tcp', 'port_range_max': 22}
        ]
        list_rules = self.driver.network_proxy.security_group_rules
        list_rules.return_value = fake_rules
        delete_rule = self.driver.network_proxy.delete_security_group_rule
        delete_rule.side_effect = os_exceptions.ResourceNotFound
        self.driver.update_vip(lb)
        delete_rule.assert_called_once_with('ssh-rule')

    def test_update_vip_when_security_group_missing(self):
        listeners = []
        vip = data_models.Vip(ip_address='10.0.0.2')
        lb = data_models.LoadBalancer(id='1', listeners=listeners, vip=vip)
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = None
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
        list_sec_grps = self.driver.network_proxy.find_security_group
        list_sec_grps.return_value = None
        self.driver.update_vip(lb, for_delete=True)
        update_rules.assert_not_called()

    def test_failover_preparation(self):
        original_dns_integration_state = self.driver.dns_integration_enabled
        self.driver.dns_integration_enabled = False
        ports = [
            Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                                   "ip_address": self.IP_ADDRESS_1}],
                    "id": self.FIXED_IP_ID_1,
                    "network_id": self.NETWORK_ID_1}),
            Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                                   "ip_address": self.IP_ADDRESS_2}],
                    "id": self.FIXED_IP_ID_2,
                    "network_id": self.NETWORK_ID_2})]
        self.driver.network_proxy.ports.return_value = ports
        self.driver.network_proxy.get_port = mock.Mock(
            side_effect=self._failover_show_port_side_effect)
        port_update = self.driver.network_proxy.update_port
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)
        self.driver.failover_preparation(amphora)
        self.assertFalse(port_update.called)
        self.driver.dns_integration_enabled = original_dns_integration_state

    def test_failover_preparation_dns_integration(self):
        ports = [
            Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                                   "ip_address": self.IP_ADDRESS_1}],
                    "id": self.FIXED_IP_ID_1,
                    "network_id": self.NETWORK_ID_1}),
            Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                                   "ip_address": self.IP_ADDRESS_2}],
                    "id": self.FIXED_IP_ID_2,
                    "network_id": self.NETWORK_ID_2})]
        original_dns_integration_state = self.driver.dns_integration_enabled
        self.driver.dns_integration_enabled = True
        self.driver.network_proxy.ports.return_value = ports
        self.driver.network_proxy.get_port = mock.Mock(
            side_effect=self._failover_show_port_side_effect)
        port_update = self.driver.network_proxy.update_port
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)
        self.driver.failover_preparation(amphora)
        port_update.assert_called_once_with(ports[1].get('id'),
                                            dns_name='')
        self.driver.dns_integration_enabled = original_dns_integration_state

    def _failover_show_port_side_effect(self, port_id):
        if port_id == self.LB_NET_PORT_ID:
            return Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_1,
                                          "ip_address": self.IP_ADDRESS_1}],
                           "id": self.FIXED_IP_ID_1,
                           "network_id": self.NETWORK_ID_1})
        if port_id == self.HA_PORT_ID:
            return Port(**{"fixed_ips": [{"subnet_id": self.SUBNET_ID_2,
                                          "ip_address": self.IP_ADDRESS_2}],
                           "id": self.FIXED_IP_ID_2,
                           "network_id": self.NETWORK_ID_2})

    def test_plug_port(self):
        port = mock.MagicMock()
        port.id = self.PORT_ID
        network_attach = self.driver.compute.attach_network_or_port
        network_attach.return_value = t_constants.MOCK_NOVA_INTERFACE
        amphora = data_models.Amphora(
            id=self.AMPHORA_ID, load_balancer_id=self.LB_ID,
            compute_id=self.COMPUTE_ID, status=self.ACTIVE,
            lb_network_ip=self.LB_NET_IP, ha_port_id=self.HA_PORT_ID,
            ha_ip=self.HA_IP)

        self.driver.plug_port(amphora, port)
        network_attach.assert_called_once_with(compute_id=amphora.compute_id,
                                               network_id=None,
                                               ip_address=None,
                                               port_id=self.PORT_ID)

        # NotFound cases
        network_attach.side_effect = exceptions.NotFound(
            resource='Instance', id=1)
        self.assertRaises(network_base.AmphoraNotFound,
                          self.driver.plug_port,
                          amphora,
                          port)
        network_attach.side_effect = exceptions.NotFound(
            resource='Network', id=1)
        self.assertRaises(network_base.NetworkNotFound,
                          self.driver.plug_port,
                          amphora,
                          port)
        network_attach.side_effect = exceptions.NotFound(
            resource='bogus', id=1)
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_port,
                          amphora,
                          port)

        # Already plugged case should not raise an exception
        network_attach.side_effect = nova_exceptions.Conflict(1)
        self.driver.plug_port(amphora, port)

        # Unknown error case
        network_attach.side_effect = TypeError
        self.assertRaises(network_base.PlugNetworkException,
                          self.driver.plug_port,
                          amphora,
                          port)

    def test_get_network_configs(self):
        amphora_mock = mock.MagicMock()
        amphora2_mock = mock.MagicMock()
        load_balancer_mock = mock.MagicMock()
        vip_mock = mock.MagicMock()
        amphora_mock.status = constants.DELETED
        load_balancer_mock.amphorae = [amphora_mock]
        show_port = self.driver.network_proxy.get_port
        show_port.side_effect = [
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            t_constants.MOCK_NEUTRON_PORT, t_constants.MOCK_NEUTRON_PORT,
            Exception('boom')]
        fake_subnet = Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS,
            'cidr': t_constants.MOCK_CIDR})
        fake_subnet2 = Subnet(**{
            'id': t_constants.MOCK_SUBNET_ID2,
            'gateway_ip': t_constants.MOCK_IP_ADDRESS2,
            'cidr': t_constants.MOCK_CIDR})
        show_subnet = self.driver.network_proxy.get_subnet
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
        amphora2_mock.id = 333
        amphora2_mock.status = constants.ACTIVE
        amphora2_mock.vrrp_port_id = 3
        amphora2_mock.vrrp_ip = "10.0.0.2"
        amphora2_mock.ha_port_id = 4
        amphora2_mock.ha_ip = "10.0.0.3"

        configs = self.driver.get_network_configs(load_balancer_mock)
        self.assertEqual(1, len(configs))
        config = configs[222]
        # TODO(ptoohill): find a way to return different items for multiple
        # calls to the same method, right now each call to show subnet
        # will return the same values if a method happens to call it
        # multiple times for different subnets. We should be able to verify
        # different requests get different expected data.
        expected_port_id = t_constants.MOCK_NEUTRON_PORT['id']
        self.assertEqual(expected_port_id, config.ha_port.id)
        self.assertEqual(expected_port_id, config.vrrp_port.id)
        expected_subnet_id = fake_subnet['id']
        self.assertEqual(expected_subnet_id, config.ha_subnet.id)
        self.assertEqual(expected_subnet_id, config.vrrp_subnet.id)

        # Test with additional_vips
        load_balancer_mock.additional_vips = [
            data_models.AdditionalVip(
                subnet_id=t_constants.MOCK_SUBNET_ID2,
                ip_address=t_constants.MOCK_IP_ADDRESS2)
        ]
        show_subnet.side_effect = [
            fake_subnet,
            fake_subnet,
            fake_subnet,
            fake_subnet2]

        configs = self.driver.get_network_configs(load_balancer_mock,
                                                  amphora_mock)
        self.assertEqual(1, len(configs))
        config = configs[222]
        self.assertEqual(t_constants.MOCK_SUBNET_ID2,
                         config.additional_vip_data[0].subnet.id)
        self.assertEqual(t_constants.MOCK_IP_ADDRESS2,
                         config.additional_vip_data[0].ip_address)

        show_subnet.reset_mock(side_effect=True)
        show_subnet.return_value = fake_subnet

        # Test with a specific amphora
        configs = self.driver.get_network_configs(load_balancer_mock,
                                                  amphora_mock)
        self.assertEqual(1, len(configs))
        config = configs[222]
        # TODO(ptoohill): find a way to return different items for multiple
        # calls to the same method, right now each call to show subnet
        # will return the same values if a method happens to call it
        # multiple times for different subnets. We should be able to verify
        # different requests get different expected data.
        expected_port_id = t_constants.MOCK_NEUTRON_PORT['id']
        self.assertEqual(expected_port_id, config.ha_port.id)
        self.assertEqual(expected_port_id, config.vrrp_port.id)
        expected_subnet_id = fake_subnet['id']
        self.assertEqual(expected_subnet_id, config.ha_subnet.id)
        self.assertEqual(expected_subnet_id, config.vrrp_subnet.id)

        # Test with a load balancer with two amphora, one that has a
        # neutron problem.
        load_balancer_mock.amphorae = [amphora_mock, amphora2_mock]
        configs = self.driver.get_network_configs(load_balancer_mock)
        self.assertEqual(1, len(configs))

    def test_delete_port(self):
        PORT_ID = uuidutils.generate_uuid()

        self.driver.network_proxy.delete_port.side_effect = [
            mock.DEFAULT, os_exceptions.ResourceNotFound,
            Exception('boom')]

        # Test successful delete
        self.driver.delete_port(PORT_ID)

        self.driver.network_proxy.delete_port.assert_called_once_with(PORT_ID)

        # Test port NotFound (does not raise)
        self.driver.delete_port(PORT_ID)

        # Test unknown exception
        self.assertRaises(exceptions.NetworkServiceError,
                          self.driver.delete_port, PORT_ID)

    def test_set_port_admin_state_up(self):
        PORT_ID = uuidutils.generate_uuid()
        TEST_STATE = 'test state'

        self.driver.network_proxy.update_port.side_effect = [
            mock.DEFAULT, os_exceptions.ResourceNotFound, Exception('boom')]

        # Test successful state set
        self.driver.set_port_admin_state_up(PORT_ID, TEST_STATE)

        self.driver.network_proxy.update_port.assert_called_once_with(
            PORT_ID, admin_state_up=TEST_STATE)

        # Test port NotFound
        self.assertRaises(network_base.PortNotFound,
                          self.driver.set_port_admin_state_up,
                          PORT_ID, TEST_STATE)

        # Test unknown exception
        self.assertRaises(exceptions.NetworkServiceError,
                          self.driver.set_port_admin_state_up, PORT_ID,
                          TEST_STATE)

    def test_create_port(self):
        ADMIN_STATE_UP = False
        FAKE_NAME = 'fake_name'
        IP_ADDRESS1 = '203.0.113.71'
        IP_ADDRESS2 = '203.0.113.72'
        IP_ADDRESS3 = '203.0.113.73'
        NETWORK_ID = uuidutils.generate_uuid()
        QOS_POLICY_ID = uuidutils.generate_uuid()
        SECONDARY_IPS = [IP_ADDRESS2, IP_ADDRESS3]
        SECURITY_GROUP_ID = uuidutils.generate_uuid()
        SUBNET1_ID = uuidutils.generate_uuid()
        FIXED_IPS = [{'subnet_id': SUBNET1_ID, 'ip_address': IP_ADDRESS1}]

        MOCK_NEUTRON_PORT = Port(**{
            'network_id': NETWORK_ID, 'device_id': t_constants.MOCK_DEVICE_ID,
            'device_owner': t_constants.MOCK_DEVICE_OWNER,
            'id': t_constants.MOCK_PORT_ID, 'name': FAKE_NAME,
            'tenant_id': t_constants.MOCK_PROJECT_ID,
            'admin_state_up': ADMIN_STATE_UP,
            'status': t_constants.MOCK_STATUS,
            'mac_address': t_constants.MOCK_MAC_ADDR,
            'fixed_ips': [{'ip_address': IP_ADDRESS1,
                           'subnet_id': SUBNET1_ID}],
            'security_groups': [],
            'qos_policy_id': QOS_POLICY_ID})

        reference_port_dict = {'admin_state_up': ADMIN_STATE_UP,
                               'device_id': t_constants.MOCK_DEVICE_ID,
                               'device_owner': t_constants.MOCK_DEVICE_OWNER,
                               'fixed_ips': [],
                               'id': t_constants.MOCK_PORT_ID,
                               'mac_address': t_constants.MOCK_MAC_ADDR,
                               'name': FAKE_NAME,
                               'network': None,
                               'network_id': NETWORK_ID,
                               'project_id': t_constants.MOCK_PROJECT_ID,
                               'qos_policy_id': QOS_POLICY_ID,
                               'security_group_ids': [],
                               'status': t_constants.MOCK_STATUS}

        self.driver.network_proxy.create_port.side_effect = [
            MOCK_NEUTRON_PORT, MOCK_NEUTRON_PORT, Exception('boom')]

        # Test successful path
        result = self.driver.create_port(
            NETWORK_ID, name=FAKE_NAME, fixed_ips=FIXED_IPS,
            secondary_ips=SECONDARY_IPS,
            security_group_ids=[SECURITY_GROUP_ID], admin_state_up=False,
            qos_policy_id=QOS_POLICY_ID)

        self.assertEqual(reference_port_dict, result.to_dict())
        self.driver.network_proxy.create_port.assert_called_once_with(
            **{
                'network_id': NETWORK_ID, 'admin_state_up': ADMIN_STATE_UP,
                'device_owner': allowed_address_pairs.OCTAVIA_OWNER,
                'allowed_address_pairs': [
                    {'ip_address': IP_ADDRESS2}, {'ip_address': IP_ADDRESS3}],
                'fixed_ips': [{
                    'subnet_id': SUBNET1_ID, 'ip_address': IP_ADDRESS1}],
                'name': FAKE_NAME, 'qos_policy_id': QOS_POLICY_ID,
                'security_groups': [SECURITY_GROUP_ID]})

        # Test minimal successful path
        result = self.driver.create_port(NETWORK_ID)

        self.assertEqual(reference_port_dict, result.to_dict())

        # Test exception
        self.assertRaises(network_base.CreatePortException,
                          self.driver.create_port, NETWORK_ID, name=FAKE_NAME,
                          fixed_ips=FIXED_IPS, secondary_ips=SECONDARY_IPS,
                          security_group_ids=[SECURITY_GROUP_ID],
                          admin_state_up=False, qos_policy_id=QOS_POLICY_ID)

    def test_get_security_group(self):

        # Test the case of security groups disabled in neutron
        FAKE_SG_NAME = 'Fake_SG_name'
        FAKE_NEUTRON_SECURITY_GROUPS = iter([t_constants.MOCK_SECURITY_GROUP])
        reference_sg_dict = {'id': t_constants.MOCK_SECURITY_GROUP_ID,
                             'name': t_constants.MOCK_SECURITY_GROUP_NAME,
                             'description': '', 'tags': [],
                             'security_group_rule_ids': [],
                             'stateful': None,
                             'project_id': t_constants.MOCK_PROJECT_ID}

        network_proxy = self.driver.network_proxy
        network_proxy.security_groups.side_effect = [
            FAKE_NEUTRON_SECURITY_GROUPS, iter([]), Exception('boom')]

        self.driver.sec_grp_enabled = False
        result = self.driver.get_security_group(FAKE_SG_NAME)

        self.assertIsNone(result)
        network_proxy.security_groups.assert_not_called()

        # Test successful get of the security group
        self.driver.sec_grp_enabled = True

        result = self.driver.get_security_group(FAKE_SG_NAME)

        self.assertEqual(reference_sg_dict, result.to_dict())
        network_proxy.security_groups.assert_called_once_with(
            name=FAKE_SG_NAME)

        # Test no security groups returned
        self.assertRaises(network_base.SecurityGroupNotFound,
                          self.driver.get_security_group, FAKE_SG_NAME)

        # Test with an unknown exception
        self.assertRaises(network_base.NetworkException,
                          self.driver.get_security_group, FAKE_SG_NAME)
