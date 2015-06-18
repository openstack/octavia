#    Copyright 2014 Rackspace
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


class TestHealthMonitor(base.BaseAPITest):

    def setUp(self):
        super(TestHealthMonitor, self).setUp()
        self.lb = self.create_load_balancer({})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.pool = self.create_pool(self.lb.get('id'),
                                     self.listener.get('id'),
                                     constants.PROTOCOL_HTTP,
                                     constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.hm_path = self.HM_PATH.format(lb_id=self.lb.get('id'),
                                           listener_id=self.listener.get('id'),
                                           pool_id=self.pool.get('id'))

    def test_get(self):
        api_hm = self.create_health_monitor(self.lb.get('id'),
                                            self.listener.get('id'),
                                            self.pool.get('id'),
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.get(self.hm_path)
        response_body = response.json
        self.assertEqual(api_hm, response_body)

    def test_bad_get(self):
        self.get(self.hm_path, status=404)

    def test_create(self):
        api_hm = self.create_health_monitor(self.lb.get('id'),
                                            self.listener.get('id'),
                                            self.pool.get('id'),
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assertEqual(constants.HEALTH_MONITOR_HTTP, api_hm.get('type'))
        self.assertEqual(1, api_hm.get('delay'))
        self.assertEqual(1, api_hm.get('timeout'))
        self.assertEqual(1, api_hm.get('fall_threshold'))
        self.assertEqual(1, api_hm.get('rise_threshold'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_create(self):
        hm_json = {'name': 'test1'}
        self.post(self.hm_path, hm_json, status=400)

    def test_duplicate_create(self):
        api_hm = self.create_health_monitor(self.lb.get('id'),
                                            self.listener.get('id'),
                                            self.pool.get('id'),
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1)
        self.set_lb_status(lb_id=self.lb.get('id'))
        self.post(self.hm_path, api_hm, status=409)

    def test_update(self):
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP,
                                   1, 1, 1, 1)
        self.set_lb_status(lb_id=self.lb.get('id'))
        new_hm = {'type': constants.HEALTH_MONITOR_HTTPS}
        self.put(self.hm_path, new_hm)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_update(self):
        self.skip("This test will need reviewed after a validation layer is "
                  "built")
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP,
                                   1, 1, 1, 1)
        new_hm = {'type': 'bad_type', 'delay': 2}
        self.set_lb_status(self.lb.get('id'))
        self.put(self.hm_path, new_hm, status=400)

    def test_delete(self):
        api_hm = self.create_health_monitor(self.lb.get('id'),
                                            self.listener.get('id'),
                                            self.pool['id'],
                                            constants.HEALTH_MONITOR_HTTP,
                                            1, 1, 1, 1)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.get(self.hm_path)
        self.assertEqual(api_hm, response.json)
        self.delete(self.hm_path)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_delete(self):
        self.delete(self.hm_path, status=404)

    def test_create_when_lb_pending_update(self):
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.post(self.hm_path, body={'type': constants.HEALTH_MONITOR_HTTP,
                                      'delay': 1, 'timeout': 1,
                                      'fall_threshold': 1,
                                      'rise_threshold': 1}, status=409)

    def test_update_when_lb_pending_update(self):
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.put(self.hm_path, body={'rise_threshold': 2}, status=409)

    def test_delete_when_lb_pending_update(self):
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.delete(self.hm_path, status=409)

    def test_create_when_lb_pending_delete(self):
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.post(self.hm_path, body={'type': constants.HEALTH_MONITOR_HTTP,
                                      'delay': 1, 'timeout': 1,
                                      'fall_threshold': 1,
                                      'rise_threshold': 1}, status=409)

    def test_update_when_lb_pending_delete(self):
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.put(self.hm_path, body={'rise_threshold': 2}, status=409)

    def test_delete_when_lb_pending_delete(self):
        self.create_health_monitor(self.lb.get('id'), self.listener.get('id'),
                                   self.pool.get('id'),
                                   constants.HEALTH_MONITOR_HTTP, 1, 1, 1, 1)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.delete(self.hm_path, status=409)