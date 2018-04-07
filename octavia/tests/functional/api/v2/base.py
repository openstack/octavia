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
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import repositories
from octavia.tests.functional.db import base as base_db_test


class BaseAPITest(base_db_test.OctaviaDBTestBase):

    BASE_PATH = '/v2'
    BASE_PATH_v2_0 = '/v2.0'

    # /lbaas/loadbalancers
    LBS_PATH = '/lbaas/loadbalancers'
    LB_PATH = LBS_PATH + '/{lb_id}'
    LB_STATUS_PATH = LB_PATH + '/statuses'
    LB_STATS_PATH = LB_PATH + '/stats'

    # /lbaas/listeners/
    LISTENERS_PATH = '/lbaas/listeners'
    LISTENER_PATH = LISTENERS_PATH + '/{listener_id}'
    LISTENER_STATS_PATH = LISTENER_PATH + '/stats'

    # /lbaas/pools
    POOLS_PATH = '/lbaas/pools'
    POOL_PATH = POOLS_PATH + '/{pool_id}'

    # /lbaas/pools/{pool_id}/members
    MEMBERS_PATH = POOL_PATH + '/members'
    MEMBER_PATH = MEMBERS_PATH + '/{member_id}'

    # /lbaas/healthmonitors
    HMS_PATH = '/lbaas/healthmonitors'
    HM_PATH = HMS_PATH + '/{healthmonitor_id}'

    # /lbaas/l7policies
    L7POLICIES_PATH = '/lbaas/l7policies'
    L7POLICY_PATH = L7POLICIES_PATH + '/{l7policy_id}'
    L7RULES_PATH = L7POLICY_PATH + '/rules'
    L7RULE_PATH = L7RULES_PATH + '/{l7rule_id}'

    QUOTAS_PATH = '/lbaas/quotas'
    QUOTA_PATH = QUOTAS_PATH + '/{project_id}'
    QUOTA_DEFAULT_PATH = QUOTAS_PATH + '/{project_id}/default'

    AMPHORAE_PATH = '/octavia/amphorae'
    AMPHORA_PATH = AMPHORAE_PATH + '/{amphora_id}'
    AMPHORA_FAILOVER_PATH = AMPHORA_PATH + '/failover'

    PROVIDERS_PATH = '/lbaas/providers'

    NOT_AUTHORIZED_BODY = {
        'debuginfo': None, 'faultcode': 'Client',
        'faultstring': 'Policy does not allow this request to be performed.'}

    def setUp(self):
        super(BaseAPITest, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="controller_worker",
                         network_driver='network_noop_driver')
        self.conf.config(group='api_settings', auth_strategy=constants.NOAUTH)
        self.conf.config(group='api_settings',
                         default_provider_driver='noop_driver')
        # We still need to test with the "octavia" alias
        self.conf.config(group='api_settings',
                         enabled_provider_drivers={
                             'amphora': 'Amp driver.',
                             'noop_driver': 'NoOp driver.',
                             'octavia': 'Octavia driver.'})
        self.lb_repo = repositories.LoadBalancerRepository()
        self.listener_repo = repositories.ListenerRepository()
        self.listener_stats_repo = repositories.ListenerStatisticsRepository()
        self.pool_repo = repositories.PoolRepository()
        self.member_repo = repositories.MemberRepository()
        self.l7policy_repo = repositories.L7PolicyRepository()
        self.l7rule_repo = repositories.L7RuleRepository()
        self.health_monitor_repo = repositories.HealthMonitorRepository()
        self.amphora_repo = repositories.AmphoraRepository()
        patcher2 = mock.patch('octavia.certificates.manager.barbican.'
                              'BarbicanCertManager')
        self.cert_manager_mock = patcher2.start()
        self.app = self._make_app()
        self.project_id = uuidutils.generate_uuid()

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def start_quota_mock(self, object_type):
        def mock_quota(session, lock_session, _class, project_id, count=1):
            return _class == object_type
        check_quota_met_true_mock = mock.patch(
            'octavia.db.repositories.Repositories.check_quota_met',
            side_effect=mock_quota)
        check_quota_met_true_mock.start()
        self.addCleanup(check_quota_met_true_mock.stop)

    def _make_app(self):
        return pecan.testing.load_test_app({'app': pconfig.app,
                                            'wsme': pconfig.wsme})

    def _get_full_path(self, path):
        return ''.join([self.BASE_PATH, path])

    def _get_full_path_v2_0(self, path):
        return ''.join([self.BASE_PATH_v2_0, path])

    def _build_body(self, json):
        return {self.root_tag: json}

    def delete(self, path, headers=None, params=None, status=204,
               expect_errors=False):
        headers = headers or {}
        params = params or {}
        full_path = self._get_full_path(path)
        param_string = ""
        for k, v in params.items():
            param_string += "{key}={value}&".format(key=k, value=v)
        if param_string:
            full_path = "{path}?{params}".format(
                path=full_path, params=param_string.rstrip("&"))
        response = self.app.delete(full_path,
                                   headers=headers,
                                   status=status,
                                   expect_errors=expect_errors)
        return response

    def post(self, path, body, headers=None, status=201, expect_errors=False,
             use_v2_0=False):
        headers = headers or {}
        if use_v2_0:
            full_path = self._get_full_path_v2_0(path)
        else:
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

    def create_listener_stats_dynamic(self, listener_id, amphora_id,
                                      bytes_in=0, bytes_out=0,
                                      active_connections=0,
                                      total_connections=0, request_errors=0):
        db_ls = self.listener_stats_repo.create(
            db_api.get_session(), listener_id=listener_id,
            amphora_id=amphora_id, bytes_in=bytes_in,
            bytes_out=bytes_out, active_connections=active_connections,
            total_connections=total_connections, request_errors=request_errors)
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

    def create_health_monitor(self, pool_id, type, delay, timeout,
                              max_retries_down, max_retries,
                              status=None, **optionals):
        req_dict = {'pool_id': pool_id,
                    'type': type,
                    'delay': delay,
                    'timeout': timeout,
                    'max_retries_down': max_retries_down,
                    'max_retries': max_retries}
        req_dict.update(optionals)
        body = {'healthmonitor': req_dict}
        path = self.HMS_PATH
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
        return response.json

    def create_l7policy(self, listener_id, action, status=None, **optionals):
        req_dict = {'listener_id': listener_id, 'action': action}
        req_dict.update(optionals)
        body = {'l7policy': req_dict}
        path = self.L7POLICIES_PATH
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
        return response.json

    def create_l7rule(self, l7policy_id, type, compare_type,
                      value, status=None, **optionals):
        req_dict = {'type': type, 'compare_type': compare_type, 'value': value}
        req_dict.update(optionals)
        body = {'rule': req_dict}
        path = self.L7RULES_PATH.format(l7policy_id=l7policy_id)
        status = {'status': status} if status else {}
        response = self.post(path, body, **status)
        return response.json

    def create_quota(self, project_id=-1, lb_quota=None, listener_quota=None,
                     pool_quota=None, hm_quota=None, member_quota=None):
        if project_id == -1:
            project_id = self.project_id
        req_dict = {'load_balancer': lb_quota,
                    'listener': listener_quota,
                    'pool': pool_quota,
                    'health_monitor': hm_quota,
                    'member': member_quota}
        req_dict = {k: v for k, v in req_dict.items() if v is not None}
        body = {'quota': req_dict}
        path = self.QUOTA_PATH.format(project_id=project_id)
        response = self.put(path, body, status=202)
        return response.json

    def _set_lb_and_children_statuses(self, lb_id, prov_status, op_status,
                                      autodetect=True):
        self.set_object_status(self.lb_repo, lb_id,
                               provisioning_status=prov_status,
                               operating_status=op_status)
        lb_listeners, _ = self.listener_repo.get_all(
            db_api.get_session(), load_balancer_id=lb_id)
        for listener in lb_listeners:
            if autodetect and (listener.provisioning_status ==
                               constants.PENDING_DELETE):
                listener_prov = constants.DELETED
            else:
                listener_prov = prov_status
            self.set_object_status(self.listener_repo, listener.id,
                                   provisioning_status=listener_prov,
                                   operating_status=op_status)
            lb_l7policies, _ = self.l7policy_repo.get_all(
                db_api.get_session(), listener_id=listener.id)
            for l7policy in lb_l7policies:
                if autodetect and (l7policy.provisioning_status ==
                                   constants.PENDING_DELETE):
                    l7policy_prov = constants.DELETED
                else:
                    l7policy_prov = prov_status
                self.set_object_status(self.l7policy_repo, l7policy.id,
                                       provisioning_status=l7policy_prov,
                                       operating_status=op_status)
                l7rules, _ = self.l7rule_repo.get_all(
                    db_api.get_session(), l7policy_id=l7policy.id)
                for l7rule in l7rules:
                    if autodetect and (l7rule.provisioning_status ==
                                       constants.PENDING_DELETE):
                        l7rule_prov = constants.DELETED
                    else:
                        l7rule_prov = prov_status
                    self.set_object_status(self.l7rule_repo, l7rule.id,
                                           provisioning_status=l7rule_prov,
                                           operating_status=op_status)
        lb_pools, _ = self.pool_repo.get_all(db_api.get_session(),
                                             load_balancer_id=lb_id)
        for pool in lb_pools:
            if autodetect and (pool.provisioning_status ==
                               constants.PENDING_DELETE):
                pool_prov = constants.DELETED
            else:
                pool_prov = prov_status
            self.set_object_status(self.pool_repo, pool.id,
                                   provisioning_status=pool_prov,
                                   operating_status=op_status)
            for member in pool.members:
                if autodetect and (member.provisioning_status ==
                                   constants.PENDING_DELETE):
                    member_prov = constants.DELETED
                else:
                    member_prov = prov_status
                self.set_object_status(self.member_repo, member.id,
                                       provisioning_status=member_prov,
                                       operating_status=op_status)
            if pool.health_monitor:
                if autodetect and (pool.health_monitor.provisioning_status ==
                                   constants.PENDING_DELETE):
                    hm_prov = constants.DELETED
                else:
                    hm_prov = prov_status
                self.set_object_status(self.health_monitor_repo,
                                       pool.health_monitor.id,
                                       provisioning_status=hm_prov,
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
        if status != constants.DELETED:
            return self.get(self.LB_PATH.format(lb_id=lb_id)).json

    @staticmethod
    def set_object_status(repo, id_, provisioning_status=constants.ACTIVE,
                          operating_status=constants.ONLINE):
        repo.update(db_api.get_session(), id_,
                    provisioning_status=provisioning_status,
                    operating_status=operating_status)

    def assert_final_listener_statuses(self, lb_id, listener_id, delete=False):
        expected_prov_status = constants.ACTIVE
        expected_op_status = constants.ONLINE
        self.set_lb_status(lb_id, status=expected_prov_status)
        try:
            self.assert_correct_listener_status(expected_prov_status,
                                                expected_op_status,
                                                listener_id)
        except exceptions.NotFound:
            if not delete:
                raise

    def assert_correct_lb_status(self, lb_id,
                                 operating_status, provisioning_status):
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

    def assert_correct_l7policy_status(self, provisioning_status,
                                       operating_status, l7policy_id):
        api_l7policy = self.get(self.L7POLICY_PATH.format(
            l7policy_id=l7policy_id)).json.get('l7policy')
        self.assertEqual(provisioning_status,
                         api_l7policy.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_l7policy.get('operating_status'))

    def assert_correct_l7rule_status(self, provisioning_status,
                                     operating_status, l7policy_id, l7rule_id):
        api_l7rule = self.get(self.L7RULE_PATH.format(
            l7policy_id=l7policy_id, l7rule_id=l7rule_id)).json.get('rule')
        self.assertEqual(provisioning_status,
                         api_l7rule.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_l7rule.get('operating_status'))

    def assert_correct_hm_status(self, provisioning_status,
                                 operating_status, hm_id):
        api_hm = self.get(self.HM_PATH.format(
            healthmonitor_id=hm_id)).json.get('healthmonitor')
        self.assertEqual(provisioning_status,
                         api_hm.get('provisioning_status'))
        self.assertEqual(operating_status,
                         api_hm.get('operating_status'))

    def assert_correct_status(self, lb_id=None, listener_id=None, pool_id=None,
                              member_id=None, l7policy_id=None, l7rule_id=None,
                              hm_id=None,
                              lb_prov_status=constants.ACTIVE,
                              listener_prov_status=constants.ACTIVE,
                              pool_prov_status=constants.ACTIVE,
                              member_prov_status=constants.ACTIVE,
                              l7policy_prov_status=constants.ACTIVE,
                              l7rule_prov_status=constants.ACTIVE,
                              hm_prov_status=constants.ACTIVE,
                              lb_op_status=constants.ONLINE,
                              listener_op_status=constants.ONLINE,
                              pool_op_status=constants.ONLINE,
                              member_op_status=constants.ONLINE,
                              l7policy_op_status=constants.ONLINE,
                              l7rule_op_status=constants.ONLINE,
                              hm_op_status=constants.ONLINE):
        if lb_id:
            self.assert_correct_lb_status(lb_id, lb_op_status, lb_prov_status)
        if listener_id:
            self.assert_correct_listener_status(
                listener_prov_status, listener_op_status, listener_id)
        if pool_id:
            self.assert_correct_pool_status(
                pool_prov_status, pool_op_status, pool_id)
        if member_id:
            self.assert_correct_member_status(
                member_prov_status, member_op_status, pool_id, member_id)
        if l7policy_id:
            self.assert_correct_l7policy_status(
                l7policy_prov_status, l7policy_op_status, l7policy_id)
        if l7rule_id:
            self.assert_correct_l7rule_status(
                l7rule_prov_status, l7rule_op_status, l7policy_id, l7rule_id)
        if hm_id:
            self.assert_correct_hm_status(
                hm_prov_status, hm_op_status, hm_id)
