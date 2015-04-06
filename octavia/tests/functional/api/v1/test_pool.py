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

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.tests.functional.api.v1 import base


class TestPool(base.BaseAPITest):

    def setUp(self):
        super(TestPool, self).setUp()
        self.lb = self.create_load_balancer({})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.pools_path = self.POOLS_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'))
        self.pool_path = self.pools_path + '/{pool_id}'

    def test_get(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id=self.lb.get('id'))
        api_pool['operating_status'] = constants.ONLINE
        response = self.get(self.pool_path.format(pool_id=api_pool.get('id')))
        response_body = response.json
        self.assertEqual(api_pool, response_body)

    def test_bad_get(self):
        self.get(self.pool_path.format(pool_id=uuidutils.generate_uuid()),
                 status=404)

    def test_get_all(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.get(self.pools_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(1, len(response_body))
        self.assertEqual(api_pool.get('id'), response_body[0].get('id'))

    def test_empty_get_all(self):
        response = self.get(self.pools_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(0, len(response_body))

    def test_create(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        self.assertEqual(constants.PROTOCOL_HTTP, api_pool.get('protocol'))
        self.assertEqual(constants.LB_ALGORITHM_ROUND_ROBIN,
                         api_pool.get('lb_algorithm'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_create_with_id(self):
        pid = uuidutils.generate_uuid()
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    id=pid)
        self.assertEqual(pid, api_pool.get('id'))

    def test_create_with_duplicate_id(self):
        pool = self.create_pool(self.lb.get('id'),
                                self.listener.get('id'),
                                constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        path = self.POOLS_PATH.format(lb_id=self.lb.get('id'),
                                      listener_id=self.listener.get('id'))
        body = {'id': pool.get('id'), 'protocol': constants.PROTOCOL_HTTP,
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}
        self.post(path, body, status=409, expect_errors=True)

    def test_bad_create(self):
        api_pool = {'name': 'test1'}
        self.post(self.pools_path, api_pool, status=400)

    def test_duplicate_create(self):
        pool = {'protocol': constants.PROTOCOL_HTTP,
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}
        self.post(self.pools_path, pool)
        self.post(self.pools_path, pool, status=409)

    def test_create_bad_protocol(self):
        pool = {'protocol': 'STUPID_PROTOCOL',
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}
        self.post(self.pools_path, pool, status=400)

    def test_update(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id=self.lb.get('id'))
        new_pool = {'name': 'new_name'}
        self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                 new_pool, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.pool_path.format(pool_id=api_pool.get('id')))
        response_body = response.json
        self.assertNotEqual('new_name', response_body.get('name'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_update(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        new_pool = {'enabled': 'one'}
        self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                 new_pool, status=400)

    def test_delete(self):
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id=self.lb.get('id'))
        api_pool['operating_status'] = constants.ONLINE
        response = self.get(self.pool_path.format(
            pool_id=api_pool.get('id')))
        self.assertEqual(api_pool, response.json)
        self.delete(self.pool_path.format(pool_id=api_pool.get('id')))
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
        self.delete(self.pool_path.format(
            pool_id=uuidutils.generate_uuid()), status=404)

    def test_create_with_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    session_persistence=sp)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.pool_path.format(
            pool_id=api_pool.get('id')))
        response_body = response.json
        sess_p = response_body.get('session_persistence')
        self.assertIsNotNone(sess_p)
        self.assertEqual(constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                         sess_p.get('type'))
        self.assertEqual('test_cookie_name', sess_p.get('cookie_name'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_create_with_bad_session_persistence(self):
        sp = {"type": "persistence_type",
              "cookie_name": "test_cookie_name"}
        pool = {'protocol': constants.PROTOCOL_HTTP,
                'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN,
                'session_persistence': sp}
        self.post(self.pools_path, pool, status=400)

    def test_add_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                            body={'session_persistence': sp})
        api_pool = response.json
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.assertNotEqual(sp, api_pool.get('session_persistence'))

    def test_update_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    session_persistence=sp)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.get(self.pool_path.format(
            pool_id=api_pool.get('id')))
        response_body = response.json
        sess_p = response_body.get('session_persistence')
        sess_p['cookie_name'] = 'new_test_cookie_name'
        api_pool = self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                            body={'session_persistence': sess_p}).json
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.assertNotEqual(sess_p, api_pool.get('session_persistence'))
        self.set_lb_status(self.lb.get('id'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_update_bad_session_persistence(self):
        self.skip('This test should pass after a validation layer.')
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    session_persistence=sp)
        self.set_lb_status(lb_id=self.lb.get('id'))
        response = self.get(self.pool_path.format(
            pool_id=api_pool.get('id')))
        response_body = response.json
        sess_p = response_body.get('session_persistence')
        sess_p['type'] = 'persistence_type'
        self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                 body={'session_persistence': sess_p}, status=400)

    def test_delete_with_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    session_persistence=sp)
        self.set_lb_status(lb_id=self.lb.get('id'))
        self.delete(self.pool_path.format(pool_id=api_pool.get('id')),
                    status=202)
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

    def test_delete_session_persistence(self):
        sp = {"type": constants.SESSION_PERSISTENCE_HTTP_COOKIE,
              "cookie_name": "test_cookie_name"}
        api_pool = self.create_pool(self.lb.get('id'),
                                    self.listener.get('id'),
                                    constants.PROTOCOL_HTTP,
                                    constants.LB_ALGORITHM_ROUND_ROBIN,
                                    session_persistence=sp)
        self.set_lb_status(lb_id=self.lb.get('id'))
        sp = {'session_persistence': None}
        api_pool = self.put(self.pool_path.format(pool_id=api_pool.get('id')),
                            body=sp, status=202).json
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.assertNotEqual(None, api_pool.get('session_persistence'))

    def test_create_when_lb_pending_update(self):
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.post(self.pools_path,
                  body={'protocol': constants.PROTOCOL_HTTP,
                        'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN},
                  status=409)

    def test_update_when_lb_pending_update(self):
        pool = self.create_pool(self.lb.get('id'), self.listener.get('id'),
                                constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.put(self.pool_path.format(pool_id=pool.get('id')),
                 body={'protocol': constants.PROTOCOL_HTTPS},
                 status=409)

    def test_delete_when_lb_pending_update(self):
        pool = self.create_pool(self.lb.get('id'), self.listener.get('id'),
                                constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.delete(self.pool_path.format(pool_id=pool.get('id')), status=409)

    def test_create_when_lb_pending_delete(self):
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.post(self.pools_path,
                  body={'protocol': constants.PROTOCOL_HTTP,
                        'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN},
                  status=409)

    def test_update_when_lb_pending_delete(self):
        pool = self.create_pool(self.lb.get('id'), self.listener.get('id'),
                                constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.put(self.pool_path.format(pool_id=pool.get('id')),
                 body={'protocol': constants.PROTOCOL_HTTPS},
                 status=409)

    def test_delete_when_lb_pending_delete(self):
        pool = self.create_pool(self.lb.get('id'), self.listener.get('id'),
                                constants.PROTOCOL_HTTP,
                                constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_PATH.format(lb_id=self.lb.get('id')))
        self.delete(self.pool_path.format(pool_id=pool.get('id')), status=409)
