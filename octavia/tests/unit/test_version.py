#    Copyright 2018 Rackspace, US Inc.
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

import octavia.tests.unit.base as base
from octavia import version


class TestVersion(base.TestCase):

    def setUp(self):
        super(TestVersion, self).setUp()

    def test_vendor_str(self):
        self.assertEqual("OpenStack Foundation", version.vendor_string())

    def test_product_string(self):
        self.assertEqual("OpenStack Octavia", version.product_string())

    @mock.patch('pbr.version.VersionInfo.version_string', return_value='0.0.0')
    def test_version_str(self, mock_pbr):
        self.assertEqual('0.0.0', version.version_string_with_package())
