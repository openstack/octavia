# Copyright 2016 Blue Box, an IBM Company
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

import octavia.common.constants as constants
import octavia.common.exceptions as exceptions
import octavia.common.validate as validate
import octavia.tests.unit.base as base


class TestValidations(base.TestCase):
    # Note that particularly complex validation testing is handled via
    # functional tests elsewhere (ex. repository tests)

    def test_validate_url(self):
        ret = validate.url('http://example.com')
        self.assertTrue(ret)

    def test_validate_bad_url(self):
        self.assertRaises(exceptions.InvalidURL, validate.url, 'bad url')

    def test_validate_url_bad_schema(self):
        self.assertRaises(exceptions.InvalidURL, validate.url,
                          'ssh://www.example.com/')

    def test_validate_header_name(self):
        ret = validate.header_name('Some-header')
        self.assertTrue(ret)

    def test_validate_bad_header_name(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad header')

    def test_validate_cookie_value_string(self):
        ret = validate.cookie_value_string('some-cookie')
        self.assertTrue(ret)

    def test_validate_bad_cookie_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.cookie_value_string,
                          'bad cookie value;')

    def test_validate_header_value_string(self):
        ret = validate.header_value_string('some-value')
        self.assertTrue(ret)

    def test_validate_header_value_string_quoted(self):
        ret = validate.header_value_string('"some value"')
        self.assertTrue(ret)

    def test_validate_bad_header_value_string(self):
        self.assertRaises(exceptions.InvalidString,
                          validate.header_value_string,
                          '\x18')

    def test_validate_regex(self):
        ret = validate.regex('some regex.*')
        self.assertTrue(ret)

    def test_validate_bad_regex(self):
        self.assertRaises(exceptions.InvalidRegex, validate.regex,
                          'bad regex\\')

    def test_sanitize_l7policy_api_args_action_reject(self):
        l7p = {'action': constants.L7POLICY_ACTION_REJECT,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_pool_id(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('redirect_pool_id', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_pool_model(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': None,
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool_id', s_l7p.keys())
        self.assertIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_action_rdr_url(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_url', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())

    def test_sanitize_l7policy_api_args_bad_action(self):
        l7p = {'action': 'bad-action',
               'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_action_none(self):
        l7p = {'action': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_both_rdr_args_a(self):
        l7p = {'redirect_url': 'http://www.example.com/',
               'redirect_pool_id': 'test-pool'}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_both_rdr_args_b(self):
        l7p = {'redirect_url': 'http://www.example.com/',
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_rdr_pool_id(self):
        l7p = {'redirect_pool_id': 'test-pool',
               'redirect_url': None,
               'redirect_pool': None}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_pool_id', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_pool_noid(self):
        l7p = {'redirect_pool_id': None,
               'redirect_url': None,
               'redirect_pool': {
                   'protocol': constants.PROTOCOL_HTTP,
                   'lb_algorithm': constants.LB_ALGORITHM_ROUND_ROBIN}}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIn('redirect_pool', s_l7p.keys())
        self.assertIsNone(s_l7p['redirect_url'])
        self.assertNotIn('redirect_pool_id', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_pool_id_none_create(self):
        l7p = {'redirect_pool_id': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_pool_noid_none_create(self):
        l7p = {'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_pool_both_none_create(self):
        l7p = {'redirect_pool': None,
               'redirect_pool_id': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_url(self):
        l7p = {'redirect_pool_id': None,
               'redirect_url': 'http://www.example.com/',
               'redirect_pool': None}
        s_l7p = validate.sanitize_l7policy_api_args(l7p)
        self.assertIsNone(s_l7p['redirect_pool_id'])
        self.assertNotIn('redirect_pool', s_l7p.keys())
        self.assertIn('redirect_url', s_l7p.keys())
        self.assertIn('action', s_l7p.keys())
        self.assertEqual(constants.L7POLICY_ACTION_REDIRECT_TO_URL,
                         s_l7p['action'])

    def test_sanitize_l7policy_api_args_rdr_url_none_create(self):
        l7p = {'redirect_url': None}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_rdr_url_bad_url(self):
        l7p = {'redirect_url': 'bad url'}
        self.assertRaises(exceptions.InvalidURL,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_update_action_rdr_pool_arg(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_POOL,
               'redirect_url': None,
               'redirect_pool_id': None,
               'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_update_action_rdr_url_arg(self):
        l7p = {'action': constants.L7POLICY_ACTION_REDIRECT_TO_URL,
               'redirect_url': None,
               'redirect_pool_id': None,
               'redirect_pool': None}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)

    def test_sanitize_l7policy_api_args_create_must_have_action(self):
        l7p = {}
        self.assertRaises(exceptions.InvalidL7PolicyAction,
                          validate.sanitize_l7policy_api_args, l7p, True)

    def test_sanitize_l7policy_api_args_update_must_have_args(self):
        l7p = {}
        self.assertRaises(exceptions.InvalidL7PolicyArgs,
                          validate.sanitize_l7policy_api_args, l7p)
