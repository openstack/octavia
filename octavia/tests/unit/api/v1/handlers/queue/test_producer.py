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

from oslo_config import fixture
import oslo_messaging as messaging
import six

from octavia.api.v1.handlers.queue import producer
from octavia.api.v1.types import health_monitor
from octavia.api.v1.types import listener
from octavia.api.v1.types import load_balancer
from octavia.api.v1.types import member
from octavia.api.v1.types import pool
from octavia.common import config
from octavia.common import data_models
from octavia.tests.unit import base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestProducer(base.TestCase):
    def setUp(self):
        super(TestProducer, self).setUp()
        self.config = fixture.Config()
        self.mck_model = mock.Mock()
        self.mck_model.id = '10'
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
        p.create(self.mck_model)
        kw = {'load_balancer_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_load_balancer', **kw)

    def test_delete_loadbalancer(self):
        p = producer.LoadBalancerProducer()
        p.delete(self.mck_model)
        kw = {'load_balancer_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_load_balancer', **kw)

    def test_update_loadbalancer(self):
        p = producer.LoadBalancerProducer()
        lb = data_models.LoadBalancer(id=10)
        lb_updates = load_balancer.LoadBalancerPUT(enabled=False)
        p.update(lb, lb_updates)
        kw = {'load_balancer_id': lb.id,
              'load_balancer_updates': lb_updates.to_dict(render_unsets=False)}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_load_balancer', **kw)

    def test_create_listener(self):
        p = producer.ListenerProducer()
        p.create(self.mck_model)
        kw = {'listener_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_listener', **kw)

    def test_delete_listener(self):
        p = producer.ListenerProducer()
        p.delete(self.mck_model)
        kw = {'listener_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_listener', **kw)

    def test_update_listener(self):
        p = producer.ListenerProducer()
        listener_model = data_models.LoadBalancer(id=10)
        listener_updates = listener.ListenerPUT(enabled=False)
        p.update(listener_model, listener_updates)
        kw = {'listener_id': listener_model.id,
              'listener_updates': listener_updates.to_dict(
                  render_unsets=False)}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_listener', **kw)

    def test_create_pool(self):
        p = producer.PoolProducer()
        p.create(self.mck_model)
        kw = {'pool_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_pool', **kw)

    def test_delete_pool(self):
        p = producer.PoolProducer()
        p.delete(self.mck_model)
        kw = {'pool_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_pool', **kw)

    def test_update_pool(self):
        p = producer.PoolProducer()
        pool_model = data_models.Pool(id=10)
        pool_updates = pool.PoolPUT(enabled=False)
        p.update(pool_model, pool_updates)
        kw = {'pool_id': pool_model.id,
              'pool_updates': pool_updates.to_dict(render_unsets=False)}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_pool', **kw)

    def test_create_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        p.create(self.mck_model)
        kw = {'health_monitor_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_health_monitor', **kw)

    def test_delete_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        p.delete(self.mck_model)
        kw = {'health_monitor_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_health_monitor', **kw)

    def test_update_healthmonitor(self):
        p = producer.HealthMonitorProducer()
        hm = data_models.HealthMonitor(pool_id=10)
        hm_updates = health_monitor.HealthMonitorPUT(enabled=False)
        p.update(hm, hm_updates)
        kw = {'pool_id': hm.pool_id,
              'health_monitor_updates': hm_updates.to_dict(
                  render_unsets=False)}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_health_monitor', **kw)

    def test_create_member(self):
        p = producer.MemberProducer()
        p.create(self.mck_model)
        kw = {'member_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'create_member', **kw)

    def test_delete_member(self):
        p = producer.MemberProducer()
        p.delete(self.mck_model)
        kw = {'member_id': self.mck_model.id}
        self.mck_client.cast.assert_called_once_with(
            {}, 'delete_member', **kw)

    def test_update_member(self):
        p = producer.MemberProducer()
        member_model = data_models.Member(id=10)
        member_updates = member.MemberPUT(enabled=False)
        p.update(member_model, member_updates)
        kw = {'member_id': member_model.id,
              'member_updates': member_updates.to_dict(render_unsets=False)}
        self.mck_client.cast.assert_called_once_with(
            {}, 'update_member', **kw)
