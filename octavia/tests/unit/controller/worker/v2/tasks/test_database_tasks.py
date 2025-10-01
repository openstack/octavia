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
import copy
import random
from unittest import mock

from oslo_db import exception as odb_exceptions
from oslo_utils import uuidutils
from sqlalchemy.orm import exc
from taskflow.types import failure

from octavia.api.drivers import utils as provider_utils
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import utils
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.db import repositories as repo
import octavia.tests.unit.base as base


AMP_ID = uuidutils.generate_uuid()
AMP2_ID = uuidutils.generate_uuid()
COMPUTE_ID = uuidutils.generate_uuid()
LB_ID = uuidutils.generate_uuid()
SERVER_GROUP_ID = uuidutils.generate_uuid()
LB_NET_IP = '192.0.2.2'
LISTENER_ID = uuidutils.generate_uuid()
POOL_ID = uuidutils.generate_uuid()
HM_ID = uuidutils.generate_uuid()
MEMBER_ID = uuidutils.generate_uuid()
PORT_ID = uuidutils.generate_uuid()
PORT_ID2 = uuidutils.generate_uuid()
PORT_ID3 = uuidutils.generate_uuid()
SUBNET_ID = uuidutils.generate_uuid()
SUBNET_ID2 = uuidutils.generate_uuid()
SUBNET_ID3 = uuidutils.generate_uuid()
VRRP_PORT_ID = uuidutils.generate_uuid()
HA_PORT_ID = uuidutils.generate_uuid()
L7POLICY_ID = uuidutils.generate_uuid()
L7RULE_ID = uuidutils.generate_uuid()
VIP_IP = '192.0.5.2'
VIP_IP2 = '192.0.5.5'
VIP_IP3 = '192.0.5.6'
VRRP_ID = 1
VRRP_IP = '192.0.5.3'
HA_IP = '192.0.5.4'
AMP_ROLE = 'FAKE_ROLE'
VRRP_PRIORITY = random.randrange(100)
CACHED_ZONE = 'zone1'
IMAGE_ID = uuidutils.generate_uuid()
COMPUTE_FLAVOR = uuidutils.generate_uuid()

_db_amphora_mock = mock.MagicMock()
_db_amphora_mock.id = AMP_ID
_db_amphora_mock.compute_id = COMPUTE_ID
_db_amphora_mock.lb_network_ip = LB_NET_IP
_db_amphora_mock.vrrp_ip = VRRP_IP
_db_amphora_mock.ha_ip = HA_IP
_db_amphora_mock.ha_port_id = HA_PORT_ID
_db_amphora_mock.vrrp_port_id = VRRP_PORT_ID
_db_amphora_mock.role = AMP_ROLE
_db_amphora_mock.vrrp_id = VRRP_ID
_db_amphora_mock.vrrp_priority = VRRP_PRIORITY
_db_loadbalancer_mock = mock.MagicMock()
_db_loadbalancer_mock.id = LB_ID
_db_loadbalancer_mock.vip_address = VIP_IP
_db_loadbalancer_mock.amphorae = [_db_amphora_mock]
_db_loadbalancer_mock.to_dict.return_value = {
    constants.ID: LB_ID
}
_l7policy_mock = mock.MagicMock()
_l7policy_mock.id = L7POLICY_ID
_l7rule_mock = mock.MagicMock()
_l7rule_mock.id = L7RULE_ID
_listener_mock = mock.MagicMock()
_listener_to_dict_mock = mock.MagicMock(
    return_value={constants.ID: LISTENER_ID})
_listener_mock.id = LISTENER_ID
_listener_mock.to_dict = _listener_to_dict_mock
_tf_failure_mock = mock.Mock(spec=failure.Failure)
_vip_mock = mock.MagicMock()
_vip_mock.port_id = PORT_ID
_vip_mock.subnet_id = SUBNET_ID
_vip_mock.ip_address = VIP_IP
_vip_mock.to_dict.return_value = {
    constants.PORT_ID: PORT_ID,
    constants.SUBNET_ID: SUBNET_ID,
    constants.IP_ADDRESS: VIP_IP,
}
_vrrp_group_mock = mock.MagicMock()
_cert_mock = mock.MagicMock()
_compute_mock_dict = {
    constants.LB_NETWORK_IP: LB_NET_IP,
    constants.CACHED_ZONE: CACHED_ZONE,
    constants.IMAGE_ID: IMAGE_ID,
    constants.COMPUTE_FLAVOR: COMPUTE_FLAVOR
}


