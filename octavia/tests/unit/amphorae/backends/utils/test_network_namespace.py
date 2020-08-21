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
import random
from unittest import mock

from octavia.amphorae.backends.utils import network_namespace
from octavia.tests.common import utils as test_utils
import octavia.tests.unit.base as base


class TestNetworkNamespace(base.TestCase):

    def setUp(self):
        super().setUp()

    @mock.patch('ctypes.get_errno')
    @mock.patch('ctypes.CDLL')
    def test_error_handler(self, mock_cdll, mock_get_errno):
        FAKE_NETNS = 'fake-netns'
        netns = network_namespace.NetworkNamespace(FAKE_NETNS)

        # Test result 0
        netns._error_handler(0, None, None)

        mock_get_errno.assert_not_called()

        # Test result -1
        mock_get_errno.reset_mock()

        self.assertRaises(OSError, netns._error_handler, -1, None, None)

        mock_get_errno.assert_called_once_with()

    @mock.patch('os.getpid')
    @mock.patch('ctypes.CDLL')
    def test_init(self, mock_cdll, mock_getpid):
        FAKE_NETNS = 'fake-netns'
        FAKE_PID = random.randrange(100000)
        mock_cdll_obj = mock.MagicMock()
        mock_cdll.return_value = mock_cdll_obj
        mock_getpid.return_value = FAKE_PID
        expected_current_netns = '/proc/{pid}/ns/net'.format(pid=FAKE_PID)
        expected_target_netns = '/var/run/netns/{netns}'.format(
            netns=FAKE_NETNS)

        netns = network_namespace.NetworkNamespace(FAKE_NETNS)

        self.assertEqual(expected_current_netns, netns.current_netns)
        self.assertEqual(expected_target_netns, netns.target_netns)
        self.assertEqual(mock_cdll_obj.setns, netns.set_netns)
        self.assertEqual(netns.set_netns.errcheck, netns._error_handler)

    @mock.patch('os.getpid')
    @mock.patch('ctypes.CDLL')
    def test_enter(self, mock_cdll, mock_getpid):
        CLONE_NEWNET = 0x40000000
        FAKE_NETNS = 'fake-netns'
        FAKE_PID = random.randrange(100000)
        current_netns_fd = random.randrange(100000)
        target_netns_fd = random.randrange(100000)
        mock_getpid.return_value = FAKE_PID
        mock_cdll_obj = mock.MagicMock()
        mock_cdll.return_value = mock_cdll_obj
        expected_current_netns = '/proc/{pid}/ns/net'.format(pid=FAKE_PID)
        expected_target_netns = '/var/run/netns/{netns}'.format(
            netns=FAKE_NETNS)

        netns = network_namespace.NetworkNamespace(FAKE_NETNS)

        current_mock_open = self.useFixture(
            test_utils.OpenFixture(expected_current_netns)).mock_open
        current_mock_open.return_value = current_netns_fd

        target_mock_open = self.useFixture(
            test_utils.OpenFixture(expected_target_netns)).mock_open
        handle = target_mock_open()
        handle.fileno.return_value = target_netns_fd

        netns.__enter__()

        self.assertEqual(current_netns_fd, netns.current_netns_fd)
        netns.set_netns.assert_called_once_with(target_netns_fd, CLONE_NEWNET)

    @mock.patch('os.getpid')
    @mock.patch('ctypes.CDLL')
    def test_exit(self, mock_cdll, mock_getpid):
        CLONE_NEWNET = 0x40000000
        FAKE_NETNS = 'fake-netns'
        FAKE_PID = random.randrange(100000)
        current_netns_fileno = random.randrange(100000)
        mock_getpid.return_value = FAKE_PID
        mock_cdll_obj = mock.MagicMock()
        mock_cdll.return_value = mock_cdll_obj
        mock_current_netns_fd = mock.MagicMock()
        mock_current_netns_fd.fileno.return_value = current_netns_fileno

        netns = network_namespace.NetworkNamespace(FAKE_NETNS)

        netns.current_netns_fd = mock_current_netns_fd

        netns.__exit__()

        netns.set_netns.assert_called_once_with(current_netns_fileno,
                                                CLONE_NEWNET)
        mock_current_netns_fd.close.assert_called_once_with()
