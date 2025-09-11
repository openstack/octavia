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
import tenacity

from octavia.api.drivers import utils as provider_utils
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.controller.worker.v2 import controller_worker
from octavia.controller.worker.v2.flows import flow_utils
import octavia.tests.unit.base as base

TLS_CERT_ID = uuidutils.generate_uuid()
AMP_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
LISTENER_ID = uuidutils.generate_uuid()
POOL_ID = uuidutils.generate_uuid()
PROJECT_ID = uuidutils.generate_uuid()
HM_ID = uuidutils.generate_uuid()
MEMBER_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
L7POLICY_ID = uuidutils.generate_uuid()
L7RULE_ID = uuidutils.generate_uuid()
PROJECT_ID = uuidutils.generate_uuid()
LISTENER_ID = uuidutils.generate_uuid()
FLAVOR_ID = uuidutils.generate_uuid()
SERVER_GROUP_ID = uuidutils.generate_uuid()
AZ_ID = uuidutils.generate_uuid()
HEALTH_UPDATE_DICT = {'delay': 1, 'timeout': 2}
LISTENER_UPDATE_DICT = {'name': 'test', 'description': 'test2'}
MEMBER_UPDATE_DICT = {'weight': 1, 'ip_address': '10.0.0.0'}
POOL_UPDATE_DICT = {'name': 'test', 'description': 'test2'}
L7POLICY_UPDATE_DICT = {'action': constants.L7POLICY_ACTION_REJECT}
L7RULE_UPDATE_DICT = {
    'type': constants.L7RULE_TYPE_PATH,
    'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
    'value': '/api'}

_db_amphora_mock = mock.MagicMock()
_amphora_mock = {
    constants.ID: AMP_ID,
    constants.LOAD_BALANCER_ID: LB_ID,
}
_flow_mock = mock.MagicMock()
_db_health_mon_mock = mock.MagicMock()
_health_mon_mock = {
    constants.HEALTHMONITOR_ID: HM_ID,
    constants.POOL_ID: POOL_ID
}
_vip_mock = mock.MagicMock()
_listener_mock = mock.MagicMock()
_db_load_balancer_mock = mock.MagicMock()
_load_balancer_mock = {
    constants.LOADBALANCER_ID: LB_ID,
    constants.TOPOLOGY: constants.TOPOLOGY_SINGLE,
    constants.FLAVOR_ID: 1,
    constants.AVAILABILITY_ZONE: None,
    constants.SERVER_GROUP_ID: None
}

_member_mock = mock.MagicMock()
_pool_mock = {constants.POOL_ID: POOL_ID}
_db_pool_mock = mock.MagicMock()
_db_pool_mock.load_balancer = _db_load_balancer_mock
_member_mock.pool = _db_pool_mock
_l7policy_mock = mock.MagicMock()
_l7policy_mock.id = L7POLICY_ID
_l7policy_mock.to_dict.return_value = {constants.ID: L7POLICY_ID}
_l7rule_mock = mock.MagicMock()
_create_map_flow_mock = mock.MagicMock()
_db_amphora_mock.load_balancer_id = LB_ID
_db_amphora_mock.id = AMP_ID
_db_session = mock.MagicMock()
CONF = cfg.CONF


class TestException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


@mock.patch('octavia.db.repositories.AmphoraRepository.get',
            return_value=_db_amphora_mock)
@mock.patch('octavia.db.repositories.HealthMonitorRepository.get',
            return_value=_db_health_mon_mock)
@mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
            return_value=_db_load_balancer_mock)
@mock.patch('octavia.db.repositories.ListenerRepository.get',
            return_value=_listener_mock)
@mock.patch('octavia.db.repositories.L7PolicyRepository.get',
            return_value=_l7policy_mock)
@mock.patch('octavia.db.repositories.L7RuleRepository.get',
            return_value=_l7rule_mock)
@mock.patch('octavia.db.repositories.MemberRepository.get',
            return_value=_member_mock)
@mock.patch('octavia.db.repositories.PoolRepository.get',
            return_value=_db_pool_mock)
@mock.patch('octavia.common.base_taskflow.TaskFlowServiceController',
            return_value=_flow_mock)
