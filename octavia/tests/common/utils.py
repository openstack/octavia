# Copyright (c) 2016 Hewlett Packard Enterprise Development Company LP
# All Rights Reserved.
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
import ipaddress
from unittest import mock

import fixtures

from octavia.common import constants as consts


# Borrowed from neutron
# https://review.opendev.org/#/c/232716/
class OpenFixture(fixtures.Fixture):
    """Mock access to a specific file while preserving open for others."""

    def __init__(self, filepath, contents=''):
        self.path = filepath
        self.contents = contents

    def _setUp(self):
        self.mock_open = mock.mock_open(read_data=self.contents)
        # work around for https://bugs.python.org/issue21258
        self.mock_open.return_value.__iter__ = (
            lambda self: iter(self.readline, ''))
        self._orig_open = open

        def replacement_open(name, *args, **kwargs):
            if name == self.path:
                return self.mock_open(name, *args, **kwargs)
            return self._orig_open(name, *args, **kwargs)

        self._patch = mock.patch('builtins.open', new=replacement_open)
        self._patch.start()
        self.addCleanup(self._patch.stop)


def assert_address_lists_equal(obj, l1, l2):
    obj.assertEqual(len(l1), len(l2),
                    "Address lists don't match: {} vs {}".format(l1, l2))
    for a1, a2 in zip(l1, l2):
        if consts.ADDRESS in a1 and consts.ADDRESS in a2:
            obj.assertEqual(
                ipaddress.ip_address(a1[consts.ADDRESS]),
                ipaddress.ip_address(a2[consts.ADDRESS]))
            obj.assertEqual(a1[consts.PREFIXLEN],
                            a2[consts.PREFIXLEN])
        else:
            obj.assertEqual(a1, a2)


def assert_route_lists_equal(obj, l1, l2):
    obj.assertEqual(len(l1), len(l2),
                    "Routes don't match: {} vs {}".format(l1, l2))
    for r1, r2 in zip(l1, l2):
        obj.assertEqual(
            ipaddress.ip_network(r1[consts.DST]),
            ipaddress.ip_network(r2[consts.DST]))
        if consts.GATEWAY in r1 and consts.GATEWAY in r2:
            obj.assertEqual(
                ipaddress.ip_address(r1[consts.GATEWAY]),
                ipaddress.ip_address(r2[consts.GATEWAY]))
        if consts.PREFSRC in r1 and consts.PREFSRC in r2:
            obj.assertEqual(
                ipaddress.ip_address(r1[consts.PREFSRC]),
                ipaddress.ip_address(r2[consts.PREFSRC]))
        for attr in (consts.ONLINK, consts.TABLE, consts.SCOPE):
            obj.assertEqual(r1.get(attr), r2.get(attr))


def assert_rule_lists_equal(obj, l1, l2):
    obj.assertEqual(len(l1), len(l2))
    for r1, r2 in zip(l1, l2):
        obj.assertEqual(
            ipaddress.ip_address(r1[consts.SRC]),
            ipaddress.ip_address(r2[consts.SRC]))
        obj.assertEqual(r1[consts.SRC_LEN], r2[consts.SRC_LEN])
        obj.assertEqual(r1[consts.TABLE], r2[consts.TABLE])


def assert_script_lists_equal(obj, l1, l2):
    obj.assertEqual(l1, l2)


def assert_interface_files_equal(obj, i1, i2):
    obj.assertEqual(i1[consts.NAME], i2[consts.NAME])
    obj.assertEqual(i1.get(consts.MTU), i2.get(consts.MTU))
    assert_address_lists_equal(obj,
                               i1[consts.ADDRESSES],
                               i2[consts.ADDRESSES])
    assert_route_lists_equal(obj,
                             i1[consts.ROUTES],
                             i2[consts.ROUTES])
    assert_rule_lists_equal(obj,
                            i1[consts.RULES],
                            i2[consts.RULES])
    assert_script_lists_equal(obj,
                              i1[consts.SCRIPTS],
                              i2[consts.SCRIPTS])
