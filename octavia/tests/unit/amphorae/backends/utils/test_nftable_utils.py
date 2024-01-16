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
from unittest import mock

from octavia.amphorae.backends.utils import nftable_utils
from octavia.common import constants as consts
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

        mocked_open = mock.mock_open()
        with mock.patch.object(os, 'fdopen', mocked_open):
            nftable_utils.write_nftable_vip_rules_file(
                'fake-eth2', ['test rule 1', 'test rule 2'])

        mocked_open.assert_called_once_with('fake-fd', 'w')
        mock_open.assert_called_once_with(
            consts.NFT_VIP_RULES_FILE,
            (os.O_WRONLY | os.O_CREAT | os.O_TRUNC),
            (stat.S_IRUSR | stat.S_IWUSR))

        handle = mocked_open()
        handle.write.assert_has_calls([
            mock.call(f'flush chain {consts.NFT_FAMILY} '
                      f'{consts.NFT_VIP_TABLE} {consts.NFT_VIP_CHAIN}\n'),
            mock.call(f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} '
                      '{\n'),
            mock.call(f'  chain {consts.NFT_VIP_CHAIN} {{\n'),
            mock.call('    type filter hook ingress device fake-eth2 '
                      f'priority {consts.NFT_SRIOV_PRIORITY}; policy drop;\n'),
            mock.call('    test rule 1\n'),
            mock.call('    test rule 2\n'),
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
            mock.call('  }\n'),
            mock.call('}\n')
        ])
