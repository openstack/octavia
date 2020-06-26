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

import octavia.common.utils as utils
import octavia.tests.unit.base as base


class TestConfig(base.TestCase):

    def test_get_hostname(self):
        self.assertNotEqual(utils.get_hostname(), '')

    def test_is_ipv6(self):
        self.assertFalse(utils.is_ipv6('192.0.2.10'))
        self.assertFalse(utils.is_ipv6('169.254.0.10'))
        self.assertFalse(utils.is_ipv6('0.0.0.0'))
        self.assertTrue(utils.is_ipv6('::'))
        self.assertTrue(utils.is_ipv6('2001:db8::1'))
        self.assertTrue(utils.is_ipv6('fe80::225:90ff:fefb:53ad'))

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
