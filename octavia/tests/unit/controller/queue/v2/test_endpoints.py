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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_utils import uuidutils

from octavia.common import constants
from octavia.controller.queue.v2 import endpoints
from octavia.tests.unit import base


class TestEndpoints(base.TestCase):

    def setUp(self):
        super(TestEndpoints, self).setUp()

        conf = self.useFixture(oslo_fixture.Config(cfg.CONF))
        conf.config(octavia_plugins='hot_plug_plugin')

        self.worker_patcher = mock.patch('octavia.controller.worker.v2.'
                                         'controller_worker.ControllerWorker')
        self.worker_patcher.start()

        self.ep = endpoints.Endpoints()
        self.context = {}
        self.resource_updates = {}
        self.resource_id = 1234
        self.resource = {constants.ID: self.resource_id}
        self.server_group_id = 3456
        self.listener_dict = {constants.LISTENER_ID: uuidutils.generate_uuid()}
        self.loadbalancer_dict = {
            constants.LOADBALANCER_ID: uuidutils.generate_uuid()
        }
        self.flavor_id = uuidutils.generate_uuid()
        self.availability_zone = uuidutils.generate_uuid()

    def test_create_load_balancer(self):
        self.ep.create_load_balancer(self.context, self.loadbalancer_dict,
                                     flavor=self.flavor_id,
                                     availability_zone=self.availability_zone)
        self.ep.worker.create_load_balancer.assert_called_once_with(
            self.loadbalancer_dict, self.flavor_id, self.availability_zone)

    def test_create_load_balancer_no_flavor_or_az(self):
        self.ep.create_load_balancer(self.context, self.loadbalancer_dict)
        self.ep.worker.create_load_balancer.assert_called_once_with(
            self.loadbalancer_dict, None, None)

    def test_update_load_balancer(self):
        self.ep.update_load_balancer(self.context, self.loadbalancer_dict,
                                     self.resource_updates)
        self.ep.worker.update_load_balancer.assert_called_once_with(
            self.loadbalancer_dict, self.resource_updates)

    def test_delete_load_balancer(self):
        self.ep.delete_load_balancer(self.context, self.loadbalancer_dict)
        self.ep.worker.delete_load_balancer.assert_called_once_with(
            self.loadbalancer_dict, False)

    def test_failover_load_balancer(self):
        self.ep.failover_load_balancer(self.context, self.resource_id)
        self.ep.worker.failover_loadbalancer.assert_called_once_with(
            self.resource_id)

    def test_failover_amphora(self):
        self.ep.failover_amphora(self.context, self.resource_id)
        self.ep.worker.failover_amphora.assert_called_once_with(
            self.resource_id)

    def test_create_listener(self):
        self.ep.create_listener(self.context, self.listener_dict)
        self.ep.worker.create_listener.assert_called_once_with(
            self.listener_dict)

    def test_update_listener(self):
        self.ep.update_listener(self.context, self.listener_dict,
                                self.resource_updates)
        self.ep.worker.update_listener.assert_called_once_with(
            self.listener_dict, self.resource_updates)

    def test_delete_listener(self):
        self.ep.delete_listener(self.context, self.listener_dict)
        self.ep.worker.delete_listener.assert_called_once_with(
            self.listener_dict)

    def test_create_pool(self):
        self.ep.create_pool(self.context, self.resource)
        self.ep.worker.create_pool.assert_called_once_with(
            self.resource)

    def test_update_pool(self):
        self.ep.update_pool(self.context, self.resource,
                            self.resource_updates)
        self.ep.worker.update_pool.assert_called_once_with(
            self.resource, self.resource_updates)

    def test_delete_pool(self):
        self.ep.delete_pool(self.context, self.resource)
        self.ep.worker.delete_pool.assert_called_once_with(
            self.resource)

    def test_create_health_monitor(self):
        self.ep.create_health_monitor(self.context, self.resource)
        self.ep.worker.create_health_monitor.assert_called_once_with(
            self.resource)

    def test_update_health_monitor(self):
        self.ep.update_health_monitor(self.context, self.resource,
                                      self.resource_updates)
        self.ep.worker.update_health_monitor.assert_called_once_with(
            self.resource, self.resource_updates)

    def test_delete_health_monitor(self):
        self.ep.delete_health_monitor(self.context, self.resource)
        self.ep.worker.delete_health_monitor.assert_called_once_with(
            self.resource)

    def test_create_member(self):
        self.ep.create_member(self.context, self.resource)
        self.ep.worker.create_member.assert_called_once_with(
            self.resource)

    def test_update_member(self):
        self.ep.update_member(self.context, self.resource,
                              self.resource_updates)
        self.ep.worker.update_member.assert_called_once_with(
            self.resource, self.resource_updates)

    def test_batch_update_members(self):
        self.ep.batch_update_members(
            self.context, [{constants.MEMBER_ID: 9}],
            [{constants.MEMBER_ID: 11}],
            [self.resource_updates])
        self.ep.worker.batch_update_members.assert_called_once_with(
            [{constants.MEMBER_ID: 9}], [{constants.MEMBER_ID: 11}],
            [self.resource_updates])

    def test_delete_member(self):
        self.ep.delete_member(self.context, self.resource)
        self.ep.worker.delete_member.assert_called_once_with(
            self.resource)

    def test_create_l7policy(self):
        self.ep.create_l7policy(self.context, self.resource)
        self.ep.worker.create_l7policy.assert_called_once_with(
            self.resource)

    def test_update_l7policy(self):
        self.ep.update_l7policy(self.context, self.resource,
                                self.resource_updates)
        self.ep.worker.update_l7policy.assert_called_once_with(
            self.resource, self.resource_updates)

    def test_delete_l7policy(self):
        self.ep.delete_l7policy(self.context, self.resource)
        self.ep.worker.delete_l7policy.assert_called_once_with(
            self.resource)

    def test_create_l7rule(self):
        self.ep.create_l7rule(self.context, self.resource)
        self.ep.worker.create_l7rule.assert_called_once_with(
            self.resource)

    def test_update_l7rule(self):
        self.ep.update_l7rule(self.context, self.resource,
                              self.resource_updates)
        self.ep.worker.update_l7rule.assert_called_once_with(
            self.resource, self.resource_updates)

    def test_delete_l7rule(self):
        self.ep.delete_l7rule(self.context, self.resource)
        self.ep.worker.delete_l7rule.assert_called_once_with(
            self.resource)

    def test_update_amphora_agent_config(self):
        self.ep.update_amphora_agent_config(self.context, self.resource)
        self.ep.worker.update_amphora_agent_config.assert_called_once_with(
            self.resource)
