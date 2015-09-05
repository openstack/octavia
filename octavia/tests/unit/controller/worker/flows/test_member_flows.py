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

from octavia.controller.worker.flows import member_flows
import octavia.tests.unit.base as base


class TestMemberFlows(base.TestCase):

    def setUp(self):
        self.MemberFlow = member_flows.MemberFlows()

        super(TestMemberFlows, self).setUp()

    def test_get_create_member_flow(self):

        member_flow = self.MemberFlow.get_create_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn('listener', member_flow.requires)
        self.assertIn('loadbalancer', member_flow.requires)
        self.assertIn('vip', member_flow.requires)

        self.assertEqual(len(member_flow.requires), 3)
        self.assertEqual(len(member_flow.provides), 2)

    def test_get_delete_member_flow(self):

        member_flow = self.MemberFlow.get_delete_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn('listener', member_flow.requires)
        self.assertIn('loadbalancer', member_flow.requires)
        self.assertIn('member', member_flow.requires)
        self.assertIn('member_id', member_flow.requires)
        self.assertIn('vip', member_flow.requires)

        self.assertEqual(len(member_flow.requires), 5)
        self.assertEqual(len(member_flow.provides), 0)

    def test_get_update_member_flow(self):

        member_flow = self.MemberFlow.get_update_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn('listener', member_flow.requires)
        self.assertIn('loadbalancer', member_flow.requires)
        self.assertIn('vip', member_flow.requires)
        self.assertIn('update_dict', member_flow.requires)

        self.assertEqual(len(member_flow.requires), 5)
        self.assertEqual(len(member_flow.provides), 0)
