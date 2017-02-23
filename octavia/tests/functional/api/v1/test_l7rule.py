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


class TestL7Rule(base.BaseAPITest):

    def setUp(self):
        super(TestL7Rule, self).setUp()
        self.lb = self.create_load_balancer(
            {'subnet_id': uuidutils.generate_uuid()})
        self.set_lb_status(self.lb.get('id'))
        self.listener = self.create_listener(self.lb.get('id'),
                                             constants.PROTOCOL_HTTP, 80)
        self.set_lb_status(self.lb.get('id'))
        self.l7policy = self.create_l7policy(
            self.lb.get('id'), self.listener.get('id'),
            constants.L7POLICY_ACTION_REJECT)
        self.set_lb_status(self.lb.get('id'))
        self.l7rules_path = self.L7RULES_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'),
            l7policy_id=self.l7policy.get('id'))
        self.l7rule_path = self.l7rules_path + '/{l7rule_id}'

    def test_get(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        response = self.get(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')))
        response_body = response.json
        self.assertEqual(l7rule, response_body)

    def test_get_bad_parent_policy(self):
        bad_path = (self.L7RULES_PATH.format(
            lb_id=self.lb.get('id'), listener_id=self.listener.get('id'),
            l7policy_id=uuidutils.generate_uuid()) + '/' +
            uuidutils.generate_uuid())
        self.get(bad_path, status=404)

    def test_bad_get(self):
        self.get(self.l7rule_path.format(
            l7rule_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        api_l7r_a = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        api_l7r_b = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/images')
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.l7rules_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(2, len(response_body))
        self.assertIn(api_l7r_a, response_body)
        self.assertIn(api_l7r_b, response_body)

    def test_empty_get_all(self):
        response = self.get(self.l7rules_path)
        response_body = response.json
        self.assertIsInstance(response_body, list)
        self.assertEqual(0, len(response_body))

    def test_create_host_name_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO, 'www.example.com')
        self.assertEqual(constants.L7RULE_TYPE_HOST_NAME, l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                         l7rule.get('compare_type'))
        self.assertEqual('www.example.com', l7rule.get('value'))
        self.assertIsNone(l7rule.get('key'))
        self.assertFalse(l7rule.get('invert'))
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

    def test_create_path_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api',
            invert=True)
        self.assertEqual(constants.L7RULE_TYPE_PATH, l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                         l7rule.get('compare_type'))
        self.assertEqual('/api', l7rule.get('value'))
        self.assertIsNone(l7rule.get('key'))
        self.assertTrue(l7rule.get('invert'))
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

    def test_create_file_type_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_FILE_TYPE,
            constants.L7RULE_COMPARE_TYPE_REGEX, 'jpg|png')
        self.assertEqual(constants.L7RULE_TYPE_FILE_TYPE, l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_REGEX,
                         l7rule.get('compare_type'))
        self.assertEqual('jpg|png', l7rule.get('value'))
        self.assertIsNone(l7rule.get('key'))
        self.assertFalse(l7rule.get('invert'))
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

    def test_create_header_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_HEADER,
            constants.L7RULE_COMPARE_TYPE_ENDS_WITH, '"some string"',
            key='Some-header')
        self.assertEqual(constants.L7RULE_TYPE_HEADER, l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                         l7rule.get('compare_type'))
        self.assertEqual('"some string"', l7rule.get('value'))
        self.assertEqual('Some-header', l7rule.get('key'))
        self.assertFalse(l7rule.get('invert'))
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

    def test_create_cookie_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie')
        self.assertEqual(constants.L7RULE_TYPE_COOKIE, l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_CONTAINS,
                         l7rule.get('compare_type'))
        self.assertEqual('some-value', l7rule.get('value'))
        self.assertEqual('some-cookie', l7rule.get('key'))
        self.assertFalse(l7rule.get('invert'))
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
        l7r_id = uuidutils.generate_uuid()
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api', id=l7r_id)
        self.assertEqual(l7r_id, l7rule.get('id'))

    def test_create_with_duplicate_id(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        path = self.L7RULES_PATH.format(lb_id=self.lb.get('id'),
                                        listener_id=self.listener.get('id'),
                                        l7policy_id=self.l7policy.get('id'))
        body = {'id': l7rule.get('id'),
                'type': constants.L7RULE_TYPE_PATH,
                'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                'value': '/api'}
        self.post(path, body, status=409)

    def test_create_too_many_rules(self):
        for i in range(0, constants.MAX_L7RULES_PER_L7POLICY):
            self.create_l7rule(
                self.lb.get('id'), self.listener.get('id'),
                self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
                constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
            self.set_lb_status(self.lb.get('id'), constants.ACTIVE)
        body = {'type': constants.L7RULE_TYPE_PATH,
                'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                'value': '/api'}
        self.post(self.l7rules_path, body, status=409)

    def test_bad_create(self):
        l7rule = {'name': 'test1'}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_bad_create_host_name_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_bad_create_path_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_PATH,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                  'value': 'bad string\\'}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_bad_create_file_type_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_FILE_TYPE,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                  'value': 'png'}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_bad_create_header_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_HEADER,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_CONTAINS,
                  'value': 'some-string'}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_bad_create_cookie_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_COOKIE,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                  'key': 'bad cookie name',
                  'value': 'some-string'}
        self.post(self.l7rules_path, l7rule, status=400)

    def test_create_with_bad_handler(self):
        self.handler_mock().l7rule.create.side_effect = Exception()
        self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_update(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        new_l7rule = {'value': '/images'}
        response = self.put(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')), new_l7rule, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ONLINE)
        self.set_lb_status(self.lb.get('id'))
        response_body = response.json
        self.assertEqual('/api', response_body.get('value'))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE, constants.ONLINE)

    def test_bad_update(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        new_l7rule = {'type': 'bad type'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 new_l7rule, expect_errors=True)

    def test_update_with_bad_handler(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        new_l7rule = {'value': '/images'}
        self.handler_mock().l7rule.update.side_effect = Exception()
        self.put(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')), new_l7rule, status=202)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_update_with_invalid_rule(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        new_l7rule = {'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                      'value': 'bad string\\'}
        self.put(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')), new_l7rule, status=400)
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.ACTIVE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.ACTIVE,
                                            constants.ONLINE)

    def test_delete(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')))
        self.assertEqual(l7rule, response.json)
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')))
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
        self.delete(self.l7rule_path.format(
            l7rule_id=uuidutils.generate_uuid()), status=404)

    def test_delete_with_bad_handler(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        response = self.get(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')))
        self.assertEqual(l7rule, response.json)
        self.handler_mock().l7rule.delete.side_effect = Exception()
        self.delete(self.l7rule_path.format(
            l7rule_id=l7rule.get('id')))
        self.assert_correct_lb_status(self.lb.get('id'),
                                      constants.PENDING_UPDATE,
                                      constants.ONLINE)
        self.assert_correct_listener_status(self.lb.get('id'),
                                            self.listener.get('id'),
                                            constants.PENDING_UPDATE,
                                            constants.ERROR)

    def test_create_when_lb_pending_update(self):
        self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        new_l7rule = {'type': constants.L7RULE_TYPE_PATH,
                      'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                      'value': '/api'}
        self.post(self.l7rules_path, body=new_l7rule, status=409)

    def test_update_when_lb_pending_update(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        new_l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                      'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                      'value': '.*.example.com'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 body=new_l7rule, status=409)

    def test_delete_when_lb_pending_update(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.put(self.LB_PATH.format(lb_id=self.lb.get('id')),
                 body={'name': 'test_name_change'})
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        new_l7rule = {'type': constants.L7RULE_TYPE_HEADER,
                      'compare_type':
                          constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                      'value': 'some-string',
                      'key': 'Some-header'}
        self.post(self.l7rules_path, body=new_l7rule, status=409)

    def test_update_when_lb_pending_delete(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        new_l7rule = {'type': constants.L7RULE_TYPE_COOKIE,
                      'compare_type':
                          constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                      'value': 'some-string',
                      'key': 'some-cookie'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 body=new_l7rule, status=409)

    def test_delete_when_lb_pending_delete(self):
        l7rule = self.create_l7rule(
            self.lb.get('id'), self.listener.get('id'),
            self.l7policy.get('id'), constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api')
        self.set_lb_status(self.lb.get('id'))
        self.delete(self.LB_DELETE_CASCADE_PATH.format(
            lb_id=self.lb.get('id')))
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                    status=409)
