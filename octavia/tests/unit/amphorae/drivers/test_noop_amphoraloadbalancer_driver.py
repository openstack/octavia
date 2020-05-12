# Copyright 2014, Author: Min Wang,German Eichberger
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
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_utils import uuidutils

from octavia.amphorae.drivers.noop_driver import driver
from octavia.common import constants
from octavia.common import data_models
from octavia.network import data_models as network_models
from octavia.tests.unit import base


FAKE_UUID_1 = uuidutils.generate_uuid()


class TestLoggingUpdate(base.TestCase):
    def setUp(self):
        super(TestLoggingUpdate, self).setUp()
        self.mixin = driver.LoggingUpdate()

    def test_update_stats(self):
        self.mixin.update_stats('test update stats')
        self.assertEqual('test update stats', self.mixin.stats)

    def test_update_health(self):
        self.mixin.update_health('test update health')
        self.assertEqual('test update health', self.mixin.health)


class TestNoopAmphoraLoadBalancerDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestNoopAmphoraLoadBalancerDriver, self).setUp()
        self.driver = driver.NoopAmphoraLoadBalancerDriver()
        self.listener = data_models.Listener()
        self.listener.id = uuidutils.generate_uuid()
        self.listener.protocol_port = 80
        self.vip = data_models.Vip()
        self.vip.ip_address = "10.0.0.1"
        self.amphora = data_models.Amphora()
        self.amphora.id = self.FAKE_UUID_1
        self.load_balancer = data_models.LoadBalancer(
            id=FAKE_UUID_1, amphorae=[self.amphora], vip=self.vip,
            listeners=[self.listener])
        self.network = network_models.Network(id=self.FAKE_UUID_1)
        self.port = network_models.Port(id=uuidutils.generate_uuid())
        self.amphorae_net_configs = {
            self.amphora.id:
                network_models.AmphoraNetworkConfig(
                    amphora=self.amphora,
                    vip_subnet=network_models.Subnet(id=self.FAKE_UUID_1))
        }
        self.pem_file = 'test_pem_file'
        self.timeout_dict = {constants.REQ_CONN_TIMEOUT: 1,
                             constants.REQ_READ_TIMEOUT: 2,
                             constants.CONN_MAX_RETRIES: 3,
                             constants.CONN_RETRY_INTERVAL: 4}

    def test_update_amphora_listeners(self):
        amphorae = [self.amphora]
        self.driver.update_amphora_listeners([self.listener], 0, amphorae,
                                             self.timeout_dict)
        self.assertEqual((self.listener, self.amphora.id, self.timeout_dict,
                          'update_amp'),
                         self.driver.driver.amphoraconfig[(
                             self.listener.id,
                             self.amphora.id)])

    def test_update(self):
        self.driver.update(self.listener, self.vip)
        self.assertEqual((self.listener, self.vip, 'active'),
                         self.driver.driver.amphoraconfig[(
                             self.listener.protocol_port,
                             self.vip.ip_address)])

    def test_stop(self):
        self.driver.stop(self.listener, self.vip)
        self.assertEqual((self.listener, self.vip, 'stop'),
                         self.driver.driver.amphoraconfig[(
                             self.listener.protocol_port,
                             self.vip.ip_address)])

    def test_start(self):
        self.driver.start(self.listener, self.vip)
        self.assertEqual((self.listener, self.vip, 'start'),
                         self.driver.driver.amphoraconfig[(
                             self.listener.protocol_port,
                             self.vip.ip_address)])

    def test_delete(self):
        self.driver.delete(self.listener, self.vip)
        self.assertEqual((self.listener, self.vip, 'delete'),
                         self.driver.driver.amphoraconfig[(
                             self.listener.protocol_port,
                             self.vip.ip_address)])

    def test_get_info(self):
        self.driver.get_info(self.amphora)
        self.assertEqual((self.amphora.id, 'get_info'),
                         self.driver.driver.amphoraconfig[
                             self.amphora.id])

    def test_get_diagnostics(self):
        self.driver.get_diagnostics(self.amphora)
        self.assertEqual((self.amphora.id, 'get_diagnostics'),
                         self.driver.driver.amphoraconfig[
                             self.amphora.id])

    def test_finalize_amphora(self):
        self.driver.finalize_amphora(self.amphora)
        self.assertEqual((self.amphora.id, 'finalize amphora'),
                         self.driver.driver.amphoraconfig[
                             self.amphora.id])

    def test_post_network_plug(self):
        self.driver.post_network_plug(self.amphora, self.port)
        self.assertEqual((self.amphora.id, self.port.id, 'post_network_plug'),
                         self.driver.driver.amphoraconfig[(
                             self.amphora.id, self.port.id)])

    def test_post_vip_plug(self):
        self.driver.post_vip_plug(self.amphora, self.load_balancer,
                                  self.amphorae_net_configs)
        expected_method_and_args = (self.load_balancer.id,
                                    self.amphorae_net_configs,
                                    'post_vip_plug')
        actual_method_and_args = self.driver.driver.amphoraconfig[(
            self.load_balancer.id, id(self.amphorae_net_configs)
        )]
        self.assertEqual(expected_method_and_args, actual_method_and_args)

    def test_upload_cert_amp(self):
        self.driver.upload_cert_amp(self.amphora, self.pem_file)
        self.assertEqual(
            (self.amphora.id, self.pem_file, 'update_amp_cert_file'),
            self.driver.driver.amphoraconfig[(
                self.amphora.id, self.pem_file)])
