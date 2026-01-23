#    Copyright 2021 Red Hat, Inc. All rights reserved.
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

from octavia.api import app
from octavia.api.drivers import driver_factory
import octavia.tests.unit.base as base


class TestApp(base.TestCase):

    def setUp(self):
        super().setUp()

    @mock.patch.object(driver_factory, "get_driver")
    def test__init_drivers(self, mock_get_driver):
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.CONF.config(
            group="api_settings",
            enabled_provider_drivers="provider1:desc1,provider2:desc2")

        app._init_drivers()
        mock_get_driver.assert_any_call("provider1")
        mock_get_driver.assert_any_call("provider2")

    @mock.patch.object(driver_factory, "get_driver")
    def test__init_drivers_with_error(self, mock_get_driver):
        self.CONF = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.CONF.config(
            group="api_settings",
            enabled_provider_drivers="provider1:desc1,provider2:desc2")

        mock_get_driver.side_effect = [True, Exception('Internal Error')]

        app._init_drivers()
        mock_get_driver.assert_any_call("provider1")
        mock_get_driver.assert_any_call("provider2")
        enabled_providers = driver_factory.get_providers()
        self.assertEqual(enabled_providers, {'provider1': 'desc1'})
