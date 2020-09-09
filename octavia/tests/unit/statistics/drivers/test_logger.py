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

from unittest import mock

from oslo_utils import uuidutils

from octavia.common import data_models
from octavia.statistics.drivers import logger
from octavia.tests.unit import base


class TestStatsUpdateLogger(base.TestCase):
    def setUp(self):
        super().setUp()
        self.logger = logger.StatsLogger()
        self.amphora_id = uuidutils.generate_uuid()

    @mock.patch('octavia.statistics.drivers.logger.LOG')
    def test_update_stats(self, mock_log):
        self.logger.update_stats([data_models.ListenerStatistics()])
        self.assertEqual(1, mock_log.info.call_count)
