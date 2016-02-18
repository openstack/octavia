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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.common import exceptions
from octavia.controller.worker.flows import load_balancer_flows
import octavia.tests.unit.base as base


class TestLoadBalancerFlows(base.TestCase):

    def setUp(self):
        self.LBFlow = load_balancer_flows.LoadBalancerFlows()
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="nova", enable_anti_affinity=False)
        super(TestLoadBalancerFlows, self).setUp()

    def test_get_create_load_balancer_flow(self):
        amp_flow = self.LBFlow.get_create_load_balancer_flow(
            constants.TOPOLOGY_SINGLE)
        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

    def test_get_create_active_standby_load_balancer_flow(self):
        amp_flow = self.LBFlow.get_create_load_balancer_flow(
            constants.TOPOLOGY_ACTIVE_STANDBY)
        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

    def test_get_create_anti_affinity_active_standby_load_balancer_flow(self):
        cfg.CONF.set_override('enable_anti_affinity', True,
                              group='nova')
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

    def test_get_create_bogus_topology_load_balancer_flow(self):
        self.assertRaises(exceptions.InvalidTopology,
                          self.LBFlow.get_create_load_balancer_flow,
                          'BOGUS')

    def test_get_delete_load_balancer_flow(self):

        lb_flow = self.LBFlow.get_delete_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, lb_flow.requires)

        self.assertEqual(0, len(lb_flow.provides))
        self.assertEqual(2, len(lb_flow.requires))

    def test_get_new_LB_networking_subflow(self):

        lb_flow = self.LBFlow.get_new_LB_networking_subflow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.VIP, lb_flow.provides)
        self.assertIn(constants.AMPS_DATA, lb_flow.provides)
        self.assertIn(constants.LOADBALANCER, lb_flow.provides)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, lb_flow.requires)

        self.assertEqual(4, len(lb_flow.provides))
        self.assertEqual(2, len(lb_flow.requires))

    def test_get_update_load_balancer_flow(self):

        lb_flow = self.LBFlow.get_update_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)

        self.assertEqual(0, len(lb_flow.provides))
        self.assertEqual(2, len(lb_flow.requires))

    def test_get_post_lb_amp_association_flow(self):
        amp_flow = self.LBFlow.get_post_lb_amp_association_flow(
            '123', constants.TOPOLOGY_SINGLE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.UPDATE_DICT, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

        # Test Active/Standby path
        amp_flow = self.LBFlow.get_post_lb_amp_association_flow(
            '123', constants.TOPOLOGY_ACTIVE_STANDBY)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.UPDATE_DICT, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))
