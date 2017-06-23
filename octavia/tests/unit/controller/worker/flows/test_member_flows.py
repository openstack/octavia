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

import mock
from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.controller.worker.flows import member_flows
import octavia.tests.unit.base as base


# NOTE: We patch the get_network_driver for all the calls so we don't
# inadvertently make real calls.
@mock.patch('octavia.common.utils.get_network_driver')
class TestMemberFlows(base.TestCase):

    def setUp(self):
        self.MemberFlow = member_flows.MemberFlows()

        super(TestMemberFlows, self).setUp()

    def test_get_create_member_flow(self, mock_get_net_driver):

        member_flow = self.MemberFlow.get_create_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn(constants.LISTENERS, member_flow.requires)
        self.assertIn(constants.LOADBALANCER, member_flow.requires)
        self.assertIn(constants.POOL, member_flow.requires)

        self.assertEqual(4, len(member_flow.requires))
        self.assertEqual(2, len(member_flow.provides))

    def test_get_delete_member_flow(self, mock_get_net_driver):

        member_flow = self.MemberFlow.get_delete_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn(constants.MEMBER, member_flow.requires)
        self.assertIn(constants.LISTENERS, member_flow.requires)
        self.assertIn(constants.LOADBALANCER, member_flow.requires)
        self.assertIn(constants.POOL, member_flow.requires)

        self.assertEqual(4, len(member_flow.requires))
        self.assertEqual(0, len(member_flow.provides))

    def test_get_update_member_flow(self, mock_get_net_driver):

        member_flow = self.MemberFlow.get_update_member_flow()

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn(constants.MEMBER, member_flow.requires)
        self.assertIn(constants.LISTENERS, member_flow.requires)
        self.assertIn(constants.LOADBALANCER, member_flow.requires)
        self.assertIn(constants.POOL, member_flow.requires)
        self.assertIn(constants.UPDATE_DICT, member_flow.requires)

        self.assertEqual(5, len(member_flow.requires))
        self.assertEqual(0, len(member_flow.provides))

    def test_get_batch_update_members_flow(self, mock_get_net_driver):

        member_flow = self.MemberFlow.get_batch_update_members_flow(
            [], [], [])

        self.assertIsInstance(member_flow, flow.Flow)

        self.assertIn(constants.LISTENERS, member_flow.requires)
        self.assertIn(constants.LOADBALANCER, member_flow.requires)
        self.assertIn(constants.POOL, member_flow.requires)

        self.assertEqual(3, len(member_flow.requires))
        self.assertEqual(2, len(member_flow.provides))
