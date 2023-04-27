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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from werkzeug import exceptions as wz_exceptions

from octavia.amphorae.backends.agent.api_server import osutils
from octavia.amphorae.backends.agent.api_server import plug
from octavia.common import constants
import octavia.tests.unit.base as base

FAKE_CIDR_IPV4 = '10.0.0.0/24'
FAKE_GATEWAY_IPV4 = '10.0.0.1'
FAKE_IP_IPV4 = '10.0.0.2'
FAKE_CIDR_IPV6 = '2001:db8::/32'
FAKE_GATEWAY_IPV6 = '2001:db8::1'
FAKE_IP_IPV6 = '2001:db8::2'
FAKE_IP_IPV6_EXPANDED = '2001:0db8:0000:0000:0000:0000:0000:0002'
FAKE_MAC_ADDRESS = 'ab:cd:ef:00:ff:22'
FAKE_INTERFACE = 'eth33'


class TestPlug(base.TestCase):
    def setUp(self):
        super().setUp()
        self.mock_platform = mock.patch("distro.id").start()
        self.mock_platform.return_value = "ubuntu"
        self.osutil = osutils.BaseOS.get_os_util()
        self.test_plug = plug.Plug(self.osutil)
        self.addCleanup(self.mock_platform.stop)

    @mock.patch('pyroute2.IPRoute', create=True)
    def test__interface_by_mac_case_insensitive_ubuntu(self, mock_ipr):
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = [33]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr().__enter__.return_value = mock_ipr_instance

        interface = self.test_plug._interface_by_mac(FAKE_MAC_ADDRESS.upper())
        self.assertEqual(FAKE_INTERFACE, interface)
        mock_ipr_instance.get_links.assert_called_once_with(33)

    @mock.patch('pyroute2.IPRoute', create=True)
    def test__interface_by_mac_not_found(self, mock_ipr):
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = []
        mock_ipr().__enter__.return_value = mock_ipr_instance

        fd_mock = mock.mock_open()
        open_mock = mock.Mock()
        isfile_mock = mock.Mock()
        with mock.patch('os.open', open_mock), mock.patch.object(
                os, 'fdopen', fd_mock), mock.patch.object(
                os.path, 'isfile', isfile_mock):
            self.assertRaises(wz_exceptions.HTTPException,
                              self.test_plug._interface_by_mac,
                              FAKE_MAC_ADDRESS.upper())
        open_mock.assert_called_once_with('/sys/bus/pci/rescan', os.O_WRONLY)
        fd_mock().write.assert_called_once_with('1')

    @mock.patch('pyroute2.IPRoute', create=True)
    def test__interface_by_mac_case_insensitive_rh(self, mock_ipr):
        mock_ipr_instance = mock.MagicMock()
        mock_ipr_instance.link_lookup.return_value = [33]
        mock_ipr_instance.get_links.return_value = ({
            'attrs': [('IFLA_IFNAME', FAKE_INTERFACE)]},)
        mock_ipr().__enter__.return_value = mock_ipr_instance

        with mock.patch('distro.id', return_value='centos'):
            osutil = osutils.BaseOS.get_os_util()
            self.test_plug = plug.Plug(osutil)
            interface = self.test_plug._interface_by_mac(
                FAKE_MAC_ADDRESS.upper())
            self.assertEqual(FAKE_INTERFACE, interface)
            mock_ipr_instance.get_links.assert_called_once_with(33)

    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch.object(plug, "webob")
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_ipv4(self, mock_makedirs, mock_copytree,
                           mock_check_output, mock_netns, mock_pyroute2,
                           mock_webob, mock_nspopen, mock_by_mac):
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_vip(
                vip=FAKE_IP_IPV4,
                subnet_cidr=FAKE_CIDR_IPV4,
                gateway=FAKE_GATEWAY_IPV4,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_webob.Response.assert_any_call(json={
            'message': 'OK',
            'details': 'VIPs plugged on interface {interface}: {vips}'.format(
                vips=FAKE_IP_IPV4, interface='eth1')
        }, status=202)

    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch.object(plug, "webob")
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_ipv6(self, mock_makedirs, mock_copytree,
                           mock_check_output, mock_netns, mock_pyroute2,
                           mock_webob, mock_nspopen, mock_by_mac):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='controller_worker',
                    loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_vip(
                vip=FAKE_IP_IPV6,
                subnet_cidr=FAKE_CIDR_IPV6,
                gateway=FAKE_GATEWAY_IPV6,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_webob.Response.assert_any_call(json={
            'message': 'OK',
            'details': 'VIPs plugged on interface {interface}: {vips}'.format(
                vips=FAKE_IP_IPV6_EXPANDED, interface='eth1')
        }, status=202)

    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.NSPopen', create=True)
    @mock.patch.object(plug, "webob")
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_ipv4_and_ipv6(
            self, mock_makedirs, mock_copytree,
            mock_check_output, mock_netns,
            mock_pyroute2, mock_webob, mock_nspopen, mock_by_mac):
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='controller_worker',
                    loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        additional_vips = [
            {'ip_address': FAKE_IP_IPV4, 'subnet_cidr': FAKE_CIDR_IPV4,
             'host_routes': [], 'gateway': FAKE_GATEWAY_IPV4}
        ]
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_vip(
                vip=FAKE_IP_IPV6,
                subnet_cidr=FAKE_CIDR_IPV6,
                gateway=FAKE_GATEWAY_IPV6,
                mac_address=FAKE_MAC_ADDRESS,
                additional_vips=additional_vips
            )
        mock_webob.Response.assert_any_call(json={
            'message': 'OK',
            'details': 'VIPs plugged on interface {interface}: {vips}'.format(
                vips=", ".join([FAKE_IP_IPV6_EXPANDED, FAKE_IP_IPV4]),
                interface='eth1')
        }, status=202)

    @mock.patch.object(plug, "webob")
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_bad_ip(self, mock_makedirs, mock_copytree,
                             mock_check_output, mock_netns, mock_pyroute2,
                             mock_webob):
        m = mock.mock_open()
        BAD_IP_ADDRESS = "error"
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_vip(
                vip=BAD_IP_ADDRESS,
                subnet_cidr=FAKE_CIDR_IPV4,
                gateway=FAKE_GATEWAY_IPV4,
                mac_address=FAKE_MAC_ADDRESS
            )
        mock_webob.Response.assert_any_call(
            json={'message': ("Invalid VIP: '{ip}' does not appear to be an "
                              "IPv4 or IPv6 address").format(
                                  ip=BAD_IP_ADDRESS)},
            status=400)

    @mock.patch.object(plug, "webob")
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch('subprocess.check_output')
    @mock.patch('shutil.copytree')
    @mock.patch('os.makedirs')
    def test_plug_vip_bad_vrrp_ip(self, mock_makedirs, mock_copytree,
                                  mock_check_output, mock_netns, mock_pyroute2,
                                  mock_webob):
        m = mock.mock_open()
        BAD_IP_ADDRESS = "error"
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_vip(
                vip=FAKE_IP_IPV4,
                subnet_cidr=FAKE_CIDR_IPV4,
                gateway=FAKE_GATEWAY_IPV4,
                mac_address=FAKE_MAC_ADDRESS,
                vrrp_ip=BAD_IP_ADDRESS
            )
        mock_webob.Response.assert_any_call(
            json={'message': ("Invalid VRRP Address: '{ip}' does not appear "
                              "to be an IPv4 or IPv6 address").format(
                                  ip=BAD_IP_ADDRESS)},
            status=400)

    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.write_interface_file")
    def test_plug_lo(self, mock_write_interface):
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_lo()
        mock_write_interface.assert_called_once_with(interface='lo',
                                                     ip_address='127.0.0.1',
                                                     prefixlen=8)

    @mock.patch('pyroute2.NetNS', create=True)
    def test__netns_interface_exists(self, mock_netns):

        netns_handle = mock_netns.return_value.__enter__.return_value

        netns_handle.get_links.return_value = [{
            'attrs': [['IFLA_ADDRESS', '123'],
                      ['IFLA_IFNAME', 'eth0']]}]

        # Interface is found in netns
        self.assertTrue(self.test_plug._netns_interface_exists('123'))

        # Interface is not found in netns
        self.assertFalse(self.test_plug._netns_interface_exists('321'))

    @mock.patch.object(plug, "webob")
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_netns_interface_exists', return_value=False)
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.write_port_interface_file")
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.bring_interface_up")
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "send_member_advertisements")
    def test_plug_network(self, mock_send_member_adv,
                          mock_if_up, mock_write_port_interface,
                          mock_netns, mock_iproute,
                          mock_by_mac, mock_interface_exists, mock_webob):
        fixed_ips = [
            {'ip_address': FAKE_IP_IPV4,
             'subnet_cidr': FAKE_CIDR_IPV4,
             'gateway': FAKE_GATEWAY_IPV4,
             'host_routes': [
                 {'destination': '192.0.2.0/24',
                  'nexthop': '192.0.2.254'}]
             }]
        mtu = 1400
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_network(FAKE_MAC_ADDRESS, fixed_ips, 1400)

        mock_write_port_interface.assert_called_once_with(
            interface='eth2', fixed_ips=fixed_ips, mtu=mtu)
        mock_if_up.assert_called_once_with('eth2', 'network')
        mock_send_member_adv.assert_called_once_with(fixed_ips)

        mock_webob.Response.assert_any_call(
            json={'message': 'OK',
                  'details': 'Plugged on interface eth2'},
            status=202)

    @mock.patch.object(plug, "webob")
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_netns_interface_exists', return_value=True)
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_netns_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.write_port_interface_file")
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.bring_interface_up")
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "send_member_advertisements")
    def test_plug_network_existing_interface(self, mock_send_member_adv,
                                             mock_if_up,
                                             mock_write_port_interface,
                                             mock_netns, mock_by_mac,
                                             mock_interface_exists,
                                             mock_webob):
        fixed_ips = [
            {'ip_address': FAKE_IP_IPV4,
             'subnet_cidr': FAKE_CIDR_IPV4,
             'gateway': FAKE_GATEWAY_IPV4,
             'host_routes': [
                 {'destination': '192.0.2.0/24',
                  'nexthop': '192.0.2.254'}]
             }, {'ip_address': FAKE_IP_IPV6,
                 'subnet_cidr': FAKE_CIDR_IPV6,
                 'gateway': FAKE_GATEWAY_IPV6,
                 'host_routes': [
                     {'destination': '2001:db8::/64',
                      'nexthop': '2001:db8::ffff'}]
                 }]
        mtu = 1400
        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_network(FAKE_MAC_ADDRESS, fixed_ips, 1400)

        mock_write_port_interface.assert_called_once_with(
            interface=FAKE_INTERFACE, fixed_ips=fixed_ips, mtu=mtu)
        mock_if_up.assert_called_once_with(FAKE_INTERFACE, 'network')
        mock_send_member_adv.assert_called_once_with(fixed_ips)

        mock_webob.Response.assert_any_call(
            json={'message': 'OK',
                  'details': 'Updated existing interface {}'.format(
                      FAKE_INTERFACE)},
            status=202)

    @mock.patch.object(plug, "webob")
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_netns_interface_exists', return_value=True)
    @mock.patch('octavia.amphorae.backends.agent.api_server.plug.Plug.'
                '_netns_interface_by_mac', return_value=FAKE_INTERFACE)
    @mock.patch('pyroute2.NetNS', create=True)
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.write_vip_interface_file")
    @mock.patch("octavia.amphorae.backends.agent.api_server.osutils."
                "BaseOS.bring_interface_up")
    @mock.patch("octavia.amphorae.backends.agent.api_server.util."
                "send_member_advertisements")
    def test_plug_network_on_vip(
            self, mock_send_member_adv, mock_if_up, mock_write_vip_interface,
            mock_netns, mock_by_mac, mock_interface_exists, mock_webob):
        fixed_ips = [
            {'ip_address': FAKE_IP_IPV4,
             'subnet_cidr': FAKE_CIDR_IPV4,
             'gateway': FAKE_GATEWAY_IPV4,
             'host_routes': [
                 {'destination': '192.0.2.128/25',
                  'nexthop': '192.0.2.100'}]
             }, {'ip_address': FAKE_IP_IPV6,
                 'subnet_cidr': FAKE_CIDR_IPV6,
                 'gateway': FAKE_GATEWAY_IPV6,
                 'host_routes': [
                     {'destination': '2001:db8::/64',
                      'nexthop': '2001:db8::ffff'}]
                 }]
        mtu = 1400
        vip_net_info = {
            'vip': '192.0.2.10',
            'subnet_cidr': '192.0.2.0/25',
            'vrrp_ip': '192.0.2.11',
            'gateway': '192.0.2.1',
            'host_routes': []
        }

        m = mock.mock_open()
        with mock.patch('os.open'), mock.patch.object(os, 'fdopen', m):
            self.test_plug.plug_network(FAKE_MAC_ADDRESS, fixed_ips, mtu=1400,
                                        vip_net_info=vip_net_info)

        mock_write_vip_interface.assert_called_once_with(
            interface=FAKE_INTERFACE,
            vips=[{
                'ip_address': vip_net_info['vip'],
                'ip_version': 4,
                'prefixlen': 25,
                'gateway': vip_net_info['gateway'],
                'host_routes': [],
            }],
            vrrp_info={
                'ip': vip_net_info['vrrp_ip'],
                'ip_version': 4,
                'prefixlen': 25,
                'gateway': vip_net_info['gateway'],
                'host_routes': [],
            },
            fixed_ips=fixed_ips, mtu=mtu)

        mock_if_up.assert_called_once_with(FAKE_INTERFACE, 'vip')
        mock_send_member_adv.assert_called_once_with(fixed_ips)

        mock_webob.Response.assert_any_call(
            json={'message': 'OK',
                  'details': 'Updated existing interface {}'.format(
                      FAKE_INTERFACE)},
            status=202)

    @mock.patch('pyroute2.NetNS', create=True)
    def test__netns_get_next_interface(self, mock_netns):
        netns_handle = mock_netns.return_value.__enter__.return_value

        netns_handle.get_links.return_value = [
            {'attrs': [['IFLA_IFNAME', 'lo']]},
        ]

        ifname = self.test_plug._netns_get_next_interface()
        self.assertEqual('eth2', ifname)

        netns_handle.get_links.return_value = [
            {'attrs': [['IFLA_IFNAME', 'lo']]},
            {'attrs': [['IFLA_IFNAME', 'eth1']]},
            {'attrs': [['IFLA_IFNAME', 'eth2']]},
            {'attrs': [['IFLA_IFNAME', 'eth3']]},
        ]

        ifname = self.test_plug._netns_get_next_interface()
        self.assertEqual('eth4', ifname)

        netns_handle.get_links.return_value = [
            {'attrs': [['IFLA_IFNAME', 'lo']]},
            {'attrs': [['IFLA_IFNAME', 'eth1']]},
            {'attrs': [['IFLA_IFNAME', 'eth3']]},
        ]

        ifname = self.test_plug._netns_get_next_interface()
        self.assertEqual('eth2', ifname)

        netns_handle.get_links.return_value = [
            {'attrs': [['IFLA_IFNAME', f'eth{idx}']]}
            for idx in range(2, 1000)]

        ifname = self.test_plug._netns_get_next_interface()
        self.assertEqual('eth1000', ifname)
