# Copyright 2024 Red Hat, Inc. All rights reserved.
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
import os
import stat
import subprocess
from unittest import mock

from octavia_lib.common import constants as lib_consts
from webob import exc

from octavia.amphorae.backends.utils import nftable_utils
from octavia.common import constants as consts
from octavia.common import exceptions
import octavia.tests.unit.base as base


class TestNFTableUtils(base.TestCase):
    @mock.patch('os.open')
    @mock.patch('os.path.isfile')
    def test_write_nftable_vip_rules_file_exists(self, mock_isfile, mock_open):
        """Test when a rules file exists and no new rules

        When an existing rules file is present and we call
        write_nftable_vip_rules_file with no rules, the method should not
        overwrite the existing rules.
        """
        mock_isfile.return_value = True

        nftable_utils.write_nftable_vip_rules_file('fake-eth2', [])

        mock_open.assert_not_called()

    @mock.patch('os.open')
    @mock.patch('os.path.isfile')
    def test_write_nftable_vip_rules_file_rules(self, mock_isfile,
                                                mock_open):
        """Test when a rules file exists and rules are passed in

        This should create a simple rules file with the base chain and rules.
        """
        mock_isfile.return_value = True
        mock_open.return_value = 'fake-fd'

        test_rule_1 = {consts.CIDR: None,
                       consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
                       consts.PORT: 1234}
        test_rule_2 = {consts.CIDR: '192.0.2.0/24',
                       consts.PROTOCOL: consts.VRRP,
                       consts.PORT: 4321}

        mocked_open = mock.mock_open()
        with mock.patch.object(os, 'fdopen', mocked_open):
            nftable_utils.write_nftable_vip_rules_file(
                'fake-eth2', [test_rule_1, test_rule_2])

        mocked_open.assert_called_once_with('fake-fd', 'w')
        mock_open.assert_called_once_with(
            consts.NFT_VIP_RULES_FILE,
            (os.O_WRONLY | os.O_CREAT | os.O_TRUNC),
            (stat.S_IRUSR | stat.S_IWUSR))

        handle = mocked_open()
        handle.write.assert_has_calls([
            mock.call(f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} '
                      '{}\n'),
            mock.call(f'delete table {consts.NFT_FAMILY} '
                      f'{consts.NFT_VIP_TABLE}\n'),
            mock.call(f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} '
                      '{\n'),
            mock.call(f'  chain {consts.NFT_VIP_CHAIN} {{\n'),
            mock.call('    type filter hook ingress device fake-eth2 '
                      f'priority {consts.NFT_SRIOV_PRIORITY}; policy drop;\n'),
            mock.call('      icmp type destination-unreachable accept\n'),
            mock.call('      icmpv6 type { nd-neighbor-solicit, '
                      'nd-router-advert, nd-neighbor-advert, packet-too-big, '
                      'destination-unreachable } accept\n'),
            mock.call('      udp sport 67 udp dport 68 accept\n'),
            mock.call('      udp sport 547 udp dport 546 accept\n'),
            mock.call('      tcp dport 1234 accept\n'),
            mock.call('      ip saddr 192.0.2.0/24 ip protocol 112 accept\n'),
            mock.call('  }\n'),
            mock.call('}\n')
        ])

    @mock.patch('os.open')
    @mock.patch('os.path.isfile')
    def test_write_nftable_vip_rules_file_missing(self, mock_isfile,
                                                  mock_open):
        """Test when a rules file does not exist and no new rules

        This should create a simple rules file with the base chain.
        """
        mock_isfile.return_value = False
        mock_open.return_value = 'fake-fd'

        mocked_open = mock.mock_open()
        with mock.patch.object(os, 'fdopen', mocked_open):
            nftable_utils.write_nftable_vip_rules_file('fake-eth2', [])

        mocked_open.assert_called_once_with('fake-fd', 'w')
        mock_open.assert_called_once_with(
            consts.NFT_VIP_RULES_FILE,
            (os.O_WRONLY | os.O_CREAT | os.O_TRUNC),
            (stat.S_IRUSR | stat.S_IWUSR))

        handle = mocked_open()
        handle.write.assert_has_calls([
            mock.call(f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} '
                      '{\n'),
            mock.call(f'  chain {consts.NFT_VIP_CHAIN} {{\n'),
            mock.call('    type filter hook ingress device fake-eth2 '
                      f'priority {consts.NFT_SRIOV_PRIORITY}; policy drop;\n'),
            mock.call('      icmp type destination-unreachable accept\n'),
            mock.call('      icmpv6 type { nd-neighbor-solicit, '
                      'nd-router-advert, nd-neighbor-advert, packet-too-big, '
                      'destination-unreachable } accept\n'),
            mock.call('      udp sport 67 udp dport 68 accept\n'),
            mock.call('      udp sport 547 udp dport 546 accept\n'),
            mock.call('  }\n'),
            mock.call('}\n')
        ])

    @mock.patch('octavia.common.utils.ip_version')
    def test__build_rule_cmd(self, mock_ip_version):

        mock_ip_version.side_effect = [4, 6, 99]

        cmd = nftable_utils._build_rule_cmd({
            consts.CIDR: '192.0.2.0/24',
            consts.PROTOCOL: lib_consts.PROTOCOL_SCTP,
            consts.PORT: 1234})
        self.assertEqual('ip saddr 192.0.2.0/24 sctp dport 1234 accept', cmd)

        cmd = nftable_utils._build_rule_cmd({
            consts.CIDR: '2001:db8::/32',
            consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
            consts.PORT: 1235})
        self.assertEqual('ip6 saddr 2001:db8::/32 tcp dport 1235 accept', cmd)

        self.assertRaises(exc.HTTPBadRequest, nftable_utils._build_rule_cmd,
                          {consts.CIDR: '192/32',
                           consts.PROTOCOL: lib_consts.PROTOCOL_TCP,
                           consts.PORT: 1237})

        cmd = nftable_utils._build_rule_cmd({
            consts.CIDR: None,
            consts.PROTOCOL: lib_consts.PROTOCOL_UDP,
            consts.PORT: 1236})
        self.assertEqual('udp dport 1236 accept', cmd)

        cmd = nftable_utils._build_rule_cmd({
            consts.CIDR: None,
            consts.PROTOCOL: consts.VRRP,
            consts.PORT: 1237})
        self.assertEqual('ip protocol 112 accept', cmd)

        self.assertRaises(exc.HTTPBadRequest, nftable_utils._build_rule_cmd,
                          {consts.CIDR: None,
                           consts.PROTOCOL: 'bad-protocol',
                           consts.PORT: 1237})

    @mock.patch('octavia.amphorae.backends.utils.network_namespace.'
                'NetworkNamespace')
    @mock.patch('subprocess.check_output')
    def test_load_nftables_file(self, mock_check_output, mock_netns):

        mock_netns.side_effect = [
            mock.DEFAULT,
            subprocess.CalledProcessError(cmd=consts.NFT_CMD, returncode=-1),
            exceptions.AmphoraNetworkConfigException]

        nftable_utils.load_nftables_file()

        mock_netns.assert_called_once_with(consts.AMPHORA_NAMESPACE)
        mock_check_output.assert_called_once_with([
            consts.NFT_CMD, '-o', '-f', consts.NFT_VIP_RULES_FILE],
            stderr=subprocess.STDOUT)

        self.assertRaises(subprocess.CalledProcessError,
                          nftable_utils.load_nftables_file)

        self.assertRaises(exceptions.AmphoraNetworkConfigException,
                          nftable_utils.load_nftables_file)
