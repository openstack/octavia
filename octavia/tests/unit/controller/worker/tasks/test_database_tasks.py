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
from taskflow.types import failure

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.tasks import database_tasks
from octavia.db import repositories as repo
import octavia.tests.unit.base as base

if six.PY2:
    import mock
else:
    import unittest.mock as mock

AMP_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
LB_NET_IP = '192.0.2.2'
LISTENER_ID = uuidutils.generate_uuid()
POOL_ID = uuidutils.generate_uuid()
MEMBER_ID = uuidutils.generate_uuid()

_amphora_mock = mock.MagicMock()
_amphora_mock.id = AMP_ID
_amphora_mock.compute_id = COMPUTE_ID
_amphora_mock.lb_network_ip = LB_NET_IP
_loadbalancer_mock = mock.MagicMock()
_loadbalancer_mock.id = LB_ID
_loadbalancer_mock.amphorae = [_amphora_mock]
_pool_mock = mock.MagicMock()
_pool_mock.id = POOL_ID
_listener_mock = mock.MagicMock()
_listener_mock.id = LISTENER_ID
_tf_failure_mock = mock.Mock(spec=failure.Failure)


@mock.patch('octavia.db.repositories.AmphoraRepository.delete')
@mock.patch('octavia.db.repositories.AmphoraRepository.update')
@mock.patch('octavia.db.repositories.ListenerRepository.update')
@mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
@mock.patch('octavia.db.api.get_session', return_value='TEST')
@mock.patch('octavia.controller.worker.tasks.database_tasks.LOG')
@mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=AMP_ID)
class TestDatabaseTasks(base.TestCase):

    def setUp(self):

        self.health_mon_mock = mock.MagicMock()
        self.health_mon_mock.pool_id = POOL_ID

        self.listener_mock = mock.MagicMock()
        self.listener_mock.id = LISTENER_ID

        self.loadbalancer_mock = mock.MagicMock()
        self.loadbalancer_mock.id = LB_ID

        self.member_mock = mock.MagicMock()
        self.member_mock.id = MEMBER_ID

        self.pool_mock = mock.MagicMock()
        self.pool_mock.id = POOL_ID

        super(TestDatabaseTasks, self).setUp()

    @mock.patch('octavia.db.repositories.AmphoraRepository.create',
                return_value=_amphora_mock)
    def test_create_amphora_in_db(self,
                                  mock_create,
                                  mock_generate_uuid,
                                  mock_LOG,
                                  mock_get_session,
                                  mock_loadbalancer_repo_update,
                                  mock_listener_repo_update,
                                  mock_amphora_repo_update,
                                  mock_amphora_repo_delete):

        create_amp_in_db = database_tasks.CreateAmphoraInDB()
        amp_id = create_amp_in_db.execute()

        repo.AmphoraRepository.create.assert_called_once_with(
            'TEST',
            id=AMP_ID,
            status=constants.PENDING_CREATE)

        assert(amp_id == _amphora_mock.id)

        # Test the revert

# TODO(johnsom) finish when this method is updated
        amp = create_amp_in_db.revert(_tf_failure_mock)

        self.assertIsNone(amp)

        amp = create_amp_in_db.revert(result='TEST')

        self.assertIsNone(amp)

