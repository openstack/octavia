# Copyright 2016 IBM
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

import random

import mock
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.common import data_models
from octavia.common import stats
from octavia.tests.unit import base


class TestStatsMixin(base.TestCase):

    def setUp(self):
        super(TestStatsMixin, self).setUp()
        self.sm = stats.StatsMixin()

        self.session = mock.MagicMock()
        self.listener_id = uuidutils.generate_uuid()
        self.amphora_id = uuidutils.generate_uuid()

        self.repo_listener_stats = mock.MagicMock()
        self.sm.listener_stats_repo = self.repo_listener_stats

        self.fake_stats = data_models.ListenerStatistics(
            listener_id=self.listener_id,
            amphora_id=self.amphora_id,
            bytes_in=random.randrange(1000000000),
            bytes_out=random.randrange(1000000000),
            active_connections=random.randrange(1000000000),
            total_connections=random.randrange(1000000000),
            request_errors=random.randrange(1000000000))

        self.sm.listener_stats_repo.get_all.return_value = ([self.fake_stats],
                                                            None)

        self.repo_amphora = mock.MagicMock()
        self.sm.repo_amphora = self.repo_amphora

    def test_get_listener_stats(self):
        fake_amp = mock.MagicMock()
        fake_amp.status = constants.AMPHORA_ALLOCATED
        self.sm.repo_amphora.get.return_value = fake_amp

        ls_stats = self.sm.get_listener_stats(
            self.session, self.listener_id)
        self.repo_listener_stats.get_all.assert_called_once_with(
            self.session, listener_id=self.listener_id)
        self.repo_amphora.get.assert_called_once_with(
            self.session, id=self.amphora_id)

        self.assertEqual(self.fake_stats.bytes_in, ls_stats.bytes_in)
        self.assertEqual(self.fake_stats.bytes_out, ls_stats.bytes_out)
        self.assertEqual(
            self.fake_stats.active_connections, ls_stats.active_connections)
        self.assertEqual(
            self.fake_stats.total_connections, ls_stats.total_connections)
        self.assertEqual(
            self.fake_stats.request_errors, ls_stats.request_errors)
        self.assertEqual(self.listener_id, ls_stats.listener_id)
        self.assertIsNone(ls_stats.amphora_id)

    def test_get_listener_stats_with_amphora_deleted(self):
        fake_amp = mock.MagicMock()
        fake_amp.status = constants.DELETED
        self.sm.repo_amphora.get.return_value = fake_amp

        ls_stats = self.sm.get_listener_stats(self.session, self.listener_id)
        self.repo_listener_stats.get_all.assert_called_once_with(
            self.session, listener_id=self.listener_id)
        self.repo_amphora.get.assert_called_once_with(
            self.session, id=self.amphora_id)

        self.assertEqual(self.fake_stats.bytes_in, ls_stats.bytes_in)
        self.assertEqual(self.fake_stats.bytes_out, ls_stats.bytes_out)
        self.assertEqual(0, ls_stats.active_connections)
        self.assertEqual(
            self.fake_stats.total_connections, ls_stats.total_connections)
        self.assertEqual(
            self.fake_stats.request_errors, ls_stats.request_errors)
        self.assertEqual(self.listener_id, ls_stats.listener_id)
        self.assertIsNone(ls_stats.amphora_id)
