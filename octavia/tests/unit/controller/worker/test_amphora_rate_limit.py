# Copyright 2016 Hewlett-Packard Development Company, L.P.
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
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.controller.worker import amphora_rate_limit
import octavia.tests.unit.base as base

AMP_ID = uuidutils.generate_uuid()
BUILD_PRIORITY = 40
USED_BUILD_SLOTS = 0


class TestAmphoraBuildRateLimit(base.TestCase):

    def setUp(self):
        super(TestAmphoraBuildRateLimit, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        self.rate_limit = amphora_rate_limit.AmphoraBuildRateLimit()
        self.amp_build_slots_repo = mock.MagicMock()
        self.amp_build_req_repo = mock.MagicMock()
        self.conf.config(group='haproxy_amphora', build_rate_limit=1)

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.wait_for_build_slot')
    @mock.patch('octavia.db.repositories.AmphoraBuildReqRepository'
                '.add_to_build_queue')
    def test_add_to_build_request_queue(self,
                                        mock_add_to_build_queue,
                                        mock_wait_for_build_slot):
        self.rate_limit.add_to_build_request_queue(AMP_ID, BUILD_PRIORITY)

        mock_add_to_build_queue.assert_called_once()
        mock_wait_for_build_slot.assert_called_once()

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.db.repositories.AmphoraBuildSlotsRepository'
                '.get_used_build_slots_count',
                return_value=USED_BUILD_SLOTS)
    def test_has_build_slot(self, mock_get_used_build_slots_count):
        result = self.rate_limit.has_build_slot()

        mock_get_used_build_slots_count.assert_called_once()
        self.assertTrue(result)

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.db.repositories.AmphoraBuildReqRepository'
                '.get_highest_priority_build_req', return_value=AMP_ID)
    def test_has_highest_priority(self, mock_get_highest_priority_build_req):
        result = self.rate_limit.has_highest_priority(AMP_ID)

        mock_get_highest_priority_build_req.assert_called_once()
        self.assertTrue(result)

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.db.repositories.AmphoraBuildReqRepository'
                '.update_req_status')
    @mock.patch('octavia.db.repositories.AmphoraBuildSlotsRepository'
                '.update_count')
    def test_update_build_status_and_available_build_slots(self,
                                                           mock_update_count,
                                                           mock_update_status):
        self.rate_limit.update_build_status_and_available_build_slots(AMP_ID)

        mock_update_count.assert_called_once()
        mock_update_status.assert_called_once()

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.db.repositories.AmphoraBuildReqRepository.delete')
    @mock.patch('octavia.db.repositories.AmphoraBuildSlotsRepository'
                '.update_count')
    def test_remove_from_build_req_queue(self,
                                         mock_update_count,
                                         mock_delete):
        self.rate_limit.remove_from_build_req_queue(AMP_ID)

        mock_update_count.assert_called_once()
        mock_delete.assert_called_once()

    @mock.patch('octavia.db.api.get_session', mock.MagicMock())
    @mock.patch('octavia.db.repositories.AmphoraBuildReqRepository'
                '.delete_all')
    @mock.patch('octavia.db.repositories.AmphoraBuildSlotsRepository'
                '.update_count')
    def test_remove_all_from_build_req_queue(self,
                                             mock_update_count,
                                             mock_delete_all):
        self.rate_limit.remove_all_from_build_req_queue()

        mock_update_count.assert_called_once()
        mock_delete_all.assert_called_once()

    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.has_build_slot', return_value=True)
    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.has_highest_priority',
                return_value=True)
    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.'
                'update_build_status_and_available_build_slots')
    @mock.patch('octavia.controller.worker.amphora_rate_limit'
                '.AmphoraBuildRateLimit.remove_all_from_build_req_queue')
    @mock.patch('time.sleep')
    def test_wait_for_build_slot(self,
                                 mock_time_sleep,
                                 mock_remove_all,
                                 mock_update_status_and_slots_count,
                                 mock_has_high_priority,
                                 mock_has_build_slot):
        self.rate_limit.wait_for_build_slot(AMP_ID)

        self.assertTrue(mock_has_build_slot.called)
        self.assertTrue(mock_has_high_priority.called)
