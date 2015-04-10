#    Copyright 2014 Rackspace
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
#    under the License.#    Copyright 2014 Rackspace
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

import mock
from oslo_config import fixture
import oslo_messaging as messaging

from octavia.api.v1.handlers.queue import producer
from octavia.common import config
from octavia.tests.unit import base


class TestProducer(base.TestCase):
    def setUp(self):
        super(TestProducer, self).setUp()
        self.config = fixture.Config()
        config.cfg.CONF.set_override('topic', 'OCTAVIA_PROV',
                                     group='oslo_messaging')
        mck_target = mock.patch(
            'octavia.api.v1.handlers.queue.producer.messaging.Target')
        mck_transport = mock.patch(
            'octavia.api.v1.handlers.queue.producer.messaging.get_transport')
        self.mck_client = mock.create_autospec(messaging.RPCClient)
        mck_client = mock.patch(
            'octavia.api.v1.handlers.queue.producer.messaging.RPCClient',
            return_value=self.mck_client)
        mck_target.start()
        mck_transport.start()
        mck_client.start()
        self.addCleanup(mck_target.stop)
        self.addCleanup(mck_transport.stop)
        self.addCleanup(mck_client.stop)

    def test_create_loadbalancer(self):
        p = producer.LoadBalancerProducer()
        p.create(10)
        kw = {'load_balancer_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_load_balancer', **kw)

    def test_delete_loadbalancer(self):
        p = producer.LoadBalancerProducer()
        p.delete(10)
        kw = {'load_balancer_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_load_balancer', **kw)

    def test_update_loadbalancer(self):
        p = producer.LoadBalancerProducer()
        p.update(10, {'admin_state_up': False})
        kw = {'load_balancer_updates': {'admin_state_up': False},
              'load_balancer_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_load_balancer', **kw)

    def test_create_listener(self):
        p = producer.ListenerProducer()
        p.create(10)
        kw = {'listener_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_listener', **kw)

    def test_delete_listener(self):
        p = producer.ListenerProducer()
        p.delete(10)
        kw = {'listener_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_listener', **kw)

    def test_update_listener(self):
        p = producer.ListenerProducer()
        p.update(10, {'admin_state_up': False})
        kw = {'listener_updates': {'admin_state_up': False},
              'listener_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_listener', **kw)

    def test_create_pool(self):
        p = producer.PoolProducer()
        p.create(10)
        kw = {'pool_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_pool', **kw)

    def test_delete_pool(self):
        p = producer.PoolProducer()
        p.delete(10)
        kw = {'pool_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_pool', **kw)

    def test_update_pool(self):
        p = producer.PoolProducer()
        p.update(10, {'admin_state_up': False})
        kw = {'pool_updates': {'admin_state_up': False},
              'pool_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_pool', **kw)

    def test_create_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        p.create(10)
        kw = {'health_monitor_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_health_monitor', **kw)

    def test_delete_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        p.delete(10)
        kw = {'health_monitor_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_health_monitor', **kw)

    def test_update_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        p.update(10, {'admin_state_up': False})
        kw = {'health_monitor_updates': {'admin_state_up': False},
              'health_monitor_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_health_monitor', **kw)

    def test_create_member(self):
        p = producer.MemberProducer()
        p.create(10)
        kw = {'member_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_member', **kw)

    def test_delete_member(self):
        p = producer.MemberProducer()
        p.delete(10)
        kw = {'member_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_member', **kw)

    def test_update_member(self):
        p = producer.MemberProducer()
        p.update(10, {'admin_state_up': False})
        kw = {'member_updates': {'admin_state_up': False},
              'member_id': 10}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_member', **kw)