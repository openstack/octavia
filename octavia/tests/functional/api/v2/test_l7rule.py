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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base


class TestL7Rule(base.BaseAPITest):

    root_tag = 'rule'
    root_tag_list = 'rules'
    root_tag_links = 'rules_links'

    def setUp(self):
        super(TestL7Rule, self).setUp()
        self.lb = self.create_load_balancer(uuidutils.generate_uuid())
        self.lb_id = self.lb.get('loadbalancer').get('id')
        self.project_id = self.lb.get('loadbalancer').get('project_id')
        self.set_lb_status(self.lb_id)
        self.listener = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb_id=self.lb_id)
        self.listener_id = self.listener.get('listener').get('id')
        self.set_lb_status(self.lb_id)
        self.l7policy = self.create_l7policy(
            self.listener_id, constants.L7POLICY_ACTION_REJECT)
        self.l7policy_id = self.l7policy.get('l7policy').get('id')
        self.set_lb_status(self.lb_id)
        self.l7rules_path = self.L7RULES_PATH.format(
            l7policy_id=self.l7policy_id)
        self.l7rule_path = self.l7rules_path + '/{l7rule_id}'

    def test_get(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        response = self.get(self.l7rule_path.format(
            l7rule_id=l7rule.get('id'))).json.get(self.root_tag)
        self.assertEqual(l7rule, response)

    def test_get_authorized(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.l7rule_path.format(
                    l7rule_id=l7rule.get('id'))).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(l7rule, response)

    def test_get_not_authorized(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            response = self.get(self.l7rule_path.format(
                l7rule_id=l7rule.get('id')), status=403).json
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response)

    def test_get_hides_deleted(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)

        response = self.get(self.l7rules_path)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 1)
        self.set_object_status(self.l7rule_repo, api_l7rule.get('id'),
                               provisioning_status=constants.DELETED)
        response = self.get(self.l7rules_path)
        objects = response.json.get(self.root_tag_list)
        self.assertEqual(len(objects), 0)

    def test_get_bad_parent_policy(self):
        bad_path = (self.L7RULES_PATH.format(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=uuidutils.generate_uuid()) + '/' +
            uuidutils.generate_uuid())
        self.get(bad_path, status=404)

    def test_bad_get(self):
        self.get(self.l7rule_path.format(
            l7rule_id=uuidutils.generate_uuid()), status=404)

    def test_get_all(self):
        api_l7r_a = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_l7r_b = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        rules = self.get(self.l7rules_path).json.get(self.root_tag_list)
        self.assertIsInstance(rules, list)
        self.assertEqual(2, len(rules))
        rule_id_types = [(r.get('id'), r.get('type')) for r in rules]
        self.assertIn((api_l7r_a.get('id'), api_l7r_a.get('type')),
                      rule_id_types)
        self.assertIn((api_l7r_b.get('id'), api_l7r_b.get('type')),
                      rule_id_types)

    def test_get_all_authorized(self):
        api_l7r_a = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        api_l7r_b = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                rules = self.get(
                    self.l7rules_path).json.get(self.root_tag_list)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertIsInstance(rules, list)
        self.assertEqual(2, len(rules))
        rule_id_types = [(r.get('id'), r.get('type')) for r in rules]
        self.assertIn((api_l7r_a.get('id'), api_l7r_a.get('type')),
                      rule_id_types)
        self.assertIn((api_l7r_b.get('id'), api_l7r_b.get('type')),
                      rule_id_types)

    def test_get_all_not_authorized(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            rules = self.get(self.l7rules_path, status=403)

        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, rules.json)

    def test_get_all_sorted(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        response = self.get(self.l7rules_path,
                            params={'sort': 'type:desc'})
        rules_desc = response.json.get(self.root_tag_list)
        response = self.get(self.l7rules_path,
                            params={'sort': 'type:asc'})
        rules_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(rules_desc))
        self.assertEqual(3, len(rules_asc))

        rule_id_types_desc = [(rule.get('id'), rule.get('type'))
                              for rule in rules_desc]
        rule_id_types_asc = [(rule.get('id'), rule.get('type'))
                             for rule in rules_asc]
        self.assertEqual(rule_id_types_asc,
                         list(reversed(rule_id_types_desc)))

    def test_get_all_limited(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        # First two -- should have 'next' link
        first_two = self.get(self.l7rules_path, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.l7rules_path, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.l7rules_path, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_all_fields_filter(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        l7rus = self.get(self.l7rules_path, params={
            'fields': ['id', 'compare_type']}).json
        for l7ru in l7rus['rules']:
            self.assertIn(u'id', l7ru)
            self.assertIn(u'compare_type', l7ru)
            self.assertNotIn(u'project_id', l7ru)

    def test_get_one_fields_filter(self):
        l7r1 = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        l7ru = self.get(
            self.l7rule_path.format(l7rule_id=l7r1.get('id')),
            params={'fields': ['id', 'compare_type']}).json.get(self.root_tag)
        self.assertIn(u'id', l7ru)
        self.assertIn(u'compare_type', l7ru)
        self.assertNotIn(u'project_id', l7ru)

    def test_get_all_filter(self):
        ru1 = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)
        self.set_lb_status(self.lb_id)

        l7rus = self.get(self.l7rules_path, params={
            'id': ru1['id']}).json

        self.assertEqual(1, len(l7rus['rules']))
        self.assertEqual(ru1['id'],
                         l7rus['rules'][0]['id'])

    def test_empty_get_all(self):
        response = self.get(self.l7rules_path).json.get(self.root_tag_list)
        self.assertIsInstance(response, list)
        self.assertEqual(0, len(response))

    def test_create_host_name_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
            constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
            'www.example.com').get(self.root_tag)
        self.assertEqual(constants.L7RULE_TYPE_HOST_NAME,
                         api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                         api_l7rule.get('compare_type'))
        self.assertEqual('www.example.com', api_l7rule.get('value'))
        self.assertIsNone(api_l7rule.get('key'))
        self.assertFalse(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_rule_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                api_l7rule = self.create_l7rule(
                    self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
                    constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                    'www.example.com').get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(constants.L7RULE_TYPE_HOST_NAME,
                         api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                         api_l7rule.get('compare_type'))
        self.assertEqual('www.example.com', api_l7rule.get('value'))
        self.assertIsNone(api_l7rule.get('key'))
        self.assertFalse(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_rule_not_authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)

        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            api_l7rule = self.create_l7rule(
                self.l7policy_id, constants.L7RULE_TYPE_HOST_NAME,
                constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                'www.example.com', status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, api_l7rule)

    def test_create_path_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH, '/api',
            invert=True).get(self.root_tag)
        self.assertEqual(constants.L7RULE_TYPE_PATH, api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                         api_l7rule.get('compare_type'))
        self.assertEqual('/api', api_l7rule.get('value'))
        self.assertIsNone(api_l7rule.get('key'))
        self.assertTrue(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_file_type_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_FILE_TYPE,
            constants.L7RULE_COMPARE_TYPE_REGEX, 'jpg|png').get(self.root_tag)
        self.assertEqual(constants.L7RULE_TYPE_FILE_TYPE,
                         api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_REGEX,
                         api_l7rule.get('compare_type'))
        self.assertEqual('jpg|png', api_l7rule.get('value'))
        self.assertIsNone(api_l7rule.get('key'))
        self.assertFalse(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_header_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_HEADER,
            constants.L7RULE_COMPARE_TYPE_ENDS_WITH, '"some string"',
            key='Some-header').get(self.root_tag)
        self.assertEqual(constants.L7RULE_TYPE_HEADER, api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                         api_l7rule.get('compare_type'))
        self.assertEqual('"some string"', api_l7rule.get('value'))
        self.assertEqual('Some-header', api_l7rule.get('key'))
        self.assertFalse(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_cookie_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_COOKIE,
            constants.L7RULE_COMPARE_TYPE_CONTAINS, 'some-value',
            key='some-cookie').get(self.root_tag)
        self.assertEqual(constants.L7RULE_TYPE_COOKIE, api_l7rule.get('type'))
        self.assertEqual(constants.L7RULE_COMPARE_TYPE_CONTAINS,
                         api_l7rule.get('compare_type'))
        self.assertEqual('some-value', api_l7rule.get('value'))
        self.assertEqual('some-cookie', api_l7rule.get('key'))
        self.assertFalse(api_l7rule.get('invert'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_CREATE,
            l7rule_op_status=constants.OFFLINE)

    def test_create_too_many_rules(self):
        for i in range(0, constants.MAX_L7RULES_PER_L7POLICY):
            self.create_l7rule(
                self.l7policy_id, constants.L7RULE_TYPE_PATH,
                constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                '/api').get(self.root_tag)
            self.set_lb_status(self.lb_id)
        body = {'type': constants.L7RULE_TYPE_PATH,
                'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                'value': '/api'}
        self.post(self.l7rules_path, self._build_body(body), status=409)

    def test_bad_create(self):
        l7rule = {'name': 'test1'}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_bad_create_host_name_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_bad_create_path_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_PATH,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                  'value': 'bad string\\'}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_bad_create_file_type_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_FILE_TYPE,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                  'value': 'png'}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_bad_create_header_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_HEADER,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_CONTAINS,
                  'value': 'some-string'}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_bad_create_cookie_rule(self):
        l7rule = {'type': constants.L7RULE_TYPE_COOKIE,
                  'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                  'key': 'bad cookie name',
                  'value': 'some-string'}
        self.post(self.l7rules_path, self._build_body(l7rule), status=400)

    def test_create_with_bad_handler(self):
        self.handler_mock().l7rule.create.side_effect = Exception()
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            l7rule_prov_status=constants.ERROR,
            l7rule_op_status=constants.OFFLINE)

    def test_update(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_l7rule = {'value': '/images'}
        response = self.put(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id')),
            self._build_body(new_l7rule)).json.get(self.root_tag)
        self.assertEqual('/api', response.get('value'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_UPDATE)

    def test_update_authorized(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_l7rule = {'value': '/images'}

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.put(self.l7rule_path.format(
                    l7rule_id=api_l7rule.get('id')),
                    self._build_body(new_l7rule)).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual('/api', response.get('value'))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_UPDATE)

    def test_update_not_authorized(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_l7rule = {'value': '/images'}

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            response = self.put(self.l7rule_path.format(
                l7rule_id=api_l7rule.get('id')),
                self._build_body(new_l7rule), status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            l7policy_prov_status=constants.ACTIVE,
            l7rule_prov_status=constants.ACTIVE)

    def test_bad_update(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        new_l7rule = {'type': 'bad type'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 self._build_body(new_l7rule), status=400)

    def test_update_with_bad_handler(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_l7rule = {'value': '/images'}
        self.handler_mock().l7rule.update.side_effect = Exception()
        self.put(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id')), self._build_body(new_l7rule))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            l7rule_prov_status=constants.ERROR)

    def test_update_with_invalid_rule(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        new_l7rule = {'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                      'value': 'bad string\\'}
        self.put(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id')), self._build_body(new_l7rule),
            status=400)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            l7rule_prov_status=constants.ACTIVE)

    def test_delete(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_l7rule['provisioning_status'] = constants.ACTIVE
        api_l7rule['operating_status'] = constants.ONLINE
        api_l7rule.pop('updated_at')

        response = self.get(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id'))).json.get(self.root_tag)
        response.pop('updated_at')
        self.assertEqual(api_l7rule, response)

        self.delete(self.l7rule_path.format(l7rule_id=api_l7rule.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_DELETE)
        self.set_lb_status(self.lb_id)

    def test_delete_authorized(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_l7rule['provisioning_status'] = constants.ACTIVE
        api_l7rule['operating_status'] = constants.ONLINE
        api_l7rule.pop('updated_at')

        response = self.get(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id'))).json.get(self.root_tag)
        response.pop('updated_at')
        self.assertEqual(api_l7rule, response)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):

                self.delete(
                    self.l7rule_path.format(l7rule_id=api_l7rule.get('id')))
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.PENDING_UPDATE,
            listener_prov_status=constants.PENDING_UPDATE,
            l7policy_prov_status=constants.PENDING_UPDATE,
            l7rule_prov_status=constants.PENDING_DELETE)
        self.set_lb_status(self.lb_id)

    def test_delete_not_authorized(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_l7rule['provisioning_status'] = constants.ACTIVE
        api_l7rule['operating_status'] = constants.ONLINE
        api_l7rule.pop('updated_at')

        response = self.get(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id'))).json.get(self.root_tag)
        response.pop('updated_at')
        self.assertEqual(api_l7rule, response)

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               self.project_id):
            self.delete(
                self.l7rule_path.format(l7rule_id=api_l7rule.get('id')),
                status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            lb_prov_status=constants.ACTIVE,
            listener_prov_status=constants.ACTIVE,
            l7policy_prov_status=constants.ACTIVE,
            l7rule_prov_status=constants.ACTIVE)

    def test_bad_delete(self):
        self.delete(self.l7rule_path.format(
            l7rule_id=uuidutils.generate_uuid()), status=404)

    def test_delete_with_bad_handler(self):
        api_l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        # Set status to ACTIVE/ONLINE because set_lb_status did it in the db
        api_l7rule['provisioning_status'] = constants.ACTIVE
        api_l7rule['operating_status'] = constants.ONLINE
        response = self.get(self.l7rule_path.format(
            l7rule_id=api_l7rule.get('id'))).json.get(self.root_tag)

        self.assertIsNone(api_l7rule.pop('updated_at'))
        self.assertIsNotNone(response.pop('updated_at'))
        self.assertEqual(api_l7rule, response)

        self.handler_mock().l7rule.delete.side_effect = Exception()
        self.delete(self.l7rule_path.format(l7rule_id=api_l7rule.get('id')))
        self.assert_correct_status(
            lb_id=self.lb_id, listener_id=self.listener_id,
            l7policy_id=self.l7policy_id, l7rule_id=api_l7rule.get('id'),
            l7rule_prov_status=constants.ERROR)

    def test_create_when_lb_pending_update(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        new_l7rule = {'type': constants.L7RULE_TYPE_PATH,
                      'compare_type': constants.L7RULE_COMPARE_TYPE_EQUAL_TO,
                      'value': '/api'}
        self.post(self.l7rules_path, body=self._build_body(new_l7rule),
                  status=409)

    def test_update_when_lb_pending_update(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        new_l7rule = {'type': constants.L7RULE_TYPE_HOST_NAME,
                      'compare_type': constants.L7RULE_COMPARE_TYPE_REGEX,
                      'value': '.*.example.com'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 body=self._build_body(new_l7rule), status=409)

    def test_delete_when_lb_pending_update(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.put(self.LB_PATH.format(lb_id=self.lb_id),
                 body={'loadbalancer': {'name': 'test_name_change'}})
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                    status=409)

    def test_create_when_lb_pending_delete(self):
        self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        new_l7rule = {'type': constants.L7RULE_TYPE_HEADER,
                      'compare_type':
                          constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
                      'value': 'some-string',
                      'key': 'Some-header'}
        self.post(self.l7rules_path, body=self._build_body(new_l7rule),
                  status=409)

    def test_update_when_lb_pending_delete(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        new_l7rule = {'type': constants.L7RULE_TYPE_COOKIE,
                      'compare_type':
                          constants.L7RULE_COMPARE_TYPE_ENDS_WITH,
                      'value': 'some-string',
                      'key': 'some-cookie'}
        self.put(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                 body=self._build_body(new_l7rule), status=409)

    def test_delete_when_lb_pending_delete(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        self.set_lb_status(self.lb_id)
        self.delete(self.LB_PATH.format(lb_id=self.lb_id),
                    params={'cascade': "true"})
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                    status=409)

    def test_delete_already_deleted(self):
        l7rule = self.create_l7rule(
            self.l7policy_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api').get(self.root_tag)
        # This updates the child objects
        self.set_lb_status(self.lb_id, status=constants.DELETED)
        self.delete(self.l7rule_path.format(l7rule_id=l7rule.get('id')),
                    status=204)
