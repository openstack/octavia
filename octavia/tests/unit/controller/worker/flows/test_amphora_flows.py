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
from octavia.controller.worker.flows import amphora_flows
import octavia.tests.unit.base as base

AUTH_VERSION = '2'


class TestAmphoraFlows(base.TestCase):

    def setUp(self):
        cfg.CONF.set_override('amphora_driver', 'amphora_haproxy_ssh_driver',
                              group='controller_worker')
        self.AmpFlow = amphora_flows.AmphoraFlows()
        conf = oslo_fixture.Config(cfg.CONF)
        conf.config(group="keystone_authtoken", auth_version=AUTH_VERSION)

        super(TestAmphoraFlows, self).setUp()

    def test_get_create_amphora_flow(self):

        amp_flow = self.AmpFlow.get_create_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)

        self.assertEqual(len(amp_flow.provides), 3)
        self.assertEqual(len(amp_flow.requires), 0)

    def test_get_create_amphora_flow_cert(self):
        cfg.CONF.set_override('amphora_driver', 'amphora_haproxy_rest_driver',
                              group='controller_worker')
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_create_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)

        self.assertEqual(len(amp_flow.provides), 4)
        self.assertEqual(len(amp_flow.requires), 0)

    def test_get_create_amphora_for_lb_flow(self):

        amp_flow = self.AmpFlow.get_create_amphora_for_lb_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)
        self.assertIn(constants.VIP, amp_flow.provides)
        self.assertIn(constants.AMPS_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

        self.assertEqual(len(amp_flow.provides), 8)
        self.assertEqual(len(amp_flow.requires), 1)

    def test_get_cert_create_amphora_for_lb_flow(self):
        cfg.CONF.set_override('amphora_driver', 'amphora_haproxy_rest_driver',
                              group='controller_worker')
        self.AmpFlow = amphora_flows.AmphoraFlows()
        amp_flow = self.AmpFlow.get_create_amphora_for_lb_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)
        self.assertIn(constants.VIP, amp_flow.provides)
        self.assertIn(constants.AMPS_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)

        self.assertEqual(len(amp_flow.provides), 9)
        self.assertEqual(len(amp_flow.requires), 1)

    def test_get_delete_amphora_flow(self):

        amp_flow = self.AmpFlow.get_delete_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)

        self.assertEqual(len(amp_flow.provides), 0)
        self.assertEqual(len(amp_flow.requires), 1)

    def test_get_failover_flow(self):

        amp_flow = self.AmpFlow.get_failover_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.FAILOVER_AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.AMPS_DATA, amp_flow.provides)
        self.assertIn(constants.PORTS, amp_flow.provides)
        self.assertIn(constants.LISTENERS, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(len(amp_flow.requires), 2)
        self.assertEqual(len(amp_flow.provides), 12)
