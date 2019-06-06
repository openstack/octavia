# Copyright 2016 Blue Box, an IBM Company
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
from octavia.controller.worker.v1.flows import l7rule_flows
import octavia.tests.unit.base as base


class TestL7RuleFlows(base.TestCase):

    def setUp(self):
        self.L7RuleFlow = l7rule_flows.L7RuleFlows()

        super(TestL7RuleFlows, self).setUp()

    def test_get_create_l7rule_flow(self):

        l7rule_flow = self.L7RuleFlow.get_create_l7rule_flow()

        self.assertIsInstance(l7rule_flow, flow.Flow)

        self.assertIn(constants.LISTENERS, l7rule_flow.requires)
        self.assertIn(constants.LOADBALANCER, l7rule_flow.requires)

        self.assertEqual(4, len(l7rule_flow.requires))
        self.assertEqual(0, len(l7rule_flow.provides))

    def test_get_delete_l7rule_flow(self):

        l7rule_flow = self.L7RuleFlow.get_delete_l7rule_flow()

        self.assertIsInstance(l7rule_flow, flow.Flow)

        self.assertIn(constants.LISTENERS, l7rule_flow.requires)
        self.assertIn(constants.LOADBALANCER, l7rule_flow.requires)
        self.assertIn(constants.L7RULE, l7rule_flow.requires)

        self.assertEqual(4, len(l7rule_flow.requires))
        self.assertEqual(0, len(l7rule_flow.provides))

    def test_get_update_l7rule_flow(self):

        l7rule_flow = self.L7RuleFlow.get_update_l7rule_flow()

        self.assertIsInstance(l7rule_flow, flow.Flow)

        self.assertIn(constants.L7RULE, l7rule_flow.requires)
        self.assertIn(constants.LISTENERS, l7rule_flow.requires)
        self.assertIn(constants.LOADBALANCER, l7rule_flow.requires)
        self.assertIn(constants.UPDATE_DICT, l7rule_flow.requires)

        self.assertEqual(5, len(l7rule_flow.requires))
        self.assertEqual(0, len(l7rule_flow.provides))
