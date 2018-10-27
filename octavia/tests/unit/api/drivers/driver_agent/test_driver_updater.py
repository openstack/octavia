#    Copyright 2018 Rackspace, US Inc.
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

import copy

import mock
from mock import call

from octavia.api.drivers.driver_agent import driver_updater
import octavia.tests.unit.base as base
from octavia_lib.api.drivers import exceptions as driver_exceptions
from octavia_lib.common import constants as lib_consts


class TestDriverUpdater(base.TestCase):

    @mock.patch('octavia.db.repositories.LoadBalancerRepository')
    @mock.patch('octavia.db.repositories.ListenerRepository')
    @mock.patch('octavia.db.repositories.L7PolicyRepository')
    @mock.patch('octavia.db.repositories.L7RuleRepository')
    @mock.patch('octavia.db.repositories.PoolRepository')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository')
    @mock.patch('octavia.db.repositories.MemberRepository')
    @mock.patch('octavia.db.api.get_session')
    def setUp(self, mock_get_session, mock_member_repo, mock_health_repo,
              mock_pool_repo, mock_l7r_repo, mock_l7p_repo, mock_list_repo,
              mock_lb_repo):
        super(TestDriverUpdater, self).setUp()
        self.mock_session = "FAKE_DB_SESSION"
        mock_get_session.return_value = self.mock_session

        member_mock = mock.MagicMock()
        mock_member_repo.return_value = member_mock
        self.mock_member_repo = member_mock
        health_mock = mock.MagicMock()
        mock_health_repo.return_value = health_mock
        self.mock_health_repo = health_mock
        pool_mock = mock.MagicMock()
        mock_pool_repo.return_value = pool_mock
        self.mock_pool_repo = pool_mock
        l7r_mock = mock.MagicMock()
        mock_l7r_repo.return_value = l7r_mock
        self.mock_l7r_repo = l7r_mock
        l7p_mock = mock.MagicMock()
        mock_l7p_repo.return_value = l7p_mock
        self.mock_l7p_repo = l7p_mock
        list_mock = mock.MagicMock()
        mock_list_repo.return_value = list_mock
        self.mock_list_repo = list_mock
        lb_mock = mock.MagicMock()
        mock_lb_repo.return_value = lb_mock
        self.mock_lb_repo = lb_mock
        self.driver_updater = driver_updater.DriverUpdater()
        self.ref_ok_response = {lib_consts.STATUS_CODE:
                                lib_consts.DRVR_STATUS_CODE_OK}

    @mock.patch('octavia.common.utils.get_network_driver')
    def test_check_for_lb_vip_deallocate(self, mock_get_net_drvr):
        mock_repo = mock.MagicMock()
        mock_lb = mock.MagicMock()
        mock_vip = mock.MagicMock()
        mock_octavia_owned = mock.PropertyMock(side_effect=[True, False])
        type(mock_vip).octavia_owned = mock_octavia_owned
        mock_lb.vip = mock_vip
        mock_repo.get.return_value = mock_lb
        mock_net_drvr = mock.MagicMock()
        mock_get_net_drvr.return_value = mock_net_drvr

        self.driver_updater._check_for_lb_vip_deallocate(mock_repo, 'bogus_id')
        mock_net_drvr.deallocate_vip.assert_called_once_with(mock_vip)

        mock_net_drvr.reset_mock()
        self.driver_updater._check_for_lb_vip_deallocate(mock_repo, 'bogus_id')
        mock_net_drvr.deallocate_vip.assert_not_called()

    @mock.patch('octavia.api.drivers.driver_agent.driver_updater.'
                'DriverUpdater._check_for_lb_vip_deallocate')
    def test_process_status_update(self, mock_deallocate):
        mock_repo = mock.MagicMock()
        list_dict = {"id": 2,
                     lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                     lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        list_prov_dict = {"id": 2,
                          lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE}
        list_oper_dict = {"id": 2,
                          lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        list_deleted_dict = {
            "id": 2, lib_consts.PROVISIONING_STATUS: lib_consts.DELETED,
            lib_consts.OPERATING_STATUS: lib_consts.ONLINE}

        # Test with full record
        self.driver_updater._process_status_update(mock_repo, 'FakeName',
                                                   list_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=lib_consts.ACTIVE,
            operating_status=lib_consts.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with only provisioning status record
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(mock_repo, 'FakeName',
                                                   list_prov_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=lib_consts.ACTIVE)
        mock_repo.delete.assert_not_called()

        # Test with only operating status record
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(mock_repo, 'FakeName',
                                                   list_oper_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, operating_status=lib_consts.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with deleted but delete_record False
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(mock_repo, 'FakeName',
                                                   list_deleted_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=lib_consts.DELETED,
            operating_status=lib_consts.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with an empty update
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(mock_repo, 'FakeName',
                                                   {"id": 2})
        mock_repo.update.assert_not_called()
        mock_repo.delete.assert_not_called()

        # Test with deleted and delete_record True
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(
            mock_repo, 'FakeName', list_deleted_dict, delete_record=True)
        mock_repo.delete.assert_called_once_with(self.mock_session, id=2)
        mock_repo.update.assert_not_called()

        # Test with LB Delete
        mock_repo.reset_mock()
        self.driver_updater._process_status_update(
            mock_repo, lib_consts.LOADBALANCERS, list_deleted_dict)
        mock_deallocate.assert_called_once_with(mock_repo, 2)

        # Test with an exception
        mock_repo.reset_mock()
        mock_repo.update.side_effect = Exception('boom')
        self.assertRaises(driver_exceptions.UpdateStatusError,
                          self.driver_updater._process_status_update,
                          mock_repo, 'FakeName', list_dict)

        # Test with no ID record
        mock_repo.reset_mock()
        self.assertRaises(driver_exceptions.UpdateStatusError,
                          self.driver_updater._process_status_update,
                          mock_repo, 'FakeName', {"fake": "data"})

    @mock.patch('octavia.api.drivers.driver_agent.driver_updater.'
                'DriverUpdater._process_status_update')
    def test_update_loadbalancer_status(self, mock_status_update):
        mock_status_update.side_effect = [
            mock.DEFAULT, mock.DEFAULT, mock.DEFAULT, mock.DEFAULT,
            mock.DEFAULT, mock.DEFAULT, mock.DEFAULT,
            driver_exceptions.UpdateStatusError(
                fault_string='boom', status_object='fruit',
                status_object_id='1', status_record='grape'),
            Exception('boom')]
        lb_dict = {"id": 1, lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                   lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        list_dict = {"id": 2,
                     lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                     lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        pool_dict = {"id": 3,
                     lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                     lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        member_dict = {"id": 4,
                       lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                       lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        hm_dict = {"id": 5, lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                   lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        l7p_dict = {"id": 6, lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                    lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        l7r_dict = {"id": 7, lib_consts.PROVISIONING_STATUS: lib_consts.ACTIVE,
                    lib_consts.OPERATING_STATUS: lib_consts.ONLINE}
        status_dict = {lib_consts.LOADBALANCERS: [lb_dict],
                       lib_consts.LISTENERS: [list_dict],
                       lib_consts.POOLS: [pool_dict],
                       lib_consts.MEMBERS: [member_dict],
                       lib_consts.HEALTHMONITORS: [hm_dict],
                       lib_consts.L7POLICIES: [l7p_dict],
                       lib_consts.L7RULES: [l7r_dict]}

        result = self.driver_updater.update_loadbalancer_status(
            copy.deepcopy(status_dict))

        calls = [call(self.mock_member_repo, lib_consts.MEMBERS, member_dict,
                      delete_record=True),
                 call(self.mock_health_repo, lib_consts.HEALTHMONITORS,
                      hm_dict, delete_record=True),
                 call(self.mock_pool_repo, lib_consts.POOLS, pool_dict,
                      delete_record=True),
                 call(self.mock_l7r_repo, lib_consts.L7RULES, l7r_dict,
                      delete_record=True),
                 call(self.mock_l7p_repo, lib_consts.L7POLICIES, l7p_dict,
                      delete_record=True),
                 call(self.mock_list_repo, lib_consts.LISTENERS, list_dict,
                      delete_record=True),
                 call(self.mock_lb_repo, lib_consts.LOADBALANCERS,
                      lb_dict)]
        mock_status_update.assert_has_calls(calls)
        self.assertEqual(self.ref_ok_response, result)

        # Test empty status updates
        mock_status_update.reset_mock()
        result = self.driver_updater.update_loadbalancer_status({})
        mock_status_update.assert_not_called()
        self.assertEqual(self.ref_ok_response, result)

        # Test UpdateStatusError case
        ref_update_status_error = {
            lib_consts.FAULT_STRING: 'boom',
            lib_consts.STATUS_CODE: lib_consts.DRVR_STATUS_CODE_FAILED,
            lib_consts.STATUS_OBJECT: 'fruit',
            lib_consts.STATUS_OBJECT_ID: '1'}
        result = self.driver_updater.update_loadbalancer_status(
            copy.deepcopy(status_dict))
        self.assertEqual(ref_update_status_error, result)

        # Test general exceptions
        result = self.driver_updater.update_loadbalancer_status(
            copy.deepcopy(status_dict))
        self.assertEqual({
            lib_consts.STATUS_CODE: lib_consts.DRVR_STATUS_CODE_FAILED,
            lib_consts.FAULT_STRING: 'boom'}, result)

    @mock.patch('octavia.db.repositories.ListenerStatisticsRepository.replace')
    def test_update_listener_statistics(self, mock_replace):
        listener_stats_list = [{"id": 1, "active_connections": 10,
                                         "bytes_in": 20,
                                         "bytes_out": 30,
                                         "request_errors": 40,
                                         "total_connections": 50},
                               {"id": 2, "active_connections": 60,
                                         "bytes_in": 70,
                                         "bytes_out": 80,
                                         "request_errors": 90,
                                         "total_connections": 100}]
        listener_stats_dict = {"listeners": listener_stats_list}

        mock_replace.side_effect = [mock.DEFAULT, mock.DEFAULT,
                                    Exception('boom')]
        result = self.driver_updater.update_listener_statistics(
            copy.deepcopy(listener_stats_dict))
        calls = [call(self.mock_session, 1, 1, active_connections=10,
                      bytes_in=20, bytes_out=30, request_errors=40,
                      total_connections=50),
                 call(self.mock_session, 2, 2, active_connections=60,
                      bytes_in=70, bytes_out=80, request_errors=90,
                      total_connections=100)]
        mock_replace.assert_has_calls(calls)
        self.assertEqual(self.ref_ok_response, result)

        # Test empty stats updates
        mock_replace.reset_mock()
        result = self.driver_updater.update_listener_statistics({})
        mock_replace.assert_not_called()
        self.assertEqual(self.ref_ok_response, result)

        # Test missing ID
        bad_id_dict = {"listeners": [{"notID": "one"}]}
        result = self.driver_updater.update_listener_statistics(bad_id_dict)
        ref_update_listener_stats_error = {
            lib_consts.STATUS_CODE: lib_consts.DRVR_STATUS_CODE_FAILED,
            lib_consts.STATS_OBJECT: lib_consts.LISTENERS,
            lib_consts.FAULT_STRING: "'id'"}
        self.assertEqual(ref_update_listener_stats_error, result)

        # Test for replace exception
        result = self.driver_updater.update_listener_statistics(
            copy.deepcopy(listener_stats_dict))
        ref_update_listener_stats_error = {
            lib_consts.STATUS_CODE: lib_consts.DRVR_STATUS_CODE_FAILED,
            lib_consts.STATS_OBJECT: lib_consts.LISTENERS,
            lib_consts.FAULT_STRING: 'boom', lib_consts.STATS_OBJECT_ID: 1}
        self.assertEqual(ref_update_listener_stats_error, result)
