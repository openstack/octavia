#    Copyright 2016 IBM
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


class TestLoadBlancerStatistics(base.BaseAPITest):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestLoadBlancerStatistics, self).setUp()
        self.lb = self.create_load_balancer(
            {'subnet_id': uuidutils.generate_uuid()})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.lb_path = self.LB_STATS_PATH.format(lb_id=self.lb.get('id'))
        self.amphora = self.create_amphora(uuidutils.generate_uuid(),
                                           self.lb.get('id'))

    def test_get(self):
        ls = self.create_listener_stats(listener_id=self.listener.get('id'),
                                        amphora_id=self.amphora.id)
        expected = {
            'loadbalancer': {
                'bytes_in': ls['bytes_in'],
                'bytes_out': ls['bytes_out'],
                'active_connections': ls['active_connections'],
                'total_connections': ls['total_connections'],
                'request_errors': ls['request_errors'],
                'listeners': [
                    {'id': self.listener.get('id'),
                     'bytes_in': ls['bytes_in'],
                     'bytes_out': ls['bytes_out'],
                     'active_connections': ls['active_connections'],
                     'total_connections': ls['total_connections'],
                     'request_errors': ls['request_errors']}]
            }
        }
        response = self.get(self.lb_path)
        response_body = response.json
        self.assertEqual(expected, response_body)
