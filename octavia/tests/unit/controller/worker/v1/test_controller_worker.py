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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import base_taskflow
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.controller.worker.v1 import controller_worker
import octavia.tests.unit.base as base


AMP_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
POOL_ID = uuidutils.generate_uuid()
HM_ID = uuidutils.generate_uuid()
MEMBER_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
L7POLICY_ID = uuidutils.generate_uuid()
L7RULE_ID = uuidutils.generate_uuid()
HEALTH_UPDATE_DICT = {'delay': 1, 'timeout': 2}
LISTENER_UPDATE_DICT = {'name': 'test', 'description': 'test2'}
MEMBER_UPDATE_DICT = {'weight': 1, 'ip_address': '10.0.0.0'}
POOL_UPDATE_DICT = {'name': 'test', 'description': 'test2'}
L7POLICY_UPDATE_DICT = {'action': constants.L7POLICY_ACTION_REJECT}
L7RULE_UPDATE_DICT = {
    'type': constants.L7RULE_TYPE_PATH,
    'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
    'value': '/api'}

_amphora_mock = mock.MagicMock()
_flow_mock = mock.MagicMock()
_health_mon_mock = mock.MagicMock()
_vip_mock = mock.MagicMock()
_listener_mock = mock.MagicMock()
_load_balancer_mock = mock.MagicMock()
_load_balancer_mock.listeners = [_listener_mock]
_load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
_load_balancer_mock.flavor_id = None
_load_balancer_mock.availability_zone = None
_member_mock = mock.MagicMock()
_pool_mock = mock.MagicMock()
_l7policy_mock = mock.MagicMock()
_l7rule_mock = mock.MagicMock()
_create_map_flow_mock = mock.MagicMock()
_amphora_mock.load_balancer_id = LB_ID
_amphora_mock.id = AMP_ID
_db_session = mock.MagicMock()

CONF = cfg.CONF


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


@mock.patch('octavia.db.repositories.AmphoraRepository.get',
            return_value=_amphora_mock)
@mock.patch('octavia.db.repositories.HealthMonitorRepository.get',
            return_value=_health_mon_mock)
@mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
            return_value=_load_balancer_mock)
@mock.patch('octavia.db.repositories.ListenerRepository.get',
            return_value=_listener_mock)
@mock.patch('octavia.db.repositories.L7PolicyRepository.get',
            return_value=_l7policy_mock)
@mock.patch('octavia.db.repositories.L7RuleRepository.get',
            return_value=_l7rule_mock)
@mock.patch('octavia.db.repositories.MemberRepository.get',
            return_value=_member_mock)
@mock.patch('octavia.db.repositories.PoolRepository.get',
            return_value=_pool_mock)
@mock.patch('octavia.common.base_taskflow.BaseTaskFlowEngine._taskflow_load',
            return_value=_flow_mock)
