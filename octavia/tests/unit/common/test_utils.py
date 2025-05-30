# Copyright 2014,  Doug Wiegley,  A10 Networks.
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
from unittest import mock

from cryptography import fernet
from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.utils as utils
import octavia.tests.unit.base as base


class TestConfig(base.TestCase):

    def test_get_hostname(self):
        self.assertNotEqual(utils.get_hostname(), '')

    def test_is_ipv4(self):
        self.assertTrue(utils.is_ipv4('192.0.2.10'))
        self.assertTrue(utils.is_ipv4('169.254.0.10'))
        self.assertTrue(utils.is_ipv4('0.0.0.0'))
        self.assertFalse(utils.is_ipv4('::'))
        self.assertFalse(utils.is_ipv4('2001:db8::1'))
        self.assertFalse(utils.is_ipv4('fe80::225:90ff:fefb:53ad'))

    def test_is_ipv6(self):
        self.assertFalse(utils.is_ipv6('192.0.2.10'))
        self.assertFalse(utils.is_ipv6('169.254.0.10'))
        self.assertFalse(utils.is_ipv6('0.0.0.0'))
        self.assertTrue(utils.is_ipv6('::'))
        self.assertTrue(utils.is_ipv6('2001:db8::1'))
        self.assertTrue(utils.is_ipv6('fe80::225:90ff:fefb:53ad'))

    def test_is_cidr_ipv6(self):
        self.assertTrue(utils.is_cidr_ipv6('2001:db8::/32'))
        self.assertFalse(utils.is_cidr_ipv6('192.0.2.0/32'))

    def test_is_ipv6_lla(self):
        self.assertFalse(utils.is_ipv6_lla('192.0.2.10'))
        self.assertFalse(utils.is_ipv6_lla('169.254.0.10'))
        self.assertFalse(utils.is_ipv6_lla('0.0.0.0'))
        self.assertFalse(utils.is_ipv6_lla('::'))
        self.assertFalse(utils.is_ipv6_lla('2001:db8::1'))
        self.assertTrue(utils.is_ipv6_lla('fe80::225:90ff:fefb:53ad'))

    def test_ip_port_str(self):
        self.assertEqual("127.0.0.1:8080",
                         utils.ip_port_str('127.0.0.1', 8080))
        self.assertEqual("[::1]:8080",
                         utils.ip_port_str('::1', 8080))

    def test_netmask_to_prefix(self):
        self.assertEqual(utils.netmask_to_prefix('255.0.0.0'), 8)
        self.assertEqual(utils.netmask_to_prefix('255.255.0.0'), 16)
        self.assertEqual(utils.netmask_to_prefix('255.255.255.0'), 24)
        self.assertEqual(utils.netmask_to_prefix('255.255.255.128'), 25)

    def test_ip_netmask_to_cidr(self):
        self.assertEqual('10.0.0.0/8',
                         utils.ip_netmask_to_cidr('10.0.0.1', '255.0.0.0'))
        self.assertEqual('10.0.0.0/9',
                         utils.ip_netmask_to_cidr('10.0.0.1', '255.128.0.0'))
        self.assertEqual('10.0.0.0/16',
                         utils.ip_netmask_to_cidr('10.0.0.1', '255.255.0.0'))
        self.assertEqual('10.0.0.0/20',
                         utils.ip_netmask_to_cidr('10.0.0.1', '255.255.240.0'))
        self.assertEqual('10.0.0.0/30', utils.ip_netmask_to_cidr(
            '10.0.0.1', '255.255.255.252'))

    def test_expand_expected_codes(self):
        exp_codes = ''
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         set())
        exp_codes = '200'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200'})
        exp_codes = '200, 201'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201'})
        exp_codes = '200, 201,202'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201', '202'})
        exp_codes = '200-202'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201', '202'})
        exp_codes = '200-202, 205'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201', '202', '205'})
        exp_codes = '200, 201-203'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201', '202', '203'})
        exp_codes = '200, 201-203, 205'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'200', '201', '202', '203', '205'})
        exp_codes = '201-200, 205'
        self.assertEqual(utils.expand_expected_codes(exp_codes),
                         {'205'})

    def test_base64_sha1_string(self):
        str_to_sha1 = [
            # no special cases str (no altchars)
            ('77e7d60d-e137-4246-8a84-a25db33571cd',
             'iVZVQ5AKmk2Ae0uGLP0Ue4OseRM='),
            # backward compat amphorae with - in str[1:]
            ('9c6e5f27-a0da-4ceb-afe5-5a81230be42e',
             'NjrNgt3Egl-H5ScbYM5ChtUH3M8='),
            # sha1 would start with -, now replaced with x
            ('4db4a3cf-9fef-4057-b1fd-b2afbf7a8a0f',
             'xxqntK8jJ_gE3QEmh-D1-XgCW_E=')
        ]
        for str, sha1 in str_to_sha1:
            self.assertEqual(sha1, utils.base64_sha1_string(str))

    @mock.patch('stevedore.driver.DriverManager')
    def test_get_amphora_driver(self, mock_stevedore_driver):
        FAKE_AMP_DRIVER = 'fake_amp_drvr'
        driver_mock = mock.MagicMock()
        driver_mock.driver = FAKE_AMP_DRIVER
        mock_stevedore_driver.return_value = driver_mock

        result = utils.get_amphora_driver()

        self.assertEqual(FAKE_AMP_DRIVER, result)

    def test_get_vip_secuirty_group_name(self):
        FAKE_LB_ID = uuidutils.generate_uuid()
        self.assertIsNone(utils.get_vip_security_group_name(None))

        expected_sg_name = constants.VIP_SECURITY_GROUP_PREFIX + FAKE_LB_ID
        self.assertEqual(expected_sg_name,
                         utils.get_vip_security_group_name(FAKE_LB_ID))

    def test_map_protocol_to_nftable_protocol(self):
        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_TCP})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_HTTP})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_HTTPS})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_TERMINATED_HTTPS})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_PROXY})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_PROXYV2})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_UDP})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_UDP}, result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_SCTP})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_SCTP},
                         result)

        result = utils.map_protocol_to_nftable_protocol(
            {constants.PROTOCOL: lib_consts.PROTOCOL_PROMETHEUS})
        self.assertEqual({constants.PROTOCOL: lib_consts.PROTOCOL_TCP}, result)

    def test_rotate_server_certs_key_passphrase(self):
        """Test rotate server_certs_key_passphrase."""
        # Use one key (default) and encrypt/decrypt it
        cfg.CONF.set_override(
            'server_certs_key_passphrase',
            ['insecure-key-do-not-use-this-key'],
            group='certificates')
        fer = utils.get_server_certs_key_passphrases_fernet()
        data1 = 'some data one'
        enc1 = fer.encrypt(data1.encode('utf-8'))
        self.assertEqual(
            data1, fer.decrypt(enc1).decode('utf-8'))

        # Use two keys, first key is new and used for encrypting
        # and default key can still be used for decryption
        cfg.CONF.set_override(
            'server_certs_key_passphrase',
            ['insecure-key-do-not-use-this-ke2',
             'insecure-key-do-not-use-this-key'],
            group='certificates')
        fer = utils.get_server_certs_key_passphrases_fernet()
        data2 = 'some other data'
        enc2 = fer.encrypt(data2.encode('utf-8'))
        self.assertEqual(
            data2, fer.decrypt(enc2).decode('utf-8'))
        self.assertEqual(
            data1, fer.decrypt(enc1).decode('utf-8'))

        # Remove first key and we should only be able to
        # decrypt the newest data
        cfg.CONF.set_override(
            'server_certs_key_passphrase',
            ['insecure-key-do-not-use-this-ke2'],
            group='certificates')
        fer = utils.get_server_certs_key_passphrases_fernet()
        self.assertEqual(
            data2, fer.decrypt(enc2).decode('utf-8'))
        self.assertRaises(fernet.InvalidToken, fer.decrypt, enc1)
