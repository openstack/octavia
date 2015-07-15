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

from octavia.common import constants
from octavia.controller.worker.tasks import amphora_driver_tasks
from octavia.db import repositories as repo
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

AMP_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LISTENER_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()

_amphora_mock = mock.MagicMock()
_amphora_mock.id = AMP_ID
_listener_mock = mock.MagicMock()
_listener_mock.id = LISTENER_ID
_vip_mock = mock.MagicMock()
_LB_mock = mock.MagicMock()
_amphorae_mock = [_amphora_mock]
_network_mock = mock.MagicMock()
_port_mock = mock.MagicMock()
_ports_mock = [_port_mock]


@mock.patch('octavia.db.repositories.AmphoraRepository.update')
@mock.patch('octavia.db.repositories.ListenerRepository.update')
@mock.patch('octavia.db.api.get_session', return_value='TEST')
@mock.patch('octavia.controller.worker.tasks.amphora_driver_tasks.LOG')
@mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=AMP_ID)
@mock.patch('stevedore.driver.DriverManager.driver')
class TestAmphoraDriverTasks(base.TestCase):

    def setUp(self):

        _LB_mock.amphorae = _amphora_mock
        _LB_mock.id = LB_ID
        super(TestAmphoraDriverTasks, self).setUp()

    def test_listener_update(self,
                             mock_driver,
                             mock_generate_uuid,
                             mock_log,
                             mock_get_session,
                             mock_listener_repo_update,
                             mock_amphora_repo_update):

        listener_update_obj = amphora_driver_tasks.ListenerUpdate()
        listener_update_obj.execute(_listener_mock, _vip_mock)

        mock_driver.update.assert_called_once_with(
            _listener_mock, _vip_mock)

        # Test the revert
        amp = listener_update_obj.revert(_listener_mock)
        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

    def test_listener_stop(self,
                           mock_driver,
                           mock_generate_uuid,
                           mock_log,
                           mock_get_session,
                           mock_listener_repo_update,
                           mock_amphora_repo_update):

        listener_stop_obj = amphora_driver_tasks.ListenerStop()
        listener_stop_obj.execute(_listener_mock, _vip_mock)

        mock_driver.stop.assert_called_once_with(
            _listener_mock, _vip_mock)

        # Test the revert
        amp = listener_stop_obj.revert(_listener_mock)
        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

    def test_listener_start(self,
                            mock_driver,
                            mock_generate_uuid,
                            mock_log,
                            mock_get_session,
                            mock_listener_repo_update,
                            mock_amphora_repo_update):

        listener_start_obj = amphora_driver_tasks.ListenerStart()
        listener_start_obj.execute(_listener_mock, _vip_mock)

        mock_driver.start.assert_called_once_with(
            _listener_mock, _vip_mock)

        # Test the revert
        amp = listener_start_obj.revert(_listener_mock)
        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

    def test_listener_delete(self,
                             mock_driver,
                             mock_generate_uuid,
                             mock_log,
                             mock_get_session,
                             mock_listener_repo_update,
                             mock_amphora_repo_update):

        listener_delete_obj = amphora_driver_tasks.ListenerDelete()
        listener_delete_obj.execute(_listener_mock, _vip_mock)

        mock_driver.delete.assert_called_once_with(
            _listener_mock, _vip_mock)

        # Test the revert
        amp = listener_delete_obj.revert(_listener_mock)
        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        self.assertIsNone(amp)

    def test_amphora_get_info(self,
                              mock_driver,
                              mock_generate_uuid,
                              mock_log,
                              mock_get_session,
                              mock_listener_repo_update,
                              mock_amphora_repo_update):

        amphora_get_info_obj = amphora_driver_tasks.AmphoraGetInfo()
        amphora_get_info_obj.execute(_amphora_mock)

        mock_driver.get_info.assert_called_once_with(
            _amphora_mock)

    def test_amphora_get_diagnostics(self,
                                     mock_driver,
                                     mock_generate_uuid,
                                     mock_log,
                                     mock_get_session,
                                     mock_listener_repo_update,
                                     mock_amphora_repo_update):

        amphora_get_diagnostics_obj = (amphora_driver_tasks.
                                       AmphoraGetDiagnostics())
        amphora_get_diagnostics_obj.execute(_amphora_mock)

        mock_driver.get_diagnostics.assert_called_once_with(
            _amphora_mock)

    def test_amphora_finalize(self,
                              mock_driver,
                              mock_generate_uuid,
                              mock_log,
                              mock_get_session,
                              mock_listener_repo_update,
                              mock_amphora_repo_update):

        amphora_finalize_obj = amphora_driver_tasks.AmphoraFinalize()
        amphora_finalize_obj.execute(_amphora_mock)

        mock_driver.finalize_amphora.assert_called_once_with(
            _amphora_mock)

        # Test revert
        amp = amphora_finalize_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            id=AMP_ID,
            status=constants.ERROR)
        self.assertIsNone(amp)

    def test_amphora_post_network_plug(self,
                                       mock_driver,
                                       mock_generate_uuid,
                                       mock_log,
                                       mock_get_session,
                                       mock_listener_repo_update,
                                       mock_amphora_repo_update):

        amphora_post_network_plug_obj = (amphora_driver_tasks.
                                         AmphoraPostNetworkPlug())
        amphora_post_network_plug_obj.execute(_amphora_mock, _ports_mock)

        (mock_driver.post_network_plug.
            assert_called_once_with)(_amphora_mock, _port_mock)

        # Test revert
        amp = amphora_post_network_plug_obj.revert(None, _amphora_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

    def test_amphorae_post_network_plug(self, mock_driver,
                                        mock_generate_uuid,
                                        mock_log,
                                        mock_get_session,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update):
        mock_driver.get_network.return_value = _network_mock
        _amphora_mock.id = AMP_ID
        _amphora_mock.compute_id = COMPUTE_ID
        _LB_mock.amphorae = [_amphora_mock]
        amphora_post_network_plug_obj = (amphora_driver_tasks.
                                         AmphoraePostNetworkPlug())
        port_mock = mock.Mock()
        _deltas_mock = {_amphora_mock.id: [port_mock]}
        amphora_post_network_plug_obj.execute(_LB_mock, _deltas_mock)

        (mock_driver.post_network_plug.
            assert_called_once_with(_amphora_mock, port_mock))

        # Test revert
        amp = amphora_post_network_plug_obj.revert(None, _LB_mock,
                                                   _deltas_mock)
        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            id=AMP_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_amphora_post_vip_plug(self,
                                   mock_loadbalancer_repo_update,
                                   mock_driver,
                                   mock_generate_uuid,
                                   mock_log,
                                   mock_get_session,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update):

        amphorae_net_config_mock = mock.Mock()
        amphora_post_vip_plug_obj = amphora_driver_tasks.AmphoraPostVIPPlug()
        amphora_post_vip_plug_obj.execute(_LB_mock, amphorae_net_config_mock)

        mock_driver.post_vip_plug.assert_called_once_with(
            _LB_mock, amphorae_net_config_mock)

        # Test revert
        amp = amphora_post_vip_plug_obj.revert(None, _LB_mock)
        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            id=LB_ID,
            status=constants.ERROR)

        self.assertIsNone(amp)
