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

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants as const
from octavia.tests.functional.api.v1 import base

CONF = cfg.CONF


class TestQuotas(base.BaseAPITest):

    def setUp(self):
        super(TestQuotas, self).setUp()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(
            group="quotas",
            default_load_balancer_quota=random.randrange(const.QUOTA_UNLIMITED,
                                                         9000))
        conf.config(
            group="quotas",
            default_listener_quota=random.randrange(const.QUOTA_UNLIMITED,
                                                    9000))
        conf.config(
            group="quotas",
            default_member_quota=random.randrange(const.QUOTA_UNLIMITED, 9000))
        # We need to make sure unlimited gets tested each pass
        conf.config(group="quotas", default_pool_quota=const.QUOTA_UNLIMITED)
        conf.config(
            group="quotas",
            default_health_monitor_quota=random.randrange(
                const.QUOTA_UNLIMITED, 9000))

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
        self.assertEqual({'quotas': []}, quota_list)

    def test_get_all_quotas_with_quotas(self):
        project_id1 = uuidutils.generate_uuid()
        project_id2 = uuidutils.generate_uuid()
        quota_path1 = self.QUOTA_PATH.format(project_id=project_id1)
        quota1 = {'load_balancer': const.QUOTA_UNLIMITED, 'listener': 30,
                  'pool': 30, 'health_monitor': 30, 'member': 30}
        body1 = {'quota': quota1}
        self.put(quota_path1, body1)
        quota_path2 = self.QUOTA_PATH.format(project_id=project_id2)
        quota2 = {'load_balancer': 50, 'listener': 50, 'pool': 50,
                  'health_monitor': 50, 'member': 50}
        body2 = {'quota': quota2}
        self.put(quota_path2, body2)

        response = self.get(self.QUOTAS_PATH)
        quota_list = response.json

        quota1['project_id'] = project_id1
        quota1['tenant_id'] = project_id1
        quota2['project_id'] = project_id2
        quota2['tenant_id'] = project_id2
        expected = {'quotas': [quota1, quota2]}
        self.assertEqual(expected, quota_list)

    def test_get_default_quotas(self):
        response = self.get(self.QUOTA_DEFAULT_PATH.format(
            project_id=self.project_id))
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])

    def test_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])

    def test_custom_partial_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': None, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        expected_body = {'quota': {
            'load_balancer': 30,
            'listener': CONF.quotas.default_listener_quota, 'pool': 30,
            'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body)
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
        self.put(quota_path, body)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'],
                                  expected=expected_body['quota'])

    def test_delete_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id=self.project_id)
        body = {'quota': {'load_balancer': 30, 'listener': 30, 'pool': 30,
                          'health_monitor': 30, 'member': 30}}
        self.put(quota_path, body)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'], expected=body['quota'])
        self.delete(quota_path)
        response = self.get(quota_path)
        quota_dict = response.json
        self._assert_quotas_equal(quota_dict['quota'])

    def test_delete_non_existent_custom_quotas(self):
        quota_path = self.QUOTA_PATH.format(project_id='bogus')
        self.delete(quota_path, status=404)