#        repo.AmphoraRepository.update.assert_called_once_with(
#            'TEST',
#            AMP_ID,
#            status=constants.ERROR,
#            compute_id=COMPUTE_ID)

    @mock.patch('octavia.db.repositories.ListenerRepository.delete')
    def test_delete_listener_in_db(self,
                                   mock_listener_repo_delete,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        delete_listener = database_tasks.DeleteListenerInDB()
        delete_listener.execute(_listener_mock)

        repo.ListenerRepository.delete.assert_called_once_with(
            'TEST',
            id=LISTENER_ID)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.delete')
    def test_delete_health_monitor_in_db(self,
                                         mock_health_mon_repo_delete,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        delete_health_mon = database_tasks.DeleteHealthMonitorInDB()
        delete_health_mon.execute(POOL_ID)

        repo.HealthMonitorRepository.delete.assert_called_once_with(
            'TEST',
            pool_id=POOL_ID)

        # Test the revert

        mock_health_mon_repo_delete.reset_mock()
        delete_health_mon.revert(POOL_ID)

# TODO(johnsom) fix once provisioning status added
#        repo.HealthMonitorRepository.update.assert_called_once_with(
#            'TEST',
#            POOL_ID,
#            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.delete')
    def test_delete_member_in_db(self,
                                 mock_member_repo_delete,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        delete_member = database_tasks.DeleteMemberInDB()
        delete_member.execute(MEMBER_ID)

        repo.MemberRepository.delete.assert_called_once_with(
            'TEST',
            id=MEMBER_ID)

        # Test the revert

        mock_member_repo_delete.reset_mock()
        delete_member.revert(MEMBER_ID)

# TODO(johnsom) Fix
#        repo.MemberRepository.delete.assert_called_once_with(
#            'TEST',
#            MEMBER_ID)

    @mock.patch('octavia.db.repositories.PoolRepository.delete')
    def test_delete_pool_in_db(self,
                               mock_pool_repo_delete,
                               mock_generate_uuid,
                               mock_LOG,
                               mock_get_session,
                               mock_loadbalancer_repo_update,
                               mock_listener_repo_update,
                               mock_amphora_repo_update,
                               mock_amphora_repo_delete):

        delete_pool = database_tasks.DeletePoolInDB()
        delete_pool.execute(_pool_mock)

        repo.PoolRepository.delete.assert_called_once_with(
            'TEST',
            id=POOL_ID)

        # Test the revert

        mock_pool_repo_delete.reset_mock()
        delete_pool.revert(POOL_ID)

# TODO(johnsom) Fix
#        repo.PoolRepository.update.assert_called_once_with(
#            'TEST',
#            POOL_ID,
#            operating_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_amphora_mock)
    def test_reload_amphora(self,
                            mock_amp_get,
                            mock_generate_uuid,
                            mock_LOG,
                            mock_get_session,
                            mock_loadbalancer_repo_update,
                            mock_listener_repo_update,
                            mock_amphora_repo_update,
                            mock_amphora_repo_delete):

        reload_amp = database_tasks.ReloadAmphora()
        amp = reload_amp.execute(AMP_ID)

        repo.AmphoraRepository.get.assert_called_once_with(
            'TEST',
            id=AMP_ID)

        self.assertEqual(_amphora_mock, amp)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_loadbalancer_mock)
    def test_reload_load_balancer(self,
                                  mock_lb_get,
                                  mock_generate_uuid,
                                  mock_LOG,
                                  mock_get_session,
                                  mock_loadbalancer_repo_update,
                                  mock_listener_repo_update,
                                  mock_amphora_repo_update,
                                  mock_amphora_repo_delete):

        reload_lb = database_tasks.ReloadLoadBalancer()
        lb = reload_lb.execute(LB_ID)

        repo.LoadBalancerRepository.get.assert_called_once_with(
            'TEST',
            id=LB_ID)

        self.assertEqual(_loadbalancer_mock, lb)

    @mock.patch('octavia.db.repositories.AmphoraRepository.'
                'allocate_and_associate',
                side_effect=[_amphora_mock, None])
    def test_map_loadbalancer_to_amphora(self,
                                         mock_allocate_and_associate,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        map_lb_to_amp = database_tasks.MapLoadbalancerToAmphora()
        amp_id = map_lb_to_amp.execute(self.loadbalancer_mock.id)

        repo.AmphoraRepository.allocate_and_associate.assert_called_once_with(
            'TEST',
            LB_ID)

        assert amp_id == _amphora_mock.id

        self.assertRaises(exceptions.NoReadyAmphoraeException,
                          map_lb_to_amp.execute, self.loadbalancer_mock.id)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_amphora_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_loadbalancer_mock)
    def test_mark_lb_amphorae_deleted_in_db(self,
                                            mock_loadbalancer_repo_get,
                                            mock_amphora_repo_get,
                                            mock_generate_uuid,
                                            mock_LOG,
                                            mock_get_session,
                                            mock_loadbalancer_repo_update,
                                            mock_listener_repo_update,
                                            mock_amphora_repo_update,
                                            mock_amphora_repo_delete):

        mark_amp_deleted_in_db = (database_tasks.
                                  MarkLBAmphoraeDeletedInDB())
        mark_amp_deleted_in_db.execute(_loadbalancer_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            id=AMP_ID,
            status=constants.DELETED)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_amphora_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_loadbalancer_mock)
    def test_mark_amphora_allocated_in_db(self,
                                          mock_loadbalancer_repo_get,
                                          mock_amphora_repo_get,
                                          mock_generate_uuid,
                                          mock_LOG,
                                          mock_get_session,
                                          mock_loadbalancer_repo_update,
                                          mock_listener_repo_update,
                                          mock_amphora_repo_update,
                                          mock_amphora_repo_delete):

        mark_amp_allocated_in_db = (database_tasks.
                                    MarkAmphoraAllocatedInDB())
        mark_amp_allocated_in_db.execute(_amphora_mock,
                                         self.loadbalancer_mock.id)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.AMPHORA_ALLOCATED,
            compute_id=COMPUTE_ID,
            lb_network_ip=LB_NET_IP,
            load_balancer_id=LB_ID)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_allocated_in_db.revert(None, _amphora_mock,
                                        self.loadbalancer_mock.id)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR)

    def test_mark_amphora_booting_in_db(self,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        mark_amp_booting_in_db = database_tasks.MarkAmphoraBootingInDB()
        mark_amp_booting_in_db.execute(_amphora_mock.id,
                                       _amphora_mock.compute_id)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.AMPHORA_BOOTING,
            compute_id=COMPUTE_ID)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_booting_in_db.revert(None, _amphora_mock.id,
                                      _amphora_mock.compute_id)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR,
            compute_id=COMPUTE_ID)

    def test_mark_amphora_deleted_in_db(self,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        mark_amp_deleted_in_db = database_tasks.MarkAmphoraDeletedInDB()
        mark_amp_deleted_in_db.execute(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.DELETED)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_deleted_in_db.revert(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR)

    def test_mark_amphora_pending_delete_in_db(self,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):

        mark_amp_pending_delete_in_db = (database_tasks.
                                         MarkAmphoraPendingDeleteInDB())
        mark_amp_pending_delete_in_db.execute(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.PENDING_DELETE)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_pending_delete_in_db.revert(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR)

    def test_mark_amphora_pending_update_in_db(self,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):

        mark_amp_pending_update_in_db = (database_tasks.
                                         MarkAmphoraPendingUpdateInDB())
        mark_amp_pending_update_in_db.execute(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.PENDING_UPDATE)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_pending_update_in_db.revert(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR)

    def test_mark_amphora_ready_in_db(self,
                                      mock_generate_uuid,
                                      mock_LOG,
                                      mock_get_session,
                                      mock_loadbalancer_repo_update,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_update,
                                      mock_amphora_repo_delete):

        _amphora_mock.lb_network_ip = LB_NET_IP

        mark_amp_ready_in_db = database_tasks.MarkAmphoraReadyInDB()
        mark_amp_ready_in_db.execute(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.AMPHORA_READY,
            compute_id=COMPUTE_ID,
            lb_network_ip=LB_NET_IP)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_ready_in_db.revert(_amphora_mock)

        repo.AmphoraRepository.update.assert_called_once_with(
            'TEST',
            AMP_ID,
            status=constants.ERROR,
            compute_id=COMPUTE_ID,
            lb_network_ip=LB_NET_IP)

    def test_mark_listener_active_in_db(self,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        mark_listener_active = database_tasks.MarkListenerActiveInDB()
        mark_listener_active.execute(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ACTIVE)

        # Test the revert

        mock_listener_repo_update.reset_mock()
        mark_listener_active.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ERROR)

    def test_mark_listener_deleted_in_db(self,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        mark_listener_deleted = database_tasks.MarkListenerDeletedInDB()
        mark_listener_deleted.execute(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.DELETED)

        # Test the revert

        mock_listener_repo_update.reset_mock()
        mark_listener_deleted.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ERROR)

    def test_mark_listener_pending_deleted_in_db(self,
                                                 mock_generate_uuid,
                                                 mock_LOG,
                                                 mock_get_session,
                                                 mock_loadbalancer_repo_update,
                                                 mock_listener_repo_update,
                                                 mock_amphora_repo_update,
                                                 mock_amphora_repo_delete):

        mark_listener_pending_delete = (database_tasks.
                                        MarkListenerPendingDeleteInDB())
        mark_listener_pending_delete.execute(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert

        mock_listener_repo_update.reset_mock()
        mark_listener_pending_delete.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ERROR)

    def test_mark_lb_and_listener_active_in_db(self,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):

        mark_lb_and_listener_active = (database_tasks.
                                       MarkLBAndListenerActiveInDB())
        mark_lb_and_listener_active.execute(self.loadbalancer_mock,
                                            self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ACTIVE)
        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ACTIVE)

        # Test the revert

        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()

        mark_lb_and_listener_active.revert(self.loadbalancer_mock,
                                           self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            provisioning_status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ERROR)

    def test_mark_LB_active_in_db(self,
                                  mock_generate_uuid,
                                  mock_LOG,
                                  mock_get_session,
                                  mock_loadbalancer_repo_update,
                                  mock_listener_repo_update,
                                  mock_amphora_repo_update,
                                  mock_amphora_repo_delete):

        mark_loadbalancer_active = database_tasks.MarkLBActiveInDB()
        mark_loadbalancer_active.execute(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ACTIVE)

        # Test the revert

        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_active.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ERROR)

    def test_mark_LB_deleted_in_db(self,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        mark_loadbalancer_deleted = database_tasks.MarkLBDeletedInDB()
        mark_loadbalancer_deleted.execute(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.DELETED)

        # Test the revert

        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_deleted.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ERROR)

    def test_mark_LB_pending_deleted_in_db(self,
                                           mock_generate_uuid,
                                           mock_LOG,
                                           mock_get_session,
                                           mock_loadbalancer_repo_update,
                                           mock_listener_repo_update,
                                           mock_amphora_repo_update,
                                           mock_amphora_repo_delete):

        mark_loadbalancer_pending_delete = (database_tasks.
                                            MarkLBPendingDeleteInDB())
        mark_loadbalancer_pending_delete.execute(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert

        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_pending_delete.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_update_health_monitor_in_db(self,
                                         mock_health_mon_repo_update,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        update_health_mon = database_tasks.UpdateHealthMonInDB()
        update_health_mon.execute(self.health_mon_mock,
                                  {'delay': 1, 'timeout': 2})

        repo.HealthMonitorRepository.update.assert_called_once_with(
            'TEST',
            POOL_ID,
            delay=1, timeout=2)

        # Test the revert

        mock_health_mon_repo_update.reset_mock()
        update_health_mon.revert(self.health_mon_mock)

# TODO(johnsom) fix this to set the upper ojects to ERROR
        repo.HealthMonitorRepository.update.assert_called_once_with(
            'TEST',
            POOL_ID,
            enabled=0)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
    def test_update_load_balancer_in_db(self,
                                        mock_listner_repo_update,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        update_load_balancer = database_tasks.UpdateLoadbalancerInDB()
        update_load_balancer.execute(self.loadbalancer_mock,
                                     {'name': 'test', 'description': 'test2'})

        repo.LoadBalancerRepository.update.assert_called_once_with(
            'TEST',
            LB_ID,
            name='test', description='test2')

        # Test the revert

        mock_listener_repo_update.reset_mock()
        update_load_balancer.revert(self.listener_mock)

    @mock.patch('octavia.db.repositories.ListenerRepository.update')
    def test_update_listener_in_db(self,
                                   mock_listner_repo_update,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        update_listener = database_tasks.UpdateListenerInDB()
        update_listener.execute(self.listener_mock,
                                {'name': 'test', 'description': 'test2'})

        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            name='test', description='test2')

        # Test the revert

        mock_listener_repo_update.reset_mock()
        update_listener.revert(self.listener_mock)

# TODO(johnsom) fix this to set the upper ojects to ERROR
        repo.ListenerRepository.update.assert_called_once_with(
            'TEST',
            LISTENER_ID,
            enabled=0)

    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_update_member_in_db(self,
                                 mock_member_repo_update,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        update_member = database_tasks.UpdateMemberInDB()
        update_member.execute(self.member_mock,
                              {'weight': 1, 'ip_address': '10.1.0.0'})

        repo.MemberRepository.update.assert_called_once_with(
            'TEST',
            MEMBER_ID,
            weight=1, ip_address='10.1.0.0')

        # Test the revert

        mock_member_repo_update.reset_mock()
        update_member.revert(self.member_mock)

# TODO(johnsom) fix this to set the upper ojects to ERROR
        repo.MemberRepository.update.assert_called_once_with(
            'TEST',
            MEMBER_ID,
            enabled=0)

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_update_pool_in_db(self,
                               mock_pool_repo_update,
                               mock_generate_uuid,
                               mock_LOG,
                               mock_get_session,
                               mock_loadbalancer_repo_update,
                               mock_listener_repo_update,
                               mock_amphora_repo_update,
                               mock_amphora_repo_delete):

        update_pool = database_tasks.UpdatePoolInDB()
        update_pool.execute(self.pool_mock,
                            {'name': 'test', 'description': 'test2'})

        repo.PoolRepository.update.assert_called_once_with(
            'TEST',
            POOL_ID,
            name='test', description='test2')

        # Test the revert

        mock_pool_repo_update.reset_mock()
        update_pool.revert(self.pool_mock)

# TODO(johnsom) fix this to set the upper ojects to ERROR
        repo.PoolRepository.update.assert_called_once_with(
            'TEST',
            POOL_ID,
            enabled=0)
