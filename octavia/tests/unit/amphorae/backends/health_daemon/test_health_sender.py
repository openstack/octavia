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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.amphorae.backends.health_daemon import health_sender
from octavia.tests.unit import base


IP_PORT = ['192.0.2.10:5555', '192.0.2.10:5555']
KEY = 'TEST'
PORT = random.randrange(1, 9000)
SAMPLE_MSG = {'testkey': 'TEST'}
SAMPLE_MSG_BIN = binascii.unhexlify('78daab562a492d2ec94ead54b252500a710d0e51a'
                                    'a050041b506243538303665356331393731653739'
                                    '39353138313833393465613665373161643938396'
                                    '66639353039343566393537336634616236663833'
                                    '653235646238656437')


class TestHealthSender(base.TestCase):

    def setUp(self):
        super(TestHealthSender, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
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
        self.conf.config(group="health_manager",
                         controller_ip_port_list='')
        sender = health_sender.UDPStatusSender()
        sender.dosend(SAMPLE_MSG)
        sendto_mock.reset_mock()

        # Test IPv4 path
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.20:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('192.0.2.20', 80))]

        sender = health_sender.UDPStatusSender()
        sender.dosend(SAMPLE_MSG)

        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('192.0.2.20', 80))
        sendto_mock.reset_mock()

        # Test IPv6 path
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['2001:0db8::f00d:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:db8::f00d', 80, 0, 0))]

        sender = health_sender.UDPStatusSender()

        sender.dosend(SAMPLE_MSG)

        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('2001:db8::f00d', 80, 0, 0))

        sendto_mock.reset_mock()

        # Test IPv6 link-local address path
        self.conf.config(
            group="health_manager",
            controller_ip_port_list=['fe80::00ff:fe00:cafe%eth0:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('fe80::ff:fe00:cafe', 80, 0, 2))]

        sender = health_sender.UDPStatusSender()

        sender.dosend(SAMPLE_MSG)

        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('fe80::ff:fe00:cafe', 80, 0, 2))

        sendto_mock.reset_mock()

        # Test socket error
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['2001:0db8::f00d:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:db8::f00d', 80, 0, 0))]
        socket_mock.sendto.side_effect = socket.error

        sender = health_sender.UDPStatusSender()

        # Should not raise an exception
        sender.dosend(SAMPLE_MSG)

        # Test an controller_ip_port_list update
        sendto_mock.reset_mock()
        mock_getaddrinfo.reset_mock()
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.20:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('192.0.2.20', 80))]
        sender = health_sender.UDPStatusSender()
        sender.dosend(SAMPLE_MSG)
        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('192.0.2.20', 80))
        mock_getaddrinfo.assert_called_once_with('192.0.2.20', '80',
                                                 0, socket.SOCK_DGRAM)
        sendto_mock.reset_mock()
        mock_getaddrinfo.reset_mock()

        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.21:81'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('192.0.2.21', 81))]
        sender.dosend(SAMPLE_MSG)
        mock_getaddrinfo.assert_called_once_with('192.0.2.21', '81',
                                                 0, socket.SOCK_DGRAM)
        sendto_mock.assert_called_once_with(SAMPLE_MSG_BIN,
                                            ('192.0.2.21', 81))
        sendto_mock.reset_mock()
        mock_getaddrinfo.reset_mock()
