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

import random
from unittest import mock

from oslo_utils import uuidutils

from octavia.common import data_models
from octavia.statistics.drivers import update_db
from octavia.tests.unit import base


class TestStatsUpdateDb(base.TestCase):
    def setUp(self):
        super(TestStatsUpdateDb, self).setUp()
        self.amphora_id = uuidutils.generate_uuid()
        self.listener_id = uuidutils.generate_uuid()

    @mock.patch('octavia.db.repositories.ListenerStatisticsRepository')
    @mock.patch('octavia.db.api.session')
    def test_update_stats(self, mock_get_session, mock_listener_stats_repo):
        bytes_in1 = random.randrange(1000000000)
        bytes_out1 = random.randrange(1000000000)
        active_conns1 = random.randrange(1000000000)
        total_conns1 = random.randrange(1000000000)
        request_errors1 = random.randrange(1000000000)
        stats_1 = data_models.ListenerStatistics(
            listener_id=self.listener_id,
            amphora_id=self.amphora_id,
            bytes_in=bytes_in1,
            bytes_out=bytes_out1,
            active_connections=active_conns1,
            total_connections=total_conns1,
            request_errors=request_errors1
        )
        bytes_in2 = random.randrange(1000000000)
        bytes_out2 = random.randrange(1000000000)
        active_conns2 = random.randrange(1000000000)
        total_conns2 = random.randrange(1000000000)
        request_errors2 = random.randrange(1000000000)
        stats_2 = data_models.ListenerStatistics(
            listener_id=self.listener_id,
            amphora_id=self.amphora_id,
            bytes_in=bytes_in2,
            bytes_out=bytes_out2,
            active_connections=active_conns2,
            total_connections=total_conns2,
            request_errors=request_errors2
        )

        mock_session = mock_get_session().begin().__enter__()

        update_db.StatsUpdateDb().update_stats(
            [stats_1, stats_2], deltas=False)

        mock_listener_stats_repo().replace.assert_has_calls([
            mock.call(mock_session, stats_1),
            mock.call(mock_session, stats_2)
        ])

        update_db.StatsUpdateDb().update_stats(
            [stats_1, stats_2], deltas=True)

        mock_listener_stats_repo().increment.assert_has_calls([
            mock.call(mock_session, stats_1),
            mock.call(mock_session, stats_2)
        ])
