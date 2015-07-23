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

from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.controller.worker.flows import load_balancer_flows
import octavia.tests.unit.base as base


class TestLoadBalancerFlows(base.TestCase):

    def setUp(self):
        self.LBFlow = load_balancer_flows.LoadBalancerFlows()

        super(TestLoadBalancerFlows, self).setUp()

    def test_get_create_load_balancer_flow(self):

        lb_flow = self.LBFlow.get_create_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, lb_flow.provides)
        self.assertIn(constants.AMPHORA_ID, lb_flow.provides)
        self.assertIn(constants.VIP, lb_flow.provides)
        self.assertIn(constants.AMPS_DATA, lb_flow.provides)
        self.assertIn(constants.LOADBALANCER, lb_flow.provides)

        self.assertIn(constants.LOADBALANCER_ID, lb_flow.requires)

        self.assertEqual(len(lb_flow.provides), 6)
        self.assertEqual(len(lb_flow.requires), 1)

    def test_get_delete_load_balancer_flow(self):

        lb_flow = self.LBFlow.get_delete_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn('loadbalancer', lb_flow.requires)

        self.assertEqual(len(lb_flow.provides), 0)
        self.assertEqual(len(lb_flow.requires), 1)

    def test_get_new_LB_networking_subflow(self):

        lb_flow = self.LBFlow.get_new_LB_networking_subflow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn(constants.VIP, lb_flow.provides)
        self.assertIn(constants.AMPS_DATA, lb_flow.provides)
        self.assertIn(constants.LOADBALANCER, lb_flow.provides)

        self.assertIn(constants.LOADBALANCER, lb_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, lb_flow.requires)

        self.assertEqual(len(lb_flow.provides), 4)
        self.assertEqual(len(lb_flow.requires), 2)

    def test_get_update_load_balancer_flow(self):

        lb_flow = self.LBFlow.get_update_load_balancer_flow()

        self.assertIsInstance(lb_flow, flow.Flow)

        self.assertIn('loadbalancer', lb_flow.requires)

        self.assertEqual(len(lb_flow.provides), 0)
        self.assertEqual(len(lb_flow.requires), 2)
