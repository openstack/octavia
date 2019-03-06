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
        self.assertEqual(12, len(version_ids))
        self.assertIn('v1', version_ids)
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

        # Each version should have a 'self' 'href' to the API version URL
        # [{u'rel': u'self', u'href': u'http://localhost/v2'}]
        # Validate that the URL exists in the response
        for version in versions:
            url_version = None
            if version['id'].startswith('v2.'):
                url_version = 'v2'
            else:
                url_version = version['id']
            version_url = 'http://localhost/{}'.format(url_version)
            links = version['links']
            # Note, there may be other links present, this test is for 'self'
            version_link = [link for link in links if link['rel'] == 'self']
            self.assertEqual(version_url, version_link[0]['href'])

    def test_api_v1_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=False, api_v2_enabled=True)
        self.assertEqual(11, len(versions))
        self.assertEqual('v2.0', versions[0].get('id'))
        self.assertEqual('v2.1', versions[1].get('id'))
        self.assertEqual('v2.2', versions[2].get('id'))
        self.assertEqual('v2.3', versions[3].get('id'))
        self.assertEqual('v2.4', versions[4].get('id'))
        self.assertEqual('v2.5', versions[5].get('id'))
        self.assertEqual('v2.6', versions[6].get('id'))
        self.assertEqual('v2.7', versions[7].get('id'))
        self.assertEqual('v2.8', versions[8].get('id'))
        self.assertEqual('v2.9', versions[9].get('id'))
        self.assertEqual('v2.10', versions[10].get('id'))

    def test_api_v2_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=True, api_v2_enabled=False)
        self.assertEqual(1, len(versions))
        self.assertEqual('v1', versions[0].get('id'))

    def test_api_both_disabled(self):
        versions = self._get_versions_with_config(
            api_v1_enabled=False, api_v2_enabled=False)
        self.assertEqual(0, len(versions))
