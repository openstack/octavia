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

import mock
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
import pecan
import pecan.testing

from octavia.api import config as pconfig
# needed for tests to function when run independently:
from octavia.common import config  # noqa: F401
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import repositories
from octavia.tests.functional.db import base as base_db_test


class BaseAPITest(base_db_test.OctaviaDBTestBase):

    BASE_PATH = '/v1'
    QUOTAS_PATH = '/quotas'
    QUOTA_PATH = QUOTAS_PATH + '/{project_id}'
    QUOTA_DEFAULT_PATH = QUOTAS_PATH + '/{project_id}/default'
    LBS_PATH = '/loadbalancers'
    LB_PATH = LBS_PATH + '/{lb_id}'
    LB_DELETE_CASCADE_PATH = LB_PATH + '/delete_cascade'
    LB_STATS_PATH = LB_PATH + '/stats'
    LISTENERS_PATH = LB_PATH + '/listeners'
    LISTENER_PATH = LISTENERS_PATH + '/{listener_id}'
    LISTENER_STATS_PATH = LISTENER_PATH + '/stats'
    POOLS_PATH = LB_PATH + '/pools'
    POOL_PATH = POOLS_PATH + '/{pool_id}'
    DEPRECATED_POOLS_PATH = LISTENER_PATH + '/pools'
    DEPRECATED_POOL_PATH = DEPRECATED_POOLS_PATH + '/{pool_id}'
    MEMBERS_PATH = POOL_PATH + '/members'
    MEMBER_PATH = MEMBERS_PATH + '/{member_id}'
    DEPRECATED_MEMBERS_PATH = DEPRECATED_POOL_PATH + '/members'
    DEPRECATED_MEMBER_PATH = DEPRECATED_MEMBERS_PATH + '/{member_id}'
    HM_PATH = POOL_PATH + '/healthmonitor'
    DEPRECATED_HM_PATH = DEPRECATED_POOL_PATH + '/healthmonitor'
    L7POLICIES_PATH = LISTENER_PATH + '/l7policies'
    L7POLICY_PATH = L7POLICIES_PATH + '/{l7policy_id}'
    L7RULES_PATH = L7POLICY_PATH + '/l7rules'
    L7RULE_PATH = L7RULES_PATH + '/{l7rule_id}'

    def setUp(self):
        super(BaseAPITest, self).setUp()
        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(group='api_settings', api_handler='simulated_handler')
        conf.config(group="controller_worker",
                    network_driver='network_noop_driver')
        conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.lb_repo = repositories.LoadBalancerRepository()
        self.listener_repo = repositories.ListenerRepository()
        self.listener_stats_repo = repositories.ListenerStatisticsRepository()
        self.pool_repo = repositories.PoolRepository()
        self.member_repo = repositories.MemberRepository()
        self.amphora_repo = repositories.AmphoraRepository()
        patcher = mock.patch('octavia.api.handlers.controller_simulator.'
                             'handler.SimulatedControllerHandler')
        self.handler_mock = patcher.start()
        self.check_quota_met_true_mock = mock.patch(
            'octavia.db.repositories.Repositories.check_quota_met',
            return_value=True)
        self.app = self._make_app()
        self.project_id = uuidutils.generate_uuid()

        def reset_pecan():
            patcher.stop()
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _make_app(self):
        return pecan.testing.load_test_app(
            {'app': pconfig.app, 'wsme': pconfig.wsme})

    def _get_full_path(self, path):
        return ''.join([self.BASE_PATH, path])

    def delete(self, path, headers=None, status=202, expect_errors=False):
        headers = headers or {}
        full_path = self._get_full_path(path)
        response = self.app.delete(full_path,
                                   headers=headers,
                                   status=status,
                                   expect_errors=expect_errors)
        return response

    def post(self, path, body, headers=None, status=202, expect_errors=False):
        headers = headers or {}
        full_path = self._get_full_path(path)
        response = self.app.post_json(full_path,
                                      params=body,
                                      headers=headers,
                                      status=status,
                                      expect_errors=expect_errors)
        return response

    def put(self, path, body, headers=None, status=202, expect_errors=False):
        headers = headers or {}
        full_path = self._get_full_path(path)
        response = self.app.put_json(full_path,
                                     params=body,
                                     headers=headers,
                                     status=status,
                                     expect_errors=expect_errors)
        return response

    def get(self, path, params=None, headers=None, status=200,
            expect_errors=False):
        full_path = self._get_full_path(path)
        response = self.app.get(full_path,
                                params=params,
                                headers=headers,
                                status=status,
                                expect_errors=expect_errors)
        return response

    def create_load_balancer(self, vip, **optionals):
        req_dict = {'vip': vip, 'project_id': self.project_id}
        req_dict.update(optionals)
        response = self.post(self.LBS_PATH, req_dict)
        return response.json

    def create_listener(self, lb_id, protocol, protocol_port, **optionals):
        req_dict = {'protocol': protocol, 'protocol_port': protocol_port,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.LISTENERS_PATH.format(lb_id=lb_id)
        response = self.post(path, req_dict)
        return response.json

    def create_listener_stats(self, listener_id, amphora_id):
        db_ls = self.listener_stats_repo.create(
            db_api.get_session(), listener_id=listener_id,
            amphora_id=amphora_id, bytes_in=0,
            bytes_out=0, active_connections=0, total_connections=0,
            request_errors=0)
        return db_ls.to_dict()

    def create_amphora(self, amphora_id, loadbalancer_id, **optionals):
        # We need to default these values in the request.
        opts = {'compute_id': uuidutils.generate_uuid(),
                'status': constants.ACTIVE}
        opts.update(optionals)
        amphora = self.amphora_repo.create(
            self.session, id=amphora_id,
            load_balancer_id=loadbalancer_id,
            **opts)
        return amphora

    def get_listener(self, lb_id, listener_id):
        path = self.LISTENER_PATH.format(lb_id=lb_id, listener_id=listener_id)
        response = self.get(path)
        return response.json

    def create_pool_sans_listener(self, lb_id, protocol, lb_algorithm,
                                  **optionals):
        req_dict = {'protocol': protocol, 'lb_algorithm': lb_algorithm,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.POOLS_PATH.format(lb_id=lb_id)
        response = self.post(path, req_dict)
        return response.json

    def create_pool(self, lb_id, listener_id, protocol, lb_algorithm,
                    **optionals):
        req_dict = {'protocol': protocol, 'lb_algorithm': lb_algorithm,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.DEPRECATED_POOLS_PATH.format(lb_id=lb_id,
                                                 listener_id=listener_id)
        response = self.post(path, req_dict)
        return response.json

    def create_member(self, lb_id, pool_id, ip_address,
                      protocol_port, expect_error=False, **optionals):
        req_dict = {'ip_address': ip_address, 'protocol_port': protocol_port,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.MEMBERS_PATH.format(lb_id=lb_id, pool_id=pool_id)
        response = self.post(path, req_dict, expect_errors=expect_error)
        return response.json

    def create_member_with_listener(self, lb_id, listener_id, pool_id,
                                    ip_address, protocol_port, **optionals):
        req_dict = {'ip_address': ip_address, 'protocol_port': protocol_port,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.DEPRECATED_MEMBERS_PATH.format(
            lb_id=lb_id, listener_id=listener_id, pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def create_health_monitor(self, lb_id, pool_id, type,
                              delay, timeout, fall_threshold, rise_threshold,
                              **optionals):
        req_dict = {'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'fall_threshold': fall_threshold,
                    'rise_threshold': rise_threshold,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.HM_PATH.format(lb_id=lb_id,
                                   pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def create_health_monitor_with_listener(
            self, lb_id, listener_id, pool_id, type,
            delay, timeout, fall_threshold, rise_threshold, **optionals):
        req_dict = {'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'fall_threshold': fall_threshold,
                    'rise_threshold': rise_threshold,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        path = self.DEPRECATED_HM_PATH.format(
            lb_id=lb_id, listener_id=listener_id, pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def create_l7policy(self, lb_id, listener_id, action, **optionals):
        req_dict = {'action': action}
        req_dict.update(optionals)
        path = self.L7POLICIES_PATH.format(lb_id=lb_id,
                                           listener_id=listener_id)
        response = self.post(path, req_dict)
        return response.json

    def create_l7rule(self, lb_id, listener_id, l7policy_id, type,
                      compare_type, value, **optionals):
        req_dict = {'type': type, 'compare_type': compare_type, 'value': value}
        req_dict.update(optionals)
        path = self.L7RULES_PATH.format(lb_id=lb_id, listener_id=listener_id,
                                        l7policy_id=l7policy_id)
        response = self.post(path, req_dict)
        return response.json

    def _set_lb_and_children_statuses(self, lb_id, prov_status, op_status):
        self.lb_repo.update(db_api.get_session(), lb_id,
                            provisioning_status=prov_status,
                            operating_status=op_status)
        lb_listeners, _ = self.listener_repo.get_all(
            db_api.get_session(), load_balancer_id=lb_id)
        for listener in lb_listeners:
            for pool in listener.pools:
                self.pool_repo.update(db_api.get_session(), pool.id,
                                      operating_status=op_status)
                for member in pool.members:
                    self.member_repo.update(db_api.get_session(), member.id,
                                            operating_status=op_status)
            self.listener_repo.update(db_api.get_session(), listener.id,
                                      provisioning_status=prov_status,
                                      operating_status=op_status)

    def set_lb_status(self, lb_id, status=constants.ACTIVE):
        if status == constants.DELETED:
            op_status = constants.OFFLINE
        elif status == constants.ACTIVE:
            op_status = constants.ONLINE
        else:
            db_lb = self.lb_repo.get(db_api.get_session(), id=lb_id)
            op_status = db_lb.operating_status
        self._set_lb_and_children_statuses(lb_id, status, op_status)
        return self.get(self.LB_PATH.format(lb_id=lb_id)).json

    def assert_final_lb_statuses(self, lb_id, delete=False):
        expected_prov_status = constants.ACTIVE
        expected_op_status = constants.ONLINE
        if delete:
            expected_prov_status = constants.DELETED
            expected_op_status = constants.OFFLINE
        self.set_lb_status(lb_id, status=expected_prov_status)
        self.assert_correct_lb_status(lb_id, expected_prov_status,
                                      expected_op_status)

    def assert_final_listener_statuses(self, lb_id, listener_id, delete=False):
        expected_prov_status = constants.ACTIVE
        expected_op_status = constants.ONLINE
        if delete:
            expected_prov_status = constants.DELETED
            expected_op_status = constants.OFFLINE
        self.set_lb_status(lb_id, status=expected_prov_status)
        self.assert_correct_listener_status(lb_id, listener_id,
                                            expected_prov_status,
                                            expected_op_status)

    def assert_correct_lb_status(self, lb_id, provisioning_status,
                                 operating_status):
        api_lb = self.get(self.LB_PATH.format(lb_id=lb_id)).json
        self.assertEqual(provisioning_status,
                         api_lb.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_lb.get('operating_status'))

    def assert_correct_listener_status(self, lb_id, listener_id,
                                       provisioning_status, operating_status):
        api_listener = self.get(self.LISTENER_PATH.format(
            lb_id=lb_id, listener_id=listener_id)).json
        self.assertEqual(provisioning_status,
                         api_listener.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_listener.get('operating_status'))
