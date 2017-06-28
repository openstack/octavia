#    Copyright 2017 GoDaddy
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

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import pecan.testing

from octavia.api import config as pconfig
from octavia.common import constants
from octavia.tests.functional.db import base as base_db_test


class TestRootController(base_db_test.OctaviaDBTestBase):

    def get(self, app, path, params=None, headers=None, status=200,
            expect_errors=False):
        response = app.get(
            path, params=params, headers=headers, status=status,
            expect_errors=expect_errors)
        return response

    def setUp(self):
        super(TestRootController, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='api_settings', auth_strategy=constants.NOAUTH)

    def _get_versions_with_config(self, api_v1_enabled, api_v2_enabled):
        self.conf.config(group='api_settings', api_v1_enabled=api_v1_enabled)
        self.conf.config(group='api_settings', api_v2_enabled=api_v2_enabled)
        app = pecan.testing.load_test_app({'app': pconfig.app,
                                           'wsme': pconfig.wsme})
        return self.get(app=app, path='/').json.get('versions', None)

    def test_api_versions(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=True, api_v2_enabled=True)
        version_ids = tuple(v.get('id') for v in versions)
        self.assertEqual(2, len(version_ids))
        self.assertIn('v1', version_ids)
        self.assertIn('v2.0', version_ids)

    def test_api_v1_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=False, api_v2_enabled=True)
        self.assertEqual(1, len(versions))
        self.assertEqual('v2.0', versions[0].get('id'))

    def test_api_v2_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=True, api_v2_enabled=False)
        self.assertEqual(1, len(versions))
        self.assertEqual('v1', versions[0].get('id'))

    def test_api_both_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=False, api_v2_enabled=False)
        self.assertEqual(0, len(versions))
