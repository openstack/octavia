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
import struct
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.amphorae.backends.health_daemon import health_sender
from octavia.common import constants
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


class BaseTestStatusSender(base.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="health_manager",
                         controller_ip_port_list=IP_PORT)
        self.conf.config(group="health_manager",
                         heartbeat_key=KEY)

    def _test_sender(self, mock_getaddrinfo):

        # Test when no addresses are returned
        self.conf.config(group="health_manager",
                         controller_ip_port_list='')
        sender = self.tested_class()
        sender.dosend(SAMPLE_MSG_BIN)
        self._reset_mocks()

        # Test IPv4 path
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.20:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('192.0.2.20', 80))]

        sender = self.tested_class()
        sender.dosend(SAMPLE_MSG_BIN)

        self._check_sendto(SAMPLE_MSG_BIN, ('192.0.2.20', 80))
        self._reset_mocks()

        # Test IPv6 path
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['2001:0db8::f00d:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('2001:db8::f00d', 80, 0, 0))]

        sender = self.tested_class()

        sender.dosend(SAMPLE_MSG_BIN)

        self._check_sendto(SAMPLE_MSG_BIN, ('2001:db8::f00d', 80, 0, 0))
        self._reset_mocks()

        # Test IPv6 path enclosed within square brackets ("[" and "]").
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['[2001:0db8::f00d]:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          socket.SOCK_DGRAM,
                                          socket.IPPROTO_UDP,
                                          '',
                                          ('2001:db8::f00d', 80, 0, 0))]

        sender = self.tested_class()

        sender.dosend(SAMPLE_MSG_BIN)

        self._check_sendto(SAMPLE_MSG_BIN, ('2001:db8::f00d', 80, 0, 0))
        self._reset_mocks()

        # Test IPv6 link-local address path
        self.conf.config(
            group="health_manager",
            controller_ip_port_list=['fe80::00ff:fe00:cafe%eth0:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('fe80::ff:fe00:cafe', 80, 0, 2))]

        sender = self.tested_class()

        sender.dosend(SAMPLE_MSG_BIN)

        self._check_sendto(SAMPLE_MSG_BIN, ('fe80::ff:fe00:cafe', 80, 0, 2))
        self._reset_mocks()

        # Test socket error
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['2001:0db8::f00d:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET6,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('2001:db8::f00d', 80, 0, 0))]
        self._set_sendto_side_effect(socket.error)

        sender = self.tested_class()

        # Should not raise an exception
        sender.dosend(SAMPLE_MSG_BIN)

        # Test an controller_ip_port_list update
        self._reset_mocks()
        mock_getaddrinfo.reset_mock()
        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.20:80'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('192.0.2.20', 80))]
        sender = self.tested_class()
        sender.dosend(SAMPLE_MSG_BIN)
        mock_getaddrinfo.assert_called_once_with('192.0.2.20', '80',
                                                 0, self.socket_type)
        mock_getaddrinfo.reset_mock()
        self._check_sendto(SAMPLE_MSG_BIN, ('192.0.2.20', 80))
        self._reset_mocks()

        self.conf.config(group="health_manager",
                         controller_ip_port_list=['192.0.2.21:81'])
        mock_getaddrinfo.return_value = [(socket.AF_INET,
                                          self.socket_type,
                                          self.socket_proto,
                                          '',
                                          ('192.0.2.21', 81))]
        sender.dosend(SAMPLE_MSG_BIN)
        mock_getaddrinfo.assert_called_once_with('192.0.2.21', '81',
                                                 0, self.socket_type)
        mock_getaddrinfo.reset_mock()
        self._check_sendto(SAMPLE_MSG_BIN, ('192.0.2.21', 81))
        self._reset_mocks()


class TestUDPStatusSender(BaseTestStatusSender):
    tested_class = health_sender.UDPStatusSender
    socket_type = socket.SOCK_DGRAM
    socket_proto = socket.IPPROTO_UDP

    def _check_sendto(self, message, address):
        self.sendto_mock.assert_called_once_with(message, address)

    def _reset_mocks(self):
        self.sendto_mock.reset_mock(side_effect=True)

    def _set_sendto_side_effect(self, side_effect):
        self.sendto_mock.side_effect = side_effect

    @mock.patch('socket.getaddrinfo')
    @mock.patch('socket.socket')
    def test_sender(self, mock_socket, mock_getaddrinfo):
        socket_mock = mock.MagicMock()
        mock_socket.return_value = socket_mock
        self.sendto_mock = mock.MagicMock()
        socket_mock.sendto = self.sendto_mock

        self._test_sender(mock_getaddrinfo)


class TestTCPStatusSender(BaseTestStatusSender):
    tested_class = health_sender.TCPStatusSender
    socket_type = socket.SOCK_STREAM
    socket_proto = socket.IPPROTO_TCP

    def _check_sendto(self, message, address):
        header = struct.pack(">II", constants.AMP_HEARTBEAT_HEADER,
                             len(message) + 8)

        self.connect_mock.assert_called_once_with(address)
        self.sendall_mock.assert_any_call(header + message)

    def _reset_mocks(self):
        self.connect_mock.reset_mock(side_effect=True)
        self.sendall_mock.reset_mock(side_effect=True)

    def _set_sendto_side_effect(self, side_effect):
        self.connect_mock.side_effect = side_effect

    @mock.patch('socket.getaddrinfo')
    @mock.patch('socket.socket')
    def test_sender(self, mock_socket, mock_getaddrinfo):
        socket_mock = mock.MagicMock()
        mock_socket.return_value = socket_mock
        self.connect_mock = mock.MagicMock()
        socket_mock.__enter__.return_value.connect = self.connect_mock
        self.sendall_mock = mock.MagicMock()
        socket_mock.__enter__.return_value.sendall = self.sendall_mock

        self._test_sender(mock_getaddrinfo)


class TestHealthSender(base.TestCase):
    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="health_manager",
                         controller_ip_port_list=IP_PORT)
        self.conf.config(group="health_manager",
                         heartbeat_key=KEY)

    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.TCPStatusSender')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_sender_default_udp(self, mock_udp, mock_tcp):
        tcpsender_mock = mock.MagicMock()
        mock_tcp.return_value = tcpsender_mock
        udpsender_mock = mock.MagicMock()
        mock_udp.return_value = udpsender_mock

        sender = health_sender.StatusSender()
        sender.dosend(SAMPLE_MSG)
        udpsender_mock.dosend.assert_called_once_with(SAMPLE_MSG_BIN)
        tcpsender_mock.dosend.assert_not_called()

    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.TCPStatusSender')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_sender_small(self, mock_udp, mock_tcp):
        tcpsender_mock = mock.MagicMock()
        mock_tcp.return_value = tcpsender_mock
        udpsender_mock = mock.MagicMock()
        mock_udp.return_value = udpsender_mock

        # set threshold to switch to TCP higher than message size
        threshold = len(SAMPLE_MSG_BIN) + 1
        self.conf.config(group="health_manager",
                         heartbeat_use_tcp_threshold=threshold)

        sender = health_sender.StatusSender()
        sender.dosend(SAMPLE_MSG)
        udpsender_mock.dosend.assert_called_once_with(SAMPLE_MSG_BIN)
        tcpsender_mock.dosend.assert_not_called()

    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.TCPStatusSender')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_sender_big(self, mock_udp, mock_tcp):
        tcpsender_mock = mock.MagicMock()
        mock_tcp.return_value = tcpsender_mock
        udpsender_mock = mock.MagicMock()
        mock_udp.return_value = udpsender_mock

        # set threshold to switch to TCP lower than message size
        threshold = len(SAMPLE_MSG_BIN) - 1
        self.conf.config(group="health_manager",
                         heartbeat_use_tcp_threshold=threshold)

        sender = health_sender.StatusSender()
        sender.dosend(SAMPLE_MSG)
        udpsender_mock.dosend.assert_not_called()
        tcpsender_mock.dosend.assert_called_once_with(SAMPLE_MSG_BIN)

    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.TCPStatusSender')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_sender_always_tcp(self, mock_udp, mock_tcp):
        tcpsender_mock = mock.MagicMock()
        mock_tcp.return_value = tcpsender_mock
        udpsender_mock = mock.MagicMock()
        mock_udp.return_value = udpsender_mock

        # set threshold to switch to TCP to 0, i.e. "always use TCP"
        self.conf.config(group="health_manager",
                         heartbeat_use_tcp_threshold=0)

        sender = health_sender.StatusSender()
        sender.dosend(SAMPLE_MSG)
        udpsender_mock.dosend.assert_not_called()
        tcpsender_mock.dosend.assert_called_once_with(SAMPLE_MSG_BIN)

    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.TCPStatusSender')
    @mock.patch('octavia.amphorae.backends.health_daemon.'
                'health_sender.UDPStatusSender')
    def test_sender_always_udp(self, mock_udp, mock_tcp):
        tcpsender_mock = mock.MagicMock()
        mock_tcp.return_value = tcpsender_mock
        udpsender_mock = mock.MagicMock()
        mock_udp.return_value = udpsender_mock

        # set threshold to switch to TCP to -1, i.e. "never use TCP"
        self.conf.config(group="health_manager",
                         heartbeat_use_tcp_threshold=-1)

        sender = health_sender.StatusSender()
        sender.dosend(SAMPLE_MSG)
        udpsender_mock.dosend.assert_called_once_with(SAMPLE_MSG_BIN)
        tcpsender_mock.dosend.assert_not_called()
