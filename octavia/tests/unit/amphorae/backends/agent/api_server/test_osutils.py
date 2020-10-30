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
from unittest import mock

from octavia.amphorae.backends.agent.api_server import osutils
from octavia.common import exceptions as octavia_exceptions
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

    @mock.patch('octavia.amphorae.backends.utils.interface_file.'
                'VIPInterfaceFile')
    def test_write_vip_interface_file(self, mock_vip_interface_file):
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

        ipv6 = ipaddress.ip_address(FIXED_IP_IPV6)
        networkv6 = ipaddress.ip_network(SUBNET_CIDR_IPV6)

        host_routes = [
            {'nexthop': NEXTHOP, 'destination': DEST1},
            {'nexthop': NEXTHOP, 'destination': DEST2}
        ]

        self.ubuntu_os_util.write_vip_interface_file(
            interface=netns_interface,
            vip=FIXED_IP,
            ip_version=ip.version,
            prefixlen=network.prefixlen,
            gateway=GATEWAY,
            mtu=MTU,
            vrrp_ip=None,
            host_routes=host_routes)

        mock_vip_interface_file.assert_called_once_with(
            name=netns_interface,
            vip=FIXED_IP,
            ip_version=ip.version,
            prefixlen=network.prefixlen,
            gateway=GATEWAY,
            mtu=MTU,
            vrrp_ip=None,
            host_routes=host_routes,
            topology="SINGLE")
        mock_vip_interface_file.return_value.write.assert_called_once()

        # Now test with an IPv6 VIP
        mock_vip_interface_file.reset_mock()

        self.ubuntu_os_util.write_vip_interface_file(
            interface=netns_interface,
            vip=FIXED_IP_IPV6,
            ip_version=ipv6.version,
            prefixlen=networkv6.prefixlen,
            gateway=GATEWAY,
            mtu=MTU,
            vrrp_ip=None,
            host_routes=host_routes)

        mock_vip_interface_file.assert_called_once_with(
            name=netns_interface,
            vip=FIXED_IP_IPV6,
            ip_version=ipv6.version,
            prefixlen=networkv6.prefixlen,
            gateway=GATEWAY,
            mtu=MTU,
            vrrp_ip=None,
            host_routes=host_routes,
            topology="SINGLE")

    @mock.patch('octavia.amphorae.backends.utils.interface_file.'
                'PortInterfaceFile')
    def test_write_port_interface_file(self, mock_port_interface_file):
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

        self.base_os_util.write_port_interface_file(
            interface=netns_interface,
            fixed_ips=fixed_ips,
            mtu=MTU)

        mock_port_interface_file.assert_called_once_with(
            name=netns_interface,
            fixed_ips=fixed_ips,
            mtu=MTU)
        mock_port_interface_file.return_value.write.assert_called_once()
