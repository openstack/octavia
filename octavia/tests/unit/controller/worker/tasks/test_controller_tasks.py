# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
#

import mock
from oslo_utils import uuidutils

from octavia.controller.worker import controller_worker
from octavia.controller.worker.tasks import controller_tasks
from octavia.db import repositories as repo
import octavia.tests.unit.base as base


AMP_ID = uuidutils.generate_uuid()
LB1_ID = uuidutils.generate_uuid()
LB2_ID = uuidutils.generate_uuid()
LISTENER1_ID = uuidutils.generate_uuid()
LISTENER2_ID = uuidutils.generate_uuid()

_lb1_mock = mock.MagicMock()
_lb1_mock.id = LB1_ID
_lb2_mock = mock.MagicMock()
_lb2_mock.id = LB2_ID
_lbs = [_lb1_mock, _lb2_mock]

_listener1_mock = mock.MagicMock()
_listener1_mock.id = LISTENER1_ID
_listener1_mock.enabled = False
_listener2_mock = mock.MagicMock()
_listener2_mock.id = LISTENER2_ID
_listener2_mock.enabled = True
_listeners = [_listener1_mock, _listener2_mock]


@mock.patch('octavia.db.api.get_session', return_value='TEST')
class TestControllerTasks(base.TestCase):

    def setUp(self):

        self.amphora_mock = mock.MagicMock()
        self.amphora_mock.id = AMP_ID

        self.loadbalancer_mock = mock.MagicMock()
        self.loadbalancer_mock.id = LB1_ID
        self.loadbalancer_mock.enabled = True

        super(TestControllerTasks, self).setUp()

    @mock.patch('octavia.controller.worker.controller_worker.'
                'ControllerWorker.delete_load_balancer')
    @mock.patch('octavia.db.repositories.AmphoraRepository.'
                'get_all_lbs_on_amphora',
                return_value=_lbs)
    def test_delete_load_balancers_on_amp(self,
                                          mock_get_all_lbs_on_amp,
                                          mock_delete_lb,
                                          mock_get_session):

        delete_lbs_on_amp = controller_tasks.DeleteLoadBalancersOnAmp()
        delete_lbs_on_amp.execute(self.amphora_mock)

        repo.AmphoraRepository.get_all_lbs_on_amphora.assert_called_once_with(
            'TEST',
            amphora_id=AMP_ID)

        (controller_worker.
         ControllerWorker.delete_load_balancer.assert_has_calls)([
             mock.call(LB1_ID),
             mock.call(LB2_ID)], any_order=False)
