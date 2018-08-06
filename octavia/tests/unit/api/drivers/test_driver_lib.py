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

import mock
from mock import call

from octavia.api.drivers import driver_lib
from octavia.api.drivers import exceptions as driver_exceptions
from octavia.common import constants
from octavia.tests.unit import base


class TestDriverLib(base.TestCase):
    @mock.patch('octavia.db.repositories.L7RuleRepository')
    @mock.patch('octavia.db.repositories.L7PolicyRepository')
    @mock.patch('octavia.db.repositories.HealthMonitorRepository')
    @mock.patch('octavia.db.repositories.MemberRepository')
    @mock.patch('octavia.db.repositories.PoolRepository')
    @mock.patch('octavia.db.repositories.ListenerRepository')
    @mock.patch('octavia.db.repositories.LoadBalancerRepository')
    @mock.patch('octavia.db.api.get_session')
    def setUp(self, mock_get_session, mock_lb_repo, mock_list_repo,
              mock_pool_repo, mock_member_repo, mock_health_repo,
              mock_l7p_repo, mock_l7r_repo):
        super(TestDriverLib, self).setUp()
        self.mock_session = "FAKE_DB_SESSION"
        mock_get_session.return_value = self.mock_session
        lb_mock = mock.MagicMock()
        mock_lb_repo.return_value = lb_mock
        self.mock_lb_repo = lb_mock
        list_mock = mock.MagicMock()
        mock_list_repo.return_value = list_mock
        self.mock_list_repo = list_mock
        pool_mock = mock.MagicMock()
        mock_pool_repo.return_value = pool_mock
        self.mock_pool_repo = pool_mock
        member_mock = mock.MagicMock()
        mock_member_repo.return_value = member_mock
        self.mock_member_repo = member_mock
        health_mock = mock.MagicMock()
        mock_health_repo.return_value = health_mock
        self.mock_health_repo = health_mock
        l7p_mock = mock.MagicMock()
        mock_l7p_repo.return_value = l7p_mock
        self.mock_l7p_repo = l7p_mock
        l7r_mock = mock.MagicMock()
        mock_l7r_repo.return_value = l7r_mock
        self.mock_l7r_repo = l7r_mock
        self.driver_lib = driver_lib.DriverLibrary()
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
        self.listener_stats_dict = {"listeners": listener_stats_list}

    @mock.patch('octavia.common.utils.get_network_driver')
    def test_check_for_lb_vip_deallocate(self, mock_get_driver):
        mock_repo = mock.MagicMock()
        mock_lb = mock.MagicMock()

        # Test VIP not owned by Octavia
        mock_lb.vip.octavia_owned = False
        mock_repo.get.return_value = mock_lb
        self.driver_lib._check_for_lb_vip_deallocate(mock_repo, 4)
        mock_get_driver.assert_not_called()

        # Test VIP is owned by Octavia
        mock_lb.vip.octavia_owned = True
        mock_repo.get.return_value = mock_lb
        mock_net_driver = mock.MagicMock()
        mock_get_driver.return_value = mock_net_driver
        self.driver_lib._check_for_lb_vip_deallocate(mock_repo, 4)
        mock_net_driver.deallocate_vip.assert_called_once_with(mock_lb.vip)

    @mock.patch('octavia.api.drivers.driver_lib.DriverLibrary.'
                '_check_for_lb_vip_deallocate')
    def test_process_status_update(self, mock_deallocate):
        mock_repo = mock.MagicMock()
        list_dict = {"id": 2, constants.PROVISIONING_STATUS: constants.ACTIVE,
                     constants.OPERATING_STATUS: constants.ONLINE}
        list_prov_dict = {"id": 2,
                          constants.PROVISIONING_STATUS: constants.ACTIVE}
        list_oper_dict = {"id": 2,
                          constants.OPERATING_STATUS: constants.ONLINE}
        list_deleted_dict = {
            "id": 2, constants.PROVISIONING_STATUS: constants.DELETED,
            constants.OPERATING_STATUS: constants.ONLINE}

        # Test with full record
        self.driver_lib._process_status_update(mock_repo, 'FakeName',
                                               list_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=constants.ACTIVE,
            operating_status=constants.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with only provisioning status record
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(mock_repo, 'FakeName',
                                               list_prov_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=constants.ACTIVE)
        mock_repo.delete.assert_not_called()

        # Test with only operating status record
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(mock_repo, 'FakeName',
                                               list_oper_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, operating_status=constants.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with deleted but delete_record False
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(mock_repo, 'FakeName',
                                               list_deleted_dict)
        mock_repo.update.assert_called_once_with(
            self.mock_session, 2, provisioning_status=constants.DELETED,
            operating_status=constants.ONLINE)
        mock_repo.delete.assert_not_called()

        # Test with an empty update
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(mock_repo, 'FakeName',
                                               {"id": 2})
        mock_repo.update.assert_not_called()
        mock_repo.delete.assert_not_called()

        # Test with deleted and delete_record True
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(
            mock_repo, 'FakeName', list_deleted_dict, delete_record=True)
        mock_repo.delete.assert_called_once_with(self.mock_session, id=2)
        mock_repo.update.assert_not_called()

        # Test with LB Delete
        mock_repo.reset_mock()
        self.driver_lib._process_status_update(
            mock_repo, constants.LOADBALANCERS, list_deleted_dict)
        mock_deallocate.assert_called_once_with(mock_repo, 2)

        # Test with an exception
        mock_repo.reset_mock()
        mock_repo.update.side_effect = Exception('boom')
        self.assertRaises(driver_exceptions.UpdateStatusError,
                          self.driver_lib._process_status_update,
                          mock_repo, 'FakeName', list_dict)

        # Test with no ID record
        mock_repo.reset_mock()
        self.assertRaises(driver_exceptions.UpdateStatusError,
                          self.driver_lib._process_status_update,
                          mock_repo, 'FakeName', {"fake": "data"})

    @mock.patch(
        'octavia.api.drivers.driver_lib.DriverLibrary._process_status_update')
    def test_update_loadbalancer_status(self, mock_status_update):
        lb_dict = {"id": 1, constants.PROVISIONING_STATUS: constants.ACTIVE,
                   constants.OPERATING_STATUS: constants.ONLINE}
        list_dict = {"id": 2, constants.PROVISIONING_STATUS: constants.ACTIVE,
                     constants.OPERATING_STATUS: constants.ONLINE}
        pool_dict = {"id": 3, constants.PROVISIONING_STATUS: constants.ACTIVE,
                     constants.OPERATING_STATUS: constants.ONLINE}
        member_dict = {"id": 4,
                       constants.PROVISIONING_STATUS: constants.ACTIVE,
                       constants.OPERATING_STATUS: constants.ONLINE}
        hm_dict = {"id": 5, constants.PROVISIONING_STATUS: constants.ACTIVE,
                   constants.OPERATING_STATUS: constants.ONLINE}
        l7p_dict = {"id": 6, constants.PROVISIONING_STATUS: constants.ACTIVE,
                    constants.OPERATING_STATUS: constants.ONLINE}
        l7r_dict = {"id": 7, constants.PROVISIONING_STATUS: constants.ACTIVE,
                    constants.OPERATING_STATUS: constants.ONLINE}
        status_dict = {constants.LOADBALANCERS: [lb_dict],
                       constants.LISTENERS: [list_dict],
                       constants.POOLS: [pool_dict],
                       constants.MEMBERS: [member_dict],
                       constants.HEALTHMONITORS: [hm_dict],
                       constants.L7POLICIES: [l7p_dict],
                       constants.L7RULES: [l7r_dict]}

        self.driver_lib.update_loadbalancer_status(status_dict)

        calls = [call(self.mock_member_repo, constants.MEMBERS, member_dict,
                      delete_record=True),
                 call(self.mock_health_repo, constants.HEALTHMONITORS,
                      hm_dict, delete_record=True),
                 call(self.mock_pool_repo, constants.POOLS, pool_dict,
                      delete_record=True),
                 call(self.mock_l7r_repo, constants.L7RULES, l7r_dict,
                      delete_record=True),
                 call(self.mock_l7p_repo, constants.L7POLICIES, l7p_dict,
                      delete_record=True),
                 call(self.mock_list_repo, constants.LISTENERS, list_dict,
                      delete_record=True),
                 call(self.mock_lb_repo, constants.LOADBALANCERS,
                      lb_dict)]
        mock_status_update.assert_has_calls(calls)

        mock_status_update.reset_mock()
        self.driver_lib.update_loadbalancer_status({})
        mock_status_update.assert_not_called()

    @mock.patch('octavia.db.repositories.ListenerStatisticsRepository.replace')
    def test_update_listener_statistics(self, mock_replace):
        self.driver_lib.update_listener_statistics(self.listener_stats_dict)
        calls = [call(self.mock_session, 1, 1, active_connections=10,
                      bytes_in=20, bytes_out=30, request_errors=40,
                      total_connections=50),
                 call(self.mock_session, 2, 2, active_connections=60,
                      bytes_in=70, bytes_out=80, request_errors=90,
                      total_connections=100)]
        mock_replace.assert_has_calls(calls)

        mock_replace.reset_mock()
        self.driver_lib.update_listener_statistics({})
        mock_replace.assert_not_called()

        # Test missing ID
        bad_id_dict = {"listeners": [{"notID": "one"}]}
        self.assertRaises(driver_exceptions.UpdateStatisticsError,
                          self.driver_lib.update_listener_statistics,
                          bad_id_dict)

    # Coverage doesn't like this test as part of the above test
    # So, broke it out in it's own test
    @mock.patch('octavia.db.repositories.ListenerStatisticsRepository.replace')
    def test_update_listener_statistics_exception(self, mock_replace):

        # Test stats exception
        mock_replace.side_effect = Exception('boom')
        self.assertRaises(driver_exceptions.UpdateStatisticsError,
                          self.driver_lib.update_listener_statistics,
                          self.listener_stats_dict)
