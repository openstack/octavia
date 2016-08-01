# Copyright 2015 Rackspace
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

import mock
import netifaces

from octavia.amphorae.backends.agent.api_server import plug
import octavia.tests.unit.base as base

FAKE_CIDR_IPV4 = '10.0.0.0/24'
FAKE_GATEWAY_IPV4 = '10.0.0.1'
FAKE_IP_IPV4 = '10.0.0.2'
FAKE_CIDR_IPV6 = '2001:db8::/32'
FAKE_GATEWAY_IPV6 = '2001:db8::1'
FAKE_IP_IPV6 = '2001:db8::2'
FAKE_IP_IPV6_EXPANDED = '2001:0db8:0000:0000:0000:0000:0000:0002'
FAKE_MAC_ADDRESS = 'ab:cd:ef:00:ff:22'
FAKE_INTERFACE = 'eth0'


class TestPlug(base.TestCase):
    def setUp(self):
        super(TestPlug, self).setUp()

        self.mock_netifaces = mock.patch.object(plug, "netifaces").start()
        self.addCleanup(self.mock_netifaces.stop)

        # Set up our fake interface
        self.mock_netifaces.AF_LINK = netifaces.AF_LINK
        self.mock_netifaces.interfaces.return_value = [FAKE_INTERFACE]
        self.mock_netifaces.ifaddresses.return_value = {
            netifaces.AF_LINK: [
                {'addr': FAKE_MAC_ADDRESS.lower()}
            ]
        }

    def test__interface_by_mac_case_insensitive(self):
        interface = plug._interface_by_mac(FAKE_MAC_ADDRESS.upper())
        self.assertEqual(FAKE_INTERFACE, interface)

    @mock.patch.object(plug, "flask")
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.netns.create')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_ipv4(self, mock_makedirs, mock_copytree,
                           mock_check_output, mock_netns, mock_netns_create,
                           mock_pyroute2, mock_flask):
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            plug.plug_vip(
                vip=FAKE_IP_IPV4,
                subnet_cidr=FAKE_CIDR_IPV4,
                gateway=FAKE_GATEWAY_IPV4,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_flask.jsonify.assert_any_call({
            'message': 'OK',
            'details': 'VIP {vip} plugged on interface {interface}'.format(
                vip=FAKE_IP_IPV4, interface='eth1')
        })

    @mock.patch.object(plug, "flask")
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.netns.create')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_ipv6(self, mock_makedirs, mock_copytree,
                           mock_check_output, mock_netns, mock_netns_create,
                           mock_pyroute2, mock_flask):
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            plug.plug_vip(
                vip=FAKE_IP_IPV6,
                subnet_cidr=FAKE_CIDR_IPV6,
                gateway=FAKE_GATEWAY_IPV6,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_flask.jsonify.assert_any_call({
            'message': 'OK',
            'details': 'VIP {vip} plugged on interface {interface}'.format(
                vip=FAKE_IP_IPV6_EXPANDED, interface='eth1')
        })

    @mock.patch.object(plug, "flask")
    @mock.patch('pyroute2.IPRoute')
    @mock.patch('pyroute2.netns.create')
    @mock.patch('pyroute2.NetNS')
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_bad_ip(self, mock_makedirs, mock_copytree,
                             mock_check_output, mock_netns, mock_netns_create,
                             mock_pyroute2, mock_flask):
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            plug.plug_vip(
                vip="error",
                subnet_cidr=FAKE_CIDR_IPV4,
                gateway=FAKE_GATEWAY_IPV4,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_flask.jsonify.assert_any_call({'message': 'Invalid VIP'})

    @mock.patch('pyroute2.NetNS')
    def test__netns_interface_exists(self, mock_netns):

        netns_handle = mock_netns.return_value.__enter__.return_value

        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_ADDRESS', '123']]}]

        # Interface is found in netns
        self.assertTrue(plug._netns_interface_exists('123'))

        # Interface is not found in netns
        self.assertFalse(plug._netns_interface_exists('321'))


class TestPlugNetwork(base.TestCase):

    def test__generate_network_file_text_static_ip(self):
        netns_interface = 'eth1234'
        FIXED_IP = '192.0.2.2'
        BROADCAST = '192.0.2.255'
        SUBNET_CIDR = '192.0.2.0/24'
        NETMASK = '255.255.255.0'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        NEXTHOP = '192.0.2.1'
        fixed_ips = [{'ip_address': FIXED_IP,
                      'subnet_cidr': SUBNET_CIDR,
                      'host_routes': [
                          {'destination': DEST1, 'nexthop': NEXTHOP},
                          {'destination': DEST2, 'nexthop': NEXTHOP}
                      ]}]
        text = plug._generate_network_file_text(netns_interface, fixed_ips)
        expected_text = (
            '\n\n# Generated by Octavia agent\n'
            'auto ' + netns_interface + '\n'
            'iface ' + netns_interface + ' inet static\n'
            'address ' + FIXED_IP + '\n'
            'broadcast ' + BROADCAST + '\n'
            'netmask ' + NETMASK + '\n'
            'up route add -net ' + DEST1 + ' gw ' + NEXTHOP +
            ' dev ' + netns_interface + '\n'
            'down route del -net ' + DEST1 + ' gw ' + NEXTHOP +
            ' dev ' + netns_interface + '\n'
            'up route add -net ' + DEST2 + ' gw ' + NEXTHOP +
            ' dev ' + netns_interface + '\n'
            'down route del -net ' + DEST2 + ' gw ' + NEXTHOP +
            ' dev ' + netns_interface + '\n')
        self.assertEqual(expected_text, text)
