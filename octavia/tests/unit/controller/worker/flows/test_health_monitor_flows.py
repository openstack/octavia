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

from octavia.controller.worker.flows import health_monitor_flows
import octavia.tests.unit.base as base


class TestHealthMonitorFlows(base.TestCase):

    def setUp(self):
        self.HealthMonitorFlow = health_monitor_flows.HealthMonitorFlows()

        super(TestHealthMonitorFlows, self).setUp()

    def test_get_create_health_monitor_flow(self):

        health_mon_flow = (self.HealthMonitorFlow.
                           get_create_health_monitor_flow())

        self.assertIsInstance(health_mon_flow, flow.Flow)

        self.assertIn('listener', health_mon_flow.requires)
        self.assertIn('loadbalancer', health_mon_flow.requires)
        self.assertIn('vip', health_mon_flow.requires)

        self.assertEqual(len(health_mon_flow.requires), 3)
        self.assertEqual(len(health_mon_flow.provides), 0)

    def test_get_delete_health_monitor_flow(self):

        health_mon_flow = (self.HealthMonitorFlow.
                           get_delete_health_monitor_flow())

        self.assertIsInstance(health_mon_flow, flow.Flow)

        self.assertIn('health_mon', health_mon_flow.requires)
        self.assertIn('pool_id', health_mon_flow.requires)
        self.assertIn('listener', health_mon_flow.requires)
        self.assertIn('vip', health_mon_flow.requires)

        self.assertEqual(len(health_mon_flow.requires), 5)
        self.assertEqual(len(health_mon_flow.provides), 0)

    def test_get_update_health_monitor_flow(self):

        health_mon_flow = (self.HealthMonitorFlow.
                           get_update_health_monitor_flow())

        self.assertIsInstance(health_mon_flow, flow.Flow)

        self.assertIn('listener', health_mon_flow.requires)
        self.assertIn('loadbalancer', health_mon_flow.requires)
        self.assertIn('vip', health_mon_flow.requires)
        self.assertIn('health_mon', health_mon_flow.requires)
        self.assertIn('update_dict', health_mon_flow.requires)

        self.assertEqual(len(health_mon_flow.requires), 5)
        self.assertEqual(len(health_mon_flow.provides), 0)
