# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
#

from oslo_utils import uuidutils
import six

from octavia.common import base_taskflow
from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker import controller_worker
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

AMP_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
POOL_ID = uuidutils.generate_uuid()
HM_ID = uuidutils.generate_uuid()
MEMBER_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
HEALTH_UPDATE_DICT = {'delay': 1, 'timeout': 2}
LISTENER_UPDATE_DICT = {'name': 'test', 'description': 'test2'}
MEMBER_UPDATE_DICT = {'weight': 1, 'ip_address': '10.0.0.0'}
POOL_UPDATE_DICT = {'name': 'test', 'description': 'test2'}

_amphora_mock = mock.MagicMock()
_flow_mock = mock.MagicMock()
_health_mon_mock = mock.MagicMock()
_vip_mock = mock.MagicMock()
_listener_mock = mock.MagicMock()
_load_balancer_mock = mock.MagicMock()
_member_mock = mock.MagicMock()
_pool_mock = mock.MagicMock()
_create_map_flow_mock = mock.MagicMock()
_amphora_mock.load_balancer_id = LB_ID


@mock.patch('octavia.db.repositories.AmphoraRepository.get',
            return_value=_amphora_mock)
@mock.patch('octavia.db.repositories.HealthMonitorRepository.get',
            return_value=_health_mon_mock)
@mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
            return_value=_load_balancer_mock)
@mock.patch('octavia.db.repositories.ListenerRepository.get',
            return_value=_listener_mock)
@mock.patch('octavia.db.repositories.MemberRepository.get',
            return_value=_member_mock)
@mock.patch('octavia.db.repositories.PoolRepository.get',
            return_value=_pool_mock)
@mock.patch('octavia.common.base_taskflow.BaseTaskFlowEngine._taskflow_load',
            return_value=_flow_mock)
