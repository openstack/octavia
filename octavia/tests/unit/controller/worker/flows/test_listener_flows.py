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

from octavia.controller.worker.flows import listener_flows
import octavia.tests.unit.base as base


class TestListenerFlows(base.TestCase):

    def setUp(self):
        self.ListenerFlow = listener_flows.ListenerFlows()

        super(TestListenerFlows, self).setUp()

    def test_get_create_listener_flow(self):

        listener_flow = self.ListenerFlow.get_create_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn('listener', listener_flow.requires)
        self.assertIn('loadbalancer', listener_flow.requires)
        self.assertIn('vip', listener_flow.requires)

        self.assertEqual(len(listener_flow.requires), 3)
        self.assertEqual(len(listener_flow.provides), 0)

    def test_get_delete_listener_flow(self):

        listener_flow = self.ListenerFlow.get_delete_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn('listener', listener_flow.requires)
        self.assertIn('loadbalancer', listener_flow.requires)
        self.assertIn('vip', listener_flow.requires)

        self.assertEqual(len(listener_flow.requires), 3)
        self.assertEqual(len(listener_flow.provides), 0)

    def test_get_update_listener_flow(self):

        listener_flow = self.ListenerFlow.get_update_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn('listener', listener_flow.requires)
        self.assertIn('loadbalancer', listener_flow.requires)
        self.assertIn('vip', listener_flow.requires)
        self.assertIn('update_dict', listener_flow.requires)

        self.assertEqual(len(listener_flow.requires), 4)
        self.assertEqual(len(listener_flow.provides), 0)
