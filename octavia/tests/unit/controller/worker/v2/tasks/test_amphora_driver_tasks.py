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

from cryptography import fernet
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from taskflow.types import failure

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.common import constants
from octavia.common import data_models
from octavia.common import utils
from octavia.controller.worker.v2.tasks import amphora_driver_tasks
from octavia.db import repositories as repo
from octavia.network import data_models as network_data_models
import octavia.tests.unit.base as base


AMP_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LISTENER_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
CONN_MAX_RETRIES = 10
CONN_RETRY_INTERVAL = 6
FAKE_CONFIG_FILE = 'fake config file'

_db_amphora_mock = mock.MagicMock()
_db_amphora_mock.id = AMP_ID
_db_amphora_mock.status = constants.AMPHORA_ALLOCATED
_db_amphora_mock.vrrp_ip = '198.51.100.65'
_amphora_mock = {
    constants.ID: AMP_ID,
    constants.STATUS: constants.AMPHORA_ALLOCATED,
    constants.COMPUTE_ID: COMPUTE_ID,
}
_db_load_balancer_mock = mock.MagicMock()
_db_load_balancer_mock.id = LB_ID
_listener_mock = mock.MagicMock()
_listener_mock.id = LISTENER_ID
_db_load_balancer_mock.listeners = [_listener_mock]
_vip_mock = mock.MagicMock()
_db_load_balancer_mock.vip = _vip_mock
_LB_mock = {
    constants.LOADBALANCER_ID: LB_ID,
}
_amphorae_mock = [_db_amphora_mock]
_amphora_network_config_mock = mock.MagicMock()
_amphorae_network_config_mock = {
    _amphora_mock[constants.ID]: _amphora_network_config_mock}
_network_mock = mock.MagicMock()
_session_mock = mock.MagicMock()


@mock.patch('octavia.db.repositories.AmphoraRepository.update')
@mock.patch('octavia.db.repositories.AmphoraRepository.get')
@mock.patch('octavia.db.repositories.ListenerRepository.update')
@mock.patch('octavia.db.repositories.ListenerRepository.get',
            return_value=_listener_mock)
