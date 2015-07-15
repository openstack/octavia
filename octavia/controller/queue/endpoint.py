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
from oslo_log import log as logging
import oslo_messaging as messaging
from stevedore import driver as stevedore_driver

from octavia.common import constants
from octavia.i18n import _LI

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class Endpoint(object):

    # API version history:
    #   1.0 - Initial version.
    target = messaging.Target(
        namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
        version='1.0')

    def __init__(self):
        self.worker = stevedore_driver.DriverManager(
            namespace='octavia.plugins',
            name=CONF.octavia_plugins,
            invoke_on_load=True
        ).driver

    def create_load_balancer(self, context, load_balancer_id):
        LOG.info(_LI('Creating load balancer \'%s\'...') % load_balancer_id)
        self.worker.create_load_balancer(load_balancer_id)

    def update_load_balancer(self, context, load_balancer_id,
                             load_balancer_updates):
        LOG.info(_LI('Updating load balancer \'%s\'...') % load_balancer_id)
        self.worker.update_load_balancer(load_balancer_id,
                                         load_balancer_updates)

    def delete_load_balancer(self, context, load_balancer_id):
        LOG.info(_LI('Deleting load balancer \'%s\'...') % load_balancer_id)
        self.worker.delete_load_balancer(load_balancer_id)

    def create_listener(self, context, listener_id):
        LOG.info(_LI('Creating listener \'%s\'...') % listener_id)
        self.worker.create_listener(listener_id)

    def update_listener(self, context, listener_id, listener_updates):
        LOG.info(_LI('Updating listener \'%s\'...') % listener_id)
        self.worker.update_listener(listener_id, listener_updates)

    def delete_listener(self, context, listener_id):
        LOG.info(_LI('Deleting listener \'%s\'...') % listener_id)
        self.worker.delete_listener(listener_id)

    def create_pool(self, context, pool_id):
        LOG.info(_LI('Creating pool \'%s\'...') % pool_id)
        self.worker.create_pool(pool_id)

    def update_pool(self, context, pool_id, pool_updates):
        LOG.info(_LI('Updating pool \'%s\'...') % pool_id)
        self.worker.update_pool(pool_id, pool_updates)

    def delete_pool(self, context, pool_id):
        LOG.info(_LI('Deleting pool \'%s\'...') % pool_id)
        self.worker.delete_pool(pool_id)

    def create_health_monitor(self, context, pool_id):
        LOG.info(_LI('Creating health monitor on pool \'%s\'...') % pool_id)
        self.worker.create_health_monitor(pool_id)

    def update_health_monitor(self, context, pool_id, health_monitor_updates):
        LOG.info(_LI('Updating health monitor on pool \'%s\'...') % pool_id)
        self.worker.update_health_monitor(pool_id, health_monitor_updates)

    def delete_health_monitor(self, context, pool_id):
        LOG.info(_LI('Deleting health monitor on pool \'%s\'...') % pool_id)
        self.worker.delete_health_monitor(pool_id)

    def create_member(self, context, member_id):
        LOG.info(_LI('Creating member \'%s\'...') % member_id)
        self.worker.create_member(member_id)

    def update_member(self, context, member_id, member_updates):
        LOG.info(_LI('Updating member \'%s\'...') % member_id)
        self.worker.update_member(member_id, member_updates)

    def delete_member(self, context, member_id):
        LOG.info(_LI('Deleting member \'%s\'...') % member_id)
        self.worker.delete_member(member_id)