@mock.patch('taskflow.listeners.logging.DynamicLoggingListener')
@mock.patch('octavia.db.api.get_session', return_value='TEST')
class TestControllerWorker(base.TestCase):

    def setUp(self):

        _health_mon_mock.pool.listener.load_balancer.amphorae = _amphora_mock
        _health_mon_mock.pool.listener = _listener_mock
        _health_mon_mock.pool.listener.load_balancer.vip = _vip_mock
        _listener_mock.load_balancer = _load_balancer_mock
        _listener_mock.load_balancer.amphorae = _amphora_mock
        _listener_mock.load_balancer.vip = _vip_mock
        _member_mock.pool.listener = _listener_mock
        _member_mock.pool.listener.load_balancer.vip = _vip_mock
        _pool_mock.listener = _listener_mock
        _pool_mock.listener.load_balancer.vip = _vip_mock

        fetch_mock = mock.MagicMock(return_value=AMP_ID)
        _flow_mock.storage.fetch = fetch_mock

        _health_mon_mock.pool_id = POOL_ID
        _health_mon_mock.id = HM_ID

        super(TestControllerWorker, self).setUp()

    @mock.patch('octavia.controller.worker.flows.'
                'amphora_flows.AmphoraFlows.get_create_amphora_flow',
                return_value='TEST')
    def test_create_amphora(self,
                            mock_api_get_session,
                            mock_get_create_amp_flow,
                            mock_dyn_log_listener,
                            mock_taskflow_load,
                            mock_pool_repo_get,
                            mock_member_repo_get,
                            mock_listener_repo_get,
                            mock_lb_repo_get,
                            mock_health_mon_repo_get,
                            mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        amp = cw.create_amphora()

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with('TEST'))

        _flow_mock.run.assert_called_once_with()

        _flow_mock.storage.fetch.assert_called_once_with('amphora')

        assert (amp == AMP_ID)

    @mock.patch('octavia.controller.worker.flows.'
                'amphora_flows.AmphoraFlows.get_delete_amphora_flow',
                return_value='TEST')
    def test_delete_amphora(self,
                            mock_get_delete_amp_flow,
                            mock_api_get_session,
                            mock_dyn_log_listener,
                            mock_taskflow_load,
                            mock_pool_repo_get,
                            mock_member_repo_get,
                            mock_listener_repo_get,
                            mock_lb_repo_get,
                            mock_health_mon_repo_get,
                            mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_amphora(AMP_ID)

        mock_amp_repo_get.assert_called_once_with(
            'TEST',
            id=AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with('TEST',
                                    store={'amphora': _amphora_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'health_monitor_flows.HealthMonitorFlows.'
                'get_create_health_monitor_flow',
                return_value=_flow_mock)
    def test_create_health_monitor(self,
                                   mock_get_create_hm_flow,
                                   mock_api_get_session,
                                   mock_dyn_log_listener,
                                   mock_taskflow_load,
                                   mock_pool_repo_get,
                                   mock_member_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.create_health_monitor(_health_mon_mock)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'health_mon': _health_mon_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'health_monitor_flows.HealthMonitorFlows.'
                'get_delete_health_monitor_flow',
                return_value=_flow_mock)
    def test_delete_health_monitor(self,
                                   mock_get_delete_hm_flow,
                                   mock_api_get_session,
                                   mock_dyn_log_listener,
                                   mock_taskflow_load,
                                   mock_pool_repo_get,
                                   mock_member_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_health_monitor(HM_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'health_mon': _health_mon_mock,
                                           'pool_id': HM_ID,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'health_monitor_flows.HealthMonitorFlows.'
                'get_update_health_monitor_flow',
                return_value=_flow_mock)
    def test_update_health_monitor(self,
                                   mock_get_update_hm_flow,
                                   mock_api_get_session,
                                   mock_dyn_log_listener,
                                   mock_taskflow_load,
                                   mock_pool_repo_get,
                                   mock_member_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.update_health_monitor(_health_mon_mock.id,
                                 HEALTH_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'health_mon': _health_mon_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock,
                                           'update_dict': HEALTH_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'listener_flows.ListenerFlows.get_create_listener_flow',
                return_value=_flow_mock)
    def test_create_listener(self,
                             mock_get_create_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.create_listener(LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'listener_flows.ListenerFlows.get_delete_listener_flow',
                return_value=_flow_mock)
    def test_delete_listener(self,
                             mock_get_delete_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_listener(LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
         assert_called_once_with(
             _flow_mock, store={constants.LISTENER: _listener_mock,
                                constants.VIP: _vip_mock,
                                constants.LOADBALANCER: _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'listener_flows.ListenerFlows.get_update_listener_flow',
                return_value=_flow_mock)
    def test_update_listener(self,
                             mock_get_update_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.update_listener(LB_ID, LISTENER_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'listener': _listener_mock,
                                           'vip': _vip_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'update_dict':
                                               LISTENER_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.controller.worker.flows.'
                'amphora_flows.AmphoraFlows.get_create_amphora_flow',
                return_value='TEST2')
    @mock.patch('octavia.controller.worker.flows.'
                'amphora_flows.AmphoraFlows.get_create_amphora_for_lb_flow',
                return_value='TEST2')
    def test_create_load_balancer(self,
                                  mock_get_create_amp_for_lb_flow,
                                  mock_get_create_amp_flow,
                                  mock_get_create_lb_flow,
                                  mock_api_get_session,
                                  mock_dyn_log_listener,
                                  mock_taskflow_load,
                                  mock_pool_repo_get,
                                  mock_member_repo_get,
                                  mock_listener_repo_get,
                                  mock_lb_repo_get,
                                  mock_health_mon_repo_get,
                                  mock_amp_repo_get):

        # Test code path with an existing READY amphora
        _flow_mock.reset_mock()

        store = {constants.LOADBALANCER_ID: LB_ID}
        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock, store=store))

        _flow_mock.run.assert_called_once_with()

        self.assertFalse(mock_get_create_amp_for_lb_flow.called)

        # Test code path with no existing READY amphora

        _flow_mock.reset_mock()
        mock_get_create_lb_flow.reset_mock()
        mock_taskflow_load.reset_mock()

        mock_eng = mock.Mock()
        mock_taskflow_load.return_value = mock_eng
        mock_eng.run.side_effect = [exceptions.NoReadyAmphoraeException, None]

        cw.create_load_balancer(LB_ID)

        # mock is showing odd calls, even persisting through a reset
        # mock_taskflow_load.assert_has_calls([
        #     mock.call(_flow_mock, store=store),
        #     mock.call('TEST2', store=store),
        # ], anyorder=False)

        mock_eng.run.assert_any_call()

        self.assertEqual(mock_eng.run.call_count, 2)

        mock_eng.reset()
        mock_eng.run = mock.MagicMock(
            side_effect=[exceptions.NoReadyAmphoraeException,
                         exceptions.ComputeBuildException])

        self.assertRaises(exceptions.NoSuitableAmphoraException,
                          cw.create_load_balancer,
                          LB_ID)

    @mock.patch('octavia.controller.worker.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_delete_load_balancer_flow',
                return_value=_flow_mock)
    def test_delete_load_balancer(self,
                                  mock_get_delete_lb_flow,
                                  mock_api_get_session,
                                  mock_dyn_log_listener,
                                  mock_taskflow_load,
                                  mock_pool_repo_get,
                                  mock_member_repo_get,
                                  mock_listener_repo_get,
                                  mock_lb_repo_get,
                                  mock_health_mon_repo_get,
                                  mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_load_balancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(
            'TEST',
            id=LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'loadbalancer':
                                           _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_update_load_balancer_flow',
                return_value=_flow_mock)
    def test_update_load_balancer(self,
                                  mock_get_update_lb_flow,
                                  mock_api_get_session,
                                  mock_dyn_log_listener,
                                  mock_taskflow_load,
                                  mock_pool_repo_get,
                                  mock_member_repo_get,
                                  mock_listener_repo_get,
                                  mock_lb_repo_get,
                                  mock_health_mon_repo_get,
                                  mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        change = 'TEST2'
        cw.update_load_balancer(LB_ID, change)

        mock_lb_repo_get.assert_called_once_with(
            'TEST',
            id=LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'update_dict': change,
                                           'loadbalancer':
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'member_flows.MemberFlows.get_create_member_flow',
                return_value=_flow_mock)
    def test_create_member(self,
                           mock_get_create_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.create_member(MEMBER_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'member': _member_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'member_flows.MemberFlows.get_delete_member_flow',
                return_value=_flow_mock)
    def test_delete_member(self,
                           mock_get_delete_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_member(MEMBER_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock, store={'member': _member_mock,
                                   'member_id': MEMBER_ID,
                                   'listener': _listener_mock,
                                   'vip': _vip_mock,
                                   'loadbalancer': _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'member_flows.MemberFlows.get_update_member_flow',
                return_value=_flow_mock)
    def test_update_member(self,
                           mock_get_update_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.update_member(MEMBER_ID, MEMBER_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'member': _member_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock,
                                           'update_dict': MEMBER_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'pool_flows.PoolFlows.get_create_pool_flow',
                return_value=_flow_mock)
    def test_create_pool(self,
                         mock_get_create_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.create_pool(POOL_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'pool': _pool_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'pool_flows.PoolFlows.get_delete_pool_flow',
                return_value=_flow_mock)
    def test_delete_pool(self,
                         mock_get_delete_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_pool(POOL_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'pool': _pool_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'pool_flows.PoolFlows.get_update_pool_flow',
                return_value=_flow_mock)
    def test_update_pool(self,
                         mock_get_update_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.update_pool(POOL_ID, POOL_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={'pool': _pool_mock,
                                           'listener': _listener_mock,
                                           'loadbalancer': _load_balancer_mock,
                                           'vip': _vip_mock,
                                           'update_dict': POOL_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.flows.'
                'amphora_flows.AmphoraFlows.get_failover_flow',
                return_value=_flow_mock)
    def test_failover_amphora(self,
                              mock_get_update_listener_flow,
                              mock_api_get_session,
                              mock_dyn_log_listener,
                              mock_taskflow_load,
                              mock_pool_repo_get,
                              mock_member_repo_get,
                              mock_listener_repo_get,
                              mock_lb_repo_get,
                              mock_health_mon_repo_get,
                              mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.AMPHORA: _amphora_mock,
                       constants.LOADBALANCER_ID:
                           _amphora_mock.load_balancer_id}))

        _flow_mock.run.assert_called_once_with()