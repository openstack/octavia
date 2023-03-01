#    Copyright 2022 Red Hat
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
from octavia.api.common import hooks
from octavia.api.config import app
from octavia.api.config import wsme
from octavia.tests.unit import base


class TestConfig(base.TestCase):

    def test_app_config(self):
        self.assertEqual(
            'octavia.api.root_controller.RootController', app['root'])
        self.assertEqual(['octavia.api'], app['modules'])
        expected_hook_types = [
            hooks.ContentTypeHook,
            hooks.ContextHook,
            hooks.QueryParametersHook
        ]
        self.assertEqual(expected_hook_types, list(map(type, app['hooks'])))
        self.assertFalse(app['debug'])

    def test_wsme_config(self):
        self.assertFalse(wsme['debug'])
