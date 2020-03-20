# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import pecan

from octavia.api import config as pconfig
from octavia.api.healthcheck import healthcheck_plugins
from octavia.tests.functional.db import base as base_db_test


class TestHealthCheck(base_db_test.OctaviaDBTestBase):

    def setUp(self):
        super(TestHealthCheck, self).setUp()

        # We need to define these early as they are late loaded in oslo
        # middleware and our configuration overrides would not apply.
        # Note: These must match exactly the option definitions in
        # oslo.middleware healthcheck! If not you will get duplicate option
        # errors.
        healthcheck_opts = [
            cfg.BoolOpt(
                'detailed', default=False,
                help='Show more detailed information as part of the response. '
                     'Security note: Enabling this option may expose '
                     'sensitive details about the service being monitored. '
                     'Be sure to verify that it will not violate your '
                     'security policies.'),
            cfg.ListOpt(
                'backends', default=[],
                help='Additional backends that can perform health checks and '
                     'report that information back as part of a request.'),
        ]
        cfg.CONF.register_opts(healthcheck_opts, group='healthcheck')

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group='healthcheck', backends=['octavia_db_check'])
        self.UNAVAILABLE = (healthcheck_plugins.OctaviaDBHealthcheck.
                            UNAVAILABLE_REASON)

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _make_app(self):
        # Note: we need to set argv=() to stop the wsgi setup_app from
        # pulling in the testing tool sys.argv
        return pecan.testing.load_test_app({'app': pconfig.app,
                                            'wsme': pconfig.wsme}, argv=())

    def _get_enabled_app(self):
        self.conf.config(group='api_settings', healthcheck_enabled=True)
        return self._make_app()

    def _get_disabled_app(self):
        self.conf.config(group='api_settings', healthcheck_enabled=False)
        return self._make_app()

    def _get(self, app, path, params=None, headers=None, status=200,
             expect_errors=False):
        response = app.get(path, params=params, headers=headers, status=status,
                           expect_errors=expect_errors)
        return response

    def _head(self, app, path, headers=None, status=204, expect_errors=False):
        response = app.head(path, headers=headers, status=status,
                            expect_errors=expect_errors)
        return response

    def _post(self, app, path, body, headers=None, status=201,
              expect_errors=False):
        response = app.post_json(path, params=body, headers=headers,
                                 status=status, expect_errors=expect_errors)
        return response

    def _put(self, app, path, body, headers=None, status=200,
             expect_errors=False):
        response = app.put_json(path, params=body, headers=headers,
                                status=status, expect_errors=expect_errors)
        return response

    def _delete(self, app, path, params=None, headers=None, status=204,
                expect_errors=False):
        response = app.delete(path, headers=headers, status=status,
                              expect_errors=expect_errors)
        return response

    def test_healthcheck_get_text(self):
        self.conf.config(group='healthcheck', detailed=False)
        response = self._get(self._get_enabled_app(), '/healthcheck')
        self.assertEqual(200, response.status_code)
        self.assertEqual('OK', response.text)

    # Note: For whatever reason, detailed=True text has no additonal info
    def test_healthcheck_get_text_detailed(self):
        self.conf.config(group='healthcheck', detailed=True)
        response = self._get(self._get_enabled_app(), '/healthcheck')
        self.assertEqual(200, response.status_code)
        self.assertEqual('OK', response.text)

    def test_healthcheck_get_json(self):
        self.conf.config(group='healthcheck', detailed=False)
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'application/json'})
        self.assertEqual(200, response.status_code)
        self.assertFalse(response.json['detailed'])
        self.assertEqual(['OK'], response.json['reasons'])

    def test_healthcheck_get_json_detailed(self):
        self.conf.config(group='healthcheck', detailed=True)
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'application/json'})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.json['detailed'])
        self.assertEqual('OK', response.json['reasons'][0]['reason'])
        self.assertTrue(response.json['gc'])

    def test_healthcheck_get_html(self):
        self.conf.config(group='healthcheck', detailed=False)
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'text/html'})
        self.assertEqual(200, response.status_code)
        self.assertIn('OK', response.text)

    def test_healthcheck_get_html_detailed(self):
        self.conf.config(group='healthcheck', detailed=True)
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'text/html'})
        self.assertEqual(200, response.status_code)
        self.assertIn('OK', response.text)
        self.assertIn('Garbage collector', response.text)

    def test_healthcheck_disabled_get(self):
        self._get(self._get_disabled_app(), '/healthcheck', status=404)

    def test_healthcheck_head(self):
        response = self._head(self._get_enabled_app(), '/healthcheck')
        self.assertEqual(204, response.status_code)

    def test_healthcheck_disabled_head(self):
        self._head(self._get_disabled_app(), '/healthcheck', status=404)

    # These should be denied by the API
    def test_healthcheck_post(self):
        self._post(self._get_enabled_app(), '/healthcheck',
                   {'foo': 'bar'}, status=405)

    def test_healthcheck_put(self):
        self._put(self._get_enabled_app(), '/healthcheck',
                  {'foo': 'bar'}, status=405)

    def test_healthcheck_delete(self):
        self._delete(self._get_enabled_app(), '/healthcheck',
                     status=405)

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_failed(self, mock_get_session):
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             status=503)
        self.assertEqual(503, response.status_code)
        self.assertEqual(self.UNAVAILABLE, response.text)

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_head_failed(self, mock_get_session):
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._head(self._get_enabled_app(), '/healthcheck',
                              status=503)
        self.assertEqual(503, response.status_code)

    @mock.patch('octavia.db.healthcheck.check_database_connection',
                side_effect=Exception('boom'))
    def test_healthcheck_get_failed_check(self, mock_db_check):
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             status=503)
        self.assertEqual(503, response.status_code)
        self.assertEqual(self.UNAVAILABLE, response.text)

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_json_failed(self, mock_get_session):
        self.conf.config(group='healthcheck', detailed=False)
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'application/json'},
                             status=503)
        self.assertEqual(503, response.status_code)
        self.assertFalse(response.json['detailed'])
        self.assertEqual([self.UNAVAILABLE],
                         response.json['reasons'])

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_json_detailed_failed(self, mock_get_session):
        self.conf.config(group='healthcheck', detailed=True)
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'application/json'},
                             status=503)
        self.assertEqual(503, response.status_code)
        self.assertTrue(response.json['detailed'])
        self.assertEqual(self.UNAVAILABLE,
                         response.json['reasons'][0]['reason'])
        self.assertIn('boom', response.json['reasons'][0]['details'])

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_html_failed(self, mock_get_session):
        self.conf.config(group='healthcheck', detailed=False)
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'text/html'}, status=503)
        self.assertEqual(503, response.status_code)
        self.assertIn(self.UNAVAILABLE, response.text)

    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_html_detailed_failed(self, mock_get_session):
        self.conf.config(group='healthcheck', detailed=True)
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             headers={'Accept': 'text/html'}, status=503)
        self.assertEqual(503, response.status_code)
        self.assertIn(self.UNAVAILABLE, response.text)
        self.assertIn('boom', response.text)
        self.assertIn('Garbage collector', response.text)

    # Note: For whatever reason, detailed=True text has no additonal info
    @mock.patch('octavia.db.api.get_session')
    def test_healthcheck_get_text_detailed_failed(self, mock_get_session):
        self.conf.config(group='healthcheck', detailed=True)
        mock_session = mock.MagicMock()
        mock_session.execute.side_effect = [Exception('boom')]
        mock_get_session.return_value = mock_session
        response = self._get(self._get_enabled_app(), '/healthcheck',
                             status=503)
        self.assertEqual(503, response.status_code)
        self.assertEqual(self.UNAVAILABLE, response.text)
