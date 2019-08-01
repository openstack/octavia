#    Copyright 2019 Red Hat, Inc. All rights reserved.
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

from octavia.api.drivers.noop_driver import agent
import octavia.tests.unit.base as base


class TestNoopProviderAgent(base.TestCase):

    def setUp(self):
        super(TestNoopProviderAgent, self).setUp()

    @mock.patch('time.sleep')
    def test_noop_provider_agent(self, mock_sleep):
        mock_exit_event = mock.MagicMock()
        mock_exit_event.is_set.side_effect = [False, True]

        agent.noop_provider_agent(mock_exit_event)

        mock_sleep.assert_called_once_with(1)
