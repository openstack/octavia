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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils
from taskflow.patterns import linear_flow as flow

from octavia.common import constants
from octavia.common import data_models
from octavia.controller.worker.v2.flows import amphora_flows
import octavia.tests.unit.base as base

AUTH_VERSION = '2'


# NOTE: We patch the get_network_driver for all the calls so we don't
# inadvertently make real calls.
@mock.patch('octavia.common.utils.get_network_driver')
class TestAmphoraFlows(base.TestCase):

    def setUp(self):
        super().setUp()
        self.conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        self.conf.config(
            group="controller_worker",
            amphora_driver='amphora_haproxy_rest_driver')
        self.conf.config(group="nova", enable_anti_affinity=False)
        self.AmpFlow = amphora_flows.AmphoraFlows()
        self.amp1 = data_models.Amphora(id=1)
        self.amp2 = data_models.Amphora(id=2)
        self.amp3 = data_models.Amphora(id=3, status=constants.DELETED)
        self.amp4 = data_models.Amphora(id=uuidutils.generate_uuid())
        self.lb = data_models.LoadBalancer(
            id=4, amphorae=[self.amp1, self.amp2, self.amp3])

    def test_get_amphora_for_lb_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_STANDALONE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))

    def test_get_cert_create_amphora_for_lb_flow(self, mock_get_net_driver):

        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_STANDALONE)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))

    def test_get_cert_master_create_amphora_for_lb_flow(
            self, mock_get_net_driver):

        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_MASTER)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))

    def test_get_cert_master_rest_anti_affinity_create_amphora_for_lb_flow(
            self, mock_get_net_driver):

        self.conf.config(group="nova", enable_anti_affinity=True)

        self.AmpFlow = amphora_flows.AmphoraFlows()
        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_MASTER)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))
        self.conf.config(group="nova", enable_anti_affinity=False)

    def test_get_cert_backup_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_BACKUP)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))

    def test_get_cert_bogus_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.AmpFlow = amphora_flows.AmphoraFlows()

        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', 'BOGUS_ROLE')

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))

    def test_get_cert_backup_rest_anti_affinity_create_amphora_for_lb_flow(
            self, mock_get_net_driver):
        self.conf.config(group="nova", enable_anti_affinity=True)

        self.AmpFlow = amphora_flows.AmphoraFlows()
        amp_flow = self.AmpFlow.get_amphora_for_lb_subflow(
            'SOMEPREFIX', constants.ROLE_BACKUP)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.requires)

        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.SERVER_GROUP_ID, amp_flow.requires)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)

        self.assertEqual(5, len(amp_flow.provides))
        self.assertEqual(5, len(amp_flow.requires))
        self.conf.config(group="nova", enable_anti_affinity=False)

    def test_get_delete_amphora_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.get_delete_amphora_flow(self.amp4.to_dict())

        self.assertIsInstance(amp_flow, flow.Flow)

        # This flow injects the required data at flow compile time.

        self.assertEqual(0, len(amp_flow.provides))
        self.assertEqual(0, len(amp_flow.requires))

    def test_get_failover_flow_act_stdby(self, mock_get_net_driver):
        failed_amphora = data_models.Amphora(
            id=uuidutils.generate_uuid(), role=constants.ROLE_MASTER,
            load_balancer_id=uuidutils.generate_uuid()).to_dict()

        amp_flow = self.AmpFlow.get_failover_amphora_flow(
            failed_amphora, 2)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.VIP, amp_flow.requires)

        self.assertIn(constants.UPDATED_PORTS, amp_flow.provides)
        self.assertIn(constants.AMP_VRRP_INT, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_STATUS, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.BASE_PORT, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.DELTA, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)
        self.assertIn(constants.VIP_SG_ID, amp_flow.provides)

        self.assertEqual(8, len(amp_flow.requires))
        self.assertEqual(14, len(amp_flow.provides))

    def test_get_failover_flow_standalone(self, mock_get_net_driver):
        failed_amphora = data_models.Amphora(
            id=uuidutils.generate_uuid(), role=constants.ROLE_STANDALONE,
            load_balancer_id=uuidutils.generate_uuid(),
            vrrp_ip='2001:3b8::32').to_dict()

        amp_flow = self.AmpFlow.get_failover_amphora_flow(
            failed_amphora, 1)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AVAILABILITY_ZONE, amp_flow.requires)
        self.assertIn(constants.BUILD_TYPE_PRIORITY, amp_flow.requires)
        self.assertIn(constants.FLAVOR, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.VIP, amp_flow.requires)

        self.assertIn(constants.UPDATED_PORTS, amp_flow.provides)
        self.assertIn(constants.AMPHORA, amp_flow.provides)
        self.assertIn(constants.AMPHORA_ID, amp_flow.provides)
        self.assertIn(constants.AMPHORAE, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_STATUS, amp_flow.provides)
        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, amp_flow.provides)
        self.assertIn(constants.BASE_PORT, amp_flow.provides)
        self.assertIn(constants.COMPUTE_ID, amp_flow.provides)
        self.assertIn(constants.COMPUTE_OBJ, amp_flow.provides)
        self.assertIn(constants.DELTA, amp_flow.provides)
        self.assertIn(constants.LOADBALANCER, amp_flow.provides)
        self.assertIn(constants.SERVER_PEM, amp_flow.provides)
        self.assertIn(constants.VIP_SG_ID, amp_flow.provides)

        self.assertEqual(8, len(amp_flow.requires))
        self.assertEqual(13, len(amp_flow.provides))

    def test_get_failover_flow_bogus_role(self, mock_get_net_driver):
        failed_amphora = data_models.Amphora(id=uuidutils.generate_uuid(),
                                             role='bogus').to_dict()

        amp_flow = self.AmpFlow.get_failover_amphora_flow(
            failed_amphora, 1)

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.LOADBALANCER_ID, amp_flow.requires)
        self.assertIn(constants.LOADBALANCER, amp_flow.requires)

        self.assertIn(constants.VIP_SG_ID, amp_flow.provides)

        self.assertEqual(2, len(amp_flow.requires))
        self.assertEqual(1, len(amp_flow.provides))

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

        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, vrrp_subflow.provides)
        self.assertIn(constants.AMP_VRRP_INT, vrrp_subflow.provides)
        self.assertIn(constants.AMPHORAE_STATUS, vrrp_subflow.provides)

        self.assertIn(constants.LOADBALANCER_ID, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORAE, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORA_ID, vrrp_subflow.requires)

        self.assertEqual(3, len(vrrp_subflow.provides))
        self.assertEqual(3, len(vrrp_subflow.requires))

    def test_get_vrrp_subflow_dont_get_status(self, mock_get_net_driver):
        vrrp_subflow = self.AmpFlow.get_vrrp_subflow('123',
                                                     get_amphorae_status=False)

        self.assertIsInstance(vrrp_subflow, flow.Flow)

        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, vrrp_subflow.provides)
        self.assertIn(constants.AMP_VRRP_INT, vrrp_subflow.provides)

        self.assertIn(constants.LOADBALANCER_ID, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORAE, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORA_ID, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORAE_STATUS, vrrp_subflow.requires)

        self.assertEqual(2, len(vrrp_subflow.provides))
        self.assertEqual(4, len(vrrp_subflow.requires))

    def test_get_vrrp_subflow_dont_create_vrrp_group(
            self, mock_get_net_driver):
        vrrp_subflow = self.AmpFlow.get_vrrp_subflow('123',
                                                     create_vrrp_group=False)

        self.assertIsInstance(vrrp_subflow, flow.Flow)

        self.assertIn(constants.AMPHORAE_NETWORK_CONFIG, vrrp_subflow.provides)
        self.assertIn(constants.AMP_VRRP_INT, vrrp_subflow.provides)
        self.assertIn(constants.AMPHORAE_STATUS, vrrp_subflow.provides)

        self.assertIn(constants.LOADBALANCER_ID, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORAE, vrrp_subflow.requires)
        self.assertIn(constants.AMPHORA_ID, vrrp_subflow.requires)

        self.assertEqual(3, len(vrrp_subflow.provides))
        self.assertEqual(3, len(vrrp_subflow.requires))

    def test_update_amphora_config_flow(self, mock_get_net_driver):

        amp_flow = self.AmpFlow.update_amphora_config_flow()

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)
        self.assertIn(constants.FLAVOR, amp_flow.requires)

        self.assertEqual(2, len(amp_flow.requires))
        self.assertEqual(0, len(amp_flow.provides))

    def test__retry_flow(self, mock_get_net_driver):
        amp_flow = self.AmpFlow._retry_flow('test_flow')

        self.assertIsInstance(amp_flow, flow.Flow)

        self.assertIn(constants.AMPHORA, amp_flow.requires)

        self.assertEqual(1, len(amp_flow.requires))
        self.assertEqual(0, len(amp_flow.provides))
