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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
import pecan

from octavia.api import config as pconfig
from octavia.common import constants
from octavia.tests.functional.db import base as base_db_test


class TestContentTypes(base_db_test.OctaviaDBTestBase):

    def setUp(self):
        super().setUp()

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        # Mock log_opt_values, it prevents the dump of the configuration
        # with LOG.info for each test. It saves a lot of time when running
        # the functional tests.
        self.conf.conf.log_opt_values = mock.MagicMock()

        # Note: we need to set argv=() to stop the wsgi setup_app from
        # pulling in the testing tool sys.argv
        self.app = pecan.testing.load_test_app({'app': pconfig.app,
                                                'wsme': pconfig.wsme},
                                               argv=())

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

        self.test_url = '/'

    def test_no_accept_header(self):
        response = self.app.get(self.test_url, status=200, expect_errors=False)
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    # TODO(johnsom) Testing for an empty string is a workaround for an
    #               openstacksdk bug present up to the initial
    #               antelope release of openstacksdk. This means the
    #               octavia dashboard would also be impacted.
    #               This test should change to a 406 error once the workaround
    #               is removed.
    # See: https://review.opendev.org/c/openstack/openstacksdk/+/876669
    def test_empty_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: ''})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    # Note: webob will treat invalid content types as no accept header provided
    def test_bogus_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: 'bogus'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_valid_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: constants.APPLICATION_JSON})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_valid_mixed_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT:
                     'text/html,' + constants.APPLICATION_JSON})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_wildcard_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: '*/*'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_json_wildcard_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: constants.APPLICATION_JSON + ', */*'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_json_plain_wildcard_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT: constants.APPLICATION_JSON +
                     ', text/plain, */*'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_wildcard_mixed_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT:
                     'text/html,*/*'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_valid_mixed_weighted_accept_header(self):
        response = self.app.get(
            self.test_url, status=200, expect_errors=False,
            headers={constants.ACCEPT:
                     'text/html,' + constants.APPLICATION_JSON + ';q=0.8'})
        self.assertEqual(200, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)

    def test_invalid_accept_header(self):
        response = self.app.get(
            self.test_url, status=406, expect_errors=False,
            headers={constants.ACCEPT: 'application/xml'})
        self.assertEqual(406, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)
        self.assertEqual(406, response.json[constants.CODE])
        self.assertEqual('Not Acceptable', response.json[constants.TITLE])
        self.assertEqual('Only content type application/json is accepted.',
                         response.json[constants.DESCRIPTION])

    def test_invalid_mixed_accept_header(self):
        response = self.app.get(
            self.test_url, status=406, expect_errors=False,
            headers={constants.ACCEPT: 'application/xml,text/html'})
        self.assertEqual(406, response.status_code)
        self.assertEqual(constants.APPLICATION_JSON, response.content_type)
        self.assertEqual(406, response.json[constants.CODE])
        self.assertEqual('Not Acceptable', response.json[constants.TITLE])
        self.assertEqual('Only content type application/json is accepted.',
                         response.json[constants.DESCRIPTION])
