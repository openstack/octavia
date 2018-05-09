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

from octavia.api.drivers import driver_factory
from octavia.common import exceptions
import octavia.tests.unit.base as base


class TestDriverFactory(base.TestCase):

    def setUp(self):
        super(TestDriverFactory, self).setUp()

    @mock.patch('stevedore.driver.DriverManager')
    def test_driver_factory_no_provider(self, mock_drivermgr):
        mock_mgr = mock.MagicMock()
        mock_drivermgr.return_value = mock_mgr

        driver = driver_factory.get_driver(None)

        self.assertEqual(mock_mgr.driver, driver)

    @mock.patch('stevedore.driver.DriverManager')
    def test_driver_factory_failed_to_load_driver(self, mock_drivermgr):
        mock_drivermgr.side_effect = Exception('boom')

        self.assertRaises(exceptions.ProviderNotFound,
                          driver_factory.get_driver, None)

    @mock.patch('stevedore.driver.DriverManager')
    def test_driver_factory_not_enabled(self, mock_drivermgr):

        self.assertRaises(exceptions.ProviderNotEnabled,
                          driver_factory.get_driver,
                          'dont-enable-this-fake-driver-name')
