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
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import repositories
from octavia.tests.functional.db import base as base_db_test


class BaseAPITest(base_db_test.OctaviaDBTestBase):

    BASE_PATH = '/v2.0/lbaas'

    # /lbaas/loadbalancers
    LBS_PATH = '/loadbalancers'
    LB_PATH = LBS_PATH + '/{lb_id}'
    LB_STATUS_PATH = LB_PATH + '/statuses'
    LB_STATS_PATH = LB_PATH + '/stats'

    # /lbaas/listeners/
    LISTENERS_PATH = '/listeners'
    LISTENER_PATH = LISTENERS_PATH + '/{listener_id}'
    LISTENER_STATS_PATH = LISTENER_PATH + '/stats'

    # /lbaas/pools
    POOLS_PATH = '/pools'
    POOL_PATH = POOLS_PATH + '/{pool_id}'

    # /lbaas/pools/{pool_id}/members
    MEMBERS_PATH = POOL_PATH + '/members'
    MEMBER_PATH = MEMBERS_PATH + '/{member_id}'

    # /lbaas/healthmonitors
    HMS_PATH = '/healthmonitors'
    HM_PATH = HMS_PATH + '/{healthmonitor_id}'

    # /lbaas/l7policies
    L7POLICIES_PATH = '/l7policies'
    L7POLICY_PATH = L7POLICIES_PATH + '/{l7policy_id}'
    L7RULES_PATH = L7POLICY_PATH + '/l7rules'
    L7RULE_PATH = L7RULES_PATH + '/{l7rule_id}'

    def setUp(self):
        super(BaseAPITest, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(api_handler='simulated_handler')
        self.conf.config(group="controller_worker",
                         network_driver='network_noop_driver')
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
        # For no apparent reason, the controller code for v2 uses a static
        # handler mock (the one generated on the initial run) so we need to
        # retrieve it so we use the "correct" mock instead of the one above
        self.handler_mock_bug_workaround = getattr(
            self.app.app.application.application.application.root,
            'v2.0').handler
        self.project_id = uuidutils.generate_uuid()

        def reset_pecan():
            patcher.stop()
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _make_app(self):
        return pecan.testing.load_test_app({'app': pconfig.app,
                                            'wsme': pconfig.wsme})

    def _get_full_path(self, path):
        return ''.join([self.BASE_PATH, path])

    def _build_body(self, json):
        return {self.root_tag: json}

    def delete(self, path, headers=None, status=204, expect_errors=False):
        headers = headers or {}
        full_path = self._get_full_path(path)
        response = self.app.delete(full_path,
                                   headers=headers,
                                   status=status,
                                   expect_errors=expect_errors)
        return response

    def post(self, path, body, headers=None, status=201, expect_errors=False):
        headers = headers or {}
        full_path = self._get_full_path(path)
        response = self.app.post_json(full_path,
                                      params=body,
                                      headers=headers,
                                      status=status,
                                      expect_errors=expect_errors)
        return response

    def put(self, path, body, headers=None, status=200, expect_errors=False):
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

    def create_load_balancer(self, vip_subnet_id,
                             **optionals):
        req_dict = {'vip_subnet_id': vip_subnet_id,
                    'project_id': self.project_id}
        req_dict.update(optionals)
        body = {'loadbalancer': req_dict}
        response = self.post(self.LBS_PATH, body)
        return response.json

    def create_listener(self, protocol, protocol_port, lb_id,
                        status=None, **optionals):
        req_dict = {'protocol': protocol, 'protocol_port': protocol_port,
                    'loadbalancer_id': lb_id}
        req_dict.update(optionals)
        path = self.LISTENERS_PATH
        body = {'listener': req_dict}
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
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

    def get_listener(self, listener_id):
        path = self.LISTENER_PATH.format(listener_id=listener_id)
        response = self.get(path)
        return response.json

    def create_pool_with_listener(self, lb_id, listener_id, protocol,
                                  lb_algorithm, **optionals):
        req_dict = {'loadbalancer_id': lb_id, 'listener_id': listener_id,
                    'protocol': protocol, 'lb_algorithm': lb_algorithm}
        req_dict.update(optionals)
        body = {'pool': req_dict}
        path = self.POOLS_PATH
        response = self.post(path, body)
        return response.json

    def create_pool(self, lb_id, protocol, lb_algorithm,
                    status=None, **optionals):
        req_dict = {'loadbalancer_id': lb_id, 'protocol': protocol,
                    'lb_algorithm': lb_algorithm}
        req_dict.update(optionals)
        body = {'pool': req_dict}
        path = self.POOLS_PATH
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
        return response.json

    def create_member(self, pool_id, address, protocol_port,
                      status=None, **optionals):
        req_dict = {'address': address, 'protocol_port': protocol_port}
        req_dict.update(optionals)
        body = {'member': req_dict}
        path = self.MEMBERS_PATH.format(pool_id=pool_id)
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
        return response.json

    # TODO(sindhu): Will be modified later in the Health_Monitor review
    def create_health_monitor(self, lb_id, type, delay, timeout,
                              fall_threshold, rise_threshold, root_tag=None,
                              **optionals):
        req_dict = {'load_balancer_id': lb_id, 'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'fall_threshold': fall_threshold,
                    'rise_threshold': rise_threshold}
        req_dict.update(optionals)
        body = {root_tag: req_dict}
        path = self.HMS_PATH
        response = self.post(path, body)
        return response.json

    # TODO(sindhu): Will be modified according to the
    # health_monitor_test_cases later
    def create_health_monitor_with_listener(
            self, lb_id, listener_id, pool_id, type,
            delay, timeout, fall_threshold, rise_threshold, **optionals):
        req_dict = {'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'fall_threshold': fall_threshold,
                    'rise_threshold': rise_threshold}
        req_dict.update(optionals)
        path = self.DEPRECATED_HM_PATH.format(
            lb_id=lb_id, listener_id=listener_id, pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def create_l7policy(self, listener_id, action, **optionals):
        req_dict = {'listener_id': listener_id, 'action': action}
        req_dict.update(optionals)
        body = {'l7policy': req_dict}
        path = self.L7POLICIES_PATH
        response = self.post(path, body)
        return response.json

    def create_l7rule(self, l7policy_id, type, compare_type,
                      value, **optionals):
        req_dict = {'type': type, 'compare_type': compare_type, 'value': value}
        req_dict.update(optionals)
        body = {'l7rule': req_dict}
        path = self.L7RULES_PATH.format(l7policy_id=l7policy_id)
        response = self.post(path, body)
        return response.json

    def _set_lb_and_children_statuses(self, lb_id, prov_status, op_status,
                                      autodetect=True):
        self.lb_repo.update(db_api.get_session(), lb_id,
                            provisioning_status=prov_status,
                            operating_status=op_status)
        lb_listeners = self.listener_repo.get_all(db_api.get_session(),
                                                  load_balancer_id=lb_id)
        for listener in lb_listeners:
            if autodetect and (listener.provisioning_status ==
                               constants.PENDING_DELETE):
                listener_prov = constants.DELETED
            else:
                listener_prov = prov_status
            self.listener_repo.update(db_api.get_session(), listener.id,
                                      provisioning_status=listener_prov,
                                      operating_status=op_status)
        lb_pools = self.pool_repo.get_all(db_api.get_session(),
                                          load_balancer_id=lb_id)
        for pool in lb_pools:
            if autodetect and (pool.provisioning_status ==
                               constants.PENDING_DELETE):
                pool_prov = constants.DELETED
            else:
                pool_prov = prov_status
            self.pool_repo.update(db_api.get_session(), pool.id,
                                  provisioning_status=pool_prov,
                                  operating_status=op_status)
            for member in pool.members:
                if autodetect and (member.provisioning_status ==
                                   constants.PENDING_DELETE):
                    member_prov = constants.DELETED
                else:
                    member_prov = prov_status
                self.member_repo.update(db_api.get_session(), member.id,
                                        provisioning_status=member_prov,
                                        operating_status=op_status)

    def set_lb_status(self, lb_id, status=None):
        explicit_status = True if status is not None else False
        if not explicit_status:
            status = constants.ACTIVE
        if status == constants.DELETED:
            op_status = constants.OFFLINE
        elif status == constants.ACTIVE:
            op_status = constants.ONLINE
        else:
            db_lb = self.lb_repo.get(db_api.get_session(), id=lb_id)
            op_status = db_lb.operating_status
        self._set_lb_and_children_statuses(lb_id, status, op_status,
                                           autodetect=not explicit_status)
        return self.get(self.LB_PATH.format(lb_id=lb_id)).json

    def assert_final_lb_statuses(self, lb_id, delete=False):
        expected_prov_status = constants.ACTIVE
        expected_op_status = constants.ONLINE
        if delete:
            expected_prov_status = constants.DELETED
            expected_op_status = constants.OFFLINE
        self.set_lb_status(lb_id, status=expected_prov_status)
        self.assert_correct_lb_status(expected_prov_status, expected_op_status,
                                      lb_id)

    def assert_final_listener_statuses(self, lb_id, listener_id, delete=False):
        expected_prov_status = constants.ACTIVE
        expected_op_status = constants.ONLINE
        if delete:
            expected_prov_status = constants.DELETED
            expected_op_status = constants.OFFLINE
        self.set_lb_status(lb_id, status=expected_prov_status)
        self.assert_correct_listener_status(expected_prov_status,
                                            expected_op_status,
                                            listener_id)

    def assert_correct_lb_status(self, provisioning_status, operating_status,
                                 lb_id):
        api_lb = self.get(
            self.LB_PATH.format(lb_id=lb_id)).json.get('loadbalancer')
        self.assertEqual(provisioning_status,
                         api_lb.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_lb.get('operating_status'))

    def assert_correct_listener_status(self, provisioning_status,
                                       operating_status, listener_id):
        api_listener = self.get(self.LISTENER_PATH.format(
            listener_id=listener_id)).json.get('listener')
        self.assertEqual(provisioning_status,
                         api_listener.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_listener.get('operating_status'))

    def assert_correct_pool_status(self, provisioning_status, operating_status,
                                   pool_id):
        api_pool = self.get(self.POOL_PATH.format(
            pool_id=pool_id)).json.get('pool')
        self.assertEqual(provisioning_status,
                         api_pool.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_pool.get('operating_status'))

    def assert_correct_member_status(self, provisioning_status,
                                     operating_status, pool_id, member_id):
        api_member = self.get(self.MEMBER_PATH.format(
            pool_id=pool_id, member_id=member_id)).json.get('member')
        self.assertEqual(provisioning_status,
                         api_member.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_member.get('operating_status'))

    def assert_correct_status(self, lb_id=None, listener_id=None, pool_id=None,
                              member_id=None,
                              lb_prov_status=constants.ACTIVE,
                              listener_prov_status=constants.ACTIVE,
                              pool_prov_status=constants.ACTIVE,
                              member_prov_status=constants.ACTIVE,
                              lb_op_status=constants.ONLINE,
                              listener_op_status=constants.ONLINE,
                              pool_op_status=constants.ONLINE,
                              member_op_status=constants.ONLINE):
        if lb_id:
            self.assert_correct_lb_status(lb_prov_status, lb_op_status, lb_id)
        if listener_id:
            self.assert_correct_listener_status(
                listener_prov_status, listener_op_status, listener_id)
        if pool_id:
            self.assert_correct_pool_status(
                pool_prov_status, pool_op_status, pool_id)
        if member_id:
            self.assert_correct_member_status(
                member_prov_status, member_op_status, pool_id, member_id)
