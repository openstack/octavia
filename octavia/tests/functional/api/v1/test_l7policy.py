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

from oslo_utils import uuidutils

from octavia.common import constants
from octavia.tests.functional.api.v1 import base


class TestL7Policy(base.BaseAPITest):

    def setUp(self):
        super(TestL7Policy, self).setUp()
        self.lb = self.create_load_balancer(
            {'subnet_id': uuidutils.generate_uuid()})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.pool = self.create_pool_sans_listener(
            self.lb.get('id'),
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN)
        self.set_lb_status(self.lb.get('id'))
        self.l7policies_path = self.L7POLICIES_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'))
        self.l7policy_path = self.l7policies_path + '/{l7policy_id}'

    def test_get(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        response = self.get(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')))
        response_body = response.json
        self.assertEqual(api_l7policy, response_body)

    def test_bad_get(self):
        self.get(self.l7policy_path.format(
            l7policy_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        api_l7p_a = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        api_l7p_c = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        api_l7p_b = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT, position=2)
        self.set_lb_status(self.lb.get('id'))
        # api_l7p_b was inserted before api_l7p_c
        api_l7p_c['position'] = 3
        response = self.get(self.l7policies_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(3, len(response_body))
        self.assertEqual(api_l7p_a, response_body[0])
        self.assertEqual(api_l7p_b, response_body[1])
        self.assertEqual(api_l7p_c, response_body[2])

    def test_empty_get_all(self):
        response = self.get(self.l7policies_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(0, len(response_body))

    def test_create_reject_policy(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.assertEqual(constants.L7POLICY_ACTION_REJECT,
                         api_l7policy.get('action'))
        self.assertEqual(1, api_l7policy.get('position'))
        self.assertIsNone(api_l7policy.get('redirect_pool_id'))
        self.assertIsNone(api_l7policy.get('redirect_url'))
        self.assertTrue(api_l7policy.get('enabled'))
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

    def test_create_redirect_to_pool(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
            redirect_pool_id=self.pool.get('id'))
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         api_l7policy.get('action'))
        self.assertEqual(1, api_l7policy.get('position'))
        self.assertEqual(self.pool.get('id'),
                         api_l7policy.get('redirect_pool_id'))
        self.assertIsNone(api_l7policy.get('redirect_url'))
        self.assertTrue(api_l7policy.get('enabled'))
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

    def test_create_redirect_to_url(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REDIRECT_TO_URL,
            redirect_url='http://www.example.com')
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         api_l7policy.get('action'))
        self.assertEqual(1, api_l7policy.get('position'))
        self.assertIsNone(api_l7policy.get('redirect_pool_id'))
        self.assertEqual('http://www.example.com',
                         api_l7policy.get('redirect_url'))
        self.assertTrue(api_l7policy.get('enabled'))
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

    def test_create_with_id(self):
        l7p_id = uuidutils.generate_uuid()
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT, id=l7p_id)
        self.assertEqual(l7p_id, api_l7policy.get('id'))

    def test_create_with_duplicate_id(self):
        l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        path = self.L7POLICIES_PATH.format(lb_id=self.lb.get('id'),
                                           listener_id=self.listener.get('id'))
        body = {'id': l7policy.get('id'),
                'action': constants.L7POLICY_ACTION_REJECT}
        self.post(path, body, status=409)

    def test_bad_create(self):
        l7policy = {'name': 'test1'}
        self.post(self.l7policies_path, l7policy, status=400)

    def test_bad_create_redirect_to_pool(self):
        l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                    'redirect_pool_id': uuidutils.generate_uuid()}
        self.post(self.l7policies_path, l7policy, status=404)

    def test_bad_create_redirect_to_url(self):
        l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                    'redirect_url': 'bad url'}
        self.post(self.l7policies_path, l7policy, status=400)

    def test_create_with_bad_handler(self):
        self.handler_mock().l7policy.create.side_effect = Exception()
        self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_update(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        response = self.put(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')), new_l7policy, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        response_body = response.json
        self.assertEqual(constants.L7POLICY_ACTION_REJECT,
                         response_body.get('action'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_update(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        new_l7policy = {'action': 'bad action'}
        self.put(self.l7policy_path.format(l7policy_id=api_l7policy.get('id')),
                 new_l7policy, status=400)

    def test_bad_update_redirect_to_pool(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                        'redirect_pool_id': uuidutils.generate_uuid()}
        self.put(self.l7policy_path.format(l7policy_id=api_l7policy.get('id')),
                 new_l7policy, status=404)

    def test_bad_update_redirect_to_url(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'bad url'}
        self.put(self.l7policy_path.format(l7policy_id=api_l7policy.get('id')),
                 new_l7policy, status=400)

    def test_update_with_bad_handler(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        self.handler_mock().l7policy.update.side_effect = Exception()
        self.put(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')), new_l7policy, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_update_redirect_to_pool_bad_pool_id(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        path = self.l7policy_path.format(l7policy_id=api_l7policy.get('id'))
        new_l7policy = {'redirect_pool_id': uuidutils.generate_uuid()}
        self.put(path, new_l7policy, status=404)

    def test_update_redirect_to_pool_minimal(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        path = self.l7policy_path.format(l7policy_id=api_l7policy.get('id'))
        new_l7policy = {'redirect_pool_id': self.pool.get('id')}
        self.put(path, new_l7policy, status=202)

    def test_update_redirect_to_url_bad_url(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        path = self.l7policy_path.format(l7policy_id=api_l7policy.get('id'))
        new_l7policy = {'redirect_url': 'bad-url'}
        self.put(path, new_l7policy, status=400)

    def test_update_redirect_to_url_minimal(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        path = self.l7policy_path.format(l7policy_id=api_l7policy.get('id'))
        new_l7policy = {'redirect_url': 'http://www.example.com/'}
        self.put(path, new_l7policy, status=202)

    def test_delete(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')))
        self.assertEqual(api_l7policy, response.json)
        self.delete(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')))
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
        self.delete(self.l7policy_path.format(
            l7policy_id=uuidutils.generate_uuid()), status=404)

    def test_delete_with_bad_handler(self):
        api_l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')))
        self.assertEqual(api_l7policy, response.json)
        self.handler_mock().l7policy.delete.side_effect = Exception()
        self.delete(self.l7policy_path.format(
            l7policy_id=api_l7policy.get('id')))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_create_when_lb_pending_update(self):
        self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        self.post(self.l7policies_path, body=new_l7policy, status=409)

    def test_update_when_lb_pending_update(self):
        l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        self.put(self.l7policy_path.format(l7policy_id=l7policy.get('id')),
                 body=new_l7policy, status=409)

    def test_delete_when_lb_pending_update(self):
        l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.delete(self.l7policy_path.format(l7policy_id=l7policy.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        self.post(self.l7policies_path, body=new_l7policy, status=409)

    def test_update_when_lb_pending_delete(self):
        l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        new_l7policy = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                        'redirect_url': 'http://www.example.com'}
        self.put(self.l7policy_path.format(l7policy_id=l7policy.get('id')),
                 body=new_l7policy, status=409)

    def test_delete_when_lb_pending_delete(self):
        l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        self.delete(self.l7policy_path.format(l7policy_id=l7policy.get('id')),
                    status=409)
