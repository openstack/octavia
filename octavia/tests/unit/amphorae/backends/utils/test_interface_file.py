# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import ipaddress
from unittest import mock

from octavia.amphorae.backends.utils import interface_file
from octavia.common import constants as consts
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


class TestInterfaceFile(base.TestCase):
    def test_vip_interface_file(self):
        netns_interface = 'eth1234'
        MTU = 1450
        VIP_ADDRESS = '192.0.2.2'
        SUBNET_CIDR = '192.0.2.0/24'
        GATEWAY = '192.0.2.1'
        DEST1 = '198.51.100.0/24'
        NEXTHOP = '192.0.2.1'
        VRRP_IP_ADDRESS = '192.10.2.4'
        TOPOLOGY = 'SINGLE'

        cidr = ipaddress.ip_network(SUBNET_CIDR)
        prefixlen = cidr.prefixlen

        vip_interface_file = interface_file.VIPInterfaceFile(
            name=netns_interface,
            mtu=MTU,
            vips=[{
                'ip_address': VIP_ADDRESS,
                'ip_version': cidr.version,
                'prefixlen': prefixlen,
                'gateway': GATEWAY,
                'host_routes': [
                    {'destination': DEST1, 'nexthop': NEXTHOP}
                ],
            }],
            vrrp_info={
                'ip': VRRP_IP_ADDRESS,
                'prefixlen': prefixlen
            },
            fixed_ips=[],
            topology=TOPOLOGY)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.ADDRESS: VRRP_IP_ADDRESS,
                    consts.PREFIXLEN: prefixlen
                },
                {
                    consts.ADDRESS: VIP_ADDRESS,
                    consts.PREFIXLEN: 32,
                }
            ],
            consts.ROUTES: [
                {
                    consts.DST: "0.0.0.0/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK],
                },
                {
                    consts.DST: "0.0.0.0/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK],
                    consts.TABLE: 1
                },
                {
                    consts.DST: cidr.exploded,
                    consts.SCOPE: 'link'
                },
                {
                    consts.DST: cidr.exploded,
                    consts.PREFSRC: VIP_ADDRESS,
                    consts.SCOPE: 'link',
                    consts.TABLE: 1
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.TABLE: 1,
                    consts.FLAGS: [consts.ONLINK]
                }
            ],
            consts.RULES: [
                {
                    consts.SRC: VIP_ADDRESS,
                    consts.SRC_LEN: 32,
                    consts.TABLE: 1
                }
            ],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            vip_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_vip_interface_file_with_fixed_ips(self):
        netns_interface = 'eth1234'
        MTU = 1450
        VIP_ADDRESS = '192.0.2.2'
        FIXED_IP = '10.0.0.1'
        SUBNET_CIDR = '192.0.2.0/24'
        SUBNET2_CIDR = '10.0.0.0/16'
        GATEWAY = '192.0.2.1'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        NEXTHOP = '192.0.2.1'
        NEXTHOP2 = '10.0.1.254'
        VRRP_IP_ADDRESS = '192.10.2.4'
        TOPOLOGY = 'SINGLE'

        cidr = ipaddress.ip_network(SUBNET_CIDR)
        prefixlen = cidr.prefixlen

        cidr2 = ipaddress.ip_network(SUBNET2_CIDR)
        prefixlen2 = cidr2.prefixlen

        vip_interface_file = interface_file.VIPInterfaceFile(
            name=netns_interface,
            mtu=MTU,
            vips=[{
                'ip_address': VIP_ADDRESS,
                'ip_version': cidr.version,
                'prefixlen': prefixlen,
                'gateway': GATEWAY,
                'host_routes': [
                    {'destination': DEST1, 'nexthop': NEXTHOP}
                ],
            }],
            vrrp_info={
                'ip': VRRP_IP_ADDRESS,
                'prefixlen': prefixlen,
            },
            fixed_ips=[{'ip_address': FIXED_IP,
                        'subnet_cidr': SUBNET2_CIDR,
                        'host_routes': [
                            {'destination': DEST2, 'nexthop': NEXTHOP2}
                        ]}],
            topology=TOPOLOGY)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.ADDRESS: VRRP_IP_ADDRESS,
                    consts.PREFIXLEN: prefixlen
                },
                {
                    consts.ADDRESS: VIP_ADDRESS,
                    consts.PREFIXLEN: 32
                },
                {
                    consts.ADDRESS: FIXED_IP,
                    consts.PREFIXLEN: prefixlen2
                },
            ],
            consts.ROUTES: [
                {
                    consts.DST: "0.0.0.0/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK],
                },
                {
                    consts.DST: "0.0.0.0/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK],
                    consts.TABLE: 1
                },
                {
                    consts.DST: cidr.exploded,
                    consts.SCOPE: 'link'
                },
                {
                    consts.DST: cidr.exploded,
                    consts.PREFSRC: VIP_ADDRESS,
                    consts.SCOPE: 'link',
                    consts.TABLE: 1
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.TABLE: 1,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: DEST2,
                    consts.GATEWAY: NEXTHOP2,
                    consts.FLAGS: [consts.ONLINK]
                }
            ],
            consts.RULES: [
                {
                    consts.SRC: VIP_ADDRESS,
                    consts.SRC_LEN: 32,
                    consts.TABLE: 1
                }
            ],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            vip_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_vip_interface_file_dhcp(self):
        netns_interface = 'eth1234'
        MTU = 1450
        VIP_ADDRESS = '192.0.2.2'
        SUBNET_CIDR = '192.0.2.0/24'
        TOPOLOGY = 'SINGLE'

        cidr = ipaddress.ip_network(SUBNET_CIDR)
        prefixlen = cidr.prefixlen

        vip_interface_file = interface_file.VIPInterfaceFile(
            name=netns_interface,
            mtu=MTU,
            vips=[{
                'ip_address': VIP_ADDRESS,
                'ip_version': cidr.version,
                'prefixlen': prefixlen,
                'gateway': None,
                'host_routes': [],
            }],
            vrrp_info=None,
            fixed_ips=[],
            topology=TOPOLOGY)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.DHCP: True
                }, {
                    consts.ADDRESS: VIP_ADDRESS,
                    consts.PREFIXLEN: 32,
                }
            ],
            consts.ROUTES: [
                {
                    consts.DST: cidr.exploded,
                    consts.SCOPE: 'link',
                },
                {
                    consts.DST: cidr.exploded,
                    consts.PREFSRC: VIP_ADDRESS,
                    consts.SCOPE: 'link',
                    consts.TABLE: 1
                }
            ],
            consts.RULES: [
                {
                    consts.SRC: VIP_ADDRESS,
                    consts.SRC_LEN: 32,
                    consts.TABLE: 1
                }
            ],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            vip_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_vip_interface_file_active_standby(self):
        netns_interface = 'eth1234'
        MTU = 1450
        VIP_ADDRESS = '192.0.2.2'
        SUBNET_CIDR = '192.0.2.0/24'
        GATEWAY = '192.0.2.1'
        VRRP_IP_ADDRESS = '192.10.2.4'
        TOPOLOGY = 'ACTIVE_STANDBY'

        cidr = ipaddress.ip_network(SUBNET_CIDR)
        prefixlen = cidr.prefixlen

        vip_interface_file = interface_file.VIPInterfaceFile(
            name=netns_interface,
            mtu=MTU,
            vips=[{
                'ip_address': VIP_ADDRESS,
                'ip_version': cidr.version,
                'prefixlen': prefixlen,
                'gateway': GATEWAY,
                'host_routes': [],
            }],
            vrrp_info={
                'ip': VRRP_IP_ADDRESS,
                'prefixlen': prefixlen
            },
            fixed_ips=[],
            topology=TOPOLOGY)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.ADDRESS: VRRP_IP_ADDRESS,
                    consts.PREFIXLEN: prefixlen
                },
                {
                    consts.ADDRESS: VIP_ADDRESS,
                    consts.PREFIXLEN: 32,
                    consts.OCTAVIA_OWNED: False
                }
            ],
            consts.ROUTES: [
                {
                    consts.DST: "0.0.0.0/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK],
                },
                {
                    consts.DST: SUBNET_CIDR,
                    consts.PREFSRC: VIP_ADDRESS,
                    consts.SCOPE: 'link'
                }
            ],
            consts.RULES: [],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            vip_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_vip_interface_file_ipv6(self):
        netns_interface = 'eth1234'
        MTU = 1450
        VIP_ADDRESS = '2001:db8::7'
        SUBNET_CIDR = '2001:db8::/64'
        GATEWAY = '2001:db8::1'
        DEST1 = '2001:db8:2::/64'
        NEXTHOP = '2001:db8:2::1'
        VRRP_IP_ADDRESS = '2001:db8::42'
        TOPOLOGY = 'SINGLE'

        cidr = ipaddress.ip_network(SUBNET_CIDR)
        prefixlen = cidr.prefixlen

        vip_interface_file = interface_file.VIPInterfaceFile(
            name=netns_interface,
            mtu=MTU,
            vips=[{
                'ip_address': VIP_ADDRESS,
                'ip_version': cidr.version,
                'prefixlen': prefixlen,
                'gateway': GATEWAY,
                'host_routes': [
                    {'destination': DEST1, 'nexthop': NEXTHOP}
                ],
            }],
            vrrp_info={
                'ip': VRRP_IP_ADDRESS,
                'prefixlen': prefixlen,
            },
            fixed_ips=[],
            topology=TOPOLOGY)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.ADDRESS: VRRP_IP_ADDRESS,
                    consts.PREFIXLEN: prefixlen
                },
                {
                    consts.ADDRESS: VIP_ADDRESS,
                    consts.PREFIXLEN: 128
                }
            ],
            consts.ROUTES: [
                {
                    consts.DST: "::/0",
                    consts.GATEWAY: GATEWAY,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: "::/0",
                    consts.GATEWAY: GATEWAY,
                    consts.TABLE: 1,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: cidr.exploded,
                    consts.SCOPE: 'link',
                },
                {
                    consts.DST: cidr.exploded,
                    consts.PREFSRC: VIP_ADDRESS,
                    consts.SCOPE: 'link',
                    consts.TABLE: 1
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.FLAGS: [consts.ONLINK]
                },
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP,
                    consts.TABLE: 1,
                    consts.FLAGS: [consts.ONLINK]
                }
            ],
            consts.RULES: [
                {
                    consts.SRC: VIP_ADDRESS,
                    consts.SRC_LEN: 128,
                    consts.TABLE: 1
                }
            ],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            vip_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_port_interface_file(self):
        netns_interface = 'eth1234'
        FIXED_IP = '192.0.2.2'
        SUBNET_CIDR = '192.0.2.0/24'
        DEST1 = '198.51.100.0/24'
        DEST2 = '203.0.113.0/24'
        DEST3 = 'fd01::/64'
        NEXTHOP = '192.0.2.1'
        NEXTHOP2 = '2001:db7::8'
        MTU = 1450
        FIXED_IP_IPV6 = '2001:0db8:0000:0000:0000:0000:0000:0001'
        SUBNET_CIDR_IPV6 = '2001:db8::/64'
        fixed_ips = [{'ip_address': FIXED_IP,
                      'subnet_cidr': SUBNET_CIDR,
                      'host_routes': [
                          {'destination': DEST1, 'nexthop': NEXTHOP},
                          {'destination': DEST2, 'nexthop': NEXTHOP}
                      ]},
                     {'ip_address': FIXED_IP_IPV6,
                      'subnet_cidr': SUBNET_CIDR_IPV6,
                      'host_routes': [
                          {'destination': DEST3, 'nexthop': NEXTHOP2}
                      ]},
                     ]

        port_interface_file = interface_file.PortInterfaceFile(
            name=netns_interface,
            fixed_ips=fixed_ips,
            mtu=MTU)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [
                {
                    consts.ADDRESS: FIXED_IP,
                    consts.PREFIXLEN: (
                        ipaddress.ip_network(SUBNET_CIDR).prefixlen
                    )
                },
                {
                    consts.ADDRESS: FIXED_IP_IPV6,
                    consts.PREFIXLEN: (
                        ipaddress.ip_network(SUBNET_CIDR_IPV6).prefixlen
                    )
                }
            ],
            consts.ROUTES: [
                {
                    consts.DST: DEST1,
                    consts.GATEWAY: NEXTHOP
                },
                {
                    consts.DST: DEST2,
                    consts.GATEWAY: NEXTHOP
                },
                {
                    consts.DST: DEST3,
                    consts.GATEWAY: NEXTHOP2
                }
            ],
            consts.RULES: [],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }, {
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }, {
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            port_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_port_interface_file_dhcp(self):
        netns_interface = 'eth1234'
        MTU = 1450

        port_interface_file = interface_file.PortInterfaceFile(
            name=netns_interface,
            fixed_ips=None,
            mtu=MTU)

        expected_dict = {
            consts.NAME: netns_interface,
            consts.MTU: MTU,
            consts.ADDRESSES: [{
                consts.DHCP: True,
                consts.IPV6AUTO: True,
            }],
            consts.ROUTES: [],
            consts.RULES: [],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv4 "
                        "{}".format(netns_interface))
                }, {
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh add ipv6 "
                        "{}".format(netns_interface))
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv4 "
                        "{}".format(netns_interface))
                }, {
                    consts.COMMAND: (
                        "/usr/local/bin/lvs-masquerade.sh delete ipv6 "
                        "{}".format(netns_interface))
                }]
            }
        }

        with mock.patch('os.open'), mock.patch('os.fdopen'), mock.patch(
                'octavia.amphorae.backends.utils.interface_file.'
                'InterfaceFile.dump') as mock_dump:
            port_interface_file.write()

            mock_dump.assert_called_once()

            args = mock_dump.mock_calls[0][1]
            test_utils.assert_interface_files_equal(
                self, expected_dict, args[0])

    def test_from_file(self):
        filename = 'interface.json'
        content = ('{"addresses": [\n'
                   '{"address": "10.0.0.181",\n'
                   '"prefixlen": 26}\n'
                   '],\n'
                   '"mtu": 1450,\n'
                   '"if_type": "mytype",\n'
                   '"name": "eth1",\n'
                   '"routes": [\n'
                   '{"dst": "0.0.0.0/0",\n'
                   '"gateway": "10.0.0.129",\n'
                   '"onlink": true}\n'
                   '],\n'
                   '"rules": [\n'
                   '{"src": "10.0.0.157",\n'
                   '"src_len": 32,\n'
                   '"table": 1}\n'
                   '],\n'
                   '"scripts": {\n'
                   '"down": [\n'
                   '{"command": "script-down"}\n'
                   '], "up": [ \n'
                   '{"command": "script-up"}\n'
                   ']}}\n')

        self.useFixture(
            test_utils.OpenFixture(filename,
                                   contents=content))

        iface = interface_file.InterfaceFile.from_file(filename)

        expected_dict = {
            consts.NAME: "eth1",
            consts.IF_TYPE: "mytype",
            consts.MTU: 1450,
            consts.ADDRESSES: [{
                consts.ADDRESS: "10.0.0.181",
                consts.PREFIXLEN: 26
            }],
            consts.ROUTES: [{
                consts.DST: "0.0.0.0/0",
                consts.GATEWAY: "10.0.0.129",
                consts.FLAGS: [consts.ONLINK]
            }],
            consts.RULES: [{
                consts.SRC: "10.0.0.157",
                consts.SRC_LEN: 32,
                consts.TABLE: 1
            }],
            consts.SCRIPTS: {
                consts.IFACE_UP: [{
                    consts.COMMAND: "script-up"
                }],
                consts.IFACE_DOWN: [{
                    consts.COMMAND: "script-down"
                }]
            }
        }

        self.assertEqual(expected_dict[consts.NAME], iface.name)
        self.assertEqual(expected_dict[consts.MTU], iface.mtu)
        test_utils.assert_address_lists_equal(
            self, expected_dict[consts.ADDRESSES], iface.addresses)
        test_utils.assert_rule_lists_equal(
            self, expected_dict[consts.RULES], iface.rules)
        test_utils.assert_script_lists_equal(
            self, expected_dict[consts.SCRIPTS], iface.scripts)
