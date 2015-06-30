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

import logging

import pecan
import pecan.testing
import six

from octavia.api import config as pconfig
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import repositories
from octavia.tests.functional.db import base as base_db_test

if six.PY2:
    import mock
else:
    import unittest.mock as mock


LOG = logging.getLogger(__name__)


class BaseAPITest(base_db_test.OctaviaDBTestBase):

    BASE_PATH = '/v1'
    LBS_PATH = '/loadbalancers'
    LB_PATH = LBS_PATH + '/{lb_id}'
    LISTENERS_PATH = LB_PATH + '/listeners'
    LISTENER_PATH = LISTENERS_PATH + '/{listener_id}'
    POOLS_PATH = LISTENER_PATH + '/pools'
    POOL_PATH = POOLS_PATH + '/{pool_id}'
    MEMBERS_PATH = POOL_PATH + '/members'
    MEMBER_PATH = MEMBERS_PATH + '/{member_id}'
    HM_PATH = POOL_PATH + '/healthmonitor'

    def setUp(self):
        super(BaseAPITest, self).setUp()
        self.lb_repo = repositories.LoadBalancerRepository()
        self.listener_repo = repositories.ListenerRepository()
        self.pool_repo = repositories.PoolRepository()
        self.member_repo = repositories.MemberRepository()
        patcher = mock.patch('octavia.api.v1.handlers.controller_simulator.'
                             'handler.SimulatedControllerHandler')
        patcher.start()
        self.app = self._make_app()

        def reset_pecan():
            patcher.stop()
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _make_app(self):
        return pecan.testing.load_test_app({'app': pconfig.app,
                                            'wsme': pconfig.wsme})

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
        req_dict = {'vip': vip}
        req_dict.update(optionals)
        response = self.post(self.LBS_PATH, req_dict)
        return response.json

    def create_listener(self, lb_id, protocol, protocol_port, **optionals):
        req_dict = {'protocol': protocol, 'protocol_port': protocol_port}
        req_dict.update(optionals)
        path = self.LISTENERS_PATH.format(lb_id=lb_id)
        response = self.post(path, req_dict)
        return response.json

    def create_pool(self, lb_id, listener_id, protocol, lb_algorithm,
                    **optionals):
        req_dict = {'protocol': protocol, 'lb_algorithm': lb_algorithm}
        req_dict.update(optionals)
        path = self.POOLS_PATH.format(lb_id=lb_id, listener_id=listener_id)
        response = self.post(path, req_dict)
        return response.json

    def create_member(self, lb_id, listener_id, pool_id, ip_address,
                      protocol_port, **optionals):
        req_dict = {'ip_address': ip_address, 'protocol_port': protocol_port}
        req_dict.update(optionals)
        path = self.MEMBERS_PATH.format(lb_id=lb_id, listener_id=listener_id,
                                        pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def create_health_monitor(self, lb_id, listener_id, pool_id, type,
                              delay, timeout, fall_threshold, rise_threshold,
                              **optionals):
        req_dict = {'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'fall_threshold': fall_threshold,
                    'rise_threshold': rise_threshold}
        req_dict.update(optionals)
        path = self.HM_PATH.format(lb_id=lb_id, listener_id=listener_id,
                                   pool_id=pool_id)
        response = self.post(path, req_dict)
        return response.json

    def _set_lb_and_children_statuses(self, lb_id, prov_status, op_status):
        self.lb_repo.update(db_api.get_session(), lb_id,
                            provisioning_status=prov_status,
                            operating_status=op_status)
        lb_listeners = self.listener_repo.get_all(db_api.get_session(),
                                                  load_balancer_id=lb_id)
        for listener in lb_listeners:
            if listener.default_pool_id:
                self.pool_repo.update(db_api.get_session(),
                                      listener.default_pool_id,
                                      operating_status=op_status)
                for member in listener.default_pool.members:
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
