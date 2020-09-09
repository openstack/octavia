# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
import random
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import data_models
from octavia.statistics import stats_base
from octavia.tests.unit import base

STATS_DRIVERS = ['stats_db', 'stats_logger']


class TestStatsBase(base.TestCase):

    def setUp(self):
        super(TestStatsBase, self).setUp()

        self.conf = oslo_fixture.Config(cfg.CONF)
        self.conf.config(group="controller_worker",
                         statistics_drivers=STATS_DRIVERS)
        self.amphora_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()
        self.listener_stats = data_models.ListenerStatistics(
            amphora_id=self.amphora_id,
            listener_id=self.listener_id,
            bytes_in=random.randrange(1000000000),
            bytes_out=random.randrange(1000000000),
            active_connections=random.randrange(1000000000),
            total_connections=random.randrange(1000000000),
            request_errors=random.randrange(1000000000))
        self.listener_stats_dict = {
            self.listener_id: {
                "request_errors": self.listener_stats.request_errors,
                "active_connections":
                    self.listener_stats.active_connections,
                "total_connections": self.listener_stats.total_connections,
                "bytes_in": self.listener_stats.bytes_in,
                "bytes_out": self.listener_stats.bytes_out,
            }
        }

    @mock.patch('octavia.statistics.drivers.update_db.StatsUpdateDb')
    @mock.patch('octavia.statistics.drivers.logger.StatsLogger')
    def test_update_stats(self, mock_stats_logger, mock_stats_db):
        stats_base._STATS_HANDLERS = None

        # Test with update success
        stats_base.update_stats_via_driver([self.listener_stats], deltas=True)

        mock_stats_db().update_stats.assert_called_once_with(
            [self.listener_stats], deltas=True)
        mock_stats_logger().update_stats.assert_called_once_with(
            [self.listener_stats], deltas=True)

        # Test with update failure (should still run both drivers)
        mock_stats_db.reset_mock()
        mock_stats_logger.reset_mock()
        mock_stats_db().update_stats.side_effect = Exception
        mock_stats_logger().update_stats.side_effect = Exception
        stats_base.update_stats_via_driver(
            [self.listener_stats])

        mock_stats_db().update_stats.assert_called_once_with(
            [self.listener_stats], deltas=False)
        mock_stats_logger().update_stats.assert_called_once_with(
            [self.listener_stats], deltas=False)

    @mock.patch('octavia.statistics.drivers.update_db.StatsUpdateDb')
    @mock.patch('octavia.statistics.drivers.logger.StatsLogger')
    def test__get_stats_handlers(self, mock_stats_logger, mock_stats_db):
        stats_base._STATS_HANDLERS = None

        # Test that this function implements a singleton
        first_call_handlers = stats_base._get_stats_handlers()
        second_call_handlers = stats_base._get_stats_handlers()

        self.assertEqual(first_call_handlers, second_call_handlers)

        # Drivers should only load once (this is a singleton)
        mock_stats_db.assert_called_once_with()
        mock_stats_logger.assert_called_once_with()
