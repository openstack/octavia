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

from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.amphorae.drivers.noop_driver import driver as driver
from octavia.db import models as models
from octavia.tests.unit import base as base


LOG = logging.getLogger(__name__)
FAKE_UUID_1 = uuidutils.generate_uuid()


class LoggingMixIn(base.TestCase):
    def setUp(self):
        super(LoggingMixIn, self).setUp()
        self.mixin = driver.LoggingMixIn()

    def test_update_stats(self):
        self.mixin.update_stats('test update stats')
        self.assertEqual('test update stats', self.mixin.stats)

    def test_update_health(self):
        self.mixin.update_health('test update health')
        self.assertEqual('test update health', self.mixin.health)


class NoopAmphoraLoadBalancerDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()

    def setUp(self):
        super(NoopAmphoraLoadBalancerDriver, self).setUp()
        self.driver = driver.NoopAmphoraLoadBalancerDriver()
        self.listener = models.Listener()
        self.listener.protocol_port = 80
        self.vip = models.Vip()
        self.vip.ip_address = "10.0.0.1"
        self.amphora = models.Amphora()
        self.amphora.id = self.FAKE_UUID_1

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
        self.driver.post_network_plug(self.amphora)
        self.assertEqual((self.amphora.id, 'post_network_plug'),
                         self.driver.driver.amphoraconfig[
                             self.amphora.id])
