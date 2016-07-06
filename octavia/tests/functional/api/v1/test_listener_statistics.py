#    Copyright 2016 Blue Box, an IBM Company
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

from octavia.common import constants
from octavia.tests.functional.api.v1 import base

from oslo_utils import uuidutils


class TestListenerStatistics(base.BaseAPITest):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestListenerStatistics, self).setUp()
        self.lb = self.create_load_balancer({})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.ls_path = self.LISTENER_STATS_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'))
        self.amphora = self.create_amphora(uuidutils.generate_uuid(),
                                           self.lb.get('id'))

    def test_get(self):
        ls = self.create_listener_stats(listener_id=self.listener.get('id'),
                                        amphora_id=self.amphora.id)
        ls.pop('listener_id')
        ls.pop('amphora_id')
        response = self.get(self.ls_path)
        response_body = response.json
        self.assertEqual(ls, response_body)
