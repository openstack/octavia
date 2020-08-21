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

from taskflow import retry

from octavia.controller.worker.v1.tasks import retry_tasks
import octavia.tests.unit.base as base


class TestRetryTasks(base.TestCase):

    def setUp(self):
        super().setUp()

    @mock.patch('time.sleep')
    def test_sleeping_retry_times_controller(self, mock_sleep):
        retry_ctrlr = retry_tasks.SleepingRetryTimesController(
            attempts=2, name='test_retry')

        # Test on_failure that should RETRY
        history = ['boom']

        result = retry_ctrlr.on_failure(history)

        self.assertEqual(retry.RETRY, result)

        # Test on_failure retries exhausted, should REVERT
        history = ['boom', 'bang', 'pow']

        result = retry_ctrlr.on_failure(history)

        self.assertEqual(retry.REVERT, result)

        # Test revert - should not raise
        retry_ctrlr.revert(history)
