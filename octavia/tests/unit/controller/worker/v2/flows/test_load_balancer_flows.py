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
from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.v2.flows import flow_utils
from octavia.controller.worker.v2.flows import load_balancer_flows
import octavia.tests.unit.base as base


class MockNOTIFIER(mock.MagicMock):
    info = mock.MagicMock()


# NOTE: We patch the get_network_driver for all the calls so we don't
# inadvertently make real calls.
@mock.patch('octavia.common.utils.get_network_driver')
class TestLoadBalancerFlows(base.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group="controller_worker",
            amphora_driver='amphora_haproxy_rest_driver')
        self.conf.config(group="nova", enable_anti_affinity=False)
        self.LBFlow = load_balancer_flows.LoadBalancerFlows()

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_load_balancer_flow(self, mock_get_net_driver,
                                           mock_notifier):
        amp_flow = self.LBFlow.get_create_load_balancer_flow(
            constants.TOPOLOGY_SINGLE)
        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_active_standby_load_balancer_flow(
            self, mock_get_net_driver, mock_notifier):
        amp_flow = self.LBFlow.get_create_load_balancer_flow(
            constants.TOPOLOGY_ACTIVE_STANDBY)
        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_anti_affinity_active_standby_load_balancer_flow(
            self, mock_get_net_driver, mock_notifier):
        self.conf.config(group="nova", enable_anti_affinity=True)

        self._LBFlow = load_balancer_flows.LoadBalancerFlows()
        amp_flow = self._LBFlow.get_create_load_balancer_flow(
            constants.TOPOLOGY_ACTIVE_STANDBY)
        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.conf.config(group="nova", enable_anti_affinity=False)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_bogus_topology_load_balancer_flow(
            self, mock_get_net_driver, mock_notifier):
        self.assertRaises(exceptions.InvalidTopology,
                          self.LBFlow.get_create_load_balancer_flow,
                          'BOGUS')

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_delete_load_balancer_flow(self, mock_get_net_driver,
                                           mock_notifier):
        lb_mock = mock.Mock()
        listener_mock = mock.Mock()
        listener_mock.id = '123'
        lb_mock.listeners = [listener_mock]

        lb_flow = self.LBFlow.get_delete_load_balancer_flow(lb_mock)

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, lb_flow.requires)
        self.assertIn(constants.PROJECT_ID, lb_flow.requires)

        self.assertEqual(0, len(lb_flow.provides))
        self.assertEqual(3, len(lb_flow.requires))

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    @mock.patch('octavia.db.repositories.LoadBalancerRepository.get')
    @mock.patch('octavia.db.api.get_session', return_value=mock.MagicMock())
    def test_get_delete_load_balancer_flow_cascade(self, mock_session,
                                                   mock_get_lb,
                                                   mock_get_net_driver,
                                                   mock_notifier):
        lb_mock = mock.Mock()
        listener_mock = mock.Mock()
        listener_mock.id = '123'
        listener_mock.to_dict.return_value = {'id': '123'}
        lb_mock.listeners = [listener_mock]
        lb_mock.id = '321'
        lb_mock.project_id = '876'
        pool_mock = mock.Mock()
        pool_mock.id = '345'
        pool_mock.to_dict.return_value = {constants.ID: pool_mock.id}
        pool_mock.listeners = None
        pool_mock.health_monitor = None
        pool_mock.members = None
        lb_mock.pools = [pool_mock]
        l7_mock = mock.Mock()
        l7_mock.id = '678'
        listener_mock.l7policies = [l7_mock]
        mock_get_lb.return_value = lb_mock
        lb_dict = {constants.LOADBALANCER_ID: lb_mock.id}

        listeners = flow_utils.get_listeners_on_lb(lb_mock)
        pools = flow_utils.get_pools_on_lb(lb_mock)

        lb_flow = self.LBFlow.get_cascade_delete_load_balancer_flow(
            lb_dict, listeners, pools)

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, lb_flow.requires)
        self.assertIn(constants.PROJECT_ID, lb_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, lb_flow.requires)

        self.assertEqual(1, len(lb_flow.provides))
        self.assertEqual(4, len(lb_flow.requires))

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_update_load_balancer_flow(self, mock_get_net_driver,
                                           mock_notifier):

        lb_flow = self.LBFlow.get_update_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.UPDATE_DICT, lb_flow.requires)

        self.assertEqual(0, len(lb_flow.provides))
        self.assertEqual(3, len(lb_flow.requires))

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_post_lb_amp_association_flow(self, mock_get_net_driver,
                                              mock_notifier):
        amp_flow = self.LBFlow.get_post_lb_amp_association_flow(
            '123', constants.TOPOLOGY_SINGLE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.UPDATE_DICT, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(1, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

        # Test Active/Standby path
        amp_flow = self.LBFlow.get_post_lb_amp_association_flow(
            '123', constants.TOPOLOGY_ACTIVE_STANDBY)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.UPDATE_DICT, amp_flow.requires)

        self.assertIn(constants.AMPHORAE, amp_flow.provides)
        self.assertIn(constants.AMP_VRRP_INT, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(2, len(amp_flow.requires), amp_flow.requires)
        self.assertEqual(4, len(amp_flow.provides), amp_flow.provides)

        amp_flow = self.LBFlow.get_post_lb_amp_association_flow(
            '123', constants.TOPOLOGY_ACTIVE_STANDBY)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.UPDATE_DICT, amp_flow.requires)

        self.assertIn(constants.AMPHORAE, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.AMP_VRRP_INT, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(2, len(amp_flow.requires), amp_flow.requires)
        self.assertEqual(4, len(amp_flow.provides), amp_flow.provides)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_load_balancer_flows_single_listeners(
            self, mock_get_net_driver, mock_notifier):
        create_flow = (
            self.LBFlow.get_create_load_balancer_flow(
                constants.TOPOLOGY_SINGLE, True
            )
        )
        self.assertIsInstance(create_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, create_flow.requires)
        self.assertIn(constants.UPDATE_DICT, create_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, create_flow.requires)
        self.assertIn(constants.FLAVOR, create_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, create_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, create_flow.requires)

        self.assertIn(constants.LISTENERS, create_flow.provides)
        self.assertIn(constants.SUBNET, create_flow.provides)
        self.assertIn(constants.AMPHORA, create_flow.provides)
        self.assertIn(constants.AMPHORA_ID, create_flow.provides)
        self.assertIn(constants.AMPHORA_NETWORK_CONFIG, create_flow.provides)
        self.assertIn(constants.AMP_DATA, create_flow.provides)
        self.assertIn(constants.COMPUTE_ID, create_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, create_flow.provides)
        self.assertIn(constants.LOADBALANCER, create_flow.provides)
        self.assertIn(constants.DELTAS, create_flow.provides)
        self.assertIn(constants.UPDATED_PORTS, create_flow.provides)
        self.assertIn(constants.SERVER_PEM, create_flow.provides)
        self.assertIn(constants.VIP, create_flow.provides)
        self.assertIn(constants.ADDITIONAL_VIPS, create_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, create_flow.provides)

        self.assertEqual(6, len(create_flow.requires))
        self.assertEqual(15, len(create_flow.provides))

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_create_load_balancer_flows_active_standby_listeners(
            self, mock_get_net_driver, mock_notifier):
        create_flow = (
            self.LBFlow.get_create_load_balancer_flow(
                constants.TOPOLOGY_ACTIVE_STANDBY, True
            )
        )
        self.assertIsInstance(create_flow, flow.Flow)
        self.assertIn(constants.AVAILABILITY_ZONE, create_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, create_flow.requires)
        self.assertIn(constants.FLAVOR, create_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, create_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, create_flow.requires)
        self.assertIn(constants.UPDATE_DICT, create_flow.requires)

        self.assertIn(constants.UPDATED_PORTS, create_flow.provides)
        self.assertIn(constants.AMP_DATA, create_flow.provides)
        self.assertIn(constants.AMP_VRRP_INT, create_flow.provides)
        self.assertIn(constants.AMPHORA, create_flow.provides)
        self.assertIn(constants.AMPHORAE, create_flow.provides)
        self.assertIn(constants.AMPHORA_ID, create_flow.provides)
        self.assertIn(constants.AMPHORA_NETWORK_CONFIG, create_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, create_flow.provides)
        self.assertIn(constants.COMPUTE_ID, create_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, create_flow.provides)
        self.assertIn(constants.DELTAS, create_flow.provides)
        self.assertIn(constants.LOADBALANCER, create_flow.provides)
        self.assertIn(constants.LISTENERS, create_flow.provides)
        self.assertIn(constants.SERVER_PEM, create_flow.provides)
        self.assertIn(constants.SUBNET, create_flow.provides)
        self.assertIn(constants.VIP, create_flow.provides)
        self.assertIn(constants.ADDITIONAL_VIPS, create_flow.provides)

        self.assertEqual(6, len(create_flow.requires), create_flow.requires)
        self.assertEqual(17, len(create_flow.provides),
                         create_flow.provides)

    def _test_get_failover_LB_flow_single(self, amphorae):
        lb_mock = mock.MagicMock()
        lb_mock.id = uuidutils.generate_uuid()
        lb_mock.topology = constants.TOPOLOGY_SINGLE

        failover_flow = self.LBFlow.get_failover_LB_flow(amphorae, lb_mock)

        self.assertIsInstance(failover_flow, flow.Flow)

        self.assertIn(constants.AVAILABILITY_ZONE, failover_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, failover_flow.requires)
        self.assertIn(constants.FLAVOR, failover_flow.requires)
        self.assertIn(constants.LOADBALANCER, failover_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, failover_flow.requires)

        self.assertIn(constants.UPDATED_PORTS, failover_flow.provides)
        self.assertIn(constants.AMPHORA, failover_flow.provides)
        self.assertIn(constants.AMPHORA_ID, failover_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG,
                      failover_flow.provides)
        self.assertIn(constants.BASE_PORT, failover_flow.provides)
        self.assertIn(constants.COMPUTE_ID, failover_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, failover_flow.provides)
        self.assertIn(constants.DELTA, failover_flow.provides)
        self.assertIn(constants.LOADBALANCER, failover_flow.provides)
        self.assertIn(constants.SERVER_PEM, failover_flow.provides)
        self.assertIn(constants.VIP, failover_flow.provides)
        self.assertIn(constants.ADDITIONAL_VIPS, failover_flow.provides)
        self.assertIn(constants.VIP_SG_ID, failover_flow.provides)

        self.assertEqual(6, len(failover_flow.requires),
                         failover_flow.requires)
        self.assertEqual(13, len(failover_flow.provides),
                         failover_flow.provides)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_no_amps_single(self, mock_get_net_driver,
                                                 mock_notifier):
        self._test_get_failover_LB_flow_single([])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_one_amp_single(self, mock_get_net_driver,
                                                 mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: constants.ROLE_STANDALONE,
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: None, constants.VRRP_IP: None}

        self._test_get_failover_LB_flow_single([amphora_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_one_bogus_amp_single(self,
                                                       mock_get_net_driver,
                                                       mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: 'bogus',
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: None, constants.VRRP_IP: None}

        self._test_get_failover_LB_flow_single([amphora_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_two_amp_single(self, mock_get_net_driver,
                                                 mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid()}
        amphora2_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: constants.ROLE_STANDALONE,
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: None, constants.VRRP_IP: None}

        self._test_get_failover_LB_flow_single([amphora_dict, amphora2_dict])

    def _test_get_failover_LB_flow_no_amps_act_stdby(self, amphorae):
        lb_mock = mock.MagicMock()
        lb_mock.id = uuidutils.generate_uuid()
        lb_mock.topology = constants.TOPOLOGY_ACTIVE_STANDBY

        failover_flow = self.LBFlow.get_failover_LB_flow(amphorae, lb_mock)

        self.assertIsInstance(failover_flow, flow.Flow)

        self.assertIn(constants.AVAILABILITY_ZONE, failover_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, failover_flow.requires)
        self.assertIn(constants.FLAVOR, failover_flow.requires)
        self.assertIn(constants.LOADBALANCER, failover_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, failover_flow.requires)

        self.assertIn(constants.UPDATED_PORTS, failover_flow.provides)
        self.assertIn(constants.AMPHORA, failover_flow.provides)
        self.assertIn(constants.AMPHORA_ID, failover_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG,
                      failover_flow.provides)
        self.assertIn(constants.BASE_PORT, failover_flow.provides)
        self.assertIn(constants.COMPUTE_ID, failover_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, failover_flow.provides)
        self.assertIn(constants.DELTA, failover_flow.provides)
        self.assertIn(constants.LOADBALANCER, failover_flow.provides)
        self.assertIn(constants.SERVER_PEM, failover_flow.provides)
        self.assertIn(constants.VIP, failover_flow.provides)
        self.assertIn(constants.ADDITIONAL_VIPS, failover_flow.provides)
        self.assertIn(constants.VIP_SG_ID, failover_flow.provides)

        self.assertEqual(6, len(failover_flow.requires),
                         failover_flow.requires)
        self.assertEqual(13, len(failover_flow.provides),
                         failover_flow.provides)

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_no_amps_act_stdby(self, mock_get_net_driver,
                                                    mock_notifier):
        self._test_get_failover_LB_flow_no_amps_act_stdby([])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_one_amps_act_stdby(self, amphorae,
                                                     mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: constants.ROLE_MASTER,
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: None, constants.VRRP_IP: None}

        self._test_get_failover_LB_flow_no_amps_act_stdby([amphora_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_two_amps_act_stdby(self,
                                                     mock_get_net_driver,
                                                     mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: constants.ROLE_MASTER,
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                        constants.VRRP_IP: '192.0.2.46'}
        amphora2_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: constants.ROLE_BACKUP,
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                         constants.VRRP_IP: '2001:db8::46'}

        self._test_get_failover_LB_flow_no_amps_act_stdby([amphora_dict,
                                                           amphora2_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_three_amps_act_stdby(self,
                                                       mock_get_net_driver,
                                                       mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: constants.ROLE_MASTER,
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                        constants.VRRP_IP: '192.0.2.46'}
        amphora2_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: constants.ROLE_BACKUP,
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                         constants.VRRP_IP: '2001:db8::46'}
        amphora3_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: 'bogus',
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: None, constants.VRRP_IP: None}

        self._test_get_failover_LB_flow_no_amps_act_stdby(
            [amphora_dict, amphora2_dict, amphora3_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_two_amps_bogus_act_stdby(
            self, mock_get_net_driver, mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: 'bogus',
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                        constants.VRRP_IP: '192.0.2.46'}
        amphora2_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: constants.ROLE_MASTER,
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                         constants.VRRP_IP: '2001:db8::46'}

        self._test_get_failover_LB_flow_no_amps_act_stdby([amphora_dict,
                                                           amphora2_dict])

    @mock.patch('octavia.common.rpc.NOTIFIER',
                new_callable=MockNOTIFIER)
    def test_get_failover_LB_flow_two_amps_standalone_act_stdby(
            self, mock_get_net_driver, mock_notifier):
        amphora_dict = {constants.ID: uuidutils.generate_uuid(),
                        constants.ROLE: constants.ROLE_STANDALONE,
                        constants.COMPUTE_ID: uuidutils.generate_uuid(),
                        constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                        constants.VRRP_IP: '192.0.2.46'}

        amphora2_dict = {constants.ID: uuidutils.generate_uuid(),
                         constants.ROLE: constants.ROLE_MASTER,
                         constants.COMPUTE_ID: uuidutils.generate_uuid(),
                         constants.VRRP_PORT_ID: uuidutils.generate_uuid(),
                         constants.VRRP_IP: '2001:db8::46'}

        self._test_get_failover_LB_flow_no_amps_act_stdby([amphora_dict,
                                                           amphora2_dict])
