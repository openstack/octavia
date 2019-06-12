# Copyright 2019 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from octavia_lib.common import constants as lib_consts
from oslo_utils import uuidutils

from octavia.api.drivers.driver_agent import driver_get
from octavia.common import constants
import octavia.tests.unit.base as base


class TestDriverGet(base.TestCase):

    @mock.patch('octavia.db.api.get_session')
    def _test_process_get_object(self, object_name, mock_object_repo,
                                 mock_object_to_provider, mock_get_session):
        mock_get_session.return_value = 'bogus_session'
        object_repo_mock = mock.MagicMock()
        mock_object_repo.return_value = object_repo_mock
        db_object_mock = mock.MagicMock()
        object_repo_mock.get.return_value = db_object_mock

        mock_prov_object = mock.MagicMock()
        mock_object_to_provider.return_value = mock_prov_object
        ref_prov_dict = mock_prov_object.to_dict(recurse=True,
                                                 render_unsets=True)

        object_id = uuidutils.generate_uuid()

        data = {constants.OBJECT: object_name, lib_consts.ID: object_id}

        # Happy path
        result = driver_get.process_get(data)

        mock_object_repo.assert_called_once_with()
        object_repo_mock.get.assert_called_once_with(
            'bogus_session', id=object_id, show_deleted=False)
        mock_object_to_provider.assert_called_once_with(db_object_mock)
        self.assertEqual(ref_prov_dict, result)

        # No matching listener
        mock_object_repo.reset_mock()
        mock_object_to_provider.reset_mock()

        object_repo_mock.get.return_value = None

        result = driver_get.process_get(data)

        mock_object_repo.assert_called_once_with()
        object_repo_mock.get.assert_called_once_with(
            'bogus_session', id=object_id, show_deleted=False)
        mock_object_to_provider.assert_not_called()
        self.assertEqual({}, result)

    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository')
    def test_process_get_loadbalancer(self, mock_lb_repo, mock_lb_to_provider):
        self._test_process_get_object(
            lib_consts.LOADBALANCERS, mock_lb_repo, mock_lb_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_listener_to_provider_listener')
    @mock.patch('octavia.db.repositories.ListenerRepository')
    def test_process_get_listener(self, mock_listener_repo,
                                  mock_listener_to_provider):
        self._test_process_get_object(lib_consts.LISTENERS, mock_listener_repo,
                                      mock_listener_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_pool_to_provider_pool')
    @mock.patch('octavia.db.repositories.PoolRepository')
    def test_process_get_pool(self, mock_pool_repo, mock_pool_to_provider):
        self._test_process_get_object(lib_consts.POOLS, mock_pool_repo,
                                      mock_pool_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_member_to_provider_member')
    @mock.patch('octavia.db.repositories.MemberRepository')
    def test_process_get_member(self, mock_member_repo,
                                mock_member_to_provider):
        self._test_process_get_object(lib_consts.MEMBERS, mock_member_repo,
                                      mock_member_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_HM_to_provider_HM')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository')
    def test_process_get_healthmonitor(self, mock_hm_repo,
                                       mock_hm_to_provider):
        self._test_process_get_object(lib_consts.HEALTHMONITORS, mock_hm_repo,
                                      mock_hm_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_l7policy_to_provider_l7policy')
    @mock.patch('octavia.db.repositories.L7PolicyRepository')
    def test_process_get_l7policy(self, mock_l7policy_repo,
                                  mock_l7policy_to_provider):
        self._test_process_get_object(lib_consts.L7POLICIES,
                                      mock_l7policy_repo,
                                      mock_l7policy_to_provider)

    @mock.patch('octavia.api.drivers.utils.db_l7rule_to_provider_l7rule')
    @mock.patch('octavia.db.repositories.L7RuleRepository')
    def test_process_get_l7rule(self, mock_l7rule_repo,
                                mock_l7rule_to_provider):
        self._test_process_get_object(lib_consts.L7RULES, mock_l7rule_repo,
                                      mock_l7rule_to_provider)

    @mock.patch('octavia.db.api.get_session')
    def test_process_get_bogus_object(self, mock_get_session):
        data = {constants.OBJECT: 'bogus', lib_consts.ID: 'bad ID'}
        result = driver_get.process_get(data)
        self.assertEqual({}, result)
