#    Copyright 2015 Hewlett-Packard Development Company, L.P.
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

import binascii
import random
import socket

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import six

from octavia.amphorae.backends.health_daemon import health_sender
from octavia.tests.unit import base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

IP = '192.0.2.15'
IP_PORT = '192.0.2.10:5555', '192.0.2.10:5555'
KEY = 'TEST'
PORT = random.randrange(1, 9000)
SAMPLE_MSG = {'testkey': 'TEST'}
SAMPLE_MSG_BIN = binascii.unhexlify('78daab562a492d2ec94ead54b252500a710d0e5'
                                    '1aa050041b506245806e5c1971e79951818394e'
                                    'a6e71ad989ff950945f9573f4ab6f83e25db8ed7')


class TestHealthSender(base.TestCase):

    def setUp(self):
        super(TestHealthSender, self).setUp()
        self.conf = oslo_fixture.Config(cfg.CONF)
        self.conf.config(group="health_manager",
                         controller_ip_port_list=IP_PORT)
        self.conf.config(group="health_manager",
                         heartbeat_key=KEY)

    @mock.patch('socket.getaddrinfo')
    @mock.patch('socket.socket')
    def test_sender(self, mock_socket, mock_getaddrinfo):
        socket_mock = mock.MagicMock()
        mock_socket.return_value = socket_mock
        sendto_mock = mock.MagicMock()
        socket_mock.sendto = sendto_mock

        # Test when no addresses are returned
        mock_getaddrinfo.return_value = []
        sender = health_sender.UDPStatusSender()
        sender.dosend(SAMPLE_MSG)

        # Test IPv4 path
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('192.0.2.20', 80))]
        sendto_mock.reset_mock()

        sender = health_sender.UDPStatusSender()
        sender.dosend(SAMPLE_MSG)

        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('192.0.2.20', 80))

        sendto_mock.reset_mock()

        # Test IPv6 path
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:0DB8::F00D', 80))]

        sender = health_sender.UDPStatusSender()

        sender.dosend(SAMPLE_MSG)

        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('2001:0DB8::F00D', 80))

        sendto_mock.reset_mock()

        # Test invalid address family

        mock_getaddrinfo.return_value = [(socket.AF_UNIX,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:0DB8::F00D', 80))]

        sender = health_sender.UDPStatusSender()

        sender.dosend(SAMPLE_MSG)

        self.assertFalse(sendto_mock.called)

        sendto_mock.reset_mock()

        # Test socket error
        socket_mock.sendto.side_effect = socket.error

        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:0DB8::F00D', 80))]

        sender = health_sender.UDPStatusSender()

        # Should not raise an exception
        sender.dosend(SAMPLE_MSG)
