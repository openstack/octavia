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
from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.common import data_models
from octavia.controller.worker.v1.flows import amphora_flows
import octavia.tests.unit.base as base

AUTH_VERSION = '2'


# NOTE: We patch the get_network_driver for all the calls so we don't
# inadvertently make real calls.
@mock.patch('octavia.common.utils.get_network_driver')
class TestAmphoraFlows(base.TestCase):

    def setUp(self):
        super(TestAmphoraFlows, self).setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group="controller_worker",
            amphora_driver='amphora_haproxy_rest_driver')
        self.conf.config(group="nova", enable_anti_affinity=False)
        self.AmpFlow = amphora_flows.AmphoraFlows()
        self.amp1 = data_models.Amphora(id=1)
        self.amp2 = data_models.Amphora(id=2)
        self.amp3 = data_models.Amphora(id=3, status=constants.DELETED)
        self.lb = data_models.LoadBalancer(
            id=4, amphorae=[self.amp1, self.amp2, self.amp3])

    def test_get_create_amphora_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_create_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

    def test_get_create_amphora_flow_cert(self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_create_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

    def test_get_create_amphora_for_lb_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_STANDALONE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(3, len(amp_flow.requires))

    def test_get_cert_create_amphora_for_lb_flow(self, mock_get_net_driver):

        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_STANDALONE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(3, len(amp_flow.requires))

    def test_get_cert_master_create_amphora_for_lb_flow(
            self, mock_get_net_driver):

        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_MASTER)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(3, len(amp_flow.requires))

    def test_get_cert_master_rest_anti_affinity_create_amphora_for_lb_flow(
            self, mock_get_net_driver):

        self.conf.config(group="nova", enable_anti_affinity=True)

        self.AmpFlow = amphora_flows.AmphoraFlows()
        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_MASTER)

        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.requires)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(4, len(amp_flow.requires))
        self.conf.config(group="nova", enable_anti_affinity=False)

    def test_get_cert_backup_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_BACKUP)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(3, len(amp_flow.requires))

    def test_get_cert_bogus_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', 'BOGUS_ROLE')

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(3, len(amp_flow.requires))

    def test_get_cert_backup_rest_anti_affinity_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.conf.config(group="nova", enable_anti_affinity=True)

        self.AmpFlow = amphora_flows.AmphoraFlows()
        amp_flow = self.AmpFlow._get_create_amp_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_BACKUP)

        self.assertIsInstance(amp_flow, flow.Flow)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.requires)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(4, len(amp_flow.requires))
        self.conf.config(group="nova", enable_anti_affinity=False)

    def test_get_delete_amphora_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_delete_amphora_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)

        self.assertEqual(0, len(amp_flow.provides))
        self.assertEqual(1, len(amp_flow.requires))

    def test_allocate_amp_to_lb_decider(self, mock_get_net_driver):
        history = mock.MagicMock()
        values = mock.MagicMock(side_effect=[['TEST'], [None]])
        history.values = values
        result = self.AmpFlow._allocate_amp_to_lb_decider(history)
        self.assertTrue(result)
        result = self.AmpFlow._allocate_amp_to_lb_decider(history)
        self.assertFalse(result)

    def test_create_new_amp_for_lb_decider(self, mock_get_net_driver):
        history = mock.MagicMock()
        values = mock.MagicMock(side_effect=[[None], ['TEST']])
        history.values = values
        result = self.AmpFlow._create_new_amp_for_lb_decider(history)
        self.assertTrue(result)
        result = self.AmpFlow._create_new_amp_for_lb_decider(history)
        self.assertFalse(result)

    def test_get_failover_flow_allocated(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_failover_flow(
            load_balancer=self.lb)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FAILED_AMPHORA, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMP_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.LISTENERS, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.requires))
        self.assertEqual(12, len(amp_flow.provides))

        amp_flow = self.AmpFlow.get_failover_flow(
            role=constants.ROLE_MASTER, load_balancer=self.lb)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FAILED_AMPHORA, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMP_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.LISTENERS, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.requires))
        self.assertEqual(12, len(amp_flow.provides))

        amp_flow = self.AmpFlow.get_failover_flow(
            role=constants.ROLE_BACKUP, load_balancer=self.lb)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FAILED_AMPHORA, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMP_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.LISTENERS, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.requires))
        self.assertEqual(12, len(amp_flow.provides))

        amp_flow = self.AmpFlow.get_failover_flow(
            role='BOGUSROLE', load_balancer=self.lb)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FAILED_AMPHORA, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMP_DATA, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.LISTENERS, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)

        self.assertEqual(4, len(amp_flow.requires))
        self.assertEqual(12, len(amp_flow.provides))

    def test_get_failover_flow_spare(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_failover_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FAILED_AMPHORA, amp_flow.requires)

        self.assertEqual(1, len(amp_flow.requires))
        self.assertEqual(0, len(amp_flow.provides))

    def test_cert_rotate_amphora_flow(self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_rotate_flow = self.AmpFlow.cert_rotate_amphora_flow()
        self.assertIsInstance(amp_rotate_flow, flow.Flow)

        self.assertIn(constants.SERVER_PEM, amp_rotate_flow.provides)
        self.assertIn(constants.AMPHORA, amp_rotate_flow.requires)

        self.assertEqual(1, len(amp_rotate_flow.provides))
        self.assertEqual(2, len(amp_rotate_flow.requires))

    def test_get_vrrp_subflow(self, mock_get_net_driver):
        vrrp_subflow = self.AmpFlow.get_vrrp_subflow('123')

        self.assertIsInstance(vrrp_subflow, flow.Flow)

        self.assertIn(constants.LOADBALANCER, vrrp_subflow.provides)

        self.assertIn(constants.LOADBALANCER, vrrp_subflow.requires)

        self.assertEqual(2, len(vrrp_subflow.provides))
        self.assertEqual(1, len(vrrp_subflow.requires))

    def test_get_post_map_lb_subflow(self, mock_get_net_driver):

        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow._get_post_map_lb_subflow(
            'SOMEPREFIX', constants.ROLE_MASTER)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AMPHORA_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)

        self.assertEqual(1, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

        amp_flow = self.AmpFlow._get_post_map_lb_subflow(
            'SOMEPREFIX', constants.ROLE_BACKUP)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AMPHORA_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)

        self.assertEqual(1, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

        amp_flow = self.AmpFlow._get_post_map_lb_subflow(
            'SOMEPREFIX', constants.ROLE_STANDALONE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AMPHORA_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)

        self.assertEqual(1, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

        amp_flow = self.AmpFlow._get_post_map_lb_subflow(
            'SOMEPREFIX', 'BOGUS_ROLE')

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AMPHORA_ID, amp_flow.requires)
        self.assertIn(constants.AMPHORA, amp_flow.provides)

        self.assertEqual(1, len(amp_flow.provides))
        self.assertEqual(2, len(amp_flow.requires))

    def test_update_amphora_config_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.update_amphora_config_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)
        self.assertIn(constants.FLAVOR, amp_flow.requires)

        self.assertEqual(2, len(amp_flow.requires))
        self.assertEqual(0, len(amp_flow.provides))
