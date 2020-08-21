# Copyright 2017 Redhat.
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
import ipaddress
import os
import shutil
from unittest import mock

from oslo_config import fixture as oslo_fixture

from octavia.amphorae.backends.agent.api_server import osutils
from octavia.common import config
from octavia.common import constants as consts
from octavia.common import exceptions as octavia_exceptions
from octavia.common import utils
from octavia.tests.common import utils as test_utils
from octavia.tests.unit import base


class TestOSUtils(base.TestCase):

    def setUp(self):
        super().setUp()

        self.base_os_util = osutils.BaseOS('unknown')

        with mock.patch('distro.id',
                        return_value='ubuntu'):
            self.ubuntu_os_util = osutils.BaseOS.get_os_util()

        with mock.patch('distro.id',
                        return_value='rhel'):
            self.rh_os_util = osutils.BaseOS.get_os_util()

        with mock.patch('distro.id', return_value='centos'):
            with mock.patch('distro.version', return_value='8'):
                self.centos_os_util = osutils.BaseOS.get_os_util()

        with mock.patch('distro.id', return_value='centos'):
            with mock.patch('distro.version', return_value='7'):
                self.centos7_os_util = osutils.BaseOS.get_os_util()

    def test_get_os_util(self):
        with mock.patch('distro.id',
                        return_value='ubuntu'):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.Ubuntu)
        with mock.patch('distro.id',
                        return_value='fedora'):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.RH)
        with mock.patch('distro.id',
                        return_value='rhel'):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.RH)
        with mock.patch('distro.id',
                        return_value='centos'):
            returned_cls = osutils.BaseOS.get_os_util()
            self.assertIsInstance(returned_cls, osutils.CentOS)
        with mock.patch('distro.id',
                        return_value='FakeOS'):
            self.assertRaises(
                octavia_exceptions.InvalidAmphoraOperatingSystem,
                osutils.BaseOS.get_os_util)

    def test_get_network_interface_file(self):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        fake_agent_server_network_dir = "/path/to/interface"
        fake_agent_server_network_file = "/path/to/interfaces_file"

        base_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                          consts.NETNS_PRIMARY_INTERFACE)
        base_real_nic_path = os.path.join(
            consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            consts.NETNS_PRIMARY_INTERFACE)

        rh_interface_name = 'ifcfg-{nic}'.format(
            nic=consts.NETNS_PRIMARY_INTERFACE)
        rh_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                        rh_interface_name)
        rh_real_nic_path = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_interface_name)

        ubuntu_interface_name = '{nic}.cfg'.format(
            nic=consts.NETNS_PRIMARY_INTERFACE)
        ubuntu_fake_nic_path = os.path.join(fake_agent_server_network_dir,
                                            ubuntu_interface_name)
        ubuntu_real_nic_path = os.path.join(
            consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            ubuntu_interface_name)

        # Check that agent_server_network_file is returned, when provided
        conf.config(group="amphora_agent",
                    agent_server_network_file=fake_agent_server_network_file)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(fake_agent_server_network_file, ubuntu_interface_file)

        # Check that agent_server_network_dir is used, when provided
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent",
                    agent_server_network_dir=fake_agent_server_network_dir)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(base_fake_nic_path, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(rh_fake_nic_path, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(ubuntu_fake_nic_path, ubuntu_interface_file)

        # Check When neither agent_server_network_dir or
        # agent_server_network_file where provided.
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent", agent_server_network_dir=None)

        base_interface_file = (
            self.base_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(base_real_nic_path, base_interface_file)

        rh_interface_file = (
            self.rh_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(rh_real_nic_path, rh_interface_file)

        ubuntu_interface_file = (
            self.ubuntu_os_util.
            get_network_interface_file(consts.NETNS_PRIMARY_INTERFACE))
        self.assertEqual(ubuntu_real_nic_path, ubuntu_interface_file)

    def _test_RH_get_static_routes_interface_file(self, version):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        fake_agent_server_network_dir = "/path/to/interface"
        fake_agent_server_network_file = "/path/to/interfaces_file"

        route = 'route6' if version == 6 else 'route'
        rh_route_name = '{route}-{nic}'.format(
            route=route, nic=consts.NETNS_PRIMARY_INTERFACE)
        rh_fake_route_path = os.path.join(fake_agent_server_network_dir,
                                          rh_route_name)
        rh_real_route_path = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_route_name)

        # Check that agent_server_network_file is returned, when provided
        conf.config(group="amphora_agent",
                    agent_server_network_file=fake_agent_server_network_file)

        rh_route_file = (
            self.rh_os_util.
            get_static_routes_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                             version))
        self.assertEqual(fake_agent_server_network_file, rh_route_file)

        # Check that agent_server_network_dir is used, when provided
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent",
                    agent_server_network_dir=fake_agent_server_network_dir)

        rh_route_file = (
            self.rh_os_util.
            get_static_routes_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                             version))
        self.assertEqual(rh_fake_route_path, rh_route_file)

        # Check When neither agent_server_network_dir or
        # agent_server_network_file where provided.
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent", agent_server_network_dir=None)

        rh_route_file = (
            self.rh_os_util.
            get_static_routes_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                             version))
        self.assertEqual(rh_real_route_path, rh_route_file)

    def test_RH_get_static_routes_interface_file(self):
        self._test_RH_get_static_routes_interface_file(4)

    def test_RH_get_static_routes_interface_file_ipv6(self):
        self._test_RH_get_static_routes_interface_file(6)

    def _test_RH_get_route_rules_interface_file(self, version):
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))

        fake_agent_server_network_dir = "/path/to/interface"
        fake_agent_server_network_file = "/path/to/interfaces_file"

        rule = 'rule6' if version == 6 else 'rule'
        rh_route_rules_name = '{rule}-{nic}'.format(
            rule=rule, nic=consts.NETNS_PRIMARY_INTERFACE)
        rh_fake_route_rules_path = os.path.join(fake_agent_server_network_dir,
                                                rh_route_rules_name)
        rh_real_route_rules_path = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_route_rules_name)

        # Check that agent_server_network_file is returned, when provided
        conf.config(group="amphora_agent",
                    agent_server_network_file=fake_agent_server_network_file)

        rh_route_rules_file = (
            self.rh_os_util.
            get_route_rules_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                           version))
        self.assertEqual(fake_agent_server_network_file, rh_route_rules_file)

        # Check that agent_server_network_dir is used, when provided
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent",
                    agent_server_network_dir=fake_agent_server_network_dir)

        rh_route_rules_file = (
            self.rh_os_util.
            get_route_rules_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                           version))
        self.assertEqual(rh_fake_route_rules_path, rh_route_rules_file)

        # Check When neither agent_server_network_dir or
        # agent_server_network_file where provided.
        conf.config(group="amphora_agent", agent_server_network_file=None)
        conf.config(group="amphora_agent", agent_server_network_dir=None)

        rh_route_rules_file = (
            self.rh_os_util.
            get_route_rules_interface_file(consts.NETNS_PRIMARY_INTERFACE,
                                           version))
        self.assertEqual(rh_real_route_rules_path, rh_route_rules_file)

    def test_RH_get_route_rules_interface_file(self):
        self._test_RH_get_route_rules_interface_file(4)

    def test_RH_get_route_rules_interface_file_ipv6(self):
        self._test_RH_get_route_rules_interface_file(6)

    def test_cmd_get_version_of_installed_package(self):
        package_name = 'foo'
        ubuntu_cmd = "dpkg-query -W -f=${{Version}} {name}".format(
            name=package_name)
        rh_cmd = "rpm -q --queryformat %{{VERSION}} {name}".format(
            name=package_name)

        returned_ubuntu_cmd = (
            self.ubuntu_os_util.cmd_get_version_of_installed_package(
                package_name))
        self.assertEqual(ubuntu_cmd, returned_ubuntu_cmd)

        returned_rh_cmd = (self.rh_os_util.
                           cmd_get_version_of_installed_package(package_name))
        self.assertEqual(rh_cmd, returned_rh_cmd)

    def test_cmd_get_version_of_installed_package_mapped(self):
        package_name = 'haproxy'
        centos7_cmd = "rpm -q --queryformat %{VERSION} haproxy18"

        returned_centos7_cmd = (
            self.centos7_os_util.cmd_get_version_of_installed_package(
                package_name))
        self.assertEqual(centos7_cmd, returned_centos7_cmd)

        centos_cmd = "rpm -q --queryformat %{VERSION} haproxy"
        returned_centos_cmd = (
            self.centos_os_util.cmd_get_version_of_installed_package(
                package_name))
        self.assertEqual(centos_cmd, returned_centos_cmd)

    def test_has_ifup_all(self):
        self.assertTrue(self.base_os_util.has_ifup_all())
        self.assertTrue(self.ubuntu_os_util.has_ifup_all())
        self.assertFalse(self.rh_os_util.has_ifup_all())

    def test_write_vip_interface_file(self):
        netns_interface = u'eth1234'
        FIXED_IP = u'192.0.2.2'
        SUBNET_CIDR = u'192.0.2.0/24'
        GATEWAY = u'192.51.100.1'
        DEST1 = u'198.51.100.0/24'
        DEST2 = u'203.0.113.0/24'
        NEXTHOP = u'192.0.2.1'
        MTU = 1450
        FIXED_IP_IPV6 = u'2001:0db8:0000:0000:0000:0000:0000:0001'
        # Subnet prefix is purposefully not 32, because that coincidentally
        # matches the result of any arbitrary IPv4->prefixlen conversion
        SUBNET_CIDR_IPV6 = u'2001:db8::/70'

        ip = ipaddress.ip_address(FIXED_IP)
        network = ipaddress.ip_network(SUBNET_CIDR)
        broadcast = network.broadcast_address.exploded
        netmask = network.netmask.exploded
        netmask_prefix = utils.netmask_to_prefix(netmask)

        ipv6 = ipaddress.ip_address(FIXED_IP_IPV6)
        networkv6 = ipaddress.ip_network(SUBNET_CIDR_IPV6)
        broadcastv6 = networkv6.broadcast_address.exploded
        netmaskv6 = networkv6.prefixlen

        host_routes = [
            {'gw': NEXTHOP, 'network': ipaddress.ip_network(DEST1)},
            {'gw': NEXTHOP, 'network': ipaddress.ip_network(DEST2)}
        ]

        path = self.ubuntu_os_util.get_network_interface_file(netns_interface)
        mock_open = self.useFixture(test_utils.OpenFixture(path)).mock_open
        mock_template = mock.MagicMock()

        # Test an IPv4 VIP
        with mock.patch('os.open'), mock.patch.object(
                os, 'fdopen', mock_open):
            self.ubuntu_os_util.write_vip_interface_file(
                interface_file_path=path,
                primary_interface=netns_interface,
                vip=FIXED_IP,
                ip=ip,
                broadcast=broadcast,
                netmask=netmask,
                gateway=GATEWAY,
                mtu=MTU,
                vrrp_ip=None,
                vrrp_version=None,
                render_host_routes=host_routes,
                template_vip=mock_template)

        mock_template.render.assert_called_once_with(
            consts=consts,
            interface=netns_interface,
            vip=FIXED_IP,
            vip_ipv6=False,
            prefix=netmask_prefix,
            broadcast=broadcast,
            netmask=netmask,
            gateway=GATEWAY,
            network=SUBNET_CIDR,
            mtu=MTU,
            vrrp_ip=None,
            vrrp_ipv6=False,
            host_routes=host_routes,
            topology="SINGLE",
        )

        # Now test with an IPv6 VIP
        mock_template.reset_mock()
        with mock.patch('os.open'), mock.patch.object(
                os, 'fdopen', mock_open):
            self.ubuntu_os_util.write_vip_interface_file(
                interface_file_path=path,
                primary_interface=netns_interface,
                vip=FIXED_IP_IPV6,
                ip=ipv6,
                broadcast=broadcastv6,
                netmask=netmaskv6,
                gateway=GATEWAY,
                mtu=MTU,
                vrrp_ip=None,
                vrrp_version=None,
                render_host_routes=host_routes,
                template_vip=mock_template)

        mock_template.render.assert_called_once_with(
            consts=consts,
            interface=netns_interface,
            vip=FIXED_IP_IPV6,
            vip_ipv6=True,
            prefix=netmaskv6,
            broadcast=broadcastv6,
            netmask=netmaskv6,
            gateway=GATEWAY,
            network=SUBNET_CIDR_IPV6,
            mtu=MTU,
            vrrp_ip=None,
            vrrp_ipv6=False,
            host_routes=host_routes,
            topology="SINGLE",
        )

    def test_write_port_interface_file(self):
        FIXED_IP = u'192.0.2.2'
        NEXTHOP = u'192.0.2.1'
        DEST = u'198.51.100.0/24'
        host_routes = [
            {'nexthop': NEXTHOP, 'destination': ipaddress.ip_network(DEST)}
        ]
        FIXED_IP_IPV6 = u'2001:db8::2'
        NEXTHOP_IPV6 = u'2001:db8::1'
        DEST_IPV6 = u'2001:db8:51:100::/64'
        host_routes_ipv6 = [
            {'nexthop': NEXTHOP_IPV6,
             'destination': ipaddress.ip_network(DEST_IPV6)}
        ]
        ip_addr = {'ip_address': FIXED_IP, 'host_routes': host_routes}
        ipv6_addr = {'ip_address': FIXED_IP_IPV6,
                     'host_routes': host_routes_ipv6}

        netns_interface = 'eth1234'
        MTU = 1450
        fixed_ips = [ip_addr, ipv6_addr]
        path = 'mypath'
        mock_template = mock.MagicMock()
        mock_open = self.useFixture(test_utils.OpenFixture(path)).mock_open
        mock_gen_text = mock.MagicMock()
        mock_local_scripts = mock.MagicMock()
        mock_wr_fi = mock.MagicMock()

        with mock.patch('os.open'), mock.patch.object(
                os, 'fdopen', mock_open), mock.patch.object(
                osutils.BaseOS, '_generate_network_file_text', mock_gen_text):
            self.base_os_util.write_port_interface_file(
                netns_interface=netns_interface,
                fixed_ips=fixed_ips,
                mtu=MTU,
                interface_file_path=path,
                template_port=mock_template)

        mock_gen_text.assert_called_once_with(
            netns_interface, fixed_ips, MTU, mock_template)

        mock_gen_text.reset_mock()

        with mock.patch('os.open'), mock.patch.object(
                os, 'fdopen', mock_open), mock.patch.object(
                osutils.BaseOS, '_generate_network_file_text',
                mock_gen_text), mock.patch.object(
                osutils.RH, '_write_ifup_ifdown_local_scripts_if_possible',
                mock_local_scripts), mock.patch.object(
                osutils.RH, 'write_static_routes_interface_file', mock_wr_fi):
            self.rh_os_util.write_port_interface_file(
                netns_interface=netns_interface,
                fixed_ips=fixed_ips,
                mtu=MTU,
                interface_file_path=path,
                template_port=mock_template)

        rh_route_name = 'route-{nic}'.format(nic=netns_interface)
        rh_real_route_path = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_route_name)
        rh_route_name_ipv6 = 'route6-{nic}'.format(nic=netns_interface)
        rh_real_route_path_ipv6 = os.path.join(
            consts.RH_AMP_NET_DIR_TEMPLATE.format(
                netns=consts.AMPHORA_NAMESPACE),
            rh_route_name_ipv6)

        exp_routes = [
            {'network': ipaddress.ip_network(DEST), 'gw': NEXTHOP}
        ]
        exp_routes_ipv6 = [
            {'network': ipaddress.ip_network(DEST_IPV6), 'gw': NEXTHOP_IPV6}
        ]
        expected_calls = [
            mock.call(rh_real_route_path, netns_interface,
                      exp_routes, mock.ANY, None, None, None),
            mock.call(rh_real_route_path_ipv6, netns_interface,
                      exp_routes_ipv6, mock.ANY, None, None, None)]

        mock_gen_text.assert_called_once_with(
            netns_interface, fixed_ips, MTU, mock_template)
        self.assertEqual(2, mock_wr_fi.call_count)
        mock_wr_fi.assert_has_calls(expected_calls)
        mock_local_scripts.assert_called_once()

    @mock.patch('shutil.copy2')
    @mock.patch('os.makedirs')
    @mock.patch('shutil.copytree')
    def test_create_netns_dir(self, mock_copytree, mock_makedirs, mock_copy2):
        network_dir = 'foo'
        netns_network_dir = 'fake_netns_network'
        ignore = shutil.ignore_patterns('fake_eth*', 'fake_loopback*')
        self.rh_os_util.create_netns_dir(network_dir,
                                         netns_network_dir,
                                         ignore)
        mock_copytree.assert_any_call(
            network_dir,
            os.path.join('/etc/netns/',
                         consts.AMPHORA_NAMESPACE,
                         netns_network_dir),
            ignore=ignore,
            symlinks=True)

        mock_makedirs.assert_any_call(os.path.join('/etc/netns/',
                                                   consts.AMPHORA_NAMESPACE))
        mock_copy2.assert_any_call(
            '/etc/sysconfig/network',
            '/etc/netns/{netns}/sysconfig'.format(
                netns=consts.AMPHORA_NAMESPACE))

        mock_copytree.reset_mock()
        mock_makedirs.reset_mock()
        mock_copy2.reset_mock()

        self.ubuntu_os_util.create_netns_dir(network_dir,
                                             netns_network_dir,
                                             ignore)
        mock_copytree.assert_any_call(
            network_dir,
            os.path.join('/etc/netns/',
                         consts.AMPHORA_NAMESPACE,
                         netns_network_dir),
            ignore=ignore,
            symlinks=True)

        mock_makedirs.assert_any_call(os.path.join('/etc/netns/',
                                                   consts.AMPHORA_NAMESPACE))
        mock_copy2.assert_not_called()