@mock.patch('taskflow.listeners.logging.DynamicLoggingListener')
@mock.patch('octavia.db.api.get_session', return_value=_db_session)
class TestControllerWorker(base.TestCase):

    def setUp(self):

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))

        _pool_mock.listeners = [_listener_mock]
        _pool_mock.load_balancer = _load_balancer_mock
        _health_mon_mock.pool = _pool_mock
        _load_balancer_mock.amphorae = _amphora_mock
        _load_balancer_mock.vip = _vip_mock
        _listener_mock.load_balancer = _load_balancer_mock
        _member_mock.pool = _pool_mock
        _l7policy_mock.listener = _listener_mock
        _l7rule_mock.l7policy = _l7policy_mock

        fetch_mock = mock.MagicMock(return_value=AMP_ID)
        _flow_mock.storage.fetch = fetch_mock

        _pool_mock.id = POOL_ID
        _health_mon_mock.pool_id = POOL_ID
        _health_mon_mock.id = HM_ID

        super(TestControllerWorker, self).setUp()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_create_amphora_flow',
                return_value='TEST')
    def test_create_amphora(self,
                            mock_get_create_amp_flow,
                            mock_api_get_session,
                            mock_dyn_log_listener,
                            mock_taskflow_load,
                            mock_pool_repo_get,
                            mock_member_repo_get,
                            mock_l7rule_repo_get,
                            mock_l7policy_repo_get,
                            mock_listener_repo_get,
                            mock_lb_repo_get,
                            mock_health_mon_repo_get,
                            mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        amp = cw.create_amphora()

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                'TEST',
                store={constants.BUILD_TYPE_PRIORITY:
                       constants.LB_CREATE_SPARES_POOL_PRIORITY,
                       constants.FLAVOR: None,
                       constants.SERVER_GROUP_ID: None,
                       constants.AVAILABILITY_ZONE: None}))

        _flow_mock.run.assert_called_once_with()

        _flow_mock.storage.fetch.assert_called_once_with('amphora')

        self.assertEqual(AMP_ID, amp)

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_create_amphora_flow',
                return_value='TEST')
    def test_create_amphora_with_az(self,
                                    mock_get_create_amp_flow,
                                    mock_get_az_metadata,
                                    mock_api_get_session,
                                    mock_dyn_log_listener,
                                    mock_taskflow_load,
                                    mock_pool_repo_get,
                                    mock_member_repo_get,
                                    mock_l7rule_repo_get,
                                    mock_l7policy_repo_get,
                                    mock_listener_repo_get,
                                    mock_lb_repo_get,
                                    mock_health_mon_repo_get,
                                    mock_amp_repo_get):

        _flow_mock.reset_mock()
        az = 'fake_az'
        az_data = {constants.COMPUTE_ZONE: az}
        mock_get_az_metadata.return_value = az_data
        cw = controller_worker.ControllerWorker()
        amp = cw.create_amphora(availability_zone=az)
        mock_get_az_metadata.assert_called_once_with(_db_session, az)
        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                'TEST',
                store={constants.BUILD_TYPE_PRIORITY:
                       constants.LB_CREATE_SPARES_POOL_PRIORITY,
                       constants.FLAVOR: None,
                       constants.SERVER_GROUP_ID: None,
                       constants.AVAILABILITY_ZONE: az_data}))

        _flow_mock.run.assert_called_once_with()

        _flow_mock.storage.fetch.assert_called_once_with('amphora')

        self.assertEqual(AMP_ID, amp)

    @mock.patch('octavia.controller.worker.v1.flows.'
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
                                   mock_l7rule_repo_get,
                                   mock_l7policy_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_health_mon_repo_get.side_effect = [None, _health_mon_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_health_monitor(_health_mon_mock)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.POOL:
                                               _pool_mock}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_health_mon_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
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
                                   mock_l7rule_repo_get,
                                   mock_l7policy_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_health_monitor(HM_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.POOL:
                                               _pool_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
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
                                   mock_l7rule_repo_get,
                                   mock_l7policy_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):

        _flow_mock.reset_mock()
        _health_mon_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_health_monitor(_health_mon_mock.id,
                                 HEALTH_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.POOL:
                                               _pool_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.UPDATE_DICT:
                                           HEALTH_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'listener_flows.ListenerFlows.get_create_listener_flow',
                return_value=_flow_mock)
    def test_create_listener(self,
                             mock_get_create_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_listener_repo_get.side_effect = [None, _listener_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_listener(LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.LOADBALANCER:
                                           _load_balancer_mock,
                                           constants.LISTENERS:
                                           _load_balancer_mock.listeners}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_listener_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'listener_flows.ListenerFlows.get_delete_listener_flow',
                return_value=_flow_mock)
    def test_delete_listener(self,
                             mock_get_delete_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
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
                                constants.LOADBALANCER: _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'listener_flows.ListenerFlows.get_update_listener_flow',
                return_value=_flow_mock)
    def test_update_listener(self,
                             mock_get_update_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()
        _listener_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_listener(LB_ID, LISTENER_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.LISTENER: _listener_mock,
                                           constants.LOADBALANCER:
                                           _load_balancer_mock,
                                           constants.UPDATE_DICT:
                                           LISTENER_UPDATE_DICT,
                                           constants.LISTENERS:
                                           [_listener_mock]}))

        _flow_mock.run.assert_called_once_with()

    def test_create_load_balancer_single_no_anti_affinity(
            self, mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get, mock_l7policy_repo_get,
            mock_listener_repo_get, mock_lb_repo_get,
            mock_health_mon_repo_get, mock_amp_repo_get):
        # Test the code path with Nova anti-affinity disabled
        self.conf.config(group="nova", enable_anti_affinity=False)
        self._test_create_load_balancer_single(
            mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get,
            mock_l7policy_repo_get, mock_listener_repo_get,
            mock_lb_repo_get, mock_health_mon_repo_get, mock_amp_repo_get)

    def test_create_load_balancer_single_anti_affinity(
            self, mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get, mock_l7policy_repo_get,
            mock_listener_repo_get, mock_lb_repo_get,
            mock_health_mon_repo_get, mock_amp_repo_get):
        # Test the code path with Nova anti-affinity enabled
        self.conf.config(group="nova", enable_anti_affinity=True)
        self._test_create_load_balancer_single(
            mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get,
            mock_l7policy_repo_get, mock_listener_repo_get,
            mock_lb_repo_get, mock_health_mon_repo_get, mock_amp_repo_get)

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow',
                return_value=_flow_mock)
    def _test_create_load_balancer_single(
            self,
            mock_api_get_session,
            mock_dyn_log_listener,
            mock_taskflow_load,
            mock_pool_repo_get,
            mock_member_repo_get,
            mock_l7rule_repo_get,
            mock_l7policy_repo_get,
            mock_listener_repo_get,
            mock_lb_repo_get,
            mock_health_mon_repo_get,
            mock_amp_repo_get,
            mock_get_create_load_balancer_flow):

        # Test the code path with an SINGLE topology
        self.conf.config(group="controller_worker",
                         loadbalancer_topology=constants.TOPOLOGY_SINGLE)
        _flow_mock.reset_mock()
        mock_taskflow_load.reset_mock()
        mock_eng = mock.Mock()
        mock_taskflow_load.return_value = mock_eng
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_SINGLE},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None, constants.AVAILABILITY_ZONE: None,
            constants.SERVER_GROUP_ID: None
        }
        lb_mock = mock.MagicMock()
        lb_mock.listeners = []
        lb_mock.topology = constants.TOPOLOGY_SINGLE
        mock_lb_repo_get.side_effect = [None, None, None, lb_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(LB_ID)

        mock_get_create_load_balancer_flow.assert_called_with(
            topology=constants.TOPOLOGY_SINGLE, listeners=[])
        mock_taskflow_load.assert_called_with(
            mock_get_create_load_balancer_flow.return_value, store=store)
        mock_eng.run.assert_any_call()
        self.assertEqual(4, mock_lb_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow',
                return_value=_flow_mock)
    def test_create_load_balancer_active_standby(
            self,
            mock_get_create_load_balancer_flow,
            mock_api_get_session,
            mock_dyn_log_listener,
            mock_taskflow_load,
            mock_pool_repo_get,
            mock_member_repo_get,
            mock_l7rule_repo_get,
            mock_l7policy_repo_get,
            mock_listener_repo_get,
            mock_lb_repo_get,
            mock_health_mon_repo_get,
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)

        _flow_mock.reset_mock()
        mock_taskflow_load.reset_mock()
        mock_eng = mock.Mock()
        mock_taskflow_load.return_value = mock_eng
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_ACTIVE_STANDBY},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None, constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }
        setattr(mock_lb_repo_get.return_value, 'topology',
                constants.TOPOLOGY_ACTIVE_STANDBY)
        setattr(mock_lb_repo_get.return_value, 'listeners', [])

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(LB_ID)

        mock_get_create_load_balancer_flow.assert_called_with(
            topology=constants.TOPOLOGY_ACTIVE_STANDBY, listeners=[])
        mock_taskflow_load.assert_called_with(
            mock_get_create_load_balancer_flow.return_value, store=store)
        mock_eng.run.assert_any_call()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow')
    def test_create_load_balancer_full_graph_single(
            self,
            mock_get_create_load_balancer_flow,
            mock_api_get_session,
            mock_dyn_log_listener,
            mock_taskflow_load,
            mock_pool_repo_get,
            mock_member_repo_get,
            mock_l7rule_repo_get,
            mock_l7policy_repo_get,
            mock_listener_repo_get,
            mock_lb_repo_get,
            mock_health_mon_repo_get,
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_SINGLE)

        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners,
                                      topology=constants.TOPOLOGY_SINGLE)
        mock_lb_repo_get.return_value = lb
        mock_eng = mock.Mock()
        mock_taskflow_load.return_value = mock_eng
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_SINGLE},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None, constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(LB_ID)

        # mock_create_single_topology.assert_called_once()
        # mock_create_active_standby_topology.assert_not_called()
        mock_get_create_load_balancer_flow.assert_called_with(
            topology=constants.TOPOLOGY_SINGLE, listeners=lb.listeners)
        mock_taskflow_load.assert_called_with(
            mock_get_create_load_balancer_flow.return_value, store=store)
        mock_eng.run.assert_any_call()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow')
    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows._create_single_topology')
    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows._create_active_standby_topology')
    def test_create_load_balancer_full_graph_active_standby(
            self,
            mock_create_active_standby_topology,
            mock_create_single_topology,
            mock_get_create_load_balancer_flow,
            mock_api_get_session,
            mock_dyn_log_listener,
            mock_taskflow_load,
            mock_pool_repo_get,
            mock_member_repo_get,
            mock_l7rule_repo_get,
            mock_l7policy_repo_get,
            mock_listener_repo_get,
            mock_lb_repo_get,
            mock_health_mon_repo_get,
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)

        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        lb = data_models.LoadBalancer(
            id=LB_ID, listeners=listeners,
            topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        mock_lb_repo_get.return_value = lb
        mock_eng = mock.Mock()
        mock_taskflow_load.return_value = mock_eng
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_ACTIVE_STANDBY},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None, constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(LB_ID)

        mock_get_create_load_balancer_flow.assert_called_with(
            topology=constants.TOPOLOGY_ACTIVE_STANDBY, listeners=lb.listeners)
        mock_taskflow_load.assert_called_with(
            mock_get_create_load_balancer_flow.return_value, store=store)
        mock_eng.run.assert_any_call()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_delete_load_balancer_flow',
                return_value=(_flow_mock, {'test': 'test'}))
    def test_delete_load_balancer_without_cascade(self,
                                                  mock_get_delete_lb_flow,
                                                  mock_api_get_session,
                                                  mock_dyn_log_listener,
                                                  mock_taskflow_load,
                                                  mock_pool_repo_get,
                                                  mock_member_repo_get,
                                                  mock_l7rule_repo_get,
                                                  mock_l7policy_repo_get,
                                                  mock_listener_repo_get,
                                                  mock_lb_repo_get,
                                                  mock_health_mon_repo_get,
                                                  mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_load_balancer(LB_ID, cascade=False)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.LOADBALANCER:
                                           _load_balancer_mock,
                                           constants.SERVER_GROUP_ID:
                                           _load_balancer_mock.server_group_id,
                                           'test': 'test'
                                           }
                                    )
         )
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_cascade_delete_load_balancer_flow',
                return_value=(_flow_mock, {'test': 'test'}))
    def test_delete_load_balancer_with_cascade(self,
                                               mock_get_delete_lb_flow,
                                               mock_api_get_session,
                                               mock_dyn_log_listener,
                                               mock_taskflow_load,
                                               mock_pool_repo_get,
                                               mock_member_repo_get,
                                               mock_l7rule_repo_get,
                                               mock_l7policy_repo_get,
                                               mock_listener_repo_get,
                                               mock_lb_repo_get,
                                               mock_health_mon_repo_get,
                                               mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_load_balancer(LB_ID, cascade=True)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.LOADBALANCER:
                                           _load_balancer_mock,
                                           constants.SERVER_GROUP_ID:
                                           _load_balancer_mock.server_group_id,
                                           'test': 'test'
                                           }
                                    )
         )
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_update_load_balancer_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.ListenerRepository.get_all',
                return_value=([_listener_mock], None))
    def test_update_load_balancer(self,
                                  mock_listener_repo_get_all,
                                  mock_get_update_lb_flow,
                                  mock_api_get_session,
                                  mock_dyn_log_listener,
                                  mock_taskflow_load,
                                  mock_pool_repo_get,
                                  mock_member_repo_get,
                                  mock_l7rule_repo_get,
                                  mock_l7policy_repo_get,
                                  mock_listener_repo_get,
                                  mock_lb_repo_get,
                                  mock_health_mon_repo_get,
                                  mock_amp_repo_get):

        _flow_mock.reset_mock()
        _load_balancer_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        change = 'TEST2'
        cw.update_load_balancer(LB_ID, change)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.UPDATE_DICT: change,
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.LISTENERS:
                                               [_listener_mock]}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'member_flows.MemberFlows.get_create_member_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    def test_create_member(self,
                           mock_get_az_metadata_dict,
                           mock_get_create_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_get_az_metadata_dict.return_value = {}
        mock_member_repo_get.side_effect = [None, _member_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_member(MEMBER_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.MEMBER: _member_mock,
                       constants.LISTENERS: [_listener_mock],
                       constants.LOADBALANCER: _load_balancer_mock,
                       constants.POOL: _pool_mock,
                       constants.AVAILABILITY_ZONE: {}}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_member_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'member_flows.MemberFlows.get_delete_member_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    def test_delete_member(self,
                           mock_get_az_metadata_dict,
                           mock_get_delete_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.delete_member(MEMBER_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock, store={constants.MEMBER: _member_mock,
                                   constants.LISTENERS:
                                       [_listener_mock],
                                   constants.LOADBALANCER:
                                       _load_balancer_mock,
                                   constants.POOL:
                                       _pool_mock,
                                   constants.AVAILABILITY_ZONE: {}}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'member_flows.MemberFlows.get_update_member_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    def test_update_member(self,
                           mock_get_az_metadata_dict,
                           mock_get_update_member_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()
        _member_mock.provisioning_status = constants.PENDING_UPDATE
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.update_member(MEMBER_ID, MEMBER_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.MEMBER: _member_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.POOL:
                                               _pool_mock,
                                           constants.UPDATE_DICT:
                                               MEMBER_UPDATE_DICT,
                                           constants.AVAILABILITY_ZONE: {}}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'member_flows.MemberFlows.get_batch_update_members_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    def test_batch_update_members(self,
                                  mock_get_az_metadata_dict,
                                  mock_get_batch_update_members_flow,
                                  mock_api_get_session,
                                  mock_dyn_log_listener,
                                  mock_taskflow_load,
                                  mock_pool_repo_get,
                                  mock_member_repo_get,
                                  mock_l7rule_repo_get,
                                  mock_l7policy_repo_get,
                                  mock_listener_repo_get,
                                  mock_lb_repo_get,
                                  mock_health_mon_repo_get,
                                  mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_member_repo_get.side_effect = [None, _member_mock,
                                            _member_mock, _member_mock]
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.batch_update_members([9], [11], [MEMBER_UPDATE_DICT])

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={
                                        constants.LISTENERS: [_listener_mock],
                                        constants.LOADBALANCER:
                                            _load_balancer_mock,
                                        constants.POOL: _pool_mock,
                                        constants.AVAILABILITY_ZONE: {}}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(4, mock_member_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'pool_flows.PoolFlows.get_create_pool_flow',
                return_value=_flow_mock)
    def test_create_pool(self,
                         mock_get_create_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_l7rule_repo_get,
                         mock_l7policy_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_pool_repo_get.side_effect = [None, _pool_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_pool(POOL_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.POOL: _pool_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_pool_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'pool_flows.PoolFlows.get_delete_pool_flow',
                return_value=_flow_mock)
    def test_delete_pool(self,
                         mock_get_delete_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_l7rule_repo_get,
                         mock_l7policy_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_pool(POOL_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.POOL: _pool_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'pool_flows.PoolFlows.get_update_pool_flow',
                return_value=_flow_mock)
    def test_update_pool(self,
                         mock_get_update_listener_flow,
                         mock_api_get_session,
                         mock_dyn_log_listener,
                         mock_taskflow_load,
                         mock_pool_repo_get,
                         mock_member_repo_get,
                         mock_l7rule_repo_get,
                         mock_l7policy_repo_get,
                         mock_listener_repo_get,
                         mock_lb_repo_get,
                         mock_health_mon_repo_get,
                         mock_amp_repo_get):

        _flow_mock.reset_mock()
        _pool_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_pool(POOL_ID, POOL_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.POOL: _pool_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.UPDATE_DICT:
                                               POOL_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7policy_flows.L7PolicyFlows.get_create_l7policy_flow',
                return_value=_flow_mock)
    def test_create_l7policy(self,
                             mock_get_create_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_l7policy_repo_get.side_effect = [None, _l7policy_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_l7policy(L7POLICY_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_l7policy_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7policy_flows.L7PolicyFlows.get_delete_l7policy_flow',
                return_value=_flow_mock)
    def test_delete_l7policy(self,
                             mock_get_delete_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_l7policy(L7POLICY_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7policy_flows.L7PolicyFlows.get_update_l7policy_flow',
                return_value=_flow_mock)
    def test_update_l7policy(self,
                             mock_get_update_listener_flow,
                             mock_api_get_session,
                             mock_dyn_log_listener,
                             mock_taskflow_load,
                             mock_pool_repo_get,
                             mock_member_repo_get,
                             mock_l7rule_repo_get,
                             mock_l7policy_repo_get,
                             mock_listener_repo_get,
                             mock_lb_repo_get,
                             mock_health_mon_repo_get,
                             mock_amp_repo_get):

        _flow_mock.reset_mock()
        _l7policy_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_l7policy(L7POLICY_ID, L7POLICY_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.UPDATE_DICT:
                                               L7POLICY_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7rule_flows.L7RuleFlows.get_create_l7rule_flow',
                return_value=_flow_mock)
    def test_create_l7rule(self,
                           mock_get_create_listener_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()
        mock_l7rule_repo_get.side_effect = [None, _l7rule_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_l7rule(L7RULE_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7RULE: _l7rule_mock,
                                           constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()
        self.assertEqual(2, mock_l7rule_repo_get.call_count)

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7rule_flows.L7RuleFlows.get_delete_l7rule_flow',
                return_value=_flow_mock)
    def test_delete_l7rule(self,
                           mock_get_delete_listener_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()

        cw = controller_worker.ControllerWorker()
        cw.delete_l7rule(L7RULE_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7RULE: _l7rule_mock,
                                           constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'l7rule_flows.L7RuleFlows.get_update_l7rule_flow',
                return_value=_flow_mock)
    def test_update_l7rule(self,
                           mock_get_update_listener_flow,
                           mock_api_get_session,
                           mock_dyn_log_listener,
                           mock_taskflow_load,
                           mock_pool_repo_get,
                           mock_member_repo_get,
                           mock_l7rule_repo_get,
                           mock_l7policy_repo_get,
                           mock_listener_repo_get,
                           mock_lb_repo_get,
                           mock_health_mon_repo_get,
                           mock_amp_repo_get):

        _flow_mock.reset_mock()
        _l7rule_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_l7rule(L7RULE_ID, L7RULE_UPDATE_DICT)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(_flow_mock,
                                    store={constants.L7RULE: _l7rule_mock,
                                           constants.L7POLICY: _l7policy_mock,
                                           constants.LISTENERS:
                                               [_listener_mock],
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.UPDATE_DICT:
                                               L7RULE_UPDATE_DICT}))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_lb_single(self,
                                        mock_update,
                                        mock_get_failover_flow,
                                        mock_get_flavor_meta,
                                        mock_get_az_meta,
                                        mock_api_get_session,
                                        mock_dyn_log_listener,
                                        mock_taskflow_load,
                                        mock_pool_repo_get,
                                        mock_member_repo_get,
                                        mock_l7rule_repo_get,
                                        mock_l7policy_repo_get,
                                        mock_listener_repo_get,
                                        mock_lb_repo_get,
                                        mock_health_mon_repo_get,
                                        mock_amp_repo_get):
        _flow_mock.reset_mock()
        mock_lb_repo_get.return_value = _load_balancer_mock

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.FLAVOR: {'loadbalancer_topology':
                                          _load_balancer_mock.topology},
                       constants.LOADBALANCER: _load_balancer_mock,
                       constants.LOADBALANCER_ID:
                           _load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.SERVER_GROUP_ID:
                           _load_balancer_mock.server_group_id,
                       constants.AVAILABILITY_ZONE: {},
                       constants.VIP: _load_balancer_mock.vip
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_lb_act_stdby(self,
                                           mock_update,
                                           mock_get_failover_flow,
                                           mock_get_flavor_meta,
                                           mock_get_az_meta,
                                           mock_api_get_session,
                                           mock_dyn_log_listener,
                                           mock_taskflow_load,
                                           mock_pool_repo_get,
                                           mock_member_repo_get,
                                           mock_l7rule_repo_get,
                                           mock_l7policy_repo_get,
                                           mock_listener_repo_get,
                                           mock_lb_repo_get,
                                           mock_health_mon_repo_get,
                                           mock_amp_repo_get):
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        load_balancer_mock.flavor_id = None
        load_balancer_mock.availability_zone = None
        load_balancer_mock.vip = _vip_mock

        mock_lb_repo_get.return_value = load_balancer_mock

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.FLAVOR: {'loadbalancer_topology':
                                          load_balancer_mock.topology},
                       constants.LOADBALANCER: load_balancer_mock,
                       constants.LOADBALANCER_ID: load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.AVAILABILITY_ZONE: {},
                       constants.SERVER_GROUP_ID:
                           load_balancer_mock.server_group_id,
                       constants.VIP: load_balancer_mock.vip
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_unknown_topology(self,
                                               mock_update,
                                               mock_get_failover_flow,
                                               mock_get_flavor_meta,
                                               mock_get_az_meta,
                                               mock_api_get_session,
                                               mock_dyn_log_listener,
                                               mock_taskflow_load,
                                               mock_pool_repo_get,
                                               mock_member_repo_get,
                                               mock_l7rule_repo_get,
                                               mock_l7policy_repo_get,
                                               mock_listener_repo_get,
                                               mock_lb_repo_get,
                                               mock_health_mon_repo_get,
                                               mock_amp_repo_get):

        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = 'bogus'
        load_balancer_mock.flavor_id = None
        load_balancer_mock.availability_zone = None
        load_balancer_mock.vip = _vip_mock

        mock_lb_repo_get.return_value = load_balancer_mock

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.FLAVOR: {'loadbalancer_topology':
                                          load_balancer_mock.topology},
                       constants.LOADBALANCER: load_balancer_mock,
                       constants.LOADBALANCER_ID: load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.SERVER_GROUP_ID:
                           load_balancer_mock.server_group_id,
                       constants.AVAILABILITY_ZONE: {},
                       constants.VIP: load_balancer_mock.vip
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_with_flavor(self,
                                          mock_update,
                                          mock_get_failover_flow,
                                          mock_get_flavor_meta,
                                          mock_get_az_meta,
                                          mock_api_get_session,
                                          mock_dyn_log_listener,
                                          mock_taskflow_load,
                                          mock_pool_repo_get,
                                          mock_member_repo_get,
                                          mock_l7rule_repo_get,
                                          mock_l7policy_repo_get,
                                          mock_listener_repo_get,
                                          mock_lb_repo_get,
                                          mock_health_mon_repo_get,
                                          mock_amp_repo_get):
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        load_balancer_mock.flavor_id = uuidutils.generate_uuid()
        load_balancer_mock.availability_zone = None
        load_balancer_mock.vip = _vip_mock
        mock_get_flavor_meta.return_value = {'taste': 'spicy'}

        mock_lb_repo_get.return_value = load_balancer_mock

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.FLAVOR: {'loadbalancer_topology':
                                          load_balancer_mock.topology,
                                          'taste': 'spicy'},
                       constants.LOADBALANCER: load_balancer_mock,
                       constants.LOADBALANCER_ID: load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.SERVER_GROUP_ID: None,
                       constants.AVAILABILITY_ZONE: {},
                       constants.SERVER_GROUP_ID:
                           load_balancer_mock.server_group_id,
                       constants.VIP: load_balancer_mock.vip
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_with_az(self,
                                      mock_update,
                                      mock_get_failover_flow,
                                      mock_get_flavor_meta,
                                      mock_get_az_meta,
                                      mock_api_get_session,
                                      mock_dyn_log_listener,
                                      mock_taskflow_load,
                                      mock_pool_repo_get,
                                      mock_member_repo_get,
                                      mock_l7rule_repo_get,
                                      mock_l7policy_repo_get,
                                      mock_listener_repo_get,
                                      mock_lb_repo_get,
                                      mock_health_mon_repo_get,
                                      mock_amp_repo_get):

        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = 'bogus'
        load_balancer_mock.flavor_id = None
        load_balancer_mock.availability_zone = uuidutils.generate_uuid()
        load_balancer_mock.vip = _vip_mock
        mock_get_az_meta.return_value = {'planet': 'jupiter'}

        mock_lb_repo_get.return_value = load_balancer_mock

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.FLAVOR: {'loadbalancer_topology':
                                          load_balancer_mock.topology},
                       constants.LOADBALANCER: load_balancer_mock,
                       constants.LOADBALANCER_ID: load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.SERVER_GROUP_ID:
                           load_balancer_mock.server_group_id,
                       constants.AVAILABILITY_ZONE: {'planet': 'jupiter'},
                       constants.VIP: load_balancer_mock.vip
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.amphora_flows.'
                'AmphoraFlows.get_failover_amphora_flow')
    def test_failover_amp_missing_amp(self,
                                      mock_get_amp_failover,
                                      mock_api_get_session,
                                      mock_dyn_log_listener,
                                      mock_taskflow_load,
                                      mock_pool_repo_get,
                                      mock_member_repo_get,
                                      mock_l7rule_repo_get,
                                      mock_l7policy_repo_get,
                                      mock_listener_repo_get,
                                      mock_lb_repo_get,
                                      mock_health_mon_repo_get,
                                      mock_amp_repo_get):

        mock_amp_repo_get.return_value = None

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        mock_get_amp_failover.assert_not_called()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amp_flow_exception(self,
                                         mock_update,
                                         mock_api_get_session,
                                         mock_dyn_log_listener,
                                         mock_taskflow_load,
                                         mock_pool_repo_get,
                                         mock_member_repo_get,
                                         mock_l7rule_repo_get,
                                         mock_l7policy_repo_get,
                                         mock_listener_repo_get,
                                         mock_lb_repo_get,
                                         mock_health_mon_repo_get,
                                         mock_amp_repo_get):

        mock_amphora = mock.MagicMock()
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amp_repo_get.return_value = mock_amphora

        mock_lb_repo_get.side_effect = TestException('boom')
        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)
        mock_update.assert_called_with(_db_session, LB_ID,
                                       provisioning_status=constants.ERROR)

    @mock.patch('octavia.controller.worker.v1.flows.amphora_flows.'
                'AmphoraFlows.get_failover_amphora_flow')
    def test_failover_amp_no_lb(self,
                                mock_get_failover_amp_flow,
                                mock_api_get_session,
                                mock_dyn_log_listener,
                                mock_taskflow_load,
                                mock_pool_repo_get,
                                mock_member_repo_get,
                                mock_l7rule_repo_get,
                                mock_l7policy_repo_get,
                                mock_listener_repo_get,
                                mock_lb_repo_get,
                                mock_health_mon_repo_get,
                                mock_amp_repo_get):
        _flow_mock.run.reset_mock()
        FAKE_FLOW = 'FAKE_FLOW'
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.status = constants.AMPHORA_READY
        mock_amp_repo_get.return_value = mock_amphora
        mock_get_failover_amp_flow.return_value = FAKE_FLOW
        expected_stored_params = {constants.AVAILABILITY_ZONE: {},
                                  constants.BUILD_TYPE_PRIORITY:
                                      constants.LB_CREATE_FAILOVER_PRIORITY,
                                  constants.FLAVOR: {},
                                  constants.LOADBALANCER: None,
                                  constants.LOADBALANCER_ID: None,
                                  constants.SERVER_GROUP_ID: None,
                                  constants.VIP: None}

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        mock_get_failover_amp_flow.assert_called_once_with(mock_amphora, None)
        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(FAKE_FLOW, store=expected_stored_params))
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.delete')
    def test_failover_deleted_amphora(self,
                                      mock_delete,
                                      mock_api_get_session,
                                      mock_dyn_log_listener,
                                      mock_taskflow_load,
                                      mock_pool_repo_get,
                                      mock_member_repo_get,
                                      mock_l7rule_repo_get,
                                      mock_l7policy_repo_get,
                                      mock_listener_repo_get,
                                      mock_lb_repo_get,
                                      mock_health_mon_repo_get,
                                      mock_amp_repo_get):

        mock_taskflow_load.reset_mock()
        mock_amphora = mock.MagicMock()
        mock_amphora.id = AMP_ID
        mock_amphora.status = constants.DELETED
        mock_amp_repo_get.return_value = mock_amphora

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        mock_delete.assert_called_with(_db_session, amphora_id=AMP_ID)
        mock_taskflow_load.assert_not_called()

    def test_get_amphorae_for_failover_single(self,
                                              mock_api_get_session,
                                              mock_dyn_log_listener,
                                              mock_taskflow_load,
                                              mock_pool_repo_get,
                                              mock_member_repo_get,
                                              mock_l7rule_repo_get,
                                              mock_l7policy_repo_get,
                                              mock_listener_repo_get,
                                              mock_lb_repo_get,
                                              mock_health_mon_repo_get,
                                              mock_amp_repo_get):
        amphora1_mock = mock.MagicMock()
        amphora1_mock.status = constants.AMPHORA_ALLOCATED
        amphora2_mock = mock.MagicMock()
        amphora2_mock.status = constants.DELETED

        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        load_balancer_mock.amphorae = [amphora1_mock, amphora2_mock]

        cw = controller_worker.ControllerWorker()
        result = cw._get_amphorae_for_failover(load_balancer_mock)

        self.assertEqual([amphora1_mock], result)

    @mock.patch('octavia.common.utils.get_amphora_driver')
    def test_get_amphorae_for_failover_act_stdby(self,
                                                 mock_get_amp_driver,
                                                 mock_api_get_session,
                                                 mock_dyn_log_listener,
                                                 mock_taskflow_load,
                                                 mock_pool_repo_get,
                                                 mock_member_repo_get,
                                                 mock_l7rule_repo_get,
                                                 mock_l7policy_repo_get,
                                                 mock_listener_repo_get,
                                                 mock_lb_repo_get,
                                                 mock_health_mon_repo_get,
                                                 mock_amp_repo_get):
        # Note: This test uses three amphora even though we only have
        #       two per load balancer to properly test the ordering from
        #       this method.
        amp_driver_mock = mock.MagicMock()
        amp_driver_mock.get_interface_from_ip.side_effect = [
            'fake0', None, 'fake1']
        mock_get_amp_driver.return_value = amp_driver_mock
        backup_amphora_mock = mock.MagicMock()
        backup_amphora_mock.status = constants.AMPHORA_ALLOCATED
        deleted_amphora_mock = mock.MagicMock()
        deleted_amphora_mock.status = constants.DELETED
        master_amphora_mock = mock.MagicMock()
        master_amphora_mock.status = constants.AMPHORA_ALLOCATED
        bogus_amphora_mock = mock.MagicMock()
        bogus_amphora_mock.status = constants.AMPHORA_ALLOCATED

        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        load_balancer_mock.amphorae = [
            master_amphora_mock, deleted_amphora_mock, backup_amphora_mock,
            bogus_amphora_mock]

        cw = controller_worker.ControllerWorker()
        result = cw._get_amphorae_for_failover(load_balancer_mock)

        self.assertEqual([master_amphora_mock, bogus_amphora_mock,
                          backup_amphora_mock], result)

    @mock.patch('octavia.common.utils.get_amphora_driver')
    def test_get_amphorae_for_failover_act_stdby_net_split(
            self, mock_get_amp_driver, mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get, mock_l7policy_repo_get,
            mock_listener_repo_get, mock_lb_repo_get, mock_health_mon_repo_get,
            mock_amp_repo_get):
        # Case where the amps can't see eachother and somehow end up with
        # two amphora with an interface. This is highly unlikely as the
        # higher priority amphora should get the IP in a net split, but
        # let's test the code for this odd case.
        # Note: This test uses three amphora even though we only have
        #       two per load balancer to properly test the ordering from
        #       this method.
        amp_driver_mock = mock.MagicMock()
        amp_driver_mock.get_interface_from_ip.side_effect = [
            'fake0', 'fake1']
        mock_get_amp_driver.return_value = amp_driver_mock
        backup_amphora_mock = mock.MagicMock()
        backup_amphora_mock.status = constants.AMPHORA_ALLOCATED
        deleted_amphora_mock = mock.MagicMock()
        deleted_amphora_mock.status = constants.DELETED
        master_amphora_mock = mock.MagicMock()
        master_amphora_mock.status = constants.AMPHORA_ALLOCATED

        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        load_balancer_mock.amphorae = [
            backup_amphora_mock, deleted_amphora_mock, master_amphora_mock]

        cw = controller_worker.ControllerWorker()
        result = cw._get_amphorae_for_failover(load_balancer_mock)

        self.assertEqual([backup_amphora_mock, master_amphora_mock], result)

    def test_get_amphorae_for_failover_bogus_topology(self,
                                                      mock_api_get_session,
                                                      mock_dyn_log_listener,
                                                      mock_taskflow_load,
                                                      mock_pool_repo_get,
                                                      mock_member_repo_get,
                                                      mock_l7rule_repo_get,
                                                      mock_l7policy_repo_get,
                                                      mock_listener_repo_get,
                                                      mock_lb_repo_get,
                                                      mock_health_mon_repo_get,
                                                      mock_amp_repo_get):
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.topology = 'bogus'

        cw = controller_worker.ControllerWorker()
        self.assertRaises(exceptions.InvalidTopology,
                          cw._get_amphorae_for_failover,
                          load_balancer_mock)

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_failover_LB_flow')
    @mock.patch('octavia.controller.worker.v1.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_single(self,
                                          mock_get_amps_for_failover,
                                          mock_get_failover_lb_flow,
                                          mock_api_get_session,
                                          mock_dyn_log_listener,
                                          mock_taskflow_load,
                                          mock_pool_repo_get,
                                          mock_member_repo_get,
                                          mock_l7rule_repo_get,
                                          mock_l7policy_repo_get,
                                          mock_listener_repo_get,
                                          mock_lb_repo_get,
                                          mock_health_mon_repo_get,
                                          mock_amp_repo_get):
        FAKE_FLOW = 'FAKE_FLOW'
        _flow_mock.reset_mock()
        mock_lb_repo_get.return_value = _load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock]
        mock_get_failover_lb_flow.return_value = FAKE_FLOW

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           _load_balancer_mock.topology}
        expected_flow_store = {constants.LOADBALANCER: _load_balancer_mock,
                               constants.BUILD_TYPE_PRIORITY:
                                   constants.LB_CREATE_FAILOVER_PRIORITY,
                               constants.LOADBALANCER_ID:
                                   _load_balancer_mock.id,
                               constants.SERVER_GROUP_ID:
                                   _load_balancer_mock.server_group_id,
                               constants.FLAVOR: expected_flavor,
                               constants.AVAILABILITY_ZONE: {}}

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(_load_balancer_mock)
        mock_get_failover_lb_flow.assert_called_once_with([_amphora_mock],
                                                          _load_balancer_mock)
        mock_taskflow_load.assert_called_once_with(FAKE_FLOW,
                                                   store=expected_flow_store)
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_failover_LB_flow')
    @mock.patch('octavia.controller.worker.v1.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_act_stdby(self,
                                             mock_get_amps_for_failover,
                                             mock_get_failover_lb_flow,
                                             mock_api_get_session,
                                             mock_dyn_log_listener,
                                             mock_taskflow_load,
                                             mock_pool_repo_get,
                                             mock_member_repo_get,
                                             mock_l7rule_repo_get,
                                             mock_l7policy_repo_get,
                                             mock_listener_repo_get,
                                             mock_lb_repo_get,
                                             mock_health_mon_repo_get,
                                             mock_amp_repo_get):
        FAKE_FLOW = 'FAKE_FLOW'
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        load_balancer_mock.flavor_id = None
        load_balancer_mock.availability_zone = None
        load_balancer_mock.vip = _vip_mock
        mock_lb_repo_get.return_value = load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock,
                                                   _amphora_mock]
        mock_get_failover_lb_flow.return_value = FAKE_FLOW

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        expected_flow_store = {constants.LOADBALANCER: load_balancer_mock,
                               constants.BUILD_TYPE_PRIORITY:
                                   constants.LB_CREATE_FAILOVER_PRIORITY,
                               constants.LOADBALANCER_ID:
                                   load_balancer_mock.id,
                               constants.SERVER_GROUP_ID:
                                   load_balancer_mock.server_group_id,
                               constants.FLAVOR: expected_flavor,
                               constants.AVAILABILITY_ZONE: {}}

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(load_balancer_mock)
        mock_get_failover_lb_flow.assert_called_once_with(
            [_amphora_mock, _amphora_mock], load_balancer_mock)
        mock_taskflow_load.assert_called_once_with(FAKE_FLOW,
                                                   store=expected_flow_store)
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_loadbalancer_no_lb(self,
                                         mock_lb_repo_update,
                                         mock_api_get_session,
                                         mock_dyn_log_listener,
                                         mock_taskflow_load,
                                         mock_pool_repo_get,
                                         mock_member_repo_get,
                                         mock_l7rule_repo_get,
                                         mock_l7policy_repo_get,
                                         mock_listener_repo_get,
                                         mock_lb_repo_get,
                                         mock_health_mon_repo_get,
                                         mock_amp_repo_get):
        mock_lb_repo_get.return_value = None

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_update.assert_called_once_with(
            _db_session, LB_ID, provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('octavia.controller.worker.v1.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_with_bogus_topology(
            self, mock_get_amps_for_failover, mock_lb_repo_update,
            mock_api_get_session, mock_dyn_log_listener, mock_taskflow_load,
            mock_pool_repo_get, mock_member_repo_get, mock_l7rule_repo_get,
            mock_l7policy_repo_get, mock_listener_repo_get, mock_lb_repo_get,
            mock_health_mon_repo_get, mock_amp_repo_get):
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.topology = 'bogus'
        mock_lb_repo_get.return_value = load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock]

        cw = controller_worker.ControllerWorker()
        result = cw.failover_loadbalancer(LB_ID)

        self.assertIsNone(result)
        mock_lb_repo_update.assert_called_once_with(
            _db_session, LB_ID, provisioning_status=constants.ERROR)
        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(load_balancer_mock)

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_failover_LB_flow')
    @mock.patch('octavia.controller.worker.v1.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_with_az(self,
                                           mock_get_amps_for_failover,
                                           mock_get_failover_lb_flow,
                                           mock_get_az_meta,
                                           mock_api_get_session,
                                           mock_dyn_log_listener,
                                           mock_taskflow_load,
                                           mock_pool_repo_get,
                                           mock_member_repo_get,
                                           mock_l7rule_repo_get,
                                           mock_l7policy_repo_get,
                                           mock_listener_repo_get,
                                           mock_lb_repo_get,
                                           mock_health_mon_repo_get,
                                           mock_amp_repo_get):
        FAKE_FLOW = 'FAKE_FLOW'
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        load_balancer_mock.flavor_id = None
        load_balancer_mock.availability_zone = uuidutils.generate_uuid()
        load_balancer_mock.vip = _vip_mock
        mock_lb_repo_get.return_value = load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock]
        mock_get_failover_lb_flow.return_value = FAKE_FLOW
        mock_get_az_meta.return_value = {'planet': 'jupiter'}

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        expected_flow_store = {constants.LOADBALANCER: load_balancer_mock,
                               constants.BUILD_TYPE_PRIORITY:
                                   constants.LB_CREATE_FAILOVER_PRIORITY,
                               constants.LOADBALANCER_ID:
                                   load_balancer_mock.id,
                               constants.FLAVOR: expected_flavor,
                               constants.SERVER_GROUP_ID:
                                   load_balancer_mock.server_group_id,
                               constants.AVAILABILITY_ZONE: {
                                   'planet': 'jupiter'}}

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(load_balancer_mock)
        mock_get_failover_lb_flow.assert_called_once_with([_amphora_mock],
                                                          load_balancer_mock)
        mock_taskflow_load.assert_called_once_with(FAKE_FLOW,
                                                   store=expected_flow_store)
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={'taste': 'spicy'})
    @mock.patch('octavia.controller.worker.v1.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_failover_LB_flow')
    @mock.patch('octavia.controller.worker.v1.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_with_flavor(self,
                                               mock_get_amps_for_failover,
                                               mock_get_failover_lb_flow,
                                               mock_get_flavor_meta,
                                               mock_api_get_session,
                                               mock_dyn_log_listener,
                                               mock_taskflow_load,
                                               mock_pool_repo_get,
                                               mock_member_repo_get,
                                               mock_l7rule_repo_get,
                                               mock_l7policy_repo_get,
                                               mock_listener_repo_get,
                                               mock_lb_repo_get,
                                               mock_health_mon_repo_get,
                                               mock_amp_repo_get):
        FAKE_FLOW = 'FAKE_FLOW'
        _flow_mock.reset_mock()
        load_balancer_mock = mock.MagicMock()
        load_balancer_mock.listeners = [_listener_mock]
        load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        load_balancer_mock.flavor_id = uuidutils.generate_uuid()
        load_balancer_mock.availability_zone = None
        load_balancer_mock.vip = _vip_mock
        mock_lb_repo_get.return_value = load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock,
                                                   _amphora_mock]
        mock_get_failover_lb_flow.return_value = FAKE_FLOW

        expected_flavor = {'taste': 'spicy', constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        expected_flow_store = {constants.LOADBALANCER: load_balancer_mock,
                               constants.BUILD_TYPE_PRIORITY:
                                   constants.LB_CREATE_FAILOVER_PRIORITY,
                               constants.LOADBALANCER_ID:
                                   load_balancer_mock.id,
                               constants.FLAVOR: expected_flavor,
                               constants.SERVER_GROUP_ID:
                                   load_balancer_mock.server_group_id,
                               constants.AVAILABILITY_ZONE: {}}

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(load_balancer_mock)
        mock_get_failover_lb_flow.assert_called_once_with(
            [_amphora_mock, _amphora_mock], load_balancer_mock)
        mock_taskflow_load.assert_called_once_with(FAKE_FLOW,
                                                   store=expected_flow_store)
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.get_failover_amphora_flow',
                return_value=_flow_mock)
    @mock.patch(
        'octavia.db.repositories.AmphoraRepository.get_lb_for_amphora',
        return_value=_load_balancer_mock)
    def test_failover_amphora_anti_affinity(self,
                                            mock_get_lb_for_amphora,
                                            mock_get_update_listener_flow,
                                            mock_get_flavor_meta,
                                            mock_get_az_meta,
                                            mock_api_get_session,
                                            mock_dyn_log_listener,
                                            mock_taskflow_load,
                                            mock_pool_repo_get,
                                            mock_member_repo_get,
                                            mock_l7rule_repo_get,
                                            mock_l7policy_repo_get,
                                            mock_listener_repo_get,
                                            mock_lb_repo_get,
                                            mock_health_mon_repo_get,
                                            mock_amp_repo_get):

        self.conf.config(group="nova", enable_anti_affinity=True)
        _flow_mock.reset_mock()
        _load_balancer_mock.server_group_id = "123"

        cw = controller_worker.ControllerWorker()
        cw.failover_amphora(AMP_ID)

        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
            assert_called_once_with(
                _flow_mock,
                store={constants.LOADBALANCER_ID: _load_balancer_mock.id,
                       constants.BUILD_TYPE_PRIORITY:
                           constants.LB_CREATE_FAILOVER_PRIORITY,
                       constants.FLAVOR: {'loadbalancer_topology':
                                          _load_balancer_mock.topology},
                       constants.AVAILABILITY_ZONE: {},
                       constants.LOADBALANCER: _load_balancer_mock,
                       constants.VIP: _load_balancer_mock.vip,
                       constants.SERVER_GROUP_ID:
                           _load_balancer_mock.server_group_id
                       }))

        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.cert_rotate_amphora_flow',
                return_value=_flow_mock)
    def test_amphora_cert_rotation(self,
                                   mock_get_update_listener_flow,
                                   mock_api_get_session,
                                   mock_dyn_log_listener,
                                   mock_taskflow_load,
                                   mock_pool_repo_get,
                                   mock_member_repo_get,
                                   mock_l7rule_repo_get,
                                   mock_l7policy_repo_get,
                                   mock_listener_repo_get,
                                   mock_lb_repo_get,
                                   mock_health_mon_repo_get,
                                   mock_amp_repo_get):
        _flow_mock.reset_mock()
        cw = controller_worker.ControllerWorker()
        cw.amphora_cert_rotation(AMP_ID)
        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
         assert_called_once_with(_flow_mock,
                                 store={constants.AMPHORA: _amphora_mock,
                                        constants.AMPHORA_ID:
                                            _amphora_mock.id}))
        _flow_mock.run.assert_called_once_with()

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict')
    @mock.patch('octavia.db.repositories.AmphoraRepository.get_lb_for_amphora')
    @mock.patch('octavia.controller.worker.v1.flows.'
                'amphora_flows.AmphoraFlows.update_amphora_config_flow',
                return_value=_flow_mock)
    def test_update_amphora_agent_config(self,
                                         mock_update_flow,
                                         mock_get_lb_for_amp,
                                         mock_flavor_meta,
                                         mock_api_get_session,
                                         mock_dyn_log_listener,
                                         mock_taskflow_load,
                                         mock_pool_repo_get,
                                         mock_member_repo_get,
                                         mock_l7rule_repo_get,
                                         mock_l7policy_repo_get,
                                         mock_listener_repo_get,
                                         mock_lb_repo_get,
                                         mock_health_mon_repo_get,
                                         mock_amp_repo_get):
        _flow_mock.reset_mock()
        mock_lb = mock.MagicMock()
        mock_lb.flavor_id = 'vanilla'
        mock_get_lb_for_amp.return_value = mock_lb
        mock_flavor_meta.return_value = {'test': 'dict'}
        cw = controller_worker.ControllerWorker()
        cw.update_amphora_agent_config(AMP_ID)

        mock_amp_repo_get.assert_called_once_with(_db_session, id=AMP_ID)
        mock_get_lb_for_amp.assert_called_once_with(_db_session, AMP_ID)
        mock_flavor_meta.assert_called_once_with(_db_session, 'vanilla')
        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
         assert_called_once_with(_flow_mock,
                                 store={constants.AMPHORA: _amphora_mock,
                                        constants.FLAVOR: {'test': 'dict'}}))
        _flow_mock.run.assert_called_once_with()

        # Test with no flavor
        _flow_mock.reset_mock()
        mock_amp_repo_get.reset_mock()
        mock_get_lb_for_amp.reset_mock()
        mock_flavor_meta.reset_mock()
        base_taskflow.BaseTaskFlowEngine._taskflow_load.reset_mock()
        mock_lb.flavor_id = None
        cw.update_amphora_agent_config(AMP_ID)
        mock_amp_repo_get.assert_called_once_with(_db_session, id=AMP_ID)
        mock_get_lb_for_amp.assert_called_once_with(_db_session, AMP_ID)
        mock_flavor_meta.assert_not_called()
        (base_taskflow.BaseTaskFlowEngine._taskflow_load.
         assert_called_once_with(_flow_mock,
                                 store={constants.AMPHORA: _amphora_mock,
                                        constants.FLAVOR: {}}))
        _flow_mock.run.assert_called_once_with()
