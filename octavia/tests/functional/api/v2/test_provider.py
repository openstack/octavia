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

from octavia.tests.functional.api.v2 import base


class TestProvider(base.BaseAPITest):

    root_tag_list = 'providers'

    def setUp(self):
        super(TestProvider, self).setUp()

    def test_get_all_providers(self):
        octavia_dict = {u'description': u'Octavia driver.',
                        u'name': u'octavia'}
        amphora_dict = {u'description': u'Amp driver.', u'name': u'amphora'}
        noop_dict = {u'description': u'NoOp driver.', u'name': u'noop_driver'}
        providers = self.get(self.PROVIDERS_PATH).json.get(self.root_tag_list)
        self.assertEqual(3, len(providers))
        self.assertTrue(octavia_dict in providers)
        self.assertTrue(amphora_dict in providers)
        self.assertTrue(noop_dict in providers)

    def test_get_all_providers_fields(self):
        octavia_dict = {u'name': u'octavia'}
        amphora_dict = {u'name': u'amphora'}
        noop_dict = {u'name': u'noop_driver'}
        providers = self.get(self.PROVIDERS_PATH, params={'fields': ['name']})
        providers_list = providers.json.get(self.root_tag_list)
        self.assertEqual(3, len(providers_list))
        self.assertTrue(octavia_dict in providers_list)
        self.assertTrue(amphora_dict in providers_list)
        self.assertTrue(noop_dict in providers_list)