@mock.patch('taskflow.listeners.logging.DynamicLoggingListener')
@mock.patch('octavia.db.api.get_session', return_value=_db_session)
class TestControllerWorker(base.TestCase):

    def setUp(self):

        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(group="task_flow", jobboard_enabled=True)

        _db_pool_mock.listeners = [_listener_mock]
        _db_pool_mock.load_balancer = _db_load_balancer_mock
        _db_health_mon_mock.pool = _db_pool_mock
        _db_load_balancer_mock.amphorae = _db_amphora_mock
        _db_load_balancer_mock.vip = _vip_mock
        _db_load_balancer_mock.id = LB_ID
        _db_load_balancer_mock.flavor_id = 1
        _db_load_balancer_mock.availability_zone = None
        _db_load_balancer_mock.server_group_id = None
        _db_load_balancer_mock.project_id = PROJECT_ID
        _db_load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        _listener_mock.load_balancer = _db_load_balancer_mock
        _listener_mock.id = LISTENER_ID
        _listener_mock.to_dict.return_value = {
            constants.ID: LISTENER_ID, constants.LOAD_BALANCER_ID: LB_ID,
            constants.PROJECT_ID: PROJECT_ID}
        self.ref_listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                                  constants.LOADBALANCER_ID: LB_ID,
                                  constants.PROJECT_ID: PROJECT_ID}

        _member_mock.pool = _db_pool_mock
        _l7policy_mock.listener = _listener_mock
        _l7rule_mock.l7policy = _l7policy_mock
        _db_load_balancer_mock.listeners = [_listener_mock]
        _db_load_balancer_mock.to_dict.return_value = {'id': LB_ID}

        fetch_mock = mock.MagicMock()
        _flow_mock.driver.persistence = fetch_mock

        _db_pool_mock.id = POOL_ID
        _db_health_mon_mock.pool_id = POOL_ID
        _db_health_mon_mock.id = HM_ID
        _db_health_mon_mock.to_dict.return_value = {
            'id': HM_ID,
            constants.POOL_ID: POOL_ID
        }

        super().setUp()

    @mock.patch('octavia.controller.worker.v2.flows.'
                'amphora_flows.AmphoraFlows.get_delete_amphora_flow',
                return_value='TEST')
    def test_delete_amphora(self,
                            mock_get_delete_amp_flow,
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
        cw.delete_amphora(AMP_ID)

        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_delete_amphora_flow,
                store={constants.AMPHORA: _db_amphora_mock.to_dict()}))

    @mock.patch('octavia.controller.worker.v2.flows.'
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

        cw = controller_worker.ControllerWorker()
        cw.create_health_monitor(_health_mon_mock)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        mock_health_mon_repo_get.return_value = _db_health_mon_mock

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_create_health_monitor_flow,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.POOL_ID:
                                               POOL_ID}))

    def test_delete_health_monitor(self,
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
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)

        cw.delete_health_monitor(_health_mon_mock)
        mock_health_mon_repo_get.return_value = _db_health_mon_mock
        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_delete_health_monitor_flow,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.POOL_ID:
                                               POOL_ID,
                                           constants.PROJECT_ID: PROJECT_ID}))

    def test_update_health_monitor(self,
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
        mock_health_mon_repo_get.return_value = _db_health_mon_mock
        _db_health_mon_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        cw.update_health_monitor(_health_mon_mock,
                                 HEALTH_UPDATE_DICT)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_health_monitor_flow,
                                    store={constants.HEALTH_MON:
                                           _health_mon_mock,
                                           constants.POOL_ID: POOL_ID,
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.UPDATE_DICT:
                                           HEALTH_UPDATE_DICT}))

    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_health_monitor_timeout(self,
                                           mock__get_db_obj_until_pending,
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
        _db_health_mon_mock.provisioning_status = constants.ACTIVE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = _db_health_mon_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        cw = controller_worker.ControllerWorker()
        cw.update_health_monitor(_health_mon_mock,
                                 HEALTH_UPDATE_DICT)

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    def test_create_listener(self,
                             mock_get_flavor_dict,
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

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID,
                         constants.PROJECT_ID: PROJECT_ID}
        cw.create_listener(listener_dict)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)

        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_create_listener_flow, flavor_dict=flavor_dict,
                store={constants.LOADBALANCER: provider_lb,
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.LISTENERS: [listener_dict]}))

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    def test_delete_listener(self,
                             mock_get_flavor_dict,
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
        load_balancer_mock.provisioning_status = constants.PENDING_UPDATE
        load_balancer_mock.id = LB_ID
        load_balancer_mock.flavor_id = 1
        load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        mock_lb_repo_get.return_value = load_balancer_mock

        _flow_mock.reset_mock()

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID,
                         constants.PROJECT_ID: PROJECT_ID}
        cw = controller_worker.ControllerWorker()
        cw.delete_listener(listener_dict)

        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        (cw.services_controller.run_poster.
         assert_called_once_with(
             flow_utils.get_delete_listener_flow, flavor_dict=flavor_dict,
             store={constants.LISTENER: self.ref_listener_dict,
                    constants.LOADBALANCER_ID: LB_ID,
                    constants.PROJECT_ID: PROJECT_ID}))

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    def test_update_listener(self,
                             mock_get_flavor_dict,
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
        load_balancer_mock.provisioning_status = constants.PENDING_UPDATE
        load_balancer_mock.id = LB_ID
        load_balancer_mock.flavor_id = None
        load_balancer_mock.topology = constants.TOPOLOGY_SINGLE
        mock_lb_repo_get.return_value = load_balancer_mock

        _flow_mock.reset_mock()
        _listener_mock.provisioning_status = constants.PENDING_UPDATE

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID}
        cw = controller_worker.ControllerWorker()
        cw.update_listener(listener_dict, LISTENER_UPDATE_DICT)

        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_listener_flow,
                                    flavor_dict=flavor_dict,
                                    store={constants.LISTENER: listener_dict,
                                           constants.UPDATE_DICT:
                                           LISTENER_UPDATE_DICT,
                                           constants.LOADBALANCER_ID: LB_ID,
                                           constants.LISTENERS:
                                           [listener_dict]}))

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_listener_timeout(self,
                                     mock__get_db_obj_until_pending,
                                     mock_get_flavor_dict,
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
        load_balancer_mock.provisioning_status = constants.PENDING_UPDATE
        load_balancer_mock.id = LB_ID
        load_balancer_mock.flavor_id = 1
        _flow_mock.reset_mock()
        _listener_mock.provisioning_status = constants.PENDING_UPDATE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = load_balancer_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID}
        cw = controller_worker.ControllerWorker()
        cw.update_listener(listener_dict, LISTENER_UPDATE_DICT)

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
            mock_amp_repo_get):

        # Test the code path with an SINGLE topology
        self.conf.config(group="controller_worker",
                         loadbalancer_topology=constants.TOPOLOGY_SINGLE)
        _flow_mock.reset_mock()

        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_SINGLE},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None,
            constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }
        lb_mock = mock.MagicMock()
        lb_mock.listeners = []
        lb_mock.topology = constants.TOPOLOGY_SINGLE
        mock_lb_repo_get.side_effect = [None, None, None, lb_mock]

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(_load_balancer_mock)

        cw.services_controller.run_poster.assert_called_with(
            flow_utils.get_create_load_balancer_flow,
            constants.TOPOLOGY_SINGLE, listeners=[],
            flavor_dict=None, store=store)
        self.assertEqual(4, mock_lb_repo_get.call_count)

    def test_create_load_balancer_active_standby(
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
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)

        _flow_mock.reset_mock()
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_ACTIVE_STANDBY},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None,
            constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }
        setattr(mock_lb_repo_get.return_value, 'topology',
                constants.TOPOLOGY_ACTIVE_STANDBY)
        setattr(mock_lb_repo_get.return_value, 'listeners', [])

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(_load_balancer_mock)

        cw.services_controller.run_poster.assert_called_with(
            flow_utils.get_create_load_balancer_flow,
            constants.TOPOLOGY_ACTIVE_STANDBY, listeners=[],
            flavor_dict=None, store=store)

    def test_create_load_balancer_full_graph_single(
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
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_SINGLE)

        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        dict_listeners = [listener.to_dict() for listener in
                          provider_utils.db_listeners_to_provider_listeners(
                              listeners)]
        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners,
                                      topology=constants.TOPOLOGY_SINGLE)
        mock_lb_repo_get.return_value = lb
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_SINGLE},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None,
            constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(_load_balancer_mock)

        cw.services_controller.run_poster.assert_called_with(
            flow_utils.get_create_load_balancer_flow,
            constants.TOPOLOGY_SINGLE, listeners=dict_listeners,
            flavor_dict=None, store=store)

    def test_create_load_balancer_full_graph_active_standby(
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
            mock_amp_repo_get):

        self.conf.config(
            group="controller_worker",
            loadbalancer_topology=constants.TOPOLOGY_ACTIVE_STANDBY)

        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        dict_listeners = [listener.to_dict() for listener in
                          provider_utils.db_listeners_to_provider_listeners(
                              listeners)]
        lb = data_models.LoadBalancer(
            id=LB_ID, listeners=listeners,
            topology=constants.TOPOLOGY_ACTIVE_STANDBY)
        dict_listeners = [listener.to_dict() for listener in
                          provider_utils.db_listeners_to_provider_listeners(
                              listeners)]
        mock_lb_repo_get.return_value = lb
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_ACTIVE_STANDBY},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None,
            constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(_load_balancer_mock)

        cw.services_controller.run_poster.assert_called_with(
            flow_utils.get_create_load_balancer_flow,
            constants.TOPOLOGY_ACTIVE_STANDBY, listeners=dict_listeners,
            store=store, flavor_dict=None)

    @mock.patch('octavia.controller.worker.v2.flows.load_balancer_flows.'
                'LoadBalancerFlows.get_create_load_balancer_flow')
    @mock.patch('octavia.common.base_taskflow.BaseTaskFlowEngine.'
                'taskflow_load')
    def test_create_load_balancer_full_graph_jobboard_disabled(
            self,
            mock_base_taskflow_load,
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

        self.conf.config(group="task_flow", jobboard_enabled=False)

        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        dict_listeners = [listener.to_dict() for listener in
                          provider_utils.db_listeners_to_provider_listeners(
                              listeners)]
        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners,
                                      topology=constants.TOPOLOGY_SINGLE)
        mock_lb_repo_get.return_value = lb
        store = {
            constants.LOADBALANCER_ID: LB_ID,
            'update_dict': {'topology': constants.TOPOLOGY_SINGLE},
            constants.BUILD_TYPE_PRIORITY: constants.LB_CREATE_NORMAL_PRIORITY,
            constants.FLAVOR: None,
            constants.SERVER_GROUP_ID: None,
            constants.AVAILABILITY_ZONE: None,
        }

        cw = controller_worker.ControllerWorker()
        cw.create_load_balancer(_load_balancer_mock)

        mock_get_create_load_balancer_flow.assert_called_with(
            constants.TOPOLOGY_SINGLE, listeners=dict_listeners,
            flavor_dict=None)
        mock_base_taskflow_load.assert_called_with(
            mock_get_create_load_balancer_flow.return_value, store=store)

    def test_delete_load_balancer_without_cascade(self,
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
        cw.delete_load_balancer(_load_balancer_mock, cascade=False)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_delete_load_balancer_flow,
                _load_balancer_mock,
                store={constants.LOADBALANCER: _load_balancer_mock,
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.SERVER_GROUP_ID:
                           _db_load_balancer_mock.server_group_id,
                       constants.PROJECT_ID: _db_load_balancer_mock.project_id,

                       }))

    def test_delete_load_balancer_with_cascade(self,
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
        cw.delete_load_balancer(_load_balancer_mock, cascade=True)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        listener_list = [{constants.LISTENER_ID: LISTENER_ID,
                          constants.LOADBALANCER_ID: LB_ID,
                          constants.PROJECT_ID: PROJECT_ID}]

        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_cascade_delete_load_balancer_flow,
                _load_balancer_mock, listener_list, [],
                store={constants.LOADBALANCER: _load_balancer_mock,
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.SERVER_GROUP_ID:
                           _db_load_balancer_mock.server_group_id,
                       constants.PROJECT_ID: _db_load_balancer_mock.project_id,
                       })
         )

    @mock.patch(
        "octavia.common.tls_utils.cert_parser.load_certificates_data",
        side_effect=RuntimeError
    )
    def test_delete_load_balancer_with_cascade_tls_unavailable(
            self,
            mock_load_tls_cert,
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
            mock_amp_repo_get
    ):
        _flow_mock.reset_mock()

        _listener_mock.tls_certificate_id = TLS_CERT_ID
        _listener_mock.to_dict.return_value[
            constants.TLS_CERTIFICATE_ID] = TLS_CERT_ID

        cw = controller_worker.ControllerWorker()
        cw.delete_load_balancer(_load_balancer_mock, cascade=True)

        mock_lb_repo_get.assert_called_once_with(
            _db_session,
            id=LB_ID)

        # Check load_certificates_data called and error is raised
        # Error must be ignored because it is not critical for current flow
        mock_load_tls_cert.assert_called_once()

        listener_list = [{constants.LISTENER_ID: LISTENER_ID,
                          constants.LOADBALANCER_ID: LB_ID,
                          constants.PROJECT_ID: PROJECT_ID,
                          "default_tls_container_ref": TLS_CERT_ID}]

        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_cascade_delete_load_balancer_flow,
                _load_balancer_mock, listener_list, [],
                store={constants.LOADBALANCER: _load_balancer_mock,
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.SERVER_GROUP_ID:
                           _db_load_balancer_mock.server_group_id,
                       constants.PROJECT_ID: _db_load_balancer_mock.project_id,
                       })
         )

        _listener_mock.reset_mock()

    @mock.patch('octavia.db.repositories.ListenerRepository.get_all',
                return_value=([_listener_mock], None))
    def test_update_load_balancer(self,
                                  mock_listener_repo_get_all,
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
        _db_load_balancer_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        change = 'TEST2'
        cw.update_load_balancer(_load_balancer_mock, change)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_load_balancer_flow,
                                    store={constants.UPDATE_DICT: change,
                                           constants.LOADBALANCER:
                                               _load_balancer_mock,
                                           constants.LOADBALANCER_ID:
                                               _db_load_balancer_mock.id,
                                           }))

    @mock.patch('octavia.db.repositories.ListenerRepository.get_all',
                return_value=([_listener_mock], None))
    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_load_balancer_timeout(self,
                                          mock__get_db_obj_until_pending,
                                          mock_listener_repo_get_all,
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
        _db_load_balancer_mock.provisioning_status = constants.ACTIVE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = _db_load_balancer_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        cw = controller_worker.ControllerWorker()
        change = 'TEST2'
        cw.update_load_balancer(_load_balancer_mock, change)

    @mock.patch('octavia.controller.worker.v2.flows.'
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
        _member = _member_mock.to_dict()
        cw = controller_worker.ControllerWorker()
        cw.create_member(_member)

        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        (cw.services_controller.run_poster.
         assert_called_once_with(flow_utils.get_create_member_flow,
                                 store={constants.MEMBER: _member,
                                        constants.LISTENERS:
                                            [self.ref_listener_dict],
                                        constants.LOADBALANCER_ID:
                                            LB_ID,
                                        constants.LOADBALANCER:
                                            provider_lb,
                                        constants.POOL_ID:
                                            POOL_ID,
                                        constants.AVAILABILITY_ZONE: {}}))

    @mock.patch('octavia.controller.worker.v2.flows.'
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
        _member = _member_mock.to_dict()
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.delete_member(_member)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)

        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_delete_member_flow,
                store={constants.MEMBER: _member,
                       constants.LISTENERS: [self.ref_listener_dict],
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.LOADBALANCER: provider_lb,
                       constants.POOL_ID: POOL_ID,
                       constants.PROJECT_ID: PROJECT_ID,
                       constants.AVAILABILITY_ZONE: {}}))

    @mock.patch('octavia.controller.worker.v2.flows.'
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
        db_member = mock.MagicMock()
        db_member.provisioning_status = constants.PENDING_UPDATE
        db_member.pool = _db_pool_mock
        mock_member_repo_get.return_value = db_member
        _member = _member_mock.to_dict()
        _member[constants.PROVISIONING_STATUS] = constants.PENDING_UPDATE
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.update_member(_member, MEMBER_UPDATE_DICT)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_member_flow,
                                    store={constants.MEMBER: _member,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.POOL_ID:
                                               POOL_ID,
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.UPDATE_DICT:
                                               MEMBER_UPDATE_DICT,
                                           constants.AVAILABILITY_ZONE: {}}))

    @mock.patch('octavia.controller.worker.v2.flows.'
                'member_flows.MemberFlows.get_update_member_flow',
                return_value=_flow_mock)
    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict')
    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_member_timeout(self,
                                   mock__get_db_obj_until_pending,
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
        db_member = mock.MagicMock()
        db_member.provisioning_status = constants.ACTIVE
        db_member.pool = _db_pool_mock
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = db_member
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)
        mock_member_repo_get.return_value = db_member
        _member = _member_mock.to_dict()
        _member[constants.PROVISIONING_STATUS] = constants.PENDING_UPDATE
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        cw.update_member(_member, MEMBER_UPDATE_DICT)

    @mock.patch('octavia.controller.worker.v2.flows.'
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
        mock_get_az_metadata_dict.return_value = {}
        cw = controller_worker.ControllerWorker()
        old_member = mock.MagicMock()
        old_member.to_dict.return_value = {'id': 9,
                                           constants.POOL_ID: 'testtest'}
        new_member = mock.MagicMock()
        mock_member_repo_get.side_effect = [
            new_member, _member_mock, old_member]
        cw.batch_update_members([{constants.MEMBER_ID: 9,
                                  constants.POOL_ID: 'testtest'}],
                                [{constants.MEMBER_ID: 11}],
                                [MEMBER_UPDATE_DICT])
        provider_m = provider_utils.db_member_to_provider_member(_member_mock)
        old_provider_m = provider_utils.db_member_to_provider_member(
            old_member).to_dict()
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        (cw.services_controller.run_poster.
            assert_called_once_with(
                flow_utils.get_batch_update_members_flow,
                [old_provider_m],
                [{'member_id': 11}],
                [(provider_m.to_dict(), MEMBER_UPDATE_DICT)],
                store={constants.LISTENERS: [self.ref_listener_dict],
                       constants.LOADBALANCER_ID: LB_ID,
                       constants.LOADBALANCER: provider_lb,
                       constants.POOL_ID: POOL_ID,
                       constants.PROJECT_ID: PROJECT_ID,
                       constants.AVAILABILITY_ZONE: {}}))

    def test_create_pool(self,
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
        mock_pool_repo_get.return_value = _db_pool_mock

        cw = controller_worker.ControllerWorker()
        cw.create_pool(_pool_mock)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_create_pool_flow,
                                    store={constants.POOL_ID: POOL_ID,
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER:
                                               provider_lb}))

        self.assertEqual(1, mock_pool_repo_get.call_count)

    def test_delete_pool(self,
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
        _db_pool_mock.project_id = PROJECT_ID

        cw = controller_worker.ControllerWorker()
        cw.delete_pool(_pool_mock)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_delete_pool_flow,
                                    store={constants.POOL_ID: POOL_ID,
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.PROJECT_ID: PROJECT_ID}))

    def test_update_pool(self,
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
        _db_pool_mock.provisioning_status = constants.PENDING_UPDATE
        mock_pool_repo_get.return_value = _db_pool_mock

        cw = controller_worker.ControllerWorker()
        cw.update_pool(_pool_mock, POOL_UPDATE_DICT)
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict(recurse=True)
        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_pool_flow,
                                    store={constants.POOL_ID: POOL_ID,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.LOADBALANCER:
                                               provider_lb,
                                           constants.UPDATE_DICT:
                                               POOL_UPDATE_DICT}))

    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_pool_update(self,
                                mock__get_db_obj_until_pending,
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
        _db_pool_mock.provisioning_status = constants.ACTIVE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = _db_pool_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        cw = controller_worker.ControllerWorker()
        cw.update_pool(_pool_mock, POOL_UPDATE_DICT)

    def test_create_l7policy(self,
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
        l7policy_mock = {
            constants.L7POLICY_ID: L7POLICY_ID,
            constants.LISTENER_ID: LISTENER_ID
        }
        mock_l7policy_repo_get.side_effect = [None, _l7policy_mock]
        cw.create_l7policy(l7policy_mock)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_create_l7policy_flow,
                                    store={constants.L7POLICY: l7policy_mock,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID: LB_ID}))

    def test_delete_l7policy(self,
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
        l7policy_mock = {
            constants.L7POLICY_ID: L7POLICY_ID,
            constants.LISTENER_ID: LISTENER_ID
        }
        cw.delete_l7policy(l7policy_mock)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_delete_l7policy_flow,
                                    store={constants.L7POLICY: l7policy_mock,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID:
                                               LB_ID}))

    def test_update_l7policy(self,
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
        mock_listener_repo_get.return_value = _listener_mock
        _l7policy_mock.provisioning_status = constants.PENDING_UPDATE

        cw = controller_worker.ControllerWorker()
        l7policy_mock = {
            constants.L7POLICY_ID: L7POLICY_ID,
            constants.LISTENER_ID: LISTENER_ID
        }

        cw.update_l7policy(l7policy_mock, L7POLICY_UPDATE_DICT)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_l7policy_flow,
                                    store={constants.L7POLICY: l7policy_mock,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict],
                                           constants.LOADBALANCER_ID:
                                               LB_ID,
                                           constants.UPDATE_DICT:
                                               L7POLICY_UPDATE_DICT}))

    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_l7policy_timeout(self,
                                     mock__get_db_obj_until_pending,
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
        mock_listener_repo_get.return_value = _listener_mock
        _l7policy_mock.provisioning_status = constants.ACTIVE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = _l7policy_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        cw = controller_worker.ControllerWorker()
        l7policy_mock = {
            constants.L7POLICY_ID: L7POLICY_ID,
            constants.LISTENER_ID: LISTENER_ID
        }

        cw.update_l7policy(l7policy_mock, L7POLICY_UPDATE_DICT)

    def test_create_l7rule(self,
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

        cw.create_l7rule(_l7rule_mock.to_dict())

        l7_policy = provider_utils.db_l7policy_to_provider_l7policy(
            _l7policy_mock)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_create_l7rule_flow,
                                    store={constants.L7RULE:
                                           _l7rule_mock.to_dict(),
                                           constants.L7POLICY:
                                           l7_policy.to_dict(),
                                           constants.L7POLICY_ID: L7POLICY_ID,
                                           constants.LOADBALANCER_ID: LB_ID,
                                           constants.LISTENERS:
                                               [self.ref_listener_dict]
                                           }))

    def test_delete_l7rule(self,
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
        cw.delete_l7rule(_l7rule_mock.to_dict())
        l7_policy = provider_utils.db_l7policy_to_provider_l7policy(
            _l7policy_mock)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_delete_l7rule_flow,
                                    store={
                                        constants.L7RULE:
                                            _l7rule_mock.to_dict(),
                                        constants.L7POLICY:
                                            l7_policy.to_dict(),
                                        constants.L7POLICY_ID: L7POLICY_ID,
                                        constants.LISTENERS:
                                            [self.ref_listener_dict],
                                        constants.LOADBALANCER_ID: LB_ID,
                                    }))

    def test_update_l7rule(self,
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
        cw.update_l7rule(_l7rule_mock.to_dict(), L7RULE_UPDATE_DICT)
        l7_policy = provider_utils.db_l7policy_to_provider_l7policy(
            _l7policy_mock)

        (cw.services_controller.run_poster.
            assert_called_once_with(flow_utils.get_update_l7rule_flow,
                                    store={
                                        constants.L7RULE:
                                            _l7rule_mock.to_dict(),
                                        constants.L7POLICY:
                                            l7_policy.to_dict(),
                                        constants.L7POLICY_ID: L7POLICY_ID,
                                        constants.LOADBALANCER_ID: LB_ID,
                                        constants.LISTENERS:
                                            [self.ref_listener_dict],
                                        constants.UPDATE_DICT:
                                            L7RULE_UPDATE_DICT}))

    @mock.patch("octavia.controller.worker.v2.controller_worker."
                "ControllerWorker._get_db_obj_until_pending_update")
    def test_update_l7rule_timeout(self,
                                   mock__get_db_obj_until_pending,
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
        _l7rule_mock.provisioning_status = constants.ACTIVE
        last_attempt_mock = mock.MagicMock()
        last_attempt_mock.result.return_value = _l7rule_mock
        mock__get_db_obj_until_pending.side_effect = tenacity.RetryError(
            last_attempt=last_attempt_mock)

        cw = controller_worker.ControllerWorker()
        cw.update_l7rule(_l7rule_mock.to_dict(), L7RULE_UPDATE_DICT)

    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_lb_single(self,
                                        mock_update,
                                        mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_SINGLE
        mock_lb.flavor_id = None
        mock_lb.availability_zone = None
        mock_lb.server_group_id = None
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: None,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 1, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_lb_act_stdby(self,
                                           mock_update,
                                           mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        mock_lb.flavor_id = None
        mock_lb.availability_zone = None
        mock_lb.server_group_id = None
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_ACTIVE_STANDBY}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: None,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 2, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_anti_affinity(self,
                                            mock_update,
                                            mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_ACTIVE_STANDBY
        mock_lb.flavor_id = None
        mock_lb.availability_zone = None
        mock_lb.server_group_id = SERVER_GROUP_ID
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_ACTIVE_STANDBY}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: SERVER_GROUP_ID,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 2, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_unknown_topology(self,
                                               mock_update,
                                               mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = 'bogus'
        mock_lb.flavor_id = None
        mock_lb.availability_zone = None
        mock_lb.server_group_id = SERVER_GROUP_ID
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY: mock_lb.topology}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: SERVER_GROUP_ID,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), None, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={})
    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_with_flavor(self,
                                          mock_update,
                                          mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_SINGLE
        mock_lb.flavor_id = FLAVOR_ID
        mock_lb.availability_zone = None
        mock_lb.server_group_id = None
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE, 'taste': 'spicy'}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: None,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}
        mock_get_flavor_meta.return_value = {'taste': 'spicy'}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 1, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.db.repositories.AvailabilityZoneRepository.'
                'get_availability_zone_metadata_dict', return_value={})
    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_with_az(self,
                                      mock_update,
                                      mock_lb_db_to_provider,
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
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_SINGLE
        mock_lb.flavor_id = None
        mock_lb.availability_zone = AZ_ID
        mock_lb.server_group_id = None
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {'planet': 'jupiter'},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: None,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: []}
        mock_get_az_meta.return_value = {'planet': 'jupiter'}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 1, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.api.drivers.utils.'
                'db_loadbalancer_to_provider_loadbalancer')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amphora_with_add_vips(self,
                                            mock_update,
                                            mock_lb_db_to_provider,
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
        mock_additional_vips = [mock.MagicMock()]
        # mock_additional_vips[0].ip_address = mock.Mock()
        mock_lb = mock.MagicMock()
        mock_lb.id = LB_ID
        mock_lb.topology = constants.TOPOLOGY_SINGLE
        mock_lb.flavor_id = None
        mock_lb.availability_zone = None
        mock_lb.server_group_id = None
        mock_lb.additional_vips = mock_additional_vips
        mock_lb_repo_get.return_value = mock_lb
        mock_provider_lb = mock.MagicMock()
        mock_lb_db_to_provider.return_value = mock_provider_lb
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.load_balancer_id = LB_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                       constants.TOPOLOGY_SINGLE}
        expected_stored_params = {
            constants.AVAILABILITY_ZONE: {},
            constants.BUILD_TYPE_PRIORITY:
                constants.LB_CREATE_FAILOVER_PRIORITY,
            constants.FLAVOR: flavor_dict,
            constants.LOADBALANCER: mock_provider_lb.to_dict(),
            constants.LOADBALANCER_ID: LB_ID,
            constants.SERVER_GROUP_ID: None,
            constants.VIP: mock_lb.vip.to_dict(),
            constants.ADDITIONAL_VIPS: [
                add_vips.to_dict()
                for add_vips in mock_additional_vips
            ]}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(), 1, flavor_dict=flavor_dict,
            store=expected_stored_params)

    @mock.patch('octavia.controller.worker.v2.flows.amphora_flows.'
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

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_failover_amp_flow_exception_reraise(self,
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
        self.assertRaises(TestException,
                          cw.failover_amphora,
                          AMP_ID, reraise=True)

    @mock.patch('octavia.controller.worker.v2.flows.amphora_flows.'
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
        mock_amphora = mock.MagicMock()
        mock_amphora.load_balancer_id = None
        mock_amphora.id = AMP_ID
        mock_amphora.status = constants.AMPHORA_ALLOCATED
        mock_amp_repo_get.return_value = mock_amphora
        expected_stored_params = {constants.AVAILABILITY_ZONE: {},
                                  constants.BUILD_TYPE_PRIORITY:
                                      constants.LB_CREATE_FAILOVER_PRIORITY,
                                  constants.FLAVOR: {},
                                  constants.LOADBALANCER: None,
                                  constants.LOADBALANCER_ID: None,
                                  constants.SERVER_GROUP_ID: None,
                                  constants.VIP: {},
                                  constants.ADDITIONAL_VIPS: []}

        cw = controller_worker.ControllerWorker()
        cw.services_controller.reset_mock()
        cw.failover_amphora(AMP_ID)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_amphora_flow,
            mock_amphora.to_dict(),
            None, flavor_dict={}, store=expected_stored_params)

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

        self.assertEqual([amphora1_mock.to_dict()], result)

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

        self.assertEqual([master_amphora_mock.to_dict(),
                          bogus_amphora_mock.to_dict(),
                          backup_amphora_mock.to_dict()], result)

    @mock.patch('octavia.common.utils.get_amphora_driver')
    def test_get_amphorae_for_failover_act_stdby_net_split(
            self, mock_get_amp_driver, mock_api_get_session,
            mock_dyn_log_listener, mock_taskflow_load, mock_pool_repo_get,
            mock_member_repo_get, mock_l7rule_repo_get, mock_l7policy_repo_get,
            mock_listener_repo_get, mock_lb_repo_get, mock_health_mon_repo_get,
            mock_amp_repo_get):
        # Case where the amps can't see each other and somehow end up with
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

        self.assertEqual([backup_amphora_mock.to_dict(),
                          master_amphora_mock.to_dict()], result)

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

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict')
    @mock.patch('octavia.controller.worker.v2.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_single(self,
                                          mock_get_amps_for_failover,
                                          mock_get_flavor_dict,
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
        mock_lb_repo_get.return_value = _db_load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock]
        mock_get_flavor_dict.return_value = {}
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            _db_load_balancer_mock).to_dict()

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           _load_balancer_mock[constants.TOPOLOGY]}
        provider_lb[constants.FLAVOR] = expected_flavor
        expected_flow_store = {constants.LOADBALANCER: provider_lb,
                               constants.BUILD_TYPE_PRIORITY:
                                   constants.LB_CREATE_FAILOVER_PRIORITY,
                               constants.LOADBALANCER_ID:
                                   _load_balancer_mock[
                                       constants.LOADBALANCER_ID],
                               constants.SERVER_GROUP_ID:
                                   _load_balancer_mock[
                                       constants.SERVER_GROUP_ID],
                               constants.FLAVOR: expected_flavor,
                               constants.AVAILABILITY_ZONE: {}}

        cw = controller_worker.ControllerWorker()
        cw.failover_loadbalancer(LB_ID)

        mock_lb_repo_get.assert_called_once_with(_db_session, id=LB_ID)
        mock_get_amps_for_failover.assert_called_once_with(
            _db_load_balancer_mock)

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_LB_flow, [_amphora_mock], provider_lb,
            store=expected_flow_store)

    @mock.patch('octavia.controller.worker.v2.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_act_stdby(self,
                                             mock_get_amps_for_failover,
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
        mock_get_amps_for_failover.return_value = [_amphora_mock,
                                                   _amphora_mock]
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer_mock).to_dict()

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        provider_lb[constants.FLAVOR] = expected_flavor
        expected_flow_store = {constants.LOADBALANCER: provider_lb,
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

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_LB_flow, [_amphora_mock, _amphora_mock],
            provider_lb, store=expected_flow_store)

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
    @mock.patch('octavia.controller.worker.v2.controller_worker.'
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
    @mock.patch('octavia.controller.worker.v2.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_with_az(self,
                                           mock_get_amps_for_failover,
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
        load_balancer_mock.availability_zone = uuidutils.generate_uuid()
        load_balancer_mock.vip = _vip_mock
        mock_lb_repo_get.return_value = load_balancer_mock
        mock_get_amps_for_failover.return_value = [_amphora_mock]
        mock_get_az_meta.return_value = {'planet': 'jupiter'}
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer_mock).to_dict()

        expected_flavor = {constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        provider_lb[constants.FLAVOR] = expected_flavor
        expected_flow_store = {constants.LOADBALANCER: provider_lb,
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

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_LB_flow, [_amphora_mock], provider_lb,
            store=expected_flow_store)

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict', return_value={'taste': 'spicy'})
    @mock.patch('octavia.controller.worker.v2.controller_worker.'
                'ControllerWorker._get_amphorae_for_failover')
    def test_failover_loadbalancer_with_flavor(self,
                                               mock_get_amps_for_failover,
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
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer_mock).to_dict()

        expected_flavor = {'taste': 'spicy', constants.LOADBALANCER_TOPOLOGY:
                           load_balancer_mock.topology}
        provider_lb[constants.FLAVOR] = expected_flavor
        expected_flow_store = {constants.LOADBALANCER: provider_lb,
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

        cw.services_controller.run_poster.assert_called_once_with(
            flow_utils.get_failover_LB_flow, [_amphora_mock, _amphora_mock],
            provider_lb, store=expected_flow_store)

    def test_amphora_cert_rotation(self,
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
        cw.services_controller.reset_mock()
        cw.amphora_cert_rotation(AMP_ID)
        mock_amp_repo_get.return_value = _db_amphora_mock
        (cw.services_controller.run_poster.
         assert_called_once_with(flow_utils.cert_rotate_amphora_flow,
                                 store={constants.AMPHORA:
                                        _db_amphora_mock.to_dict(),
                                        constants.AMPHORA_ID:
                                        _amphora_mock[constants.ID]}))

    @mock.patch('octavia.db.repositories.FlavorRepository.'
                'get_flavor_metadata_dict')
    @mock.patch('octavia.db.repositories.AmphoraRepository.get_lb_for_amphora')
    def test_update_amphora_agent_config(self,
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
        cw.services_controller.reset_mock()
        cw.update_amphora_agent_config(AMP_ID)

        mock_amp_repo_get.assert_called_once_with(_db_session, id=AMP_ID)
        mock_get_lb_for_amp.assert_called_once_with(_db_session, AMP_ID)
        mock_flavor_meta.assert_called_once_with(_db_session, 'vanilla')
        (cw.services_controller.run_poster.
         assert_called_once_with(flow_utils.update_amphora_config_flow,
                                 store={constants.AMPHORA:
                                        _db_amphora_mock.to_dict(),
                                        constants.FLAVOR: {'test': 'dict'}}))

        # Test with no flavor
        _flow_mock.reset_mock()
        mock_amp_repo_get.reset_mock()
        mock_get_lb_for_amp.reset_mock()
        mock_flavor_meta.reset_mock()
        mock_lb.flavor_id = None
        cw.update_amphora_agent_config(AMP_ID)
        mock_amp_repo_get.assert_called_once_with(_db_session, id=AMP_ID)
        mock_get_lb_for_amp.assert_called_once_with(_db_session, AMP_ID)
        mock_flavor_meta.assert_not_called()
        (cw.services_controller.run_poster.
         assert_called_once_with(flow_utils.update_amphora_config_flow,
                                 store={constants.AMPHORA:
                                        _db_amphora_mock.to_dict(),
                                        constants.FLAVOR: {}}))
