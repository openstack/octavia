#    Copyright 2015 Hewlett Packard Enterprise Development Company LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from octavia.cmd import haproxy_vrrp_check
from octavia.tests.unit import base


class TestHAproxyVRRPCheckCMD(base.TestCase):

    def setUp(self):
        super(TestHAproxyVRRPCheckCMD, self).setUp()

    @mock.patch('socket.socket')
    def test_health_check(self, mock_socket):
        socket_mock = mock.MagicMock()
        mock_socket.return_value = socket_mock
        recv_mock = mock.MagicMock()
        recv_mock.side_effect = [b'1', Exception('BREAK')]
        socket_mock.recv = recv_mock

        self.assertRaisesRegex(Exception, 'BREAK',
                               haproxy_vrrp_check.health_check,
                               '10.0.0.1')

    @mock.patch('octavia.cmd.haproxy_vrrp_check.health_check')
    @mock.patch('sys.argv')
    @mock.patch('sys.exit')
    def test_main(self, mock_exit, mock_argv, mock_health_check):
        mock_health_check.side_effect = [1, Exception('FAIL')]
        haproxy_vrrp_check.main()
        mock_exit.assert_called_once_with(1)
