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
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.db import models as models
from octavia.network.drivers.noop_driver import driver as driver
import octavia.tests.unit.base as base


LOG = logging.getLogger(__name__)


class TestNoopNetworkDriver(base.TestCase):
    FAKE_UUID_1 = uuidutils.generate_uuid()
    FAKE_UUID_2 = uuidutils.generate_uuid()
    FAKE_UUID_3 = uuidutils.generate_uuid()

    def setUp(self):
        super(TestNoopNetworkDriver, self).setUp()
        self.driver = driver.NoopNetworkDriver(LOG)
        self.port_id = 88
        self.network_id = self.FAKE_UUID_3
        self.ip_address = "10.0.0.2"
        self.load_balancer = models.LoadBalancer()
        self.load_balancer.id = self.FAKE_UUID_2

        self.vip = models.Vip()
        self.vip.ip_address = "10.0.0.1"
        self.amphora_id = self.FAKE_UUID_1

    def test_allocate_vip(self):
        self.driver.allocate_vip(self.port_id, self.network_id,
                                 self.ip_address)
        self.assertEqual((self.port_id, self.network_id, self.ip_address,
                          'allocate_vip'),
                         self.driver.driver.networkconfigconfig[(
                             self.port_id, self.network_id, self.ip_address)])

    def test_deallocate_vip(self):
        self.driver.deallocate_vip(self.vip)
        self.assertEqual((self.vip,
                          'deallocate_vip'),
                         self.driver.driver.networkconfigconfig[
                             self.vip.ip_address])

    def test_plug_vip(self):
        self.driver.plug_vip(self.load_balancer, self.vip)
        self.assertEqual((self.load_balancer, self.vip,
                          'plug_vip'),
                         self.driver.driver.networkconfigconfig[(
                             self.load_balancer.id, self.vip.ip_address)])

    def test_unplug_vip(self):
        self.driver.unplug_vip(self.load_balancer, self.vip)
        self.assertEqual((self.load_balancer, self.vip,
                          'unplug_vip'),
                         self.driver.driver.networkconfigconfig[(
                             self.load_balancer.id, self.vip.ip_address)])

    def test_plug_network(self):
        self.driver.plug_network(self.amphora_id, self.network_id,
                                 self.ip_address)
        self.assertEqual((self.amphora_id, self.network_id, self.ip_address,
                          'plug_network'),
                         self.driver.driver.networkconfigconfig[(
                             self.amphora_id, self.network_id,
                             self.ip_address)])

    def test_unplug_network(self):
        self.driver.unplug_network(self.amphora_id, self.network_id)
        self.assertEqual((self.amphora_id, self.network_id,
                          'unplug_network'),
                         self.driver.driver.networkconfigconfig[(
                             self.amphora_id, self.network_id)])

    def test_get_plugged_networks(self):
        self.driver.get_plugged_networks(self.amphora_id)
        self.assertEqual((self.amphora_id, 'get_plugged_networks'),
                         self.driver.driver.networkconfigconfig[(
                             self.amphora_id)])