@mock.patch('octavia.db.repositories.AmphoraRepository.delete')
@mock.patch('octavia.db.repositories.AmphoraRepository.update')
@mock.patch('octavia.db.repositories.ListenerRepository.update')
@mock.patch('octavia.db.repositories.LoadBalancerRepository.update')
@mock.patch('octavia.db.api.session')
@mock.patch('octavia.controller.worker.v2.tasks.database_tasks.LOG')
@mock.patch('oslo_utils.uuidutils.generate_uuid', return_value=AMP_ID)
class TestDatabaseTasks(base.TestCase):

    def setUp(self):

        self.db_health_mon_mock = mock.MagicMock()
        self.db_health_mon_mock.id = HM_ID
        self.db_health_mon_mock.pool_id = POOL_ID

        self.health_mon_mock = {
            constants.HEALTHMONITOR_ID: HM_ID,
            constants.POOL_ID: POOL_ID,
            constants.ADMIN_STATE_UP: True,
        }

        self.listener_mock = mock.MagicMock()
        self.listener_mock.id = LISTENER_ID

        self.loadbalancer_mock = (
            provider_utils.db_loadbalancer_to_provider_loadbalancer(
                _db_loadbalancer_mock).to_dict())

        self.member_mock = mock.MagicMock()
        self.member_mock.id = MEMBER_ID

        self.db_pool_mock = mock.MagicMock()
        self.db_pool_mock.id = POOL_ID
        self.db_pool_mock.health_monitor = self.db_health_mon_mock
        self.db_health_mon_mock.to_dict.return_value = {
            constants.ID: HM_ID,
            constants.POOL_ID: POOL_ID,
        }

        self.member_mock = {
            constants.MEMBER_ID: MEMBER_ID,
            constants.POOL_ID: POOL_ID,
        }

        self.l7policy_mock = {
            constants.L7POLICY_ID: L7POLICY_ID,
            constants.ADMIN_STATE_UP: True,
        }

        self.l7rule_mock = {
            constants.L7RULE_ID: L7RULE_ID,
            constants.ADMIN_STATE_UP: True,
            constants.L7POLICY_ID: L7POLICY_ID,
        }

        self.amphora = {
            constants.ID: AMP_ID,
            constants.COMPUTE_ID: COMPUTE_ID,
            constants.LB_NETWORK_IP: LB_NET_IP,
            constants.VRRP_IP: VRRP_IP,
            constants.HA_IP: HA_IP,
            constants.HA_PORT_ID: HA_PORT_ID,
            constants.VRRP_PORT_ID: VRRP_PORT_ID,
            constants.ROLE: AMP_ROLE,
            constants.VRRP_ID: VRRP_ID,
            constants.VRRP_PRIORITY: VRRP_PRIORITY,
        }
        _db_amphora_mock.to_dict.return_value = self.amphora

        super().setUp()

    @mock.patch('octavia.db.repositories.AmphoraRepository.create',
                return_value=_db_amphora_mock)
    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.delete')
    def test_create_amphora_in_db(self,
                                  mock_amphora_health_repo_delete,
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

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.create.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            load_balancer_id=None,
            status=constants.PENDING_CREATE,
            cert_busy=False)

        self.assertEqual(_db_amphora_mock.id, amp_id)

        # Test the revert
        create_amp_in_db.revert(_tf_failure_mock)
        mock_amphora_repo_delete.assert_not_called()
        mock_amphora_health_repo_delete.assert_not_called()

        amp_id = 'AMP'
        mock_amphora_repo_delete.reset_mock()
        mock_amphora_health_repo_delete.reset_mock()
        create_amp_in_db.revert(result=amp_id)
        self.assertTrue(mock_amphora_repo_delete.called)
        self.assertTrue(mock_amphora_health_repo_delete.called)
        mock_amphora_repo_delete.assert_called_once_with(
            mock_session,
            id=amp_id)
        mock_amphora_health_repo_delete.assert_called_once_with(
            mock_session,
            amphora_id=amp_id)
        mock_LOG.error.assert_not_called()
        mock_LOG.debug.assert_not_called()

        # Test revert with exception
        mock_amphora_repo_delete.reset_mock()
        mock_amphora_health_repo_delete.reset_mock()
        err1_msg, err2_msg = ('fail', 'fail2')
        mock_amphora_repo_delete.side_effect = Exception(err1_msg)
        mock_amphora_health_repo_delete.side_effect = Exception(err2_msg)
        create_amp_in_db.revert(result=amp_id)
        self.assertTrue(mock_amphora_repo_delete.called)
        self.assertTrue(mock_amphora_health_repo_delete.called)
        mock_amphora_repo_delete.assert_called_once_with(
            mock_session,
            id=amp_id)
        mock_amphora_health_repo_delete.assert_called_once_with(
            mock_session,
            amphora_id=amp_id)
        mock_LOG.error.assert_called_once_with(
            "Failed to delete amphora %(amp)s "
            "in the database due to: "
            "%(except)s", {'amp': amp_id, 'except': err1_msg})

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
        delete_listener.execute({constants.LISTENER_ID: LISTENER_ID})

        mock_session = mock_get_session().begin().__enter__()

        repo.ListenerRepository.delete.assert_called_once_with(
            mock_session,
            id=LISTENER_ID)

        # Test the revert
        repo.ListenerRepository.delete.reset_mock()
        delete_listener.revert({constants.LISTENER_ID: LISTENER_ID})
        repo.ListenerRepository.delete.assert_not_called()

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.delete')
    def test_delete_health_monitor_in_db(self,
                                         mock_health_mon_repo_delete,
                                         mock_health_mon_repo_update,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        delete_health_mon = database_tasks.DeleteHealthMonitorInDB()
        delete_health_mon.execute(self.health_mon_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.HealthMonitorRepository.delete.assert_called_once_with(
            mock_session, id=HM_ID)

        # Test the revert
        mock_health_mon_repo_delete.reset_mock()
        delete_health_mon.revert(self.health_mon_mock)

        repo.HealthMonitorRepository.update.assert_called_once_with(
            mock_session, id=HM_ID, provisioning_status=constants.ERROR)

        # Test Not Found Exception
        mock_health_mon_repo_delete.reset_mock()
        mock_health_mon_repo_delete.side_effect = [exc.NoResultFound()]
        delete_health_mon.execute(self.health_mon_mock)

        repo.HealthMonitorRepository.delete.assert_called_once_with(
            mock_session, id=HM_ID)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.delete')
    @mock.patch('octavia.db.repositories.PoolRepository.get')
    def test_delete_health_monitor_in_db_by_pool(self,
                                                 mock_pool_repo_get,
                                                 mock_health_mon_repo_delete,
                                                 mock_health_mon_repo_update,
                                                 mock_generate_uuid,
                                                 mock_LOG,
                                                 mock_get_session,
                                                 mock_loadbalancer_repo_update,
                                                 mock_listener_repo_update,
                                                 mock_amphora_repo_update,
                                                 mock_amphora_repo_delete):
        mock_pool_repo_get.return_value = self.db_pool_mock
        delete_health_mon = database_tasks.DeleteHealthMonitorInDBByPool()
        delete_health_mon.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        repo.HealthMonitorRepository.delete.assert_called_once_with(
            mock_session,
            id=HM_ID)

        # Test the revert
        mock_health_mon_repo_delete.reset_mock()
        delete_health_mon.revert(POOL_ID)

        repo.HealthMonitorRepository.update.assert_called_once_with(
            mock_session, id=HM_ID, provisioning_status=constants.ERROR)

# TODO(johnsom) fix once provisioning status added
#        repo.HealthMonitorRepository.update.assert_called_once_with(
#            mock_session,
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
        delete_member.execute(self.member_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.MemberRepository.delete.assert_called_once_with(
            mock_session,
            id=MEMBER_ID)

        # Test the revert

        mock_member_repo_delete.reset_mock()
        delete_member.revert(self.member_mock)

# TODO(johnsom) Fix
#        repo.MemberRepository.delete.assert_called_once_with(
#            mock_session,
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
        delete_pool.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        repo.PoolRepository.delete.assert_called_once_with(
            mock_session,
            id=POOL_ID)

        # Test the revert

        mock_pool_repo_delete.reset_mock()
        delete_pool.revert(POOL_ID)

# TODO(johnsom) Fix
#        repo.PoolRepository.update.assert_called_once_with(
#            mock_session,
#            POOL_ID,
#            operating_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7PolicyRepository.delete')
    def test_delete_l7policy_in_db(self,
                                   mock_l7policy_repo_delete,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        delete_l7policy = database_tasks.DeleteL7PolicyInDB()
        delete_l7policy.execute(self.l7policy_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.L7PolicyRepository.delete.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID)

        # Test the revert

        mock_l7policy_repo_delete.reset_mock()
        delete_l7policy.revert(self.l7policy_mock)

# TODO(sbalukoff) Fix
#        repo.ListenerRepository.update.assert_called_once_with(
#            mock_session,
#            LISTENER_ID,
#            operating_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.delete')
    def test_delete_l7rule_in_db(self,
                                 mock_l7rule_repo_delete,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        delete_l7rule = database_tasks.DeleteL7RuleInDB()
        delete_l7rule.execute(self.l7rule_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.L7RuleRepository.delete.assert_called_once_with(
            mock_session,
            id=L7RULE_ID)

        # Test the revert

        mock_l7rule_repo_delete.reset_mock()
        delete_l7rule.revert(self.l7rule_mock)

# TODO(sbalukoff) Fix
#        repo.ListenerRepository.update.assert_called_once_with(
#            mock_session,
#            LISTENER_ID,
#            operating_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_db_amphora_mock)
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
        amp = reload_amp.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.get.assert_called_once_with(
            mock_session,
            id=AMP_ID)

        self.assertEqual(_db_amphora_mock.to_dict(), amp)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_db_loadbalancer_mock)
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

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.get.assert_called_once_with(
            mock_session,
            id=LB_ID)

        self.assertEqual(self.loadbalancer_mock, lb)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_db_loadbalancer_mock)
    @mock.patch('octavia.db.repositories.VipRepository.update')
    def test_update_vip_after_allocation(self,
                                         mock_vip_update,
                                         mock_loadbalancer_get,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        update_vip = database_tasks.UpdateVIPAfterAllocation()
        loadbalancer = update_vip.execute(LB_ID, _vip_mock.to_dict())

        mock_session = mock_get_session().begin().__enter__()

        self.assertEqual(self.loadbalancer_mock, loadbalancer)
        mock_vip_update.assert_called_once_with(mock_session,
                                                LB_ID,
                                                port_id=PORT_ID,
                                                subnet_id=SUBNET_ID,
                                                ip_address=VIP_IP)
        mock_loadbalancer_get.assert_called_once_with(mock_session,
                                                      id=LB_ID)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_db_loadbalancer_mock)
    @mock.patch('octavia.db.repositories.AdditionalVipRepository.update')
    def test_update_additional_vips_after_allocation(
            self,
            mock_additional_vip_update,
            mock_loadbalancer_get,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        additional_vip1_dict = {
            "subnet_id": SUBNET_ID2,
            "ip_address": VIP_IP2,
            "port_id": PORT_ID2
        }
        additional_vip2_dict = {
            "subnet_id": SUBNET_ID3,
            "ip_address": VIP_IP3,
            "port_id": PORT_ID3
        }

        mock_session = mock_get_session().begin().__enter__()

        update_additional_vips = (
            database_tasks.UpdateAdditionalVIPsAfterAllocation())
        update_additional_vips.execute(
            LB_ID, [additional_vip1_dict, additional_vip2_dict])
        mock_additional_vip_update.assert_any_call(
            mock_session, LB_ID, SUBNET_ID2, ip_address=VIP_IP2,
            port_id=PORT_ID2)
        mock_additional_vip_update.assert_any_call(
            mock_session, LB_ID, SUBNET_ID3, ip_address=VIP_IP3,
            port_id=PORT_ID3)

    def test_update_amphora_vip_data(self,
                                     mock_generate_uuid,
                                     mock_LOG,
                                     mock_get_session,
                                     mock_loadbalancer_repo_update,
                                     mock_listener_repo_update,
                                     mock_amphora_repo_update,
                                     mock_amphora_repo_delete):

        update_amp_vip_data = database_tasks.UpdateAmphoraeVIPData()
        update_amp_vip_data.execute([self.amphora])

        mock_session = mock_get_session().begin().__enter__()

        mock_amphora_repo_update.assert_called_once_with(
            mock_session,
            AMP_ID,
            vrrp_ip=VRRP_IP,
            ha_ip=HA_IP,
            vrrp_port_id=VRRP_PORT_ID,
            ha_port_id=HA_PORT_ID,
            vrrp_id=1)

    def test_update_amphora_vip_data2(self,
                                      mock_generate_uuid,
                                      mock_LOG,
                                      mock_get_session,
                                      mock_loadbalancer_repo_update,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_update,
                                      mock_amphora_repo_delete):
        update_amp_vip_data2 = database_tasks.UpdateAmphoraVIPData()
        update_amp_vip_data2.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        mock_amphora_repo_update.assert_called_once_with(
            mock_session,
            AMP_ID,
            vrrp_ip=VRRP_IP,
            ha_ip=HA_IP,
            vrrp_port_id=VRRP_PORT_ID,
            ha_port_id=HA_PORT_ID,
            vrrp_id=1)

    def test_update_amp_failover_details(self,
                                         mock_generate_uuid,
                                         mock_LOG,
                                         mock_get_session,
                                         mock_loadbalancer_repo_update,
                                         mock_listener_repo_update,
                                         mock_amphora_repo_update,
                                         mock_amphora_repo_delete):

        amphora_dict = {constants.ID: AMP_ID}
        vip_dict = {constants.IP_ADDRESS: HA_IP,
                    constants.PORT_ID: HA_PORT_ID}
        fixed_ips = [{constants.IP_ADDRESS: VRRP_IP}]
        base_port_dict = {constants.ID: VRRP_PORT_ID,
                          constants.FIXED_IPS: fixed_ips}

        update_amp_fo_details = database_tasks.UpdateAmpFailoverDetails()
        update_amp_fo_details.execute(amphora_dict, vip_dict, base_port_dict)

        mock_session = mock_get_session().begin().__enter__()

        mock_amphora_repo_update.assert_called_once_with(
            mock_session,
            AMP_ID,
            vrrp_ip=VRRP_IP,
            ha_ip=HA_IP,
            vrrp_port_id=VRRP_PORT_ID,
            ha_port_id=HA_PORT_ID,
            vrrp_id=VRRP_ID)

    @mock.patch('octavia.db.repositories.AmphoraRepository.associate')
    def test_associate_failover_amphora_with_lb_id(
            self,
            mock_associate,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        assoc_fo_amp_lb_id = database_tasks.AssociateFailoverAmphoraWithLBID()
        assoc_fo_amp_lb_id.execute(AMP_ID, LB_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_associate.assert_called_once_with(mock_session,
                                               load_balancer_id=LB_ID,
                                               amphora_id=AMP_ID)

        # Test revert
        assoc_fo_amp_lb_id.revert(AMP_ID)

        mock_amphora_repo_update.assert_called_once_with(mock_session,
                                                         AMP_ID,
                                                         loadbalancer_id=None)

        # Test revert with exception
        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')

        assoc_fo_amp_lb_id.revert(AMP_ID)

        mock_amphora_repo_update.assert_called_once_with(mock_session,
                                                         AMP_ID,
                                                         loadbalancer_id=None)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_db_amphora_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_db_loadbalancer_mock)
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
        mark_amp_deleted_in_db.execute(self.loadbalancer_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.DELETED)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_db_amphora_mock)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get',
                return_value=_db_loadbalancer_mock)
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
        mark_amp_allocated_in_db.execute(self.amphora,
                                         LB_ID)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.AMPHORA_ALLOCATED,
            compute_id=COMPUTE_ID,
            lb_network_ip=LB_NET_IP,
            load_balancer_id=LB_ID)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_allocated_in_db.revert(None, self.amphora,
                                        LB_ID)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        # Test the revert with exception

        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mark_amp_allocated_in_db.revert(None, self.amphora,
                                        LB_ID)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
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
        mark_amp_booting_in_db.execute(_db_amphora_mock.id,
                                       _db_amphora_mock.compute_id)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.AMPHORA_BOOTING,
            compute_id=COMPUTE_ID)

        # Test the revert

        mock_amphora_repo_update.reset_mock()
        mark_amp_booting_in_db.revert(None, _db_amphora_mock.id,
                                      _db_amphora_mock.compute_id)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.ERROR,
            compute_id=COMPUTE_ID)

        # Test the revert with exception

        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mark_amp_booting_in_db.revert(None, _db_amphora_mock.id,
                                      _db_amphora_mock.compute_id)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
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
        mark_amp_deleted_in_db.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.DELETED)

        # Test the revert
        mock_amphora_repo_update.reset_mock()
        mark_amp_deleted_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        # Test the revert with exception
        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mark_amp_deleted_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
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
        mark_amp_pending_delete_in_db.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.PENDING_DELETE)

        # Test the revert
        mock_amphora_repo_update.reset_mock()
        mark_amp_pending_delete_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        # Test the revert with exception
        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')

        mark_amp_pending_delete_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
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
        mark_amp_pending_update_in_db.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            status=constants.PENDING_UPDATE)

        # Test the revert
        mock_amphora_repo_update.reset_mock()
        mark_amp_pending_update_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

        # Test the revert with exception
        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mark_amp_pending_update_in_db.revert(self.amphora)

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            id=AMP_ID,
            status=constants.ERROR)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    def test_update_amphora_info(self,
                                 mock_amphora_repo_get,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        update_amphora_info = database_tasks.UpdateAmphoraInfo()
        update_amphora_info.execute(AMP_ID, _compute_mock_dict)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            lb_network_ip=LB_NET_IP,
            cached_zone=CACHED_ZONE,
            image_id=IMAGE_ID,
            compute_flavor=COMPUTE_FLAVOR)

        repo.AmphoraRepository.get.assert_called_once_with(
            mock_session,
            id=AMP_ID)

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

        mock_session = mock_get_session().begin().__enter__()

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            LISTENER_ID,
            provisioning_status=constants.DELETED)

        # Test the revert
        mock_listener_repo_update.reset_mock()
        mark_listener_deleted.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_listener_repo_update.reset_mock()
        mock_listener_repo_update.side_effect = Exception('fail')
        mark_listener_deleted.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
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

        mock_session = mock_get_session().begin().__enter__()

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            LISTENER_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_listener_repo_update.reset_mock()
        mark_listener_pending_delete.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_listener_repo_update.reset_mock()
        mock_listener_repo_update.side_effect = Exception('fail')
        mark_listener_pending_delete.revert(self.listener_mock)

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.ListenerRepository.'
                'prov_status_active_if_not_error')
    def test_mark_lb_and_listeners_active_in_db(self,
                                                mock_list_not_error,
                                                mock_generate_uuid,
                                                mock_LOG,
                                                mock_get_session,
                                                mock_loadbalancer_repo_update,
                                                mock_listener_repo_update,
                                                mock_amphora_repo_update,
                                                mock_amphora_repo_delete):

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID}
        mark_lb_and_listeners_active = (database_tasks.
                                        MarkLBAndListenersActiveInDB())
        mark_lb_and_listeners_active.execute(LB_ID, [listener_dict])

        mock_session = mock_get_session().begin().__enter__()

        mock_list_not_error.assert_called_once_with(mock_session,
                                                    LISTENER_ID)
        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.ACTIVE)

        # Test with LB_ID from listeners
        mock_loadbalancer_repo_update.reset_mock()
        mock_list_not_error.reset_mock()

        listener_dict = {constants.LISTENER_ID: LISTENER_ID,
                         constants.LOADBALANCER_ID: LB_ID}
        mark_lb_and_listeners_active = (database_tasks.
                                        MarkLBAndListenersActiveInDB())
        mark_lb_and_listeners_active.execute(None, [listener_dict])

        mock_list_not_error.assert_called_once_with(mock_session,
                                                    LISTENER_ID)
        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.ACTIVE)

        # Test with no LB_ID
        mock_loadbalancer_repo_update.reset_mock()
        mark_lb_and_listeners_active.execute(None, [])
        mock_loadbalancer_repo_update.assert_not_called()

        # Test the revert
        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()

        mark_lb_and_listeners_active.revert(LB_ID, [listener_dict])

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_not_called()

        # Test the revert LB_ID from listeners
        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()

        mark_lb_and_listeners_active.revert(None, [listener_dict])

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_not_called()

        # Test the revert no LB_ID
        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()

        mark_lb_and_listeners_active.revert(None, [])

        mock_loadbalancer_repo_update.assert_not_called()
        mock_listener_repo_update.assert_not_called()

        # Test the revert with exceptions
        mock_loadbalancer_repo_update.reset_mock()
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        mock_listener_repo_update.reset_mock()
        mock_listener_repo_update.side_effect = Exception('fail')

        mark_lb_and_listeners_active.revert(LB_ID, [listener_dict])

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)
        repo.LoadBalancerRepository.update.assert_not_called()

    @mock.patch('octavia.common.tls_utils.cert_parser.get_cert_expiration',
                return_value=_cert_mock)
    def test_update_amphora_db_cert_exp(self,
                                        mock_get_cert_exp,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        update_amp_cert = database_tasks.UpdateAmphoraDBCertExpiration()
        fer = utils.get_server_certs_key_passphrases_fernet()
        _pem_mock = fer.encrypt(
            utils.get_compatible_value('test_cert')
        ).decode('utf-8')
        update_amp_cert.execute(_db_amphora_mock.id, _pem_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            cert_expiration=_cert_mock)

    def test_update_amphora_cert_busy_to_false(self,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):
        amp_cert_busy_to_F = database_tasks.UpdateAmphoraCertBusyToFalse()
        amp_cert_busy_to_F.execute(AMP_ID)
        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session,
            AMP_ID,
            cert_busy=False)

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

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.ACTIVE)
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

        # Test the revert
        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_active.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

        # Test the revert with exception
        mock_loadbalancer_repo_update.reset_mock()
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        mark_loadbalancer_active.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

    def test_mark_LB_active_in_db_by_listener(self,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        listener_dict = {'loadbalancer_id': LB_ID}
        mark_loadbalancer_active = database_tasks.MarkLBActiveInDBByListener()
        mark_loadbalancer_active.execute(listener_dict)

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.ACTIVE)
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

        # Test the revert
        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_active.revert(listener_dict)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

        # Test the revert with exception
        mock_loadbalancer_repo_update.reset_mock()
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        mark_loadbalancer_active.revert(listener_dict)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(0, repo.ListenerRepository.update.call_count)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_mark_LB_active_in_db_and_listeners(self,
                                                mock_lb_get,
                                                mock_generate_uuid,
                                                mock_LOG,
                                                mock_get_session,
                                                mock_loadbalancer_repo_update,
                                                mock_listener_repo_update,
                                                mock_amphora_repo_update,
                                                mock_amphora_repo_delete):
        listeners = [data_models.Listener(id='listener1'),
                     data_models.Listener(id='listener2')]
        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners)
        mock_lb_get.return_value = lb
        mark_lb_active = database_tasks.MarkLBActiveInDB(mark_subobjects=True)
        mark_lb_active.execute(self.loadbalancer_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            lb.id,
            provisioning_status=constants.ACTIVE)
        self.assertEqual(2, repo.ListenerRepository.update.call_count)
        repo.ListenerRepository.update.assert_has_calls(
            [mock.call(mock_session, listeners[0].id,
                       provisioning_status=constants.ACTIVE),
             mock.call(mock_session, listeners[1].id,
                       provisioning_status=constants.ACTIVE)])

        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()
        mark_lb_active.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(2, repo.ListenerRepository.update.call_count)
        repo.ListenerRepository.update.assert_has_calls(
            [mock.call(mock_session, listeners[0].id,
                       provisioning_status=constants.ERROR),
             mock.call(mock_session, listeners[1].id,
                       provisioning_status=constants.ERROR)])

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    @mock.patch('octavia.db.repositories.MemberRepository.update')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_mark_LB_active_in_db_full_graph(self,
                                             mock_lb_repo_get,
                                             mock_l7r_repo_update,
                                             mock_l7p_repo_update,
                                             mock_hm_repo_update,
                                             mock_member_repo_update,
                                             mock_pool_repo_update,
                                             mock_generate_uuid,
                                             mock_LOG,
                                             mock_get_session,
                                             mock_loadbalancer_repo_update,
                                             mock_listener_repo_update,
                                             mock_amphora_repo_update,
                                             mock_amphora_repo_delete):
        unused_pool = data_models.Pool(id='unused_pool')
        members1 = [data_models.Member(id='member1'),
                    data_models.Member(id='member2')]
        health_monitor = data_models.HealthMonitor(id='hm1')
        default_pool = data_models.Pool(id='default_pool',
                                        members=members1,
                                        health_monitor=health_monitor)
        listener1 = data_models.Listener(id='listener1',
                                         default_pool=default_pool)
        members2 = [data_models.Member(id='member3'),
                    data_models.Member(id='member4')]
        redirect_pool = data_models.Pool(id='redirect_pool',
                                         members=members2)
        l7rules = [data_models.L7Rule(id='rule1')]
        redirect_policy = data_models.L7Policy(id='redirect_policy',
                                               redirect_pool=redirect_pool,
                                               l7rules=l7rules)
        l7policies = [redirect_policy]
        listener2 = data_models.Listener(id='listener2',
                                         l7policies=l7policies)
        listener2.l7policies = l7policies
        listeners = [listener1, listener2]
        pools = [default_pool, redirect_pool, unused_pool]

        lb = data_models.LoadBalancer(id=LB_ID, listeners=listeners,
                                      pools=pools)
        mark_lb_active = database_tasks.MarkLBActiveInDB(mark_subobjects=True)
        mock_lb_repo_get.return_value = lb
        mark_lb_active.execute(self.loadbalancer_mock)

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            lb.id,
            provisioning_status=constants.ACTIVE)
        repo.ListenerRepository.update.assert_has_calls(
            [mock.call(mock_session, listeners[0].id,
                       provisioning_status=constants.ACTIVE),
             mock.call(mock_session, listeners[1].id,
                       provisioning_status=constants.ACTIVE)])
        repo.PoolRepository.update.assert_has_calls(
            [mock.call(mock_session, default_pool.id,
                       provisioning_status=constants.ACTIVE),
             mock.call(mock_session, redirect_pool.id,
                       provisioning_status=constants.ACTIVE),
             mock.call(mock_session, unused_pool.id,
                       provisioning_status=constants.ACTIVE)])
        repo.HealthMonitorRepository.update.assert_has_calls(
            [mock.call(mock_session, health_monitor.id,
                       provisioning_status=constants.ACTIVE)])
        repo.L7PolicyRepository.update.assert_has_calls(
            [mock.call(mock_session, l7policies[0].id,
                       provisioning_status=constants.ACTIVE)])
        self.assertEqual(1, repo.L7RuleRepository.update.call_count)
        repo.L7RuleRepository.update.assert_has_calls(
            [mock.call(mock_session, l7rules[0].id,
                       provisioning_status=constants.ACTIVE)])

        mock_loadbalancer_repo_update.reset_mock()
        mock_listener_repo_update.reset_mock()
        mock_pool_repo_update.reset_mock()
        mock_member_repo_update.reset_mock()
        mock_hm_repo_update.reset_mock()
        mock_l7p_repo_update.reset_mock()
        mock_l7r_repo_update.reset_mock()
        mark_lb_active.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()
        self.assertEqual(2, repo.ListenerRepository.update.call_count)
        repo.ListenerRepository.update.assert_has_calls(
            [mock.call(mock_session, listeners[0].id,
                       provisioning_status=constants.ERROR),
             mock.call(mock_session, listeners[1].id,
                       provisioning_status=constants.ERROR)])
        repo.PoolRepository.update.assert_has_calls(
            [mock.call(mock_session, default_pool.id,
                       provisioning_status=constants.ERROR),
             mock.call(mock_session, redirect_pool.id,
                       provisioning_status=constants.ERROR),
             mock.call(mock_session, unused_pool.id,
                       provisioning_status=constants.ERROR)
             ])
        self.assertEqual(2, repo.HealthMonitorRepository.update.call_count)
        repo.HealthMonitorRepository.update.assert_has_calls(
            [mock.call(mock_session, health_monitor.id,
                       provisioning_status=constants.ERROR)])
        self.assertEqual(1, repo.L7PolicyRepository.update.call_count)
        repo.L7PolicyRepository.update.assert_has_calls(
            [mock.call(mock_session, l7policies[0].id,
                       provisioning_status=constants.ERROR)])
        self.assertEqual(1, repo.L7RuleRepository.update.call_count)
        repo.L7RuleRepository.update.assert_has_calls(
            [mock.call(mock_session, l7rules[0].id,
                       provisioning_status=constants.ERROR)])

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

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.DELETED)

        # Test the revert
        mock_loadbalancer_repo_update.reset_mock()
        mark_loadbalancer_deleted.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()

        # Test the revert with exception
        mock_loadbalancer_repo_update.reset_mock()
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        mark_loadbalancer_deleted.revert(self.loadbalancer_mock)

        repo.LoadBalancerRepository.update.assert_not_called()

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

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            provisioning_status=constants.PENDING_DELETE)

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

        mock_session = mock_get_session().begin().__enter__()

        repo.HealthMonitorRepository.update.assert_called_once_with(
            mock_session,
            HM_ID,
            delay=1, timeout=2)

        # Test the revert
        mock_health_mon_repo_update.reset_mock()
        update_health_mon.revert(self.health_mon_mock)

        repo.HealthMonitorRepository.update.assert_called_once_with(
            mock_session,
            HM_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_health_mon_repo_update.reset_mock()
        mock_health_mon_repo_update.side_effect = Exception('fail')
        update_health_mon.revert(self.health_mon_mock)

        repo.HealthMonitorRepository.update.assert_called_once_with(
            mock_session,
            HM_ID,
            provisioning_status=constants.ERROR)

    def test_update_load_balancer_in_db(self,
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

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            name='test', description='test2')

    @mock.patch('octavia.db.repositories.VipRepository.update')
    def test_update_vip_in_db_during_update_loadbalancer(self,
                                                         mock_vip_update,
                                                         mock_generate_uuid,
                                                         mock_LOG,
                                                         mock_get_session,
                                                         mock_lb_update,
                                                         mock_listener_update,
                                                         mock_amphora_update,
                                                         mock_amphora_delete):

        _db_loadbalancer_mock.vip.load_balancer_id = LB_ID
        update_load_balancer = database_tasks.UpdateLoadbalancerInDB()
        update_load_balancer.execute(self.loadbalancer_mock,
                                     {'name': 'test',
                                      'description': 'test2',
                                      'vip': {'qos_policy_id': 'fool'}})

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            LB_ID,
            name='test', description='test2')

        repo.VipRepository.update.assert_called_once_with(
            mock_session, LB_ID, qos_policy_id='fool')

    def test_update_listener_in_db(self,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        update_listener = database_tasks.UpdateListenerInDB()
        listener_dict = {constants.LISTENER_ID: LISTENER_ID}
        update_listener.execute(listener_dict,
                                {'name': 'test', 'description': 'test2'})

        mock_session = mock_get_session().begin().__enter__()

        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            LISTENER_ID,
            name='test', description='test2')

        # Test the revert
        mock_listener_repo_update.reset_mock()
        update_listener.revert(listener_dict)
        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert
        mock_listener_repo_update.reset_mock()
        mock_listener_repo_update.side_effect = Exception('fail')
        update_listener.revert(listener_dict)
        repo.ListenerRepository.update.assert_called_once_with(
            mock_session,
            id=LISTENER_ID,
            provisioning_status=constants.ERROR)

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

        mock_session = mock_get_session().begin().__enter__()

        repo.MemberRepository.update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            weight=1, ip_address='10.1.0.0')

        # Test the revert
        mock_member_repo_update.reset_mock()
        update_member.revert(self.member_mock)

        repo.MemberRepository.update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert
        mock_member_repo_update.reset_mock()
        mock_member_repo_update.side_effect = Exception('fail')
        update_member.revert(self.member_mock)

        repo.MemberRepository.update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch(
        'octavia.db.repositories.Repositories.update_pool_and_sp')
    def test_update_pool_in_db(self,
                               mock_repos_pool_update,
                               mock_generate_uuid,
                               mock_LOG,
                               mock_get_session,
                               mock_loadbalancer_repo_update,
                               mock_listener_repo_update,
                               mock_amphora_repo_update,
                               mock_amphora_repo_delete):

        sp_dict = {'type': 'SOURCE_IP', 'cookie_name': None}
        update_dict = {'name': 'test', 'description': 'test2',
                       'session_persistence': sp_dict}
        update_pool = database_tasks.UpdatePoolInDB()
        update_pool.execute(POOL_ID,
                            update_dict)

        mock_session = mock_get_session().begin().__enter__()

        repo.Repositories.update_pool_and_sp.assert_called_once_with(
            mock_session,
            POOL_ID,
            update_dict)

        # Test the revert
        mock_repos_pool_update.reset_mock()
        update_pool.revert(POOL_ID)

        repo.Repositories.update_pool_and_sp.assert_called_once_with(
            mock_session,
            POOL_ID,
            {'provisioning_status': constants.ERROR})

        # Test the revert with exception
        mock_repos_pool_update.reset_mock()
        mock_repos_pool_update.side_effect = Exception('fail')
        update_pool.revert(POOL_ID)

        repo.Repositories.update_pool_and_sp.assert_called_once_with(
            mock_session,
            POOL_ID,
            {'provisioning_status': constants.ERROR})

    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_update_l7policy_in_db(self,
                                   mock_l7policy_repo_update,
                                   mock_generate_uuid,
                                   mock_LOG,
                                   mock_get_session,
                                   mock_loadbalancer_repo_update,
                                   mock_listener_repo_update,
                                   mock_amphora_repo_update,
                                   mock_amphora_repo_delete):

        update_l7policy = database_tasks.UpdateL7PolicyInDB()
        update_l7policy.execute(self.l7policy_mock,
                                {'action': constants.L7POLICY_ACTION_REJECT})

        mock_session = mock_get_session().begin().__enter__()

        repo.L7PolicyRepository.update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            action=constants.L7POLICY_ACTION_REJECT)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        update_l7policy.revert(self.l7policy_mock)

        repo.L7PolicyRepository.update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        mock_l7policy_repo_update.side_effect = Exception('fail')
        update_l7policy.revert(self.l7policy_mock)

        repo.L7PolicyRepository.update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_update_l7rule_in_db(self,
                                 mock_l7rule_repo_update,
                                 mock_l7policy_repo_update,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        update_l7rule = database_tasks.UpdateL7RuleInDB()
        update_l7rule.execute(
            self.l7rule_mock,
            {'type': constants.L7RULE_TYPE_PATH,
             'compare_type': constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
             'value': '/api'})

        mock_session = mock_get_session().begin().__enter__()

        repo.L7RuleRepository.update.assert_called_once_with(
            mock_session,
            L7RULE_ID,
            type=constants.L7RULE_TYPE_PATH,
            compare_type=constants.L7RULE_COMPARE_TYPE_STARTS_WITH,
            value='/api')

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        update_l7rule.revert(self.l7rule_mock)

        repo.L7PolicyRepository.update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        mock_l7rule_repo_update.side_effect = Exception('fail')
        update_l7rule.revert(self.l7rule_mock)

        repo.L7PolicyRepository.update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get',
                return_value=_db_amphora_mock)
    def test_get_amphora_details(self,
                                 mock_amp_get,
                                 mock_generate_uuid,
                                 mock_LOG,
                                 mock_get_session,
                                 mock_loadbalancer_repo_update,
                                 mock_listener_repo_update,
                                 mock_amphora_repo_update,
                                 mock_amphora_repo_delete):

        get_amp_details = database_tasks.GetAmphoraDetails()
        new_amp = get_amp_details.execute(self.amphora)

        self.assertEqual(AMP_ID, new_amp[constants.ID])
        self.assertEqual(VRRP_IP, new_amp[constants.VRRP_IP])
        self.assertEqual(HA_IP, new_amp[constants.HA_IP])
        self.assertEqual(VRRP_PORT_ID, new_amp[constants.VRRP_PORT_ID])
        self.assertEqual(AMP_ROLE, new_amp[constants.ROLE])
        self.assertEqual(VRRP_ID, new_amp[constants.VRRP_ID])
        self.assertEqual(VRRP_PRIORITY, new_amp[constants.VRRP_PRIORITY])

    def test_mark_amphora_role_indb(self,
                                    mock_generate_uuid,
                                    mock_LOG,
                                    mock_get_session,
                                    mock_loadbalancer_repo_update,
                                    mock_listener_repo_update,
                                    mock_amphora_repo_update,
                                    mock_amphora_repo_delete):

        mark_amp_master_indb = database_tasks.MarkAmphoraMasterInDB()
        mark_amp_master_indb.execute(self.amphora)

        mock_session = mock_get_session().begin().__enter__()

        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role='MASTER',
            vrrp_priority=constants.ROLE_MASTER_PRIORITY)

        mock_amphora_repo_update.reset_mock()

        mark_amp_master_indb.revert("BADRESULT", self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role=None, vrrp_priority=None)

        mock_amphora_repo_update.reset_mock()

        failure_obj = failure.Failure.from_exception(Exception("TESTEXCEPT"))
        mark_amp_master_indb.revert(failure_obj, self.amphora)
        self.assertFalse(repo.AmphoraRepository.update.called)

        mock_amphora_repo_update.reset_mock()

        mark_amp_backup_indb = database_tasks.MarkAmphoraBackupInDB()
        mark_amp_backup_indb.execute(self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role='BACKUP',
            vrrp_priority=constants.ROLE_BACKUP_PRIORITY)

        mock_amphora_repo_update.reset_mock()

        mark_amp_backup_indb.revert("BADRESULT", self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role=None, vrrp_priority=None)

        mock_amphora_repo_update.reset_mock()

        mark_amp_standalone_indb = database_tasks.MarkAmphoraStandAloneInDB()
        mark_amp_standalone_indb.execute(self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role='STANDALONE',
            vrrp_priority=None)

        mock_amphora_repo_update.reset_mock()

        mark_amp_standalone_indb.revert("BADRESULT", self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role=None, vrrp_priority=None)

        # Test revert with exception
        mock_amphora_repo_update.reset_mock()
        mock_amphora_repo_update.side_effect = Exception('fail')
        mark_amp_standalone_indb.revert("BADRESULT", self.amphora)
        repo.AmphoraRepository.update.assert_called_once_with(
            mock_session, AMP_ID, role=None, vrrp_priority=None)

    @mock.patch('octavia.db.repositories.AmphoraRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_amphorae_from_loadbalancer(self,
                                            mock_lb_get,
                                            mock_amphora_get,
                                            mock_generate_uuid,
                                            mock_LOG,
                                            mock_get_session,
                                            mock_loadbalancer_repo_update,
                                            mock_listener_repo_update,
                                            mock_amphora_repo_update,
                                            mock_amphora_repo_delete):
        amp1 = mock.MagicMock()
        amp1.id = uuidutils.generate_uuid()
        amp2 = mock.MagicMock()
        amp2.id = uuidutils.generate_uuid()
        lb = mock.MagicMock()
        lb.amphorae = [amp1, amp2]

        mock_amphora_get.side_effect = [_db_amphora_mock, None]
        mock_lb_get.return_value = lb

        get_amps_from_lb_obj = database_tasks.GetAmphoraeFromLoadbalancer()
        result = get_amps_from_lb_obj.execute(self.loadbalancer_mock)
        self.assertEqual([_db_amphora_mock.to_dict()], result)
        self.assertEqual([_db_amphora_mock.to_dict()], result)

    @mock.patch('octavia.db.repositories.ListenerRepository.get')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_listeners_from_loadbalancer(self,
                                             mock_lb_get,
                                             mock_listener_get,
                                             mock_generate_uuid,
                                             mock_LOG,
                                             mock_get_session,
                                             mock_loadbalancer_repo_update,
                                             mock_listener_repo_update,
                                             mock_amphora_repo_update,
                                             mock_amphora_repo_delete):
        mock_listener_get.return_value = _listener_mock
        _db_loadbalancer_mock.listeners = [_listener_mock]
        mock_lb_get.return_value = _db_loadbalancer_mock
        get_list_from_lb_obj = database_tasks.GetListenersFromLoadbalancer()
        result = get_list_from_lb_obj.execute(self.loadbalancer_mock)
        mock_session = mock_get_session().begin().__enter__()

        mock_listener_get.assert_called_once_with(mock_session,
                                                  id=_listener_mock.id)
        self.assertEqual([{constants.LISTENER_ID: LISTENER_ID}], result)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_vip_from_loadbalancer(self,
                                       mock_lb_get,
                                       mock_generate_uuid,
                                       mock_LOG,
                                       mock_get_session,
                                       mock_loadbalancer_repo_update,
                                       mock_listener_repo_update,
                                       mock_amphora_repo_update,
                                       mock_amphora_repo_delete):
        _db_loadbalancer_mock.vip = _vip_mock
        mock_lb_get.return_value = _db_loadbalancer_mock
        get_vip_from_lb_obj = database_tasks.GetVipFromLoadbalancer()
        result = get_vip_from_lb_obj.execute(self.loadbalancer_mock)
        self.assertEqual(_vip_mock.to_dict(), result)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_get_loadbalancer(self, mock_lb_get, mock_generate_uuid, mock_LOG,
                              mock_get_session, mock_loadbalancer_repo_update,
                              mock_listener_repo_update,
                              mock_amphora_repo_update,
                              mock_amphora_repo_delete):
        LB_ID = uuidutils.generate_uuid()
        get_loadbalancer_obj = database_tasks.GetLoadBalancer()

        mock_lb_get.return_value = _db_loadbalancer_mock

        result = get_loadbalancer_obj.execute(LB_ID)

        self.assertEqual(self.loadbalancer_mock, result)
        mock_session = mock_get_session().begin().__enter__()

        mock_lb_get.assert_called_once_with(mock_session, id=LB_ID)

    @mock.patch('octavia.db.repositories.VRRPGroupRepository.create')
    def test_create_vrrp_group_for_lb(self,
                                      mock_vrrp_group_create,
                                      mock_generate_uuid,
                                      mock_LOG,
                                      mock_get_session,
                                      mock_loadbalancer_repo_update,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_update,
                                      mock_amphora_repo_delete):

        mock_session = mock_get_session().begin().__enter__()
        mock_get_session().begin().__exit__.side_effect = (
            odb_exceptions.DBDuplicateEntry)
        create_vrrp_group = database_tasks.CreateVRRPGroupForLB()
        create_vrrp_group.execute(LB_ID)
        mock_vrrp_group_create.assert_called_once_with(
            mock_session, load_balancer_id=LB_ID,
            vrrp_group_name=LB_ID.replace('-', ''),
            vrrp_auth_type=constants.VRRP_AUTH_DEFAULT,
            vrrp_auth_pass=mock_generate_uuid.return_value.replace('-',
                                                                   '')[0:7],
            advert_int=1)
        create_vrrp_group.execute(self.loadbalancer_mock)

    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.delete')
    def test_disable_amphora_health_monitoring(self,
                                               mock_amp_health_repo_delete,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):
        disable_amp_health = database_tasks.DisableAmphoraHealthMonitoring()
        disable_amp_health.execute(self.amphora)
        mock_session = mock_get_session().begin().__enter__()

        mock_amp_health_repo_delete.assert_called_once_with(
            mock_session, amphora_id=AMP_ID)

    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.delete')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_disable_lb_amphorae_health_monitoring(
            self,
            mock_lb_get,
            mock_amp_health_repo_delete,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):
        disable_amp_health = (
            database_tasks.DisableLBAmphoraeHealthMonitoring())
        mock_lb_get.return_value = _db_loadbalancer_mock
        disable_amp_health.execute(self.loadbalancer_mock)
        mock_session = mock_get_session().begin().__enter__()

        mock_amp_health_repo_delete.assert_called_once_with(
            mock_session, amphora_id=AMP_ID)

    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.update')
    def test_mark_amphora_health_monitoring_busy(self,
                                                 mock_amp_health_repo_update,
                                                 mock_generate_uuid,
                                                 mock_LOG,
                                                 mock_get_session,
                                                 mock_loadbalancer_repo_update,
                                                 mock_listener_repo_update,
                                                 mock_amphora_repo_update,
                                                 mock_amphora_repo_delete):
        mark_busy = database_tasks.MarkAmphoraHealthBusy()
        mark_busy.execute(self.amphora)
        mock_session = mock_get_session().begin().__enter__()

        mock_amp_health_repo_update.assert_called_once_with(
            mock_session, amphora_id=AMP_ID, busy=True)

    @mock.patch('octavia.db.repositories.AmphoraHealthRepository.update')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    def test_mark_lb_amphorae_health_monitoring_busy(
            self,
            mock_lb_get,
            mock_amp_health_repo_update,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):
        mark_busy = (
            database_tasks.MarkLBAmphoraeHealthBusy())
        mock_lb_get.return_value = _db_loadbalancer_mock
        mark_busy.execute(self.loadbalancer_mock)
        mock_session = mock_get_session().begin().__enter__()

        mock_amp_health_repo_update.assert_called_once_with(
            mock_session, amphora_id=AMP_ID, busy=True)

    def test_update_lb_server_group_in_db(self,
                                          mock_generate_uuid,
                                          mock_LOG,
                                          mock_get_session,
                                          mock_loadbalancer_repo_update,
                                          mock_listener_repo_update,
                                          mock_amphora_repo_update,
                                          mock_amphora_repo_delete):

        update_server_group_info = database_tasks.UpdateLBServerGroupInDB()
        update_server_group_info.execute(LB_ID, SERVER_GROUP_ID)

        mock_session = mock_get_session().begin().__enter__()

        repo.LoadBalancerRepository.update.assert_called_once_with(
            mock_session,
            id=LB_ID,
            server_group_id=SERVER_GROUP_ID)

        # Test the revert
        mock_listener_repo_update.reset_mock()
        update_server_group_info.revert(LB_ID, SERVER_GROUP_ID)

        # Test the revert with exception
        mock_listener_repo_update.reset_mock()
        mock_loadbalancer_repo_update.side_effect = Exception('fail')
        update_server_group_info.revert(LB_ID, SERVER_GROUP_ID)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.get')
    def test_mark_health_mon_active_in_db(self,
                                          mock_health_mon_repo_get,
                                          mock_health_mon_repo_update,
                                          mock_generate_uuid,
                                          mock_LOG,
                                          mock_get_session,
                                          mock_loadbalancer_repo_update,
                                          mock_listener_repo_update,
                                          mock_amphora_repo_update,
                                          mock_amphora_repo_delete):
        mock_health_mon_repo_get.return_value = self.db_health_mon_mock
        mark_health_mon_active = (database_tasks.MarkHealthMonitorActiveInDB())
        mark_health_mon_active.execute(self.health_mon_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            HM_ID,
            operating_status=constants.ONLINE,
            provisioning_status=constants.ACTIVE)

        # Test the revert
        mock_health_mon_repo_update.reset_mock()
        mark_health_mon_active.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_health_mon_repo_update.reset_mock()
        mock_health_mon_repo_update.side_effect = Exception('fail')
        mark_health_mon_active.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_mark_health_mon_pending_create_in_db(
            self,
            mock_health_mon_repo_update,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        mark_health_mon_pending_create = (database_tasks.
                                          MarkHealthMonitorPendingCreateInDB())
        mark_health_mon_pending_create.execute(self.health_mon_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            HM_ID,
            provisioning_status=constants.PENDING_CREATE)

        # Test the revert
        mock_health_mon_repo_update.reset_mock()
        mark_health_mon_pending_create.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_health_mon_repo_update.reset_mock()
        mock_health_mon_repo_update.side_effect = Exception('fail')
        mark_health_mon_pending_create.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_mark_health_mon_pending_delete_in_db(
            self,
            mock_health_mon_repo_update,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        mark_health_mon_pending_delete = (database_tasks.
                                          MarkHealthMonitorPendingDeleteInDB())
        mark_health_mon_pending_delete.execute(self.health_mon_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            HM_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_health_mon_repo_update.reset_mock()
        mark_health_mon_pending_delete.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_health_mon_repo_update.reset_mock()
        mock_health_mon_repo_update.side_effect = Exception('fail')
        mark_health_mon_pending_delete.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_mark_health_mon_pending_update_in_db(
            self,
            mock_health_mon_repo_update,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        mark_health_mon_pending_update = (database_tasks.
                                          MarkHealthMonitorPendingUpdateInDB())
        mark_health_mon_pending_update.execute(self.health_mon_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            HM_ID,
            provisioning_status=constants.PENDING_UPDATE)

        # Test the revert
        mock_health_mon_repo_update.reset_mock()
        mark_health_mon_pending_update.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_health_mon_repo_update.reset_mock()
        mock_health_mon_repo_update.side_effect = Exception('fail')
        mark_health_mon_pending_update.revert(self.health_mon_mock)

        mock_health_mon_repo_update.assert_called_once_with(
            mock_session,
            id=HM_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository.update')
    def test_mark_health_monitors_online_in_db(self,
                                               mock_health_mon_repo_update,
                                               mock_loadbalancer_repo_get,
                                               mock_generate_uuid,
                                               mock_LOG,
                                               mock_get_session,
                                               mock_loadbalancer_repo_update,
                                               mock_listener_repo_update,
                                               mock_amphora_repo_update,
                                               mock_amphora_repo_delete):
        # Creating a mock hm for a default pool
        mock_lb = mock.MagicMock()
        mock_listener = mock.MagicMock()
        mock_default_pool = mock_listener.default_pool
        mock_hm_def_pool = mock_default_pool.health_monitor
        mock_hm_def_pool.id = uuidutils.generate_uuid()
        mock_lb.listeners = [mock_listener]

        # Creating a mock hm for a redirect pool of an l7policy
        mock_l7policy = mock.MagicMock()
        mock_redirect_pool = mock_l7policy.redirect_pool
        mock_hm_l7_policy = mock_redirect_pool.health_monitor
        mock_hm_l7_policy.id = uuidutils.generate_uuid()
        mock_listener.l7policies = [mock_l7policy]

        # Creating a mock hm for a non default pool - we check its health
        # monitor won't be updated
        mock_pool = mock.MagicMock()
        mock_hm_non_def_pool = mock_pool.health_monitor
        mock_hm_non_def_pool.id = uuidutils.generate_uuid()
        mock_lb.pools = [mock_pool]

        mock_loadbalancer_repo_get.return_value = mock_lb
        mark_health_mon_online = (database_tasks.
                                  MarkHealthMonitorsOnlineInDB())
        mark_health_mon_online.execute(mock_lb)

        mock_session = mock_get_session().begin().__enter__()
        for mock_id in [mock_hm_def_pool.id, mock_hm_l7_policy.id]:
            mock_health_mon_repo_update.assert_called_with(
                mock_session,
                mock_id,
                operating_status=constants.ONLINE)
        self.assertEqual(2, mock_health_mon_repo_update.call_count)

    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    @mock.patch('octavia.db.repositories.L7PolicyRepository.get')
    def test_mark_l7policy_active_in_db(self,
                                        mock_l7policy_repo_get,
                                        mock_l7policy_repo_update,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        mark_l7policy_active = (database_tasks.MarkL7PolicyActiveInDB())
        mock_l7policy_repo_get.return_value = _l7policy_mock
        mark_l7policy_active.execute(self.l7policy_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        mark_l7policy_active.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7policy_repo_update.reset_mock()
        mock_l7policy_repo_update.side_effect = Exception('fail')
        mark_l7policy_active.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_mark_l7policy_pending_create_in_db(self,
                                                mock_l7policy_repo_update,
                                                mock_generate_uuid,
                                                mock_LOG,
                                                mock_get_session,
                                                mock_loadbalancer_repo_update,
                                                mock_listener_repo_update,
                                                mock_amphora_repo_update,
                                                mock_amphora_repo_delete):

        mark_l7policy_pending_create = (database_tasks.
                                        MarkL7PolicyPendingCreateInDB())
        mark_l7policy_pending_create.execute(self.l7policy_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.PENDING_CREATE)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        mark_l7policy_pending_create.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7policy_repo_update.reset_mock()
        mock_l7policy_repo_update.side_effect = Exception('fail')
        mark_l7policy_pending_create.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_mark_l7policy_pending_delete_in_db(self,
                                                mock_l7policy_repo_update,
                                                mock_generate_uuid,
                                                mock_LOG,
                                                mock_get_session,
                                                mock_loadbalancer_repo_update,
                                                mock_listener_repo_update,
                                                mock_amphora_repo_update,
                                                mock_amphora_repo_delete):

        mark_l7policy_pending_delete = (database_tasks.
                                        MarkL7PolicyPendingDeleteInDB())
        mark_l7policy_pending_delete.execute(self.l7policy_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        mark_l7policy_pending_delete.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7policy_repo_update.reset_mock()
        mock_l7policy_repo_update.side_effect = Exception('fail')
        mark_l7policy_pending_delete.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7PolicyRepository.update')
    def test_mark_l7policy_pending_update_in_db(self,
                                                mock_l7policy_repo_update,
                                                mock_generate_uuid,
                                                mock_LOG,
                                                mock_get_session,
                                                mock_loadbalancer_repo_update,
                                                mock_listener_repo_update,
                                                mock_amphora_repo_update,
                                                mock_amphora_repo_delete):

        mark_l7policy_pending_update = (database_tasks.
                                        MarkL7PolicyPendingUpdateInDB())
        mark_l7policy_pending_update.execute(self.l7policy_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            L7POLICY_ID,
            provisioning_status=constants.PENDING_UPDATE)

        # Test the revert
        mock_l7policy_repo_update.reset_mock()
        mark_l7policy_pending_update.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7policy_repo_update.reset_mock()
        mock_l7policy_repo_update.side_effect = Exception('fail')
        mark_l7policy_pending_update.revert(self.l7policy_mock)

        mock_l7policy_repo_update.assert_called_once_with(
            mock_session,
            id=L7POLICY_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    @mock.patch('octavia.db.repositories.L7RuleRepository.get')
    def test_mark_l7rule_active_in_db(self,
                                      mock_l7rule_repo_get,
                                      mock_l7rule_repo_update,
                                      mock_generate_uuid,
                                      mock_LOG,
                                      mock_get_session,
                                      mock_loadbalancer_repo_update,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_update,
                                      mock_amphora_repo_delete):
        mock_l7rule_repo_get.return_value = _l7rule_mock
        mark_l7rule_active = (database_tasks.MarkL7RuleActiveInDB())
        mark_l7rule_active.execute(self.l7rule_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            L7RULE_ID,
            provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE)

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        mark_l7rule_active.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7rule_repo_update.reset_mock()
        mock_l7rule_repo_update.side_effect = Exception('fail')
        mark_l7rule_active.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    def test_mark_l7rule_pending_create_in_db(self,
                                              mock_l7rule_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_l7rule_pending_create = (database_tasks.
                                      MarkL7RulePendingCreateInDB())
        mark_l7rule_pending_create.execute(self.l7rule_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            L7RULE_ID,
            provisioning_status=constants.PENDING_CREATE)

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        mark_l7rule_pending_create.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7rule_repo_update.reset_mock()
        mock_l7rule_repo_update.side_effect = Exception('fail')
        mark_l7rule_pending_create.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    def test_mark_l7rule_pending_delete_in_db(self,
                                              mock_l7rule_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_l7rule_pending_delete = (database_tasks.
                                      MarkL7RulePendingDeleteInDB())
        mark_l7rule_pending_delete.execute(self.l7rule_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            L7RULE_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        mark_l7rule_pending_delete.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7rule_repo_update.reset_mock()
        mock_l7rule_repo_update.side_effect = Exception('fail')
        mark_l7rule_pending_delete.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.L7RuleRepository.update')
    def test_mark_l7rule_pending_update_in_db(self,
                                              mock_l7rule_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_l7rule_pending_update = (database_tasks.
                                      MarkL7RulePendingUpdateInDB())
        mark_l7rule_pending_update.execute(self.l7rule_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            L7RULE_ID,
            provisioning_status=constants.PENDING_UPDATE)

        # Test the revert
        mock_l7rule_repo_update.reset_mock()
        mark_l7rule_pending_update.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_l7rule_repo_update.reset_mock()
        mock_l7rule_repo_update.side_effect = Exception('fail')
        mark_l7rule_pending_update.revert(self.l7rule_mock)

        mock_l7rule_repo_update.assert_called_once_with(
            mock_session,
            id=L7RULE_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_mark_member_active_in_db(self,
                                      mock_member_repo_update,
                                      mock_generate_uuid,
                                      mock_LOG,
                                      mock_get_session,
                                      mock_loadbalancer_repo_update,
                                      mock_listener_repo_update,
                                      mock_amphora_repo_update,
                                      mock_amphora_repo_delete):

        mark_member_active = (database_tasks.MarkMemberActiveInDB())
        mark_member_active.execute(self.member_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.ACTIVE)

        # Test the revert
        mock_member_repo_update.reset_mock()
        mark_member_active.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_member_repo_update.reset_mock()
        mock_member_repo_update.side_effect = Exception('fail')
        mark_member_active.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_mark_member_pending_create_in_db(self,
                                              mock_member_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_member_pending_create = (database_tasks.
                                      MarkMemberPendingCreateInDB())
        mark_member_pending_create.execute(self.member_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.PENDING_CREATE)

        # Test the revert
        mock_member_repo_update.reset_mock()
        mark_member_pending_create.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_member_repo_update.reset_mock()
        mock_member_repo_update.side_effect = Exception('fail')
        mark_member_pending_create.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_mark_member_pending_delete_in_db(self,
                                              mock_member_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_member_pending_delete = (database_tasks.
                                      MarkMemberPendingDeleteInDB())
        mark_member_pending_delete.execute(self.member_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_member_repo_update.reset_mock()
        mark_member_pending_delete.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_member_repo_update.reset_mock()
        mock_member_repo_update.side_effect = Exception('fail')
        mark_member_pending_delete.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.update')
    def test_mark_member_pending_update_in_db(self,
                                              mock_member_repo_update,
                                              mock_generate_uuid,
                                              mock_LOG,
                                              mock_get_session,
                                              mock_loadbalancer_repo_update,
                                              mock_listener_repo_update,
                                              mock_amphora_repo_update,
                                              mock_amphora_repo_delete):

        mark_member_pending_update = (database_tasks.
                                      MarkMemberPendingUpdateInDB())
        mark_member_pending_update.execute(self.member_mock)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            MEMBER_ID,
            provisioning_status=constants.PENDING_UPDATE)

        # Test the revert
        mock_member_repo_update.reset_mock()
        mark_member_pending_update.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_member_repo_update.reset_mock()
        mock_member_repo_update.side_effect = Exception('fail')
        mark_member_pending_update.revert(self.member_mock)

        mock_member_repo_update.assert_called_once_with(
            mock_session,
            id=MEMBER_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_mark_pool_active_in_db(self,
                                    mock_pool_repo_update,
                                    mock_generate_uuid,
                                    mock_LOG,
                                    mock_get_session,
                                    mock_loadbalancer_repo_update,
                                    mock_listener_repo_update,
                                    mock_amphora_repo_update,
                                    mock_amphora_repo_delete):

        mark_pool_active = (database_tasks.MarkPoolActiveInDB())
        mark_pool_active.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            POOL_ID,
            provisioning_status=constants.ACTIVE)

        # Test the revert
        mock_pool_repo_update.reset_mock()
        mark_pool_active.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_pool_repo_update.reset_mock()
        mock_pool_repo_update.side_effect = Exception('fail')
        mark_pool_active.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_mark_pool_pending_create_in_db(self,
                                            mock_pool_repo_update,
                                            mock_generate_uuid,
                                            mock_LOG,
                                            mock_get_session,
                                            mock_loadbalancer_repo_update,
                                            mock_listener_repo_update,
                                            mock_amphora_repo_update,
                                            mock_amphora_repo_delete):

        mark_pool_pending_create = (database_tasks.MarkPoolPendingCreateInDB())
        mark_pool_pending_create.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            POOL_ID,
            provisioning_status=constants.PENDING_CREATE)

        # Test the revert
        mock_pool_repo_update.reset_mock()
        mark_pool_pending_create.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_pool_repo_update.reset_mock()
        mock_pool_repo_update.side_effect = Exception('fail')
        mark_pool_pending_create.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_mark_pool_pending_delete_in_db(self,
                                            mock_pool_repo_update,
                                            mock_generate_uuid,
                                            mock_LOG,
                                            mock_get_session,
                                            mock_loadbalancer_repo_update,
                                            mock_listener_repo_update,
                                            mock_amphora_repo_update,
                                            mock_amphora_repo_delete):

        mark_pool_pending_delete = (database_tasks.MarkPoolPendingDeleteInDB())
        mark_pool_pending_delete.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            POOL_ID,
            provisioning_status=constants.PENDING_DELETE)

        # Test the revert
        mock_pool_repo_update.reset_mock()
        mark_pool_pending_delete.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_pool_repo_update.reset_mock()
        mock_pool_repo_update.side_effect = Exception('fail')
        mark_pool_pending_delete.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.PoolRepository.update')
    def test_mark_pool_pending_update_in_db(self,
                                            mock_pool_repo_update,
                                            mock_generate_uuid,
                                            mock_LOG,
                                            mock_get_session,
                                            mock_loadbalancer_repo_update,
                                            mock_listener_repo_update,
                                            mock_amphora_repo_update,
                                            mock_amphora_repo_delete):

        mark_pool_pending_update = (database_tasks.
                                    MarkPoolPendingUpdateInDB())
        mark_pool_pending_update.execute(POOL_ID)

        mock_session = mock_get_session().begin().__enter__()

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            POOL_ID,
            provisioning_status=constants.PENDING_UPDATE)

        # Test the revert
        mock_pool_repo_update.reset_mock()
        mark_pool_pending_update.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

        # Test the revert with exception
        mock_pool_repo_update.reset_mock()
        mock_pool_repo_update.side_effect = Exception('fail')
        mark_pool_pending_update.revert(POOL_ID)

        mock_pool_repo_update.assert_called_once_with(
            mock_session,
            id=POOL_ID,
            provisioning_status=constants.ERROR)

    @mock.patch('octavia.db.repositories.MemberRepository.update_pool_members')
    def test_update_pool_members_operating_status_in_db(
            self,
            mock_member_repo_update_pool_members,
            mock_generate_uuid,
            mock_LOG,
            mock_get_session,
            mock_loadbalancer_repo_update,
            mock_listener_repo_update,
            mock_amphora_repo_update,
            mock_amphora_repo_delete):

        update_members = database_tasks.UpdatePoolMembersOperatingStatusInDB()
        update_members.execute(POOL_ID, constants.ONLINE)

        mock_session = mock_get_session().begin().__enter__()

        mock_member_repo_update_pool_members.assert_called_once_with(
            mock_session,
            POOL_ID,
            operating_status=constants.ONLINE)

    @mock.patch('octavia.common.utils.ip_version')
    @mock.patch('octavia.db.api.get_session')
    @mock.patch('octavia.db.repositories.ListenerRepository.'
                'get_port_protocol_cidr_for_lb')
    def test_get_amphora_firewall_rules(self,
                                        mock_get_port_for_lb,
                                        mock_db_get_session,
                                        mock_ip_version,
                                        mock_generate_uuid,
                                        mock_LOG,
                                        mock_get_session,
                                        mock_loadbalancer_repo_update,
                                        mock_listener_repo_update,
                                        mock_amphora_repo_update,
                                        mock_amphora_repo_delete):

        amphora_dict = {constants.ID: AMP_ID}
        rules = [{'protocol': 'TCP', 'cidr': '192.0.2.0/24', 'port': 80},
                 {'protocol': 'TCP', 'cidr': '198.51.100.0/24', 'port': 80}]
        vrrp_rules = [
            {'protocol': 'TCP', 'cidr': '192.0.2.0/24', 'port': 80},
            {'protocol': 'TCP', 'cidr': '198.51.100.0/24', 'port': 80},
            {'cidr': '203.0.113.5/32', 'port': 112, 'protocol': 'vrrp'}]
        mock_get_port_for_lb.side_effect = [
            copy.deepcopy(rules), copy.deepcopy(rules), copy.deepcopy(rules),
            copy.deepcopy(rules)]
        mock_ip_version.side_effect = [4, 6, 55]

        get_amp_fw_rules = database_tasks.GetAmphoraFirewallRules()

        # Test non-SRIOV VIP
        amphora_net_cfg_dict = {
            AMP_ID: {constants.AMPHORA: {
                     'load_balancer': {constants.VIP: {
                         constants.VNIC_TYPE: constants.VNIC_TYPE_NORMAL}}}}}
        result = get_amp_fw_rules.execute([amphora_dict], 0,
                                          amphora_net_cfg_dict)
        self.assertEqual([{'non-sriov-vip': True}], result)

        # Test SRIOV VIP - Single
        amphora_net_cfg_dict = {
            AMP_ID: {constants.AMPHORA: {
                'load_balancer': {constants.VIP: {
                    constants.VNIC_TYPE: constants.VNIC_TYPE_DIRECT},
                    constants.TOPOLOGY: constants.TOPOLOGY_SINGLE},
                constants.LOAD_BALANCER_ID: LB_ID}}}
        result = get_amp_fw_rules.execute([amphora_dict], 0,
                                          amphora_net_cfg_dict)
        mock_get_port_for_lb.assert_called_once_with(mock_db_get_session(),
                                                     LB_ID)
        self.assertEqual(rules, result)

        mock_get_port_for_lb.reset_mock()

        # Test SRIOV VIP - Active/Standby
        amphora_net_cfg_dict = {
            AMP_ID: {constants.AMPHORA: {
                'load_balancer': {constants.VIP: {
                    constants.VNIC_TYPE: constants.VNIC_TYPE_DIRECT},
                    constants.TOPOLOGY: constants.TOPOLOGY_ACTIVE_STANDBY,
                    constants.AMPHORAE: [{
                        constants.ID: AMP_ID,
                        constants.STATUS: constants.AMPHORA_ALLOCATED},
                        {constants.ID: AMP2_ID,
                         constants.STATUS: constants.AMPHORA_ALLOCATED,
                         constants.VRRP_IP: '203.0.113.5'}]},
                constants.LOAD_BALANCER_ID: LB_ID}}}

        # IPv4 path
        mock_get_port_for_lb.reset_mock()
        vrrp_rules = [
            {'protocol': 'TCP', 'cidr': '192.0.2.0/24', 'port': 80},
            {'protocol': 'TCP', 'cidr': '198.51.100.0/24', 'port': 80},
            {'cidr': '203.0.113.5/32', 'port': 112, 'protocol': 'vrrp'}]
        result = get_amp_fw_rules.execute([amphora_dict], 0,
                                          amphora_net_cfg_dict)
        mock_get_port_for_lb.assert_called_once_with(mock_db_get_session(),
                                                     LB_ID)
        self.assertEqual(vrrp_rules, result)

        # IPv6 path
        mock_get_port_for_lb.reset_mock()
        vrrp_rules = [
            {'protocol': 'TCP', 'cidr': '192.0.2.0/24', 'port': 80},
            {'protocol': 'TCP', 'cidr': '198.51.100.0/24', 'port': 80},
            {'cidr': '203.0.113.5/128', 'port': 112, 'protocol': 'vrrp'}]
        result = get_amp_fw_rules.execute([amphora_dict], 0,
                                          amphora_net_cfg_dict)
        mock_get_port_for_lb.assert_called_once_with(mock_db_get_session(),
                                                     LB_ID)
        self.assertEqual(vrrp_rules, result)

        # Bogus IP version path
        self.assertRaises(exceptions.InvalidIPAddress,
                          get_amp_fw_rules.execute, [amphora_dict], 0,
                          amphora_net_cfg_dict)
