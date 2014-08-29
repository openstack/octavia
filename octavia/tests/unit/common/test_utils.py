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

    def test_random_string(self):
        self.assertNotEqual(utils.get_random_string(10), '')
