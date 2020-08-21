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

from octavia.amphorae.drivers.haproxy import exceptions
import octavia.tests.unit.base as base


class TestHAProxyExceptions(base.TestCase):

    def setUp(self):
        super().setUp()

    @mock.patch('octavia.amphorae.drivers.haproxy.exceptions.LOG')
    def test_check_exception(self, mock_logger):

        response_mock = mock.MagicMock()

        # Test exception that should raise and log
        response_mock.status_code = 404

        self.assertRaises(exceptions.NotFound, exceptions.check_exception,
                          response_mock)
        mock_logger.error.assert_called_once()

        # Test exception that should raise but not log
        mock_logger.reset_mock()
        response_mock.status_code = 403

        self.assertRaises(exceptions.Forbidden, exceptions.check_exception,
                          response_mock, log_error=False)
        mock_logger.error.assert_not_called()

        # Test exception that should be ignored
        mock_logger.reset_mock()
        response_mock.status_code = 401

        result = exceptions.check_exception(response_mock, ignore=[401])

        mock_logger.error.assert_not_called()
        self.assertEqual(response_mock, result)
