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
import mock
import random

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
import octavia.common.context
from octavia.tests.functional.api.v2 import base

CONF = cfg.CONF


class TestQuotas(base.BaseAPITest):

    root_tag = 'quota'
    root_tag_list = 'quotas'
    root_tag_links = 'quotas_links'

    def setUp(self):
        super(TestQuotas, self).setUp()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(
            group="quotas",
            default_load_balancer_quota=random.randrange(
                constants.QUOTA_UNLIMITED, 9000))
        conf.config(
            group="quotas",
            default_listener_quota=random.randrange(
                constants.QUOTA_UNLIMITED, 9000))
        conf.config(
            group="quotas",
            default_member_quota=random.randrange(
                constants.QUOTA_UNLIMITED, 9000))
        # We need to make sure unlimited gets tested each pass
        conf.config(group="quotas",
                    default_pool_quota=constants.QUOTA_UNLIMITED)
        conf.config(
            group="quotas",
            default_health_monitor_quota=random.randrange(
                constants.QUOTA_UNLIMITED, 9000))

        self.project_id = uuidutils.generate_uuid()

    def _assert_quotas_equal(self, observed, expected=None):
        if not expected:
            expected = {'load_balancer':
                        CONF.quotas.default_load_balancer_quota,
                        'listener': CONF.quotas.default_listener_quota,
                        'pool': CONF.quotas.default_pool_quota,
                        'health_monitor':
                        CONF.quotas.default_health_monitor_quota,
                        'member': CONF.quotas.default_member_quota}
        self.assertEqual(expected['load_balancer'], observed['load_balancer'])
        self.assertEqual(expected['listener'], observed['listener'])
        self.assertEqual(expected['pool'], observed['pool'])
        self.assertEqual(expected['health_monitor'],
                         observed['health_monitor'])
        self.assertEqual(expected['member'], observed['member'])

    def test_get_all_quotas_no_quotas(self):
        response = self.get(self.QUOTAS_PATH)
        quota_list = response.json
        self.assertEqual({'quotas': [], 'quotas_links': []}, quota_list)

    def test_get_all_quotas_with_quotas(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        quota_path1 = self.QUOTA_PATH.format(project_id=project_id1)
        quota1 = {'load_balancer': constants.QUOTA_UNLIMITED, 'listener': 30,
                  'pool': 30, 'health_monitor': 30, 'member': 30}
        body1 = {'quota': quota1}
        self.put(quota_path1, body1, status=202)
        quota_path2 = self.QUOTA_PATH.format(project_id=project_id2)
        quota2 = {'load_balancer': 50, 'listener': 50, 'pool': 50,
                  'health_monitor': 50, 'member': 50}
        body2 = {'quota': quota2}
        self.put(quota_path2, body2, status=202)

        response = self.get(self.QUOTAS_PATH)
        quota_list = response.json

        quota1['project_id'] = project_id1
        quota2['project_id'] = project_id2
        expected = {'quotas': [quota1, quota2], 'quotas_links': []}
        self.assertEqual(expected, quota_list)

    def test_get_all_not_Authorized(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        quota_path1 = self.QUOTA_PATH.format(project_id=project_id1)
        quota1 = {'load_balancer': constants.QUOTA_UNLIMITED, 'listener': 30,
                  'pool': 30, 'health_monitor': 30, 'member': 30}
        body1 = {'quota': quota1}
        self.put(quota_path1, body1, status=202)
        quota_path2 = self.QUOTA_PATH.format(project_id=project_id2)
        quota2 = {'load_balancer': 50, 'listener': 50, 'pool': 50,
                  'health_monitor': 50, 'member': 50}
        body2 = {'quota': quota2}
        self.put(quota_path2, body2, status=202)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
                response = self.get(self.QUOTAS_PATH, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_all_not_Authorized_no_role(self):
        project_id1 = uuidutils.generate_uuid()
        quota_path1 = self.QUOTA_PATH.format(project_id=project_id1)
        quota1 = {'load_balancer': constants.QUOTA_UNLIMITED, 'listener': 30,
                  'pool': 30, 'health_monitor': 30, 'member': 30}
        body1 = {'quota': quota1}
        self.put(quota_path1, body1, status=202)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project_id1):
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
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.QUOTAS_PATH, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_all_not_Authorized_bogus_role(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        quota_path1 = self.QUOTA_PATH.format(project_id=project_id1)
        quota1 = {'load_balancer': constants.QUOTA_UNLIMITED, 'listener': 30,
                  'pool': 30, 'health_monitor': 30, 'member': 30}
        body1 = {'quota': quota1}
        self.put(quota_path1, body1, status=202)
        quota_path2 = self.QUOTA_PATH.format(project_id=project_id2)
        quota2 = {'load_balancer': 50, 'listener': 50, 'pool': 50,
                  'health_monitor': 50, 'member': 50}
        body2 = {'quota': quota2}
        self.put(quota_path2, body2, status=202)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_bogus'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                response = self.get(self.QUOTAS_PATH, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_get_all_admin(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        project_id3 = uuidutils.generate_uuid()
        quota1 = self.create_quota(
            project_id=project_id1, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        quota2 = self.create_quota(
            project_id=project_id2, lb_quota=2, member_quota=2
        ).get(self.root_tag)
        quota3 = self.create_quota(
            project_id=project_id3, lb_quota=3, member_quota=3
        ).get(self.root_tag)
        quotas = self.get(self.QUOTAS_PATH).json.get(self.root_tag_list)
        self.assertEqual(3, len(quotas))
        quota_lb_member_quotas = [(l.get('load_balancer'), l.get('member'))
                                  for l in quotas]
        self.assertIn((quota1.get('load_balancer'), quota1.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota2.get('load_balancer'), quota2.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota3.get('load_balancer'), quota3.get('member')),
                      quota_lb_member_quotas)

    def test_get_all_non_admin_global_observer(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        project_id3 = uuidutils.generate_uuid()
        quota1 = self.create_quota(
            project_id=project_id1, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        quota2 = self.create_quota(
            project_id=project_id2, lb_quota=2, member_quota=2
        ).get(self.root_tag)
        quota3 = self.create_quota(
            project_id=project_id3, lb_quota=3, member_quota=3
        ).get(self.root_tag)
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
                'roles': ['load-balancer_global_observer'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                quotas = self.get(self.QUOTAS_PATH)
                quotas = quotas.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(3, len(quotas))
        quota_lb_member_quotas = [(l.get('load_balancer'), l.get('member'))
                                  for l in quotas]
        self.assertIn((quota1.get('load_balancer'), quota1.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota2.get('load_balancer'), quota2.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota3.get('load_balancer'), quota3.get('member')),
                      quota_lb_member_quotas)

    def test_get_all_quota_admin(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        project_id3 = uuidutils.generate_uuid()
        quota1 = self.create_quota(
            project_id=project_id1, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        quota2 = self.create_quota(
            project_id=project_id2, lb_quota=2, member_quota=2
        ).get(self.root_tag)
        quota3 = self.create_quota(
            project_id=project_id3, lb_quota=3, member_quota=3
        ).get(self.root_tag)
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
                'roles': ['load-balancer_quota_admin'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                quotas = self.get(self.QUOTAS_PATH)
                quotas = quotas.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(3, len(quotas))
        quota_lb_member_quotas = [(l.get('load_balancer'), l.get('member'))
                                  for l in quotas]
        self.assertIn((quota1.get('load_balancer'), quota1.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota2.get('load_balancer'), quota2.get('member')),
                      quota_lb_member_quotas)
        self.assertIn((quota3.get('load_balancer'), quota3.get('member')),
                      quota_lb_member_quotas)

    def test_get_all_non_admin(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        project3_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.create_quota(
            project_id=project2_id, lb_quota=2, member_quota=2
        ).get(self.root_tag)
        quota3 = self.create_quota(
            project_id=project3_id, lb_quota=3, member_quota=3
        ).get(self.root_tag)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project3_id):
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
                'project_id': project3_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                quotas = self.get(self.QUOTAS_PATH)
                quotas = quotas.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(1, len(quotas))
        quota_lb_member_quotas = [(l.get('load_balancer'), l.get('member'))
                                  for l in quotas]
        self.assertIn((quota3.get('load_balancer'), quota3.get('member')),
                      quota_lb_member_quotas)

    def test_get_all_non_admin_observer(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        project3_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.create_quota(
            project_id=project2_id, lb_quota=2, member_quota=2
        ).get(self.root_tag)
        quota3 = self.create_quota(
            project_id=project3_id, lb_quota=3, member_quota=3
        ).get(self.root_tag)

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings',
                         auth_strategy=constants.KEYSTONE)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project3_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': ['load-balancer_observer'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project3_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                quotas = self.get(self.QUOTAS_PATH)
                quotas = quotas.json.get(self.root_tag_list)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

        self.assertEqual(1, len(quotas))
        quota_lb_member_quotas = [(l.get('load_balancer'), l.get('member'))
                                  for l in quotas]
        self.assertIn((quota3.get('load_balancer'), quota3.get('member')),
                      quota_lb_member_quotas)

    def test_get_by_project_id(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        quota1 = self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        quota2 = self.create_quota(
            project_id=project2_id, lb_quota=2, member_quota=2
        ).get(self.root_tag)

        quotas = self.get(
            self.QUOTA_PATH.format(project_id=project1_id)
        ).json.get(self.root_tag)
        self._assert_quotas_equal(quotas, quota1)
        quotas = self.get(
            self.QUOTA_PATH.format(project_id=project2_id)
        ).json.get(self.root_tag)
        self._assert_quotas_equal(quotas, quota2)

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
        quota1 = self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project1_id):
            override_credentials = {
                'service_user_id': None,
                'user_domain_id': None,
                'is_admin_project': True,
                'service_project_domain_id': None,
                'service_project_id': None,
                'roles': [role],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': project1_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                quotas = self.get(
                    self.QUOTA_PATH.format(project_id=project1_id)
                ).json.get(self.root_tag)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self._assert_quotas_equal(quotas, quota1)

    def test_get_not_Authorized(self):
        project1_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            quotas = self.get(self.QUOTA_PATH.format(project_id=project1_id),
                              status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, quotas.json)

    def test_get_not_Authorized_bogus_role(self):
        project1_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project1_id):
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
                quotas = self.get(
                    self.QUOTA_PATH.format(project_id=project1_id),
                    status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, quotas.json)

    def test_get_not_Authorized_no_role(self):
        project1_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=1, member_quota=1
        ).get(self.root_tag)
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               project1_id):
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
                quotas = self.get(
                    self.QUOTA_PATH.format(project_id=project1_id),
                    status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, quotas.json)

    def test_get_all_sorted(self):
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        project3_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=3, member_quota=8
        ).get(self.root_tag)
        self.create_quota(
            project_id=project2_id, lb_quota=2, member_quota=10
        ).get(self.root_tag)
        self.create_quota(
            project_id=project3_id, lb_quota=1, member_quota=9
        ).get(self.root_tag)
        response = self.get(self.QUOTAS_PATH,
                            params={'sort': 'load_balancer:desc'})
        quotas_desc = response.json.get(self.root_tag_list)
        response = self.get(self.QUOTAS_PATH,
                            params={'sort': 'load_balancer:asc'})
        quotas_asc = response.json.get(self.root_tag_list)

        self.assertEqual(3, len(quotas_desc))
        self.assertEqual(3, len(quotas_asc))

        quota_lb_member_desc = [(l.get('load_balancer'), l.get('member'))
                                for l in quotas_desc]
        quota_lb_member_asc = [(l.get('load_balancer'), l.get('member'))
                               for l in quotas_asc]
        self.assertEqual(quota_lb_member_asc,
                         list(reversed(quota_lb_member_desc)))

    def test_get_all_limited(self):
        self.skipTest("No idea how this should work yet")
        # TODO(rm_work): Figure out how to make this ... work
        project1_id = uuidutils.generate_uuid()
        project2_id = uuidutils.generate_uuid()
        project3_id = uuidutils.generate_uuid()
        self.create_quota(
            project_id=project1_id, lb_quota=3, member_quota=8
        ).get(self.root_tag)
        self.create_quota(
            project_id=project2_id, lb_quota=2, member_quota=10
        ).get(self.root_tag)
        self.create_quota(
            project_id=project3_id, lb_quota=1, member_quota=9
        ).get(self.root_tag)

        # First two -- should have 'next' link
        first_two = self.get(self.QUOTAS_PATH, params={'limit': 2}).json
        objs = first_two[self.root_tag_list]
        links = first_two[self.root_tag_links]
        self.assertEqual(2, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('next', links[0]['rel'])

        # Third + off the end -- should have previous link
        third = self.get(self.QUOTAS_PATH, params={
            'limit': 2,
            'marker': first_two[self.root_tag_list][1]['id']}).json
        objs = third[self.root_tag_list]
        links = third[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(1, len(links))
        self.assertEqual('previous', links[0]['rel'])

        # Middle -- should have both links
        middle = self.get(self.QUOTAS_PATH, params={
            'limit': 1,
            'marker': first_two[self.root_tag_list][0]['id']}).json
        objs = middle[self.root_tag_list]
        links = middle[self.root_tag_links]
        self.assertEqual(1, len(objs))
        self.assertEqual(2, len(links))
        self.assertItemsEqual(['previous', 'next'], [l['rel'] for l in links])

    def test_get_default_quotas(self):
        response = self.get(self.QUOTA_DEFAULT_PATH.format(
            project_id=self.project_id))
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])

    def test_get_default_quotas_Authorized(self):
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
                response = self.get(self.QUOTA_DEFAULT_PATH.format(
                    project_id=self.project_id))
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_get_default_quotas_not_Authorized(self):
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        auth_strategy = self.conf.conf.api_settings.get('auth_strategy')
        self.conf.config(group='api_settings', auth_strategy=constants.TESTING)
        with mock.patch.object(octavia.common.context.Context, 'project_id',
                               uuidutils.generate_uuid()):
            response = self.get(self.QUOTA_DEFAULT_PATH.format(
                project_id=self.project_id), status=403)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)

    def test_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])

    def test_custom_quotas_quota_admin(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
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
                'roles': ['load-balancer_quota_admin'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.put(quota_path, body, status=202)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])

    def test_custom_quotas_not_Authorized_member(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
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
                response = self.put(quota_path, body, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        self.assertEqual(self.NOT_AUTHORIZED_BODY, response.json)

    def test_custom_partial_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': None, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        expected_body = {'quota': {
            'load_balancer': 30,
            'listener': CONF.quotas.default_listener_quota, 'pool': 30,
            'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'],
                                  expected=expected_body['quota'])

    def test_custom_missing_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        expected_body = {'quota': {
            'load_balancer': 30,
            'listener': CONF.quotas.default_listener_quota, 'pool': 30,
            'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'],
                                  expected=expected_body['quota'])

    def test_delete_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])
        self.delete(quota_path, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])

    def test_delete_custom_quotas_admin(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])
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
                'roles': ['load-balancer_quota_admin'],
                'user_id': None,
                'is_admin': False,
                'service_user_domain_id': None,
                'project_domain_id': None,
                'service_roles': [],
                'project_id': self.project_id}
            with mock.patch(
                    "oslo_context.context.RequestContext.to_policy_values",
                    return_value=override_credentials):
                self.delete(quota_path, status=202)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])

    def test_delete_quotas_not_Authorized_member(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body, status=202)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])
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
                self.delete(quota_path, status=403)
        self.conf.config(group='api_settings', auth_strategy=auth_strategy)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])

    def test_delete_non_existent_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id='bogus')
        self.delete(quota_path, status=404)
