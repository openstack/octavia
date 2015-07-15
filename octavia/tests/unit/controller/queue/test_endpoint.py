# Copyright 2014 Rackspace
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

from oslo_config import cfg
import six

from octavia.controller.queue import endpoint
from octavia.controller.worker import controller_worker
from octavia.tests.unit import base

if six.PY2:
    import mock
else:
    import unittest.mock as mock


class TestEndpoint(base.TestCase):

    def setUp(self):
        super(TestEndpoint, self).setUp()

        cfg.CONF.import_group('controller_worker', 'octavia.common.config')
        cfg.CONF.set_override('octavia_plugins', 'hot_plug_plugin')

        mock_class = mock.create_autospec(controller_worker.ControllerWorker)
        self.worker_patcher = mock.patch('octavia.controller.queue.endpoint.'
                                         'stevedore_driver')
        self.worker_patcher.start().ControllerWorker = mock_class

        self.ep = endpoint.Endpoint()
        self.context = {}
        self.resource_updates = {}
        self.resource_id = 1234

    def test_create_load_balancer(self):
        self.ep.create_load_balancer(self.context, self.resource_id)
        self.ep.worker.create_load_balancer.assert_called_once_with(
            self.resource_id)

    def test_update_load_balancer(self):
        self.ep.update_load_balancer(self.context, self.resource_id,
                                     self.resource_updates)
        self.ep.worker.update_load_balancer.assert_called_once_with(
            self.resource_id, self.resource_updates)

    def test_delete_load_balancer(self):
        self.ep.delete_load_balancer(self.context, self.resource_id)
        self.ep.worker.delete_load_balancer.assert_called_once_with(
            self.resource_id)

    def test_create_listener(self):
        self.ep.create_listener(self.context, self.resource_id)
        self.ep.worker.create_listener.assert_called_once_with(
            self.resource_id)

    def test_update_listener(self):
        self.ep.update_listener(self.context, self.resource_id,
                                self.resource_updates)
        self.ep.worker.update_listener.assert_called_once_with(
            self.resource_id, self.resource_updates)

    def test_delete_listener(self):
        self.ep.delete_listener(self.context, self.resource_id)
        self.ep.worker.delete_listener.assert_called_once_with(
            self.resource_id)

    def test_create_pool(self):
        self.ep.create_pool(self.context, self.resource_id)
        self.ep.worker.create_pool.assert_called_once_with(
            self.resource_id)

    def test_update_pool(self):
        self.ep.update_pool(self.context, self.resource_id,
                            self.resource_updates)
        self.ep.worker.update_pool.assert_called_once_with(
            self.resource_id, self.resource_updates)

    def test_delete_pool(self):
        self.ep.delete_pool(self.context, self.resource_id)
        self.ep.worker.delete_pool.assert_called_once_with(
            self.resource_id)

    def test_create_health_monitor(self):
        self.ep.create_health_monitor(self.context, self.resource_id)
        self.ep.worker.create_health_monitor.assert_called_once_with(
            self.resource_id)

    def test_update_health_monitor(self):
        self.ep.update_health_monitor(self.context, self.resource_id,
                                      self.resource_updates)
        self.ep.worker.update_health_monitor.assert_called_once_with(
            self.resource_id, self.resource_updates)

    def test_delete_health_monitor(self):
        self.ep.delete_health_monitor(self.context, self.resource_id)
        self.ep.worker.delete_health_monitor.assert_called_once_with(
            self.resource_id)

    def test_create_member(self):
        self.ep.create_member(self.context, self.resource_id)
        self.ep.worker.create_member.assert_called_once_with(
            self.resource_id)

    def test_update_member(self):
        self.ep.update_member(self.context, self.resource_id,
                              self.resource_updates)
        self.ep.worker.update_member.assert_called_once_with(
            self.resource_id, self.resource_updates)

    def test_delete_member(self):
        self.ep.delete_member(self.context, self.resource_id)
        self.ep.worker.delete_member.assert_called_once_with(
            self.resource_id)
