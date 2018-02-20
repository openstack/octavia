# Copyright 2018 GoDaddy
# Copyright (c) 2015 Rackspace
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

import mock

from octavia.controller.healthmanager.health_drivers import update_logging
from octavia.tests.unit import base


class TestHealthUpdateLogger(base.TestCase):

    def setUp(self):
        super(TestHealthUpdateLogger, self).setUp()
        self.logger = update_logging.HealthUpdateLogger()

    @mock.patch('octavia.controller.healthmanager.health_drivers'
                '.update_logging.LOG')
    def test_update_health(self, mock_log):
        self.logger.update_health({'id': 1})
        self.assertEqual(1, mock_log.info.call_count)


class TestStatsUpdateLogger(base.TestCase):
    def setUp(self):
        super(TestStatsUpdateLogger, self).setUp()
        self.logger = update_logging.StatsUpdateLogger()

    @mock.patch('octavia.controller.healthmanager.health_drivers'
                '.update_logging.LOG')
    def test_update_stats(self, mock_log):
        self.logger.update_stats({'id': 1})
        self.assertEqual(1, mock_log.info.call_count)
