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
from binascii import a2b_hex
import socket
from struct import pack
from unittest import mock

from octavia.amphorae.backends.utils import ip_advertisement
from octavia.common import constants
import octavia.tests.unit.base as base


class TestIPAdvertisement(base.TestCase):

    def setUp(self):
        super(TestIPAdvertisement, self).setUp()

    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace')
    @mock.patch('socket.AF_PACKET', create=True)
    @mock.patch('socket.socket')
    def test_garp(self, mock_socket, mock_socket_packet, mock_netns):
        ARP_ETHERTYPE = 0x0806
        EXPECTED_PACKET_DATA = (b'\xff\xff\xff\xff\xff\xff\x00\x00^\x00S3\x08'
                                b'\x06\x00\x01\x08\x00\x06\x04\x00\x01\x00'
                                b'\x00^\x00S3\xcb\x00q\x02\xff\xff\xff\xff'
                                b'\xff\xff\xcb\x00q\x02')
        FAKE_INTERFACE = 'fake0'
        FAKE_MAC = '00005E005333'
        FAKE_NETNS = 'fake_netns'

        mock_garp_socket = mock.MagicMock()
        mock_garp_socket.getsockname.return_value = [None, None, None, None,
                                                     a2b_hex(FAKE_MAC)]
        mock_socket.return_value = mock_garp_socket

        # Test with a network namespace
        ip_advertisement.garp(FAKE_INTERFACE, '203.0.113.2', net_ns=FAKE_NETNS)

        mock_netns.assert_called_once_with(FAKE_NETNS)
        mock_garp_socket.bind.assert_called_once_with((FAKE_INTERFACE,
                                                      ARP_ETHERTYPE))
        mock_garp_socket.getsockname.assert_called_once_with()
        mock_garp_socket.send.assert_called_once_with(EXPECTED_PACKET_DATA)
        mock_garp_socket.close.assert_called_once_with()

        # Test without a network namespace
        mock_netns.reset_mock()
        mock_garp_socket.reset_mock()
        ip_advertisement.garp(FAKE_INTERFACE, '203.0.113.2')

        mock_netns.assert_not_called()
        mock_garp_socket.bind.assert_called_once_with((FAKE_INTERFACE,
                                                      ARP_ETHERTYPE))
        mock_garp_socket.getsockname.assert_called_once_with()
        mock_garp_socket.send.assert_called_once_with(EXPECTED_PACKET_DATA)
        mock_garp_socket.close.assert_called_once_with()

    def test_calculate_icmpv6_checksum(self):
        TEST_PACKET1 = (
            b'\x01\r\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x003\xff\x02'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00'
            b'\x00\x00:\x00 \x88\x00\x00\x00 \x01\r\xb8\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x003\xff\x02\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00:\x00')
        TEST_PACKET2 = (
            b'\x01\r\xb8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x003\xff\x02'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00'
            b'\x00\x00:\x00 \x88\x00\x00\x00 \x01\r\xb8\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x003\xff\x02\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00:\x00\x01')

        self.assertEqual(
            35645, ip_advertisement.calculate_icmpv6_checksum(TEST_PACKET1))
        self.assertEqual(
            35389, ip_advertisement.calculate_icmpv6_checksum(TEST_PACKET2))

    @mock.patch('fcntl.ioctl')
    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace')
    @mock.patch('socket.socket')
    def test_neighbor_advertisement(self, mock_socket, mock_netns, mock_ioctl):
        ALL_NODES_ADDR = 'ff02::1'
        EXPECTED_PACKET_DATA = (b'\x88\x00\x1dk\xa0\x00\x00\x00 \x01\r\xb8\x00'
                                b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x003'
                                b'\x02\x01')
        FAKE_INTERFACE = 'fake0'
        FAKE_MAC = '00005E005333'
        FAKE_NETNS = 'fake_netns'
        ICMPV6_PROTO = socket.getprotobyname(constants.IPV6_ICMP)
        SIOCGIFHWADDR = 0x8927
        SOURCE_IP = '2001:db8::33'

        mock_na_socket = mock.MagicMock()
        mock_socket.return_value = mock_na_socket
        mock_ioctl.return_value = a2b_hex(FAKE_MAC)

        # Test with a network namespace
        ip_advertisement.neighbor_advertisement(FAKE_INTERFACE, SOURCE_IP,
                                                net_ns=FAKE_NETNS)

        mock_netns.assert_called_once_with(FAKE_NETNS)
        mock_socket.assert_called_once_with(socket.AF_INET6, socket.SOCK_RAW,
                                            ICMPV6_PROTO)
        mock_na_socket.setsockopt.assert_called_once_with(
            socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)
        mock_na_socket.bind.assert_called_once_with((SOURCE_IP, 0))
        mock_ioctl.assert_called_once_with(
            mock_na_socket.fileno(), SIOCGIFHWADDR,
            pack('256s', bytes(FAKE_INTERFACE, 'utf-8')))
        mock_na_socket.sendto.assert_called_once_with(
            EXPECTED_PACKET_DATA, (ALL_NODES_ADDR, 0, 0, 0))
        mock_na_socket.close.assert_called_once_with()

        # Test without a network namespace
        mock_na_socket.reset_mock()
        mock_netns.reset_mock()
        mock_ioctl.reset_mock()
        mock_socket.reset_mock()

        ip_advertisement.neighbor_advertisement(FAKE_INTERFACE, SOURCE_IP)

        mock_netns.assert_not_called()
        mock_socket.assert_called_once_with(socket.AF_INET6, socket.SOCK_RAW,
                                            ICMPV6_PROTO)
        mock_na_socket.setsockopt.assert_called_once_with(
            socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)
        mock_na_socket.bind.assert_called_once_with((SOURCE_IP, 0))
        mock_ioctl.assert_called_once_with(
            mock_na_socket.fileno(), SIOCGIFHWADDR,
            pack('256s', bytes(FAKE_INTERFACE, 'utf-8')))
        mock_na_socket.sendto.assert_called_once_with(
            EXPECTED_PACKET_DATA, (ALL_NODES_ADDR, 0, 0, 0))
        mock_na_socket.close.assert_called_once_with()

    @mock.patch('octavia.common.utils.is_ipv6')
    @mock.patch('octavia.amphorae.backends.utils.ip_advertisement.garp')
    @mock.patch('octavia.amphorae.backends.utils.ip_advertisement.'
                'neighbor_advertisement')
    def test_send_ip_advertisement(self, mock_na, mock_garp, mock_is_ipv6):
        FAKE_INTERFACE = 'fake0'
        FAKE_NETNS = 'fake_netns'
        IPV4_ADDRESS = '203.0.113.9'
        IPV6_ADDRESS = '2001:db8::33'

        mock_is_ipv6.side_effect = [mock.DEFAULT, mock.DEFAULT, False]

        # Test IPv4 advertisement
        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, IPV4_ADDRESS)

        mock_garp.assert_called_once_with(FAKE_INTERFACE, IPV4_ADDRESS, None)
        mock_na.assert_not_called()

        # Test IPv4 advertisement with a network namespace
        mock_garp.reset_mock()
        mock_na.reset_mock()

        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, IPV4_ADDRESS,
                                               net_ns=FAKE_NETNS)

        mock_garp.assert_called_once_with(FAKE_INTERFACE, IPV4_ADDRESS,
                                          FAKE_NETNS)
        mock_na.assert_not_called()

        # Test IPv6 advertisement
        mock_garp.reset_mock()
        mock_na.reset_mock()

        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, IPV6_ADDRESS)

        mock_garp.assert_not_called()
        mock_na.assert_called_once_with(FAKE_INTERFACE, IPV6_ADDRESS, None)

        # Test IPv6 advertisement with a network namespace
        mock_garp.reset_mock()
        mock_na.reset_mock()

        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, IPV6_ADDRESS,
                                               net_ns=FAKE_NETNS)

        mock_garp.assert_not_called()
        mock_na.assert_called_once_with(FAKE_INTERFACE, IPV6_ADDRESS,
                                        FAKE_NETNS)

        # Test bogus IP
        mock_garp.reset_mock()
        mock_na.reset_mock()

        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, 'not an IP')

        mock_garp.assert_not_called()
        mock_na.assert_not_called()

        # Test unknown IP version
        mock_garp.reset_mock()
        mock_na.reset_mock()

        ip_advertisement.send_ip_advertisement(FAKE_INTERFACE, IPV6_ADDRESS)

        mock_garp.assert_not_called()
        mock_na.assert_not_called()