@mock.patch('octavia.db.api.get_session', return_value=_session_mock)
@mock.patch('octavia.controller.worker.v2.tasks.amphora_driver_tasks.LOG')
@mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=AMP_ID)
@mock.patch('stevedore.driver.DriverManager.driver')
class TestAmphoraDriverTasks(base.TestCase):

    def setUp(self):

        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="haproxy_amphora",
                    active_connection_max_retries=CONN_MAX_RETRIES)
        conf.config(group="haproxy_amphora",
                    active_connection_retry_interval=CONN_RETRY_INTERVAL)
        conf.config(group="controller_worker",
                    loadbalancer_topology=constants.TOPOLOGY_SINGLE)
        self.timeout_dict = {constants.REQ_CONN_TIMEOUT: 1,
                             constants.REQ_READ_TIMEOUT: 2,
                             constants.CONN_MAX_RETRIES: 3,
                             constants.CONN_RETRY_INTERVAL: 4}
        super().setUp()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amp_listeners_update(self,
                                  mock_lb_get,
                                  mock_driver,
                                  mock_generate_uuid,
                                  mock_log,
                                  mock_get_session,
                                  mock_listener_repo_get,
                                  mock_listener_repo_update,
                                  mock_amphora_repo_get,
                                  mock_amphora_repo_update):

        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_lb_get.return_value = _db_load_balancer_mock
        amp_list_update_obj = amphora_driver_tasks.AmpListenersUpdate()
        amp_list_update_obj.execute(_LB_mock, _amphora_mock, self.timeout_dict)

        mock_driver.update_amphora_listeners.assert_called_once_with(
            _db_load_balancer_mock, _db_amphora_mock, self.timeout_dict)

        mock_driver.update_amphora_listeners.side_effect = Exception('boom')

        amp_list_update_obj.execute(_LB_mock, _amphora_mock, self.timeout_dict)

        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, AMP_ID, status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amp_index_listener_update(self,
                                       mock_lb_get,
                                       mock_driver,
                                       mock_generate_uuid,
                                       mock_log,
                                       mock_get_session,
                                       mock_listener_repo_get,
                                       mock_listener_repo_update,
                                       mock_amphora_repo_get,
                                       mock_amphora_repo_update):

        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_lb_get.return_value = _db_load_balancer_mock
        amp_list_update_obj = amphora_driver_tasks.AmphoraIndexListenerUpdate()
        amp_list_update_obj.execute(_LB_mock, 0, [_amphora_mock],
                                    self.timeout_dict)

        mock_driver.update_amphora_listeners.assert_called_once_with(
            _db_load_balancer_mock, _db_amphora_mock, self.timeout_dict)

        mock_driver.update_amphora_listeners.side_effect = Exception('boom')

        amp_list_update_obj.execute(_LB_mock, 0,
                                    [_amphora_mock], self.timeout_dict)

        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, AMP_ID, status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.session')
    def test_listeners_update(self,
                              mock_get_session_ctx,
                              mock_lb_get,
                              mock_driver,
                              mock_generate_uuid,
                              mock_log,
                              mock_get_session,
                              mock_listener_repo_get,
                              mock_listener_repo_update,
                              mock_amphora_repo_get,
                              mock_amphora_repo_update):
        listeners_update_obj = amphora_driver_tasks.ListenersUpdate()
        LB_ID = 'lb1'
        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        vip = data_models.Vip(ip_address='10.0.0.1')
        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners, vip=vip)
        mock_lb_get.side_effect = [lb, None, lb]
        listeners_update_obj.execute(lb.id)
        mock_driver.update.assert_called_once_with(lb)
        self.assertEqual(1, mock_driver.update.call_count)

        mock_driver.update.reset_mock()

        listeners_update_obj.execute(None)
        mock_driver.update.assert_not_called()

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test the revert
        amp = listeners_update_obj.revert(_LB_mock)
        expected_db_calls = [mock.call(mock_session,
                                       id=listeners[0].id,
                                       provisioning_status=constants.ERROR),
                             mock.call(mock_session,
                                       id=listeners[1].id,
                                       provisioning_status=constants.ERROR)]
        repo.ListenerRepository.update.assert_has_calls(expected_db_calls)
        self.assertEqual(2, repo.ListenerRepository.update.call_count)
        self.assertIsNone(amp)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_error')
    def test_amphora_index_listeners_reload(
            self, mock_prov_status_error, mock_lb_repo_get,
            mock_driver, mock_generate_uuid, mock_log, mock_get_session,
            mock_listener_repo_get, mock_listener_repo_update,
            mock_amphora_repo_get, mock_amphora_repo_update):
        amphora_mock = mock.MagicMock()
        listeners_reload_obj = (
            amphora_driver_tasks.AmphoraIndexListenersReload())
        mock_lb = mock.MagicMock()
        mock_listener = mock.MagicMock()
        mock_listener.id = '12345'
        mock_amphora_repo_get.return_value = amphora_mock
        mock_lb_repo_get.return_value = mock_lb
        mock_driver.reload.side_effect = [mock.DEFAULT, Exception('boom')]

        # Test no listeners
        mock_lb.listeners = None
        listeners_reload_obj.execute(mock_lb, 0, None)
        mock_driver.reload.assert_not_called()

        # Test with listeners
        mock_driver.start.reset_mock()
        mock_lb.listeners = [mock_listener]
        listeners_reload_obj.execute(mock_lb, 0, [amphora_mock],
                                     timeout_dict=self.timeout_dict)
        mock_driver.reload.assert_called_once_with(mock_lb, amphora_mock,
                                                   self.timeout_dict)

        # Test with reload exception
        mock_driver.reload.reset_mock()
        listeners_reload_obj.execute(mock_lb, 0, [amphora_mock],
                                     timeout_dict=self.timeout_dict)
        mock_driver.reload.assert_called_once_with(mock_lb, amphora_mock,
                                                   self.timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, amphora_mock[constants.ID],
            status=constants.ERROR)

    @mock.patch('octavia.controller.worker.task_utils.TaskUtils.'
                'mark_listener_prov_status_error')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_listeners_start(self, mock_lb_get,
                             mock_prov_status_error,
                             mock_driver,
                             mock_generate_uuid,
                             mock_log,
                             mock_get_session,
                             mock_listener_repo_get,
                             mock_listener_repo_update,
                             mock_amphora_repo_get,
                             mock_amphora_repo_update):
        listeners_start_obj = amphora_driver_tasks.ListenersStart()
        mock_lb = mock.MagicMock()
        mock_listener = mock.MagicMock()
        mock_listener.id = '12345'

        # Test no listeners
        mock_lb.listeners = None
        mock_lb_get.return_value = mock_lb
        listeners_start_obj.execute(_LB_mock)
        mock_driver.start.assert_not_called()

        # Test with listeners
        mock_driver.start.reset_mock()
        mock_lb.listeners = [mock_listener]
        listeners_start_obj.execute(_LB_mock)
        mock_driver.start.assert_called_once_with(mock_lb, None)

        # Test revert
        mock_lb.listeners = [mock_listener]
        listeners_start_obj.revert(_LB_mock)
        mock_prov_status_error.assert_called_once_with('12345')

    @mock.patch('octavia.db.api.session')
    def test_listener_delete(self,
                             mock_get_session_ctx,
                             mock_driver,
                             mock_generate_uuid,
                             mock_log,
                             mock_get_session,
                             mock_listener_repo_get,
                             mock_listener_repo_update,
                             mock_amphora_repo_get,
                             mock_amphora_repo_update):

        listener_dict = {constants.LISTENER_ID: LISTENER_ID}
        listener_delete_obj = amphora_driver_tasks.ListenerDelete()
        listener_delete_obj.execute(listener_dict)

        mock_driver.delete.assert_called_once_with(_listener_mock)

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test the revert
        amp = listener_delete_obj.revert(listener_dict)
        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

        # Test the revert with exception
        repo.ListenerRepository.update.reset_mock()
        mock_listener_repo_update.side_effect = Exception('fail')
        amp = listener_delete_obj.revert(listener_dict)
        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

    def test_amphora_get_info(self,
                              mock_driver,
                              mock_generate_uuid,
                              mock_log,
                              mock_get_session,
                              mock_listener_repo_get,
                              mock_listener_repo_update,
                              mock_amphora_repo_get,
                              mock_amphora_repo_update):

        amphora_get_info_obj = amphora_driver_tasks.AmphoraGetInfo()
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_get_info_obj.execute(_amphora_mock)

        mock_driver.get_info.assert_called_once_with(
            _db_amphora_mock)

    def test_amphora_get_diagnostics(self,
                                     mock_driver,
                                     mock_generate_uuid,
                                     mock_log,
                                     mock_get_session,
                                     mock_listener_repo_get,
                                     mock_listener_repo_update,
                                     mock_amphora_repo_get,
                                     mock_amphora_repo_update):

        amphora_get_diagnostics_obj = (amphora_driver_tasks.
                                       AmphoraGetDiagnostics())
        amphora_get_diagnostics_obj.execute(_amphora_mock)

        mock_driver.get_diagnostics.assert_called_once_with(
            _amphora_mock)

    @mock.patch('octavia.db.api.session')
    def test_amphora_finalize(self,
                              mock_get_session_ctx,
                              mock_driver,
                              mock_generate_uuid,
                              mock_log,
                              mock_get_session,
                              mock_listener_repo_get,
                              mock_listener_repo_update,
                              mock_amphora_repo_get,
                              mock_amphora_repo_update):

        amphora_finalize_obj = amphora_driver_tasks.AmphoraFinalize()
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_finalize_obj.execute(_amphora_mock)

        mock_driver.finalize_amphora.assert_called_once_with(
            _db_amphora_mock)

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test revert
        amp = amphora_finalize_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)
        self.assertIsNone(amp)

        # Test revert with exception
        repo.AmphoraRepository.update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        amp = amphora_finalize_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)
        self.assertIsNone(amp)

        # Test revert when this task failed
        repo.AmphoraRepository.update.reset_mock()
        amp = amphora_finalize_obj.revert(
            failure.Failure.from_exception(Exception('boom')), _amphora_mock)
        repo.AmphoraRepository.update.assert_not_called()

    @mock.patch('octavia.db.api.session')
    def test_amphora_post_network_plug(self,
                                       mock_get_session_ctx,
                                       mock_driver,
                                       mock_generate_uuid,
                                       mock_log,
                                       mock_get_session,
                                       mock_listener_repo_get,
                                       mock_listener_repo_update,
                                       mock_amphora_repo_get,
                                       mock_amphora_repo_update):

        amphora_post_network_plug_obj = (amphora_driver_tasks.
                                         AmphoraPostNetworkPlug())
        mock_amphora_repo_get.return_value = _db_amphora_mock
        fixed_ips = [{constants.SUBNET: {}}]
        port_mock = {constants.NETWORK: mock.MagicMock(),
                     constants.FIXED_IPS: fixed_ips,
                     constants.ID: uuidutils.generate_uuid()}
        amphora_post_network_plug_obj.execute(_amphora_mock, [port_mock],
                                              _amphora_network_config_mock)

        (mock_driver.post_network_plug.
            assert_called_once_with)(_db_amphora_mock,
                                     network_data_models.Port(**port_mock),
                                     _amphora_network_config_mock)

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test revert
        amp = amphora_post_network_plug_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

        # Test revert with exception
        repo.AmphoraRepository.update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        amp = amphora_post_network_plug_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

        # Test revert when this task failed
        repo.AmphoraRepository.update.reset_mock()
        amp = amphora_post_network_plug_obj.revert(
            failure.Failure.from_exception(Exception('boom')), _amphora_mock)
        repo.AmphoraRepository.update.assert_not_called()

    def test_amphora_post_network_plug_with_host_routes(
            self, mock_driver, mock_generate_uuid, mock_log, mock_get_session,
            mock_listener_repo_get, mock_listener_repo_update,
            mock_amphora_repo_get, mock_amphora_repo_update):

        amphora_post_network_plug_obj = (amphora_driver_tasks.
                                         AmphoraPostNetworkPlug())
        mock_amphora_repo_get.return_value = _db_amphora_mock
        host_routes = [{'destination': '10.0.0.0/16',
                        'nexthop': '192.168.10.3'},
                       {'destination': '10.2.0.0/16',
                        'nexthop': '192.168.10.5'}]
        fixed_ips = [{constants.SUBNET: {'host_routes': host_routes}}]

        port_mock = {constants.NETWORK: mock.MagicMock(),
                     constants.FIXED_IPS: fixed_ips,
                     constants.ID: uuidutils.generate_uuid()}
        amphora_post_network_plug_obj.execute(_amphora_mock, [port_mock],
                                              _amphora_network_config_mock)

        (mock_driver.post_network_plug.
            assert_called_once_with)(_db_amphora_mock,
                                     network_data_models.Port(**port_mock),
                                     _amphora_network_config_mock)

        call_args = mock_driver.post_network_plug.call_args[0]
        port_arg = call_args[1]
        subnet_arg = port_arg.fixed_ips[0].subnet
        self.assertEqual(2, len(subnet_arg.host_routes))
        for hr1, hr2 in zip(host_routes, subnet_arg.host_routes):
            self.assertEqual(hr1['destination'], hr2.destination)
            self.assertEqual(hr1['nexthop'], hr2.nexthop)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.session')
    def test_amphorae_post_network_plug(self,
                                        mock_get_session_ctx,
                                        mock_lb_get,
                                        mock_driver,
                                        mock_generate_uuid,
                                        mock_log,
                                        mock_get_session,
                                        mock_listener_repo_get,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_get,
                                        mock_amphora_repo_update):
        mock_driver.get_network.return_value = _network_mock
        _db_amphora_mock.id = AMP_ID
        _db_amphora_mock.compute_id = COMPUTE_ID
        _db_load_balancer_mock.amphorae = [_db_amphora_mock]
        mock_lb_get.return_value = _db_load_balancer_mock
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_post_network_plug_obj = (amphora_driver_tasks.
                                         AmphoraePostNetworkPlug())

        port_mock = {constants.NETWORK: mock.MagicMock(),
                     constants.FIXED_IPS: [mock.MagicMock()],
                     constants.ID: uuidutils.generate_uuid()}
        _deltas_mock = {_db_amphora_mock.id: [port_mock]}

        amphora_post_network_plug_obj.execute(_LB_mock, _deltas_mock,
                                              _amphorae_network_config_mock)

        (mock_driver.post_network_plug.
         assert_called_once_with(_db_amphora_mock,
                                 network_data_models.Port(**port_mock),
                                 _amphora_network_config_mock))

        # Test with no ports to plug
        mock_driver.post_network_plug.reset_mock()

        _deltas_mock = {'0': [port_mock]}

        amphora_post_network_plug_obj.execute(_LB_mock, _deltas_mock,
                                              _amphora_network_config_mock)
        mock_driver.post_network_plug.assert_not_called()

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test revert
        amp = amphora_post_network_plug_obj.revert(None, _LB_mock,
                                                   _deltas_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

        # Test revert with exception
        repo.AmphoraRepository.update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        amp = amphora_post_network_plug_obj.revert(None, _LB_mock,
                                                   _deltas_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

        # Test revert when this task failed
        repo.AmphoraRepository.update.reset_mock()
        amp = amphora_post_network_plug_obj.revert(
            failure.Failure.from_exception(Exception('boom')), _amphora_mock,
            None)
        repo.AmphoraRepository.update.assert_not_called()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.session')
    def test_amphora_post_vip_plug(self,
                                   mock_get_session_ctx,
                                   mock_lb_get,
                                   mock_loadbalancer_repo_update,
                                   mock_driver,
                                   mock_generate_uuid,
                                   mock_log,
                                   mock_get_session,
                                   mock_listener_repo_get,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_get,
                                   mock_amphora_repo_update):

        amphorae_net_config_mock = {
            AMP_ID: {
                constants.VIP_SUBNET: {
                    'host_routes': []
                },
                constants.VRRP_PORT: mock.MagicMock(),
                'additional_vip_data': []
            }
        }
        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_lb_get.return_value = _db_load_balancer_mock
        amphora_post_vip_plug_obj = amphora_driver_tasks.AmphoraPostVIPPlug()
        amphora_post_vip_plug_obj.execute(_amphora_mock,
                                          _LB_mock,
                                          amphorae_net_config_mock)
        vip_subnet = network_data_models.Subnet(
            **amphorae_net_config_mock[AMP_ID]['vip_subnet'])
        vrrp_port = network_data_models.Port(
            **amphorae_net_config_mock[AMP_ID]['vrrp_port'])

        mock_driver.post_vip_plug.assert_called_once_with(
            _db_amphora_mock, _db_load_balancer_mock, amphorae_net_config_mock,
            vrrp_port, vip_subnet, additional_vip_data=[])

        mock_session = mock_get_session_ctx().begin().__enter__()

        # Test revert
        amp = amphora_post_vip_plug_obj.revert(None, _amphora_mock, _LB_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_not_called()

        self.assertIsNone(amp)

        # Test revert with repo exceptions
        repo.AmphoraRepository.update.reset_mock()
        repo.LoadBalancerRepository.update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        amp = amphora_post_vip_plug_obj.revert(None, _amphora_mock, _LB_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_not_called()

        self.assertIsNone(amp)

        # Test revert when this task failed
        repo.AmphoraRepository.update.reset_mock()
        amp = amphora_post_vip_plug_obj.revert(
            failure.Failure.from_exception(Exception('boom')), _amphora_mock,
            None)
        repo.AmphoraRepository.update.assert_not_called()

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amphora_post_vip_plug_with_host_routes(
            self, mock_lb_get, mock_loadbalancer_repo_update, mock_driver,
            mock_generate_uuid, mock_log, mock_get_session,
            mock_listener_repo_get, mock_listener_repo_update,
            mock_amphora_repo_get, mock_amphora_repo_update):

        host_routes = [{'destination': '10.0.0.0/16',
                        'nexthop': '192.168.10.3'},
                       {'destination': '10.2.0.0/16',
                        'nexthop': '192.168.10.5'}]
        amphorae_net_config_mock = {
            AMP_ID: {
                constants.VIP_SUBNET: {
                    'host_routes': host_routes
                },
                constants.VRRP_PORT: mock.MagicMock(),
                'additional_vip_data': []
            }
        }
        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_lb_get.return_value = _db_load_balancer_mock
        amphora_post_vip_plug_obj = amphora_driver_tasks.AmphoraPostVIPPlug()
        amphora_post_vip_plug_obj.execute(_amphora_mock,
                                          _LB_mock,
                                          amphorae_net_config_mock)
        vip_subnet = network_data_models.Subnet(
            **amphorae_net_config_mock[AMP_ID]['vip_subnet'])
        vrrp_port = network_data_models.Port(
            **amphorae_net_config_mock[AMP_ID]['vrrp_port'])

        mock_driver.post_vip_plug.assert_called_once_with(
            _db_amphora_mock, _db_load_balancer_mock, amphorae_net_config_mock,
            vrrp_port, vip_subnet, additional_vip_data=[])

        call_args = mock_driver.post_vip_plug.call_args[0]
        vip_subnet_arg = call_args[4]
        self.assertEqual(2, len(vip_subnet_arg.host_routes))
        for hr1, hr2 in zip(host_routes, vip_subnet_arg.host_routes):
            self.assertEqual(hr1['destination'], hr2.destination)
            self.assertEqual(hr1['nexthop'], hr2.nexthop)

        self.assertEqual(
            host_routes,
            amphorae_net_config_mock[AMP_ID][
                constants.VIP_SUBNET]['host_routes'])

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amphora_post_vip_plug_with_additional_vips(
            self, mock_lb_get, mock_loadbalancer_repo_update, mock_driver,
            mock_generate_uuid, mock_log, mock_get_session,
            mock_listener_repo_get, mock_listener_repo_update,
            mock_amphora_repo_get, mock_amphora_repo_update):

        host_routes = [{'destination': '10.0.0.0/16',
                        'nexthop': '192.168.10.3'},
                       {'destination': '10.2.0.0/16',
                        'nexthop': '192.168.10.5'}]
        additional_host_routes = [{'destination': '2001:db9::/64',
                                   'nexthop': '2001:db8::1:fff'}]
        amphorae_net_config_mock = {
            AMP_ID: {
                constants.VIP_SUBNET: {
                    'host_routes': host_routes
                },
                constants.VRRP_PORT: mock.MagicMock(),
                'additional_vip_data': [{
                    'ip_address': '2001:db8::3',
                    'subnet': {
                        'host_routes': additional_host_routes
                    }
                }]
            }
        }
        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_lb_get.return_value = _db_load_balancer_mock
        amphora_post_vip_plug_obj = amphora_driver_tasks.AmphoraPostVIPPlug()
        amphora_post_vip_plug_obj.execute(_amphora_mock,
                                          _LB_mock,
                                          amphorae_net_config_mock)
        vip_subnet = network_data_models.Subnet(
            **amphorae_net_config_mock[AMP_ID]['vip_subnet'])
        vrrp_port = network_data_models.Port(
            **amphorae_net_config_mock[AMP_ID]['vrrp_port'])
        additional_vip_data = [
            network_data_models.AdditionalVipData(
                ip_address=add_vip_data['ip_address'],
                subnet=network_data_models.Subnet(
                    host_routes=add_vip_data['subnet']['host_routes']))
            for add_vip_data in amphorae_net_config_mock[
                AMP_ID]['additional_vip_data']]

        mock_driver.post_vip_plug.assert_called_once_with(
            _db_amphora_mock, _db_load_balancer_mock, amphorae_net_config_mock,
            vrrp_port, vip_subnet, additional_vip_data=additional_vip_data)

        call_args = mock_driver.post_vip_plug.call_args[0]
        call_kwargs = mock_driver.post_vip_plug.call_args[1]
        vip_subnet_arg = call_args[4]
        self.assertEqual(2, len(vip_subnet_arg.host_routes))
        for hr1, hr2 in zip(host_routes, vip_subnet_arg.host_routes):
            self.assertEqual(hr1['destination'], hr2.destination)
            self.assertEqual(hr1['nexthop'], hr2.nexthop)

        self.assertEqual(
            host_routes,
            amphorae_net_config_mock[AMP_ID][
                constants.VIP_SUBNET]['host_routes'])

        add_vip_data_arg = call_kwargs.get('additional_vip_data')
        self.assertEqual(1, len(add_vip_data_arg[0].subnet.host_routes))
        hr1 = add_vip_data_arg[0].subnet.host_routes[0]
        self.assertEqual(
            additional_host_routes[0]['destination'], hr1.destination)
        self.assertEqual(
            additional_host_routes[0]['nexthop'], hr1.nexthop)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amphorae_post_vip_plug(self, mock_lb_get,
                                    mock_loadbalancer_repo_update,
                                    mock_driver,
                                    mock_generate_uuid,
                                    mock_log,
                                    mock_get_session,
                                    mock_listener_repo_get,
                                    mock_listener_repo_update,
                                    mock_amphora_repo_get,
                                    mock_amphora_repo_update):

        amphorae_net_config_mock = mock.MagicMock()
        mock_amphora_repo_get.return_value = _db_amphora_mock
        vip_subnet = network_data_models.Subnet(
            **amphorae_net_config_mock[AMP_ID]['vip_subnet'])
        vrrp_port = network_data_models.Port(
            **amphorae_net_config_mock[AMP_ID]['vrrp_port'])
        _db_load_balancer_mock.amphorae = [_db_amphora_mock]
        mock_lb_get.return_value = _db_load_balancer_mock
        amphora_post_vip_plug_obj = amphora_driver_tasks.AmphoraePostVIPPlug()
        amphora_post_vip_plug_obj.execute(_LB_mock,
                                          amphorae_net_config_mock)

        mock_driver.post_vip_plug.assert_called_once_with(
            _db_amphora_mock, _db_load_balancer_mock, amphorae_net_config_mock,
            vrrp_port, vip_subnet, additional_vip_data=[])

    def test_amphora_cert_upload(self,
                                 mock_driver,
                                 mock_generate_uuid,
                                 mock_log,
                                 mock_get_session,
                                 mock_listener_repo_get,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_get,
                                 mock_amphora_repo_update):
        key = utils.get_compatible_server_certs_key_passphrase()
        mock_amphora_repo_get.return_value = _db_amphora_mock
        fer = fernet.Fernet(key)
        pem_file_mock = fer.encrypt(
            utils.get_compatible_value('test-pem-file')).decode('utf-8')
        amphora_cert_upload_mock = amphora_driver_tasks.AmphoraCertUpload()
        amphora_cert_upload_mock.execute(_amphora_mock, pem_file_mock)

        mock_driver.upload_cert_amp.assert_called_once_with(
            _db_amphora_mock, fer.decrypt(pem_file_mock.encode('utf-8')))

    def test_amphora_update_vrrp_interface(self,
                                           mock_driver,
                                           mock_generate_uuid,
                                           mock_log,
                                           mock_get_session,
                                           mock_listener_repo_get,
                                           mock_listener_repo_update,
                                           mock_amphora_repo_get,
                                           mock_amphora_repo_update):
        FAKE_INTERFACE = 'fake0'
        mock_amphora_repo_get.return_value = _db_amphora_mock
        mock_driver.get_interface_from_ip.side_effect = [FAKE_INTERFACE,
                                                         Exception('boom')]

        timeout_dict = {constants.CONN_MAX_RETRIES: CONN_MAX_RETRIES,
                        constants.CONN_RETRY_INTERVAL: CONN_RETRY_INTERVAL}

        amphora_update_vrrp_interface_obj = (
            amphora_driver_tasks.AmphoraUpdateVRRPInterface())
        amphora_update_vrrp_interface_obj.execute(_amphora_mock, timeout_dict)
        mock_driver.get_interface_from_ip.assert_called_once_with(
            _db_amphora_mock, _db_amphora_mock.vrrp_ip,
            timeout_dict=timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, vrrp_interface=FAKE_INTERFACE)

        # Test with an exception
        mock_amphora_repo_update.reset_mock()
        amphora_update_vrrp_interface_obj.execute(_amphora_mock, timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, status=constants.ERROR)

    def test_amphora_index_update_vrrp_interface(
            self, mock_driver, mock_generate_uuid, mock_log, mock_get_session,
            mock_listener_repo_get, mock_listener_repo_update,
            mock_amphora_repo_get, mock_amphora_repo_update):
        mock_amphora_repo_get.return_value = _db_amphora_mock
        FAKE_INTERFACE = 'fake0'
        mock_driver.get_interface_from_ip.side_effect = [FAKE_INTERFACE,
                                                         Exception('boom')]

        timeout_dict = {constants.CONN_MAX_RETRIES: CONN_MAX_RETRIES,
                        constants.CONN_RETRY_INTERVAL: CONN_RETRY_INTERVAL}

        amphora_update_vrrp_interface_obj = (
            amphora_driver_tasks.AmphoraIndexUpdateVRRPInterface())
        amphora_update_vrrp_interface_obj.execute(
            0, [_amphora_mock], timeout_dict)
        mock_driver.get_interface_from_ip.assert_called_once_with(
            _db_amphora_mock, _db_amphora_mock.vrrp_ip,
            timeout_dict=timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, vrrp_interface=FAKE_INTERFACE)

        # Test with an exception
        mock_amphora_repo_update.reset_mock()
        amphora_update_vrrp_interface_obj.execute(
            0, [_amphora_mock], timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amphora_vrrp_update(self,
                                 mock_lb_get,
                                 mock_driver,
                                 mock_generate_uuid,
                                 mock_log,
                                 mock_get_session,
                                 mock_listener_repo_get,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_get,
                                 mock_amphora_repo_update):
        amphorae_network_config = mock.MagicMock()
        mock_driver.update_vrrp_conf.side_effect = [mock.DEFAULT,
                                                    Exception('boom')]
        mock_lb_get.return_value = _db_load_balancer_mock
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_vrrp_update_obj = (
            amphora_driver_tasks.AmphoraVRRPUpdate())
        amphora_vrrp_update_obj.execute(LB_ID, amphorae_network_config,
                                        _amphora_mock, 'fakeint0')
        mock_driver.update_vrrp_conf.assert_called_once_with(
            _db_load_balancer_mock, amphorae_network_config,
            _db_amphora_mock, None)

        # Test with an exception
        mock_amphora_repo_update.reset_mock()
        amphora_vrrp_update_obj.execute(LB_ID, amphorae_network_config,
                                        _amphora_mock, 'fakeint0')
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_amphora_index_vrrp_update(self,
                                       mock_lb_get,
                                       mock_driver,
                                       mock_generate_uuid,
                                       mock_log,
                                       mock_get_session,
                                       mock_listener_repo_get,
                                       mock_listener_repo_update,
                                       mock_amphora_repo_get,
                                       mock_amphora_repo_update):
        amphorae_network_config = mock.MagicMock()
        mock_driver.update_vrrp_conf.side_effect = [mock.DEFAULT,
                                                    Exception('boom')]
        mock_lb_get.return_value = _db_load_balancer_mock
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_vrrp_update_obj = (
            amphora_driver_tasks.AmphoraIndexVRRPUpdate())

        amphora_vrrp_update_obj.execute(LB_ID, amphorae_network_config,
                                        0, [_amphora_mock], 'fakeint0',
                                        timeout_dict=self.timeout_dict)
        mock_driver.update_vrrp_conf.assert_called_once_with(
            _db_load_balancer_mock, amphorae_network_config, _db_amphora_mock,
            self.timeout_dict)

        # Test with an exception
        mock_amphora_repo_update.reset_mock()
        amphora_vrrp_update_obj.execute(LB_ID, amphorae_network_config,
                                        0, [_amphora_mock], 'fakeint0')
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, status=constants.ERROR)

    def test_amphora_vrrp_start(self,
                                mock_driver,
                                mock_generate_uuid,
                                mock_log,
                                mock_get_session,
                                mock_listener_repo_get,
                                mock_listener_repo_update,
                                mock_amphora_repo_get,
                                mock_amphora_repo_update):
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_vrrp_start_obj = (
            amphora_driver_tasks.AmphoraVRRPStart())
        amphora_vrrp_start_obj.execute(_amphora_mock,
                                       timeout_dict=self.timeout_dict)
        mock_driver.start_vrrp_service.assert_called_once_with(
            _db_amphora_mock, self.timeout_dict)

    def test_amphora_index_vrrp_start(self,
                                      mock_driver,
                                      mock_generate_uuid,
                                      mock_log,
                                      mock_get_session,
                                      mock_listener_repo_get,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_get,
                                      mock_amphora_repo_update):
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amphora_vrrp_start_obj = (
            amphora_driver_tasks.AmphoraIndexVRRPStart())
        mock_driver.start_vrrp_service.side_effect = [mock.DEFAULT,
                                                      Exception('boom')]

        amphora_vrrp_start_obj.execute(0, [_amphora_mock],
                                       timeout_dict=self.timeout_dict)
        mock_driver.start_vrrp_service.assert_called_once_with(
            _db_amphora_mock, self.timeout_dict)

        # Test with a start exception
        mock_driver.start_vrrp_service.reset_mock()
        amphora_vrrp_start_obj.execute(0, [_amphora_mock],
                                       timeout_dict=self.timeout_dict)
        mock_driver.start_vrrp_service.assert_called_once_with(
            _db_amphora_mock, self.timeout_dict)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, _db_amphora_mock.id, status=constants.ERROR)

    def test_amphora_compute_connectivity_wait(self,
                                               mock_driver,
                                               mock_generate_uuid,
                                               mock_log,
                                               mock_get_session,
                                               mock_listener_repo_get,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_get,
                                               mock_amphora_repo_update):
        amp_compute_conn_wait_obj = (
            amphora_driver_tasks.AmphoraComputeConnectivityWait())
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amp_compute_conn_wait_obj.execute(_amphora_mock,
                                          raise_retry_exception=True)
        mock_driver.get_info.assert_called_once_with(
            _db_amphora_mock, raise_retry_exception=True)

        mock_driver.get_info.side_effect = driver_except.TimeOutException()
        self.assertRaises(driver_except.TimeOutException,
                          amp_compute_conn_wait_obj.execute, _amphora_mock)
        mock_amphora_repo_update.assert_called_once_with(
            _session_mock, AMP_ID, status=constants.ERROR)

    @mock.patch('octavia.amphorae.backends.agent.agent_jinja_cfg.'
                'AgentJinjaTemplater.build_agent_config')
    def test_amphora_config_update(self,
                                   mock_build_config,
                                   mock_driver,
                                   mock_generate_uuid,
                                   mock_log,
                                   mock_get_session,
                                   mock_listener_repo_get,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_get,
                                   mock_amphora_repo_update):
        mock_build_config.return_value = FAKE_CONFIG_FILE
        amp_config_update_obj = amphora_driver_tasks.AmphoraConfigUpdate()
        mock_driver.update_amphora_agent_config.side_effect = [
            None, None, driver_except.AmpDriverNotImplementedError,
            driver_except.TimeOutException]
        # With Flavor
        flavor = {constants.LOADBALANCER_TOPOLOGY:
                  constants.TOPOLOGY_ACTIVE_STANDBY}
        mock_amphora_repo_get.return_value = _db_amphora_mock
        amp_config_update_obj.execute(_amphora_mock, flavor)
        mock_build_config.assert_called_once_with(
            _db_amphora_mock.id, constants.TOPOLOGY_ACTIVE_STANDBY)
        mock_driver.update_amphora_agent_config.assert_called_once_with(
            _db_amphora_mock, FAKE_CONFIG_FILE)
        # With no Flavor
        mock_driver.reset_mock()
        mock_build_config.reset_mock()
        amp_config_update_obj.execute(_amphora_mock, None)
        mock_build_config.assert_called_once_with(
            _db_amphora_mock.id, constants.TOPOLOGY_SINGLE)
        mock_driver.update_amphora_agent_config.assert_called_once_with(
            _db_amphora_mock, FAKE_CONFIG_FILE)
        # With amphora that does not support config update
        mock_driver.reset_mock()
        mock_build_config.reset_mock()
        amp_config_update_obj.execute(_amphora_mock, flavor)
        mock_build_config.assert_called_once_with(
            _db_amphora_mock.id, constants.TOPOLOGY_ACTIVE_STANDBY)
        mock_driver.update_amphora_agent_config.assert_called_once_with(
            _db_amphora_mock, FAKE_CONFIG_FILE)
        # With an unknown exception
        mock_driver.reset_mock()
        mock_build_config.reset_mock()
        self.assertRaises(driver_except.TimeOutException,
                          amp_config_update_obj.execute,
                          _amphora_mock, flavor)
