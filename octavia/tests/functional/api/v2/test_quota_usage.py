# Copyright 2016 Rackspace
# All Rights Reserved.
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
import random

from unittest import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base

CONF = cfg.CONF


class TestQuotaUsage(base.BaseAPITest):

    root_tag = 'quota_usage'

    def setUp(self):
        super(TestQuotaUsage, self).setUp()
        self.project_id = uuidutils.generate_uuid()

    def test_get_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        # Create first load balancer with sub-resources
        lb1 = self.create_load_balancer(uuidutils.generate_uuid(),
                                        name='lb1', project_id=project1_id,
                                        tags=['test_tag1'])
        lb1_id = lb1.get('loadbalancer').get('id')
        self.set_lb_status(lb1_id)
        listener1 = self.create_listener(
            constants.PROTOCOL_HTTP, 80, lb1_id,
            tags=['test_tag1'])
        listener1_id = listener1.get('listener').get('id')
        self.set_lb_status(lb1_id)
        pool1 = self.create_pool(
            lb1_id,
            constants.PROTOCOL_HTTP,
            constants.LB_ALGORITHM_ROUND_ROBIN,
            listener_id=listener1_id)
        pool1_id = pool1.get('pool').get('id')
        self.set_lb_status(lb1_id)
        self.set_object_status(self.pool_repo, pool1_id)
        self.create_member(
            pool1_id, '192.0.2.1', 80)
        self.set_lb_status(lb1_id)
        self.set_object_status(self.pool_repo, pool1_id)
        self.create_member(
            pool1_id, '192.0.2.2', 80)
        self.set_lb_status(lb1_id)
        self.create_health_monitor(
            pool1_id, constants.HEALTH_MONITOR_HTTP,
            1, 1, 1, 1)
        self.set_lb_status(lb1_id)
        l7policy1 = self.create_l7policy(
            listener1_id,
            constants.L7POLICY_ACTION_REJECT,
            tags=['test_tag'])
        l7policy1_id = l7policy1.get('l7policy').get('id')
        self.set_lb_status(lb1_id)
        self.create_l7rule(
            l7policy1_id, constants.L7RULE_TYPE_PATH,
            constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            '/api', tags=['test_tag'])
        # Create second load balancer without any sub-resources
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2', project_id=project2_id,
                                  tags=['test_tag2'])
        usage1 = {
            'healthmonitor': 1,
            'listener': 1,
            'loadbalancer': 1,
            'pool': 1,
            'member': 2,
            'l7policy': 1,
            'l7rule': 1,
        }
        usage2 = {
            'healthmonitor': 0,
            'listener': 0,
            'loadbalancer': 1,
            'pool': 0,
            'member': 0,
            'l7policy': 0,
            'l7rule': 0,
        }

        quota_usage = self.get(
            self.QUOTA_USAGE_PATH.format(project_id=project1_id)
        ).json.get(self.root_tag)
        self.assertEqual(usage1, quota_usage)
        quota_usage = self.get(
            self.QUOTA_USAGE_PATH.format(project_id=project2_id)
        ).json.get(self.root_tag)
        self.assertEqual(usage2, quota_usage)

    def test_get_Authorized_member(self):
        self._test_get_Authorized('load-balancer_member')

    def test_get_Authorized_observer(self):
        self._test_get_Authorized('load-balancer_observer')

    def test_get_Authorized_global_observer(self):
        self._test_get_Authorized('load-balancer_global_observer')

    def test_get_Authorized_quota_admin(self):
        self._test_get_Authorized('load-balancer_quota_admin')

    def _test_get_Authorized(self, role):
        project1_id = uuidutils.generate_uuid()
        self.create_load_balancer(uuidutils.generate_uuid(),
                                  name='lb2', project_id=project1_id,
                                  tags=['test_tag2'])
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id', project1_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_member'],
                'user_id': None,
                'is_admin': True,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project1_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                result = self.get(
                    self.QUOTA_USAGE_PATH.format(project_id=project1_id)
                ).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        usage = {
            'healthmonitor': 0,
            'listener': 0,
            'loadbalancer': 1,
            'pool': 0,
            'member': 0,
            'l7policy': 0,
            'l7rule': 0,
        }
        self.assertEqual(usage, result)

    def test_get_not_Authorized(self):
        project1_id = uuidutils.generate_uuid()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id', uuidutils.generate_uuid()):
            result = self.get(self.QUOTA_USAGE_PATH.format(project_id=project1_id),
                              status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, result.json)

    def test_get_not_Authorized_bogus_role(self):
        project1_id = uuidutils.generate_uuid()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id', project1_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer:bogus'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project1_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                result = self.get(
                    self.QUOTA_USAGE_PATH.format(project_id=project1_id),
                    status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, result.json)

    def test_get_not_Authorized_no_role(self):
        project1_id = uuidutils.generate_uuid()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.RequestContext,
                               'project_id', project1_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': [],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project1_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                result = self.get(
                    self.QUOTA_USAGE_PATH.format(project_id=project1_id),
                    status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, result.json)
