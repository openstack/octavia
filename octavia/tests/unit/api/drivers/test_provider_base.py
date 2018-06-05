#    Copyright 2018 Rackspace, US Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from octavia.api.drivers import exceptions
from octavia.api.drivers import provider_base as driver_base
import octavia.tests.unit.base as base


class TestProviderBase(base.TestCase):
    """Test base methods.

    Tests that methods not implemented by the drivers raise
    NotImplementedError.
    """
    def setUp(self):
        super(TestProviderBase, self).setUp()
        self.driver = driver_base.ProviderDriver()

    def test_create_vip_port(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.create_vip_port,
                          False, False, False)

    def test_loadbalancer_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.loadbalancer_create,
                          False)

    def test_loadbalancer_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.loadbalancer_delete,
                          False)

    def test_loadbalancer_failover(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.loadbalancer_failover,
                          False)

    def test_loadbalancer_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.loadbalancer_update,
                          False, False)

    def test_listener_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.listener_create,
                          False)

    def test_listener_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.listener_delete,
                          False)

    def test_listener_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.listener_update,
                          False, False)

    def test_pool_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.pool_create,
                          False)

    def test_pool_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.pool_delete,
                          False)

    def test_pool_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.pool_update,
                          False, False)

    def test_member_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.member_create,
                          False)

    def test_member_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.member_delete,
                          False)

    def test_member_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.member_update,
                          False, False)

    def test_member_batch_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.member_batch_update,
                          False)

    def test_health_monitor_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.health_monitor_create,
                          False)

    def test_health_monitor_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.health_monitor_delete,
                          False)

    def test_health_monitor_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.health_monitor_update,
                          False, False)

    def test_l7policy_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7policy_create,
                          False)

    def test_l7policy_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7policy_delete,
                          False)

    def test_l7policy_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7policy_update,
                          False, False)

    def test_l7rule_create(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7rule_create,
                          False)

    def test_l7rule_delete(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7rule_delete,
                          False)

    def test_l7rule_update(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.l7rule_update,
                          False, False)

    def test_get_supported_flavor_metadata(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.get_supported_flavor_metadata)

    def test_validate_flavor(self):
        self.assertRaises(exceptions.NotImplementedError,
                          self.driver.validate_flavor,
                          False)
