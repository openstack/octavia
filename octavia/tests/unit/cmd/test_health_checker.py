# Copyright 2020 Red Hat, Inc.
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
import socket
import struct
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture

from octavia.cmd import health_checker
from octavia.tests.unit import base

CONF = cfg.CONF


class TestHealthCheckerCMD(base.TestCase):

    def setUp(self):
        super(TestHealthCheckerCMD, self).setUp()
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))

    def test_crc32c(self):
        data = b'STRING1234'

        result = health_checker.crc32c(data)

        self.assertEqual(result, 0x30e0e107)

    @mock.patch('random.randint', return_value=42424242)
    def test__sctp_build_init_packet(self, mock_randint):
        expected_packet = bytearray(
            b'\x04\xd2\x16.\x00\x00\x00\x00\x1d9\x96\r\x01\x00\x00\x14:\xde'
            b'h\xb1\x00\x01\xa0\x00\x00\n\xff\xff\x02\x87W\xb2')

        src_port = 1234
        dest_port = 5678
        tag = 987654321

        pkt = health_checker._sctp_build_init_packet(
            src_port, dest_port, tag)

        self.assertEqual(pkt, expected_packet)

        decoded_src_port = struct.unpack_from('!H', pkt, 0)[0]
        decoded_dest_port = struct.unpack_from('!H', pkt, 2)[0]

        self.assertEqual(src_port, decoded_src_port)
        self.assertEqual(dest_port, decoded_dest_port)

        decoded_tag = struct.unpack_from('!L', pkt, 16)[0]

        self.assertEqual(tag, decoded_tag)

        decoded_checksum = struct.unpack_from('!L', pkt, 8)[0]

        # Reset and re-compute checksum
        pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0
        checksum = health_checker.crc32c(pkt)

        self.assertEqual(checksum, decoded_checksum)

    def test__sctp_build_abort_packet(self):
        expected_packet = bytearray(
            b'\x04\xd2\x16.\x02\x93wM3\x83\xbbN\x06\x01\x00\x04')

        src_port = 1234
        dest_port = 5678
        verification_tag = 43218765

        pkt = health_checker._sctp_build_abort_packet(
            src_port, dest_port, verification_tag)

        self.assertEqual(pkt, expected_packet)

        decoded_src_port = struct.unpack_from('!H', pkt, 0)[0]
        decoded_dest_port = struct.unpack_from('!H', pkt, 2)[0]

        self.assertEqual(src_port, decoded_src_port)
        self.assertEqual(dest_port, decoded_dest_port)

        decoded_tag = struct.unpack_from('!L', pkt, 4)[0]

        self.assertEqual(verification_tag, decoded_tag)

        decoded_checksum = struct.unpack_from('!L', pkt, 8)[0]

        # Reset and re-compute checksum
        pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0
        checksum = health_checker.crc32c(pkt)

        self.assertEqual(checksum, decoded_checksum)

    def test__sctp_decode_packet(self):
        # IPv4 INIT ACK packet
        data = (b'\x45\x00\x00\x00\x00\x01\x01\x01'
                b'\x00\x00\xff\x06\x7f\x00\x00\x00'
                b'\x7f\x00\x00\x02\x16.\x04\xd2'
                b'\x02\x93\x77\x4d\x00\x00\x00\x32'
                b'\x02\x00\x00\x16')

        family = socket.AF_INET
        expected_tag = 43218765

        ret = health_checker._sctp_decode_packet(data, family, expected_tag)

        self.assertEqual(ret, 2)  # INIT ACK

        # IPv6 ABORT packet
        data = (b'\x16.\x04\xd2\x02\x93\x77\x4d\x00\x00\x00\x32'
                b'\x06\x00\x00\x16')

        family = socket.AF_INET6
        expected_tag = 43218765

        ret = health_checker._sctp_decode_packet(data, family, expected_tag)

        self.assertEqual(ret, 6)  # ABORT

    def test__sctp_decode_packet_too_short(self):
        # IPv4 packet with different verification tag
        data = (b'\x45\x00\x00\x00\x00\x01')

        family = socket.AF_INET
        expected_tag = 43218765

        ret = health_checker._sctp_decode_packet(data, family, expected_tag)
        self.assertFalse(ret)

    def test__sctp_decode_packet_unexpected(self):
        # IPv4 packet with different verification tag
        data = (b'\x45\x00\x00\x00\x00\x01\x01\x01'
                b'\x00\x00\xff\x06\x7f\x00\x00\x00'
                b'\x7f\x00\x00\x02\x16.\x04\xd2'
                b'\x02\x91\x17\x4d\x00\x00\x00\x32'
                b'\x02\x00\x00\x16')

        family = socket.AF_INET
        expected_tag = 43218765

        ret = health_checker._sctp_decode_packet(data, family, expected_tag)
        self.assertFalse(ret)
