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

    def _get_versions_with_config(self):
        app = pecan.testing.load_test_app({'app': pconfig.app,
                                           'wsme': pconfig.wsme})
        return self.get(app=app, path='/').json.get('versions', None)

    def test_api_versions(self):
        versions = self._get_versions_with_config()
        version_ids = tuple(v.get('id') for v in versions)
        self.assertEqual(14, len(version_ids))
        self.assertIn('v2.0', version_ids)
        self.assertIn('v2.1', version_ids)
        self.assertIn('v2.2', version_ids)
        self.assertIn('v2.3', version_ids)
        self.assertIn('v2.4', version_ids)
        self.assertIn('v2.5', version_ids)
        self.assertIn('v2.6', version_ids)
        self.assertIn('v2.7', version_ids)
        self.assertIn('v2.8', version_ids)
        self.assertIn('v2.9', version_ids)
        self.assertIn('v2.10', version_ids)
        self.assertIn('v2.11', version_ids)
        self.assertIn('v2.12', version_ids)
        self.assertIn('v2.13', version_ids)

        # Each version should have a 'self' 'href' to the API version URL
        # [{u'rel': u'self', u'href': u'http://localhost/v2'}]
        # Validate that the URL exists in the response
        version_url = 'http://localhost/v2'
        for version in versions:
            links = version['links']
            # Note, there may be other links present, this test is for 'self'
            version_link = [link for link in links if link['rel'] == 'self']
            self.assertEqual(version_url, version_link[0]['href'])
