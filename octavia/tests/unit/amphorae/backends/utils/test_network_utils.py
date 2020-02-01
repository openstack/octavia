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
from unittest import mock

from octavia.amphorae.backends.utils import network_utils
from octavia.common import exceptions
from octavia.tests.common import sample_network_data
import octavia.tests.unit.base as base


class TestNetworkUtils(base.TestCase):

    def setUp(self):
        super(TestNetworkUtils, self).setUp()

    def test_find_interface(self):
        FAKE_INTERFACE = 'fake0'
        IPV4_ADDRESS = '203.0.113.55'
        BROADCAST_ADDRESS = '203.0.113.55'
        IPV6_ADDRESS = '2001:db8::55'
        SAMPLE_IPV4_ADDR = sample_network_data.create_iproute_ipv4_address(
            IPV4_ADDRESS, BROADCAST_ADDRESS, FAKE_INTERFACE)
        SAMPLE_IPV6_ADDR = sample_network_data.create_iproute_ipv6_address(
            IPV6_ADDRESS, FAKE_INTERFACE)
        SAMPLE_INTERFACE = sample_network_data.create_iproute_interface(
            FAKE_INTERFACE)
        BROKEN_INTERFACE = [{'attrs': []}]

        mock_ip_addr = mock.MagicMock()
        mock_rtnl_api = mock.MagicMock()
        mock_rtnl_api.get_addr.side_effect = [[], SAMPLE_IPV4_ADDR,
                                              SAMPLE_IPV6_ADDR,
                                              SAMPLE_IPV6_ADDR]
        mock_rtnl_api.get_links.side_effect = [SAMPLE_INTERFACE,
                                               SAMPLE_INTERFACE,
                                               BROKEN_INTERFACE]

        # Test no match
        IPV4_ADDRESS = '203.0.113.55'
        mock_ip_addr.version = 4

        self.assertIsNone(network_utils._find_interface(IPV4_ADDRESS,
                                                        mock_rtnl_api,
                                                        IPV4_ADDRESS))

        # Test with IPv4 address
        mock_rtnl_api.reset_mock()
        mock_ip_addr.version = 4

        result = network_utils._find_interface(IPV4_ADDRESS, mock_rtnl_api,
                                               IPV4_ADDRESS)

        self.assertEqual(FAKE_INTERFACE, result)
        mock_rtnl_api.get_addr.assert_called_once_with(address=IPV4_ADDRESS)
        mock_rtnl_api.get_links.assert_called_once_with(2)

        # Test with IPv6 address
        mock_rtnl_api.reset_mock()
        mock_ip_addr.version = 6

        result = network_utils._find_interface(IPV6_ADDRESS, mock_rtnl_api,
                                               IPV6_ADDRESS)

        self.assertEqual(FAKE_INTERFACE, result)
        mock_rtnl_api.get_addr.assert_called_once_with(address=IPV6_ADDRESS)
        mock_rtnl_api.get_links.assert_called_once_with(2)

        # Test with a broken interface
        mock_rtnl_api.reset_mock()
        mock_ip_addr.version = 6

        self.assertIsNone(network_utils._find_interface(IPV6_ADDRESS,
                                                        mock_rtnl_api,
                                                        IPV6_ADDRESS))
        mock_rtnl_api.get_addr.assert_called_once_with(address=IPV6_ADDRESS)
        mock_rtnl_api.get_links.assert_called_once_with(2)

    @mock.patch('octavia.amphorae.backends.utils.network_utils.'
                '_find_interface')
    @mock.patch('pyroute2.IPRoute', create=True)
    @mock.patch('pyroute2.NetNS', create=True)
    def test_get_interface_name(self, mock_netns, mock_ipr, mock_find_int):
        FAKE_INTERFACE = 'fake0'
        FAKE_NETNS = 'fake-ns'
        IPV4_ADDRESS = '203.0.113.64'

        mock_ipr_enter_obj = mock.MagicMock()
        mock_ipr_obj = mock.MagicMock()
        mock_ipr_obj.__enter__.return_value = mock_ipr_enter_obj
        mock_ipr.return_value = mock_ipr_obj

        mock_netns_enter_obj = mock.MagicMock()
        mock_netns_obj = mock.MagicMock()
        mock_netns_obj.__enter__.return_value = mock_netns_enter_obj
        mock_netns.return_value = mock_netns_obj

        mock_find_int.side_effect = [FAKE_INTERFACE, FAKE_INTERFACE, None]

        # Test a bogus IP address
        self.assertRaises(exceptions.InvalidIPAddress,
                          network_utils.get_interface_name, 'not an IP', None)

        # Test with no network namespace
        result = network_utils.get_interface_name(IPV4_ADDRESS)

        self.assertEqual(FAKE_INTERFACE, result)
        mock_ipr.assert_called_once_with()
        mock_find_int.assert_called_once_with(IPV4_ADDRESS, mock_ipr_enter_obj,
                                              IPV4_ADDRESS)

        # Test with network namespace
        mock_ipr.reset_mock()
        mock_find_int.reset_mock()

        result = network_utils.get_interface_name(IPV4_ADDRESS,
                                                  net_ns=FAKE_NETNS)
        self.assertEqual(FAKE_INTERFACE, result)
        mock_netns.assert_called_once_with(FAKE_NETNS)
        mock_find_int.assert_called_once_with(IPV4_ADDRESS,
                                              mock_netns_enter_obj,
                                              IPV4_ADDRESS)

        # Test no interface found
        mock_ipr.reset_mock()
        mock_find_int.reset_mock()

        self.assertRaises(
            exceptions.NotFound, network_utils.get_interface_name,
            IPV4_ADDRESS, net_ns=FAKE_NETNS)
