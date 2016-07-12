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
from octavia.controller.worker.flows import listener_flows
import octavia.tests.unit.base as base


# NOTE: We patch the get_network_driver for all the calls so we don't
# inadvertently make real calls.
@mock.patch('octavia.common.utils.get_network_driver')
class TestListenerFlows(base.TestCase):

    def setUp(self):
        self.ListenerFlow = listener_flows.ListenerFlows()

        super(TestListenerFlows, self).setUp()

    def test_get_create_listener_flow(self, mock_get_net_driver):

        listener_flow = self.ListenerFlow.get_create_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, listener_flow.requires)
        self.assertIn(constants.LISTENERS, listener_flow.requires)

        self.assertEqual(2, len(listener_flow.requires))
        self.assertEqual(0, len(listener_flow.provides))

    def test_get_delete_listener_flow(self, mock_get_net_driver):

        listener_flow = self.ListenerFlow.get_delete_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn(constants.LISTENER, listener_flow.requires)
        self.assertIn(constants.LOADBALANCER, listener_flow.requires)

        self.assertEqual(2, len(listener_flow.requires))
        self.assertEqual(0, len(listener_flow.provides))

    def test_get_delete_listener_internal_flow(self, mock_get_net_driver):
        listener_flow = self.ListenerFlow.get_delete_listener_internal_flow(
            'test-listener')

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn('test-listener', listener_flow.requires)
        self.assertIn(constants.LOADBALANCER, listener_flow.requires)

        self.assertEqual(2, len(listener_flow.requires))
        self.assertEqual(0, len(listener_flow.provides))

    def test_get_update_listener_flow(self, mock_get_net_driver):

        listener_flow = self.ListenerFlow.get_update_listener_flow()

        self.assertIsInstance(listener_flow, flow.Flow)

        self.assertIn(constants.LISTENER, listener_flow.requires)
        self.assertIn(constants.LOADBALANCER, listener_flow.requires)
        self.assertIn(constants.UPDATE_DICT, listener_flow.requires)
        self.assertIn(constants.LISTENERS, listener_flow.requires)

        self.assertEqual(4, len(listener_flow.requires))
        self.assertEqual(0, len(listener_flow.provides))

    def test_get_create_all_listeners_flow(self, mock_get_net_driver):
        listeners_flow = self.ListenerFlow.get_create_all_listeners_flow()
        self.assertIsInstance(listeners_flow, flow.Flow)
        self.assertIn(constants.LOADBALANCER, listeners_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, listeners_flow.requires)
        self.assertIn(constants.LOADBALANCER, listeners_flow.provides)
        self.assertEqual(2, len(listeners_flow.requires))
        self.assertEqual(2, len(listeners_flow.provides))
