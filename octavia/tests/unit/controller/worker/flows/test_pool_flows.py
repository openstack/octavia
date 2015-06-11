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

from octavia.controller.worker.flows import pool_flows
import octavia.tests.unit.base as base


class TestPoolFlows(base.TestCase):

    def setUp(self):
        self.PoolFlow = pool_flows.PoolFlows()

        super(TestPoolFlows, self).setUp()

    def test_get_create_pool_flow(self):

        pool_flow = self.PoolFlow.get_create_pool_flow()

        self.assertIsInstance(pool_flow, flow.Flow)

        self.assertIn('listener', pool_flow.requires)
        self.assertIn('loadbalancer', pool_flow.requires)
        self.assertIn('vip', pool_flow.requires)

        self.assertEqual(len(pool_flow.requires), 3)
        self.assertEqual(len(pool_flow.provides), 0)

    def test_get_delete_pool_flow(self):

        pool_flow = self.PoolFlow.get_delete_pool_flow()

        self.assertIsInstance(pool_flow, flow.Flow)

        self.assertIn('listener', pool_flow.requires)
        self.assertIn('loadbalancer', pool_flow.requires)
        self.assertIn('vip', pool_flow.requires)
        self.assertIn('pool', pool_flow.requires)

        self.assertEqual(len(pool_flow.requires), 4)
        self.assertEqual(len(pool_flow.provides), 0)

    def test_get_update_pool_flow(self):

        pool_flow = self.PoolFlow.get_update_pool_flow()

        self.assertIsInstance(pool_flow, flow.Flow)

        self.assertIn('pool', pool_flow.requires)
        self.assertIn('listener', pool_flow.requires)
        self.assertIn('loadbalancer', pool_flow.requires)
        self.assertIn('vip', pool_flow.requires)
        self.assertIn('update_dict', pool_flow.requires)

        self.assertEqual(len(pool_flow.requires), 5)
        self.assertEqual(len(pool_flow.provides), 0)
