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

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class Endpoints(object):

    # API version history:
    #   1.0 - Initial version.
    target = messaging.Target(
        namespace=constants.RPC_NAMESPACE_CONTROLLER_AGENT,
        version='1.1')

    def __init__(self):
        self.worker = stevedore_driver.DriverManager(
            namespace='octavia.plugins',
            name=CONF.octavia_plugins,
            invoke_on_load=True
        ).driver

    def create_load_balancer(self, context, load_balancer_id,
                             flavor=None):
        LOG.info('Creating load balancer \'%s\'...', load_balancer_id)
        self.worker.create_load_balancer(load_balancer_id, flavor)

    def update_load_balancer(self, context, load_balancer_id,
                             load_balancer_updates):
        LOG.info('Updating load balancer \'%s\'...', load_balancer_id)
        self.worker.update_load_balancer(load_balancer_id,
                                         load_balancer_updates)

    def delete_load_balancer(self, context, load_balancer_id, cascade=False):
        LOG.info('Deleting load balancer \'%s\'...', load_balancer_id)
        self.worker.delete_load_balancer(load_balancer_id, cascade)

    def failover_load_balancer(self, context, load_balancer_id):
        LOG.info('Failing over amphora in load balancer \'%s\'...',
                 load_balancer_id)
        self.worker.failover_loadbalancer(load_balancer_id)

    def failover_amphora(self, context, amphora_id):
        LOG.info('Failing over amphora \'%s\'...',
                 amphora_id)
        self.worker.failover_amphora(amphora_id)

    def create_listener(self, context, listener_id):
        LOG.info('Creating listener \'%s\'...', listener_id)
        self.worker.create_listener(listener_id)

    def update_listener(self, context, listener_id, listener_updates):
        LOG.info('Updating listener \'%s\'...', listener_id)
        self.worker.update_listener(listener_id, listener_updates)

    def delete_listener(self, context, listener_id):
        LOG.info('Deleting listener \'%s\'...', listener_id)
        self.worker.delete_listener(listener_id)

    def create_pool(self, context, pool_id):
        LOG.info('Creating pool \'%s\'...', pool_id)
        self.worker.create_pool(pool_id)

    def update_pool(self, context, pool_id, pool_updates):
        LOG.info('Updating pool \'%s\'...', pool_id)
        self.worker.update_pool(pool_id, pool_updates)

    def delete_pool(self, context, pool_id):
        LOG.info('Deleting pool \'%s\'...', pool_id)
        self.worker.delete_pool(pool_id)

    def create_health_monitor(self, context, health_monitor_id):
        LOG.info('Creating health monitor \'%s\'...', health_monitor_id)
        self.worker.create_health_monitor(health_monitor_id)

    def update_health_monitor(self, context, health_monitor_id,
                              health_monitor_updates):
        LOG.info('Updating health monitor \'%s\'...', health_monitor_id)
        self.worker.update_health_monitor(health_monitor_id,
                                          health_monitor_updates)

    def delete_health_monitor(self, context, health_monitor_id):
        LOG.info('Deleting health monitor \'%s\'...', health_monitor_id)
        self.worker.delete_health_monitor(health_monitor_id)

    def create_member(self, context, member_id):
        LOG.info('Creating member \'%s\'...', member_id)
        self.worker.create_member(member_id)

    def update_member(self, context, member_id, member_updates):
        LOG.info('Updating member \'%s\'...', member_id)
        self.worker.update_member(member_id, member_updates)

    def batch_update_members(self, context, old_member_ids, new_member_ids,
                             updated_members):
        updated_member_ids = [m.get('id') for m in updated_members]
        LOG.info(
            'Batch updating members: old=\'%(old)s\', new=\'%(new)s\', '
            'updated=\'%(updated)s\'...',
            {'old': old_member_ids, 'new': new_member_ids,
             'updated': updated_member_ids})
        self.worker.batch_update_members(
            old_member_ids, new_member_ids, updated_members)

    def delete_member(self, context, member_id):
        LOG.info('Deleting member \'%s\'...', member_id)
        self.worker.delete_member(member_id)

    def create_l7policy(self, context, l7policy_id):
        LOG.info('Creating l7policy \'%s\'...', l7policy_id)
        self.worker.create_l7policy(l7policy_id)

    def update_l7policy(self, context, l7policy_id, l7policy_updates):
        LOG.info('Updating l7policy \'%s\'...', l7policy_id)
        self.worker.update_l7policy(l7policy_id, l7policy_updates)

    def delete_l7policy(self, context, l7policy_id):
        LOG.info('Deleting l7policy \'%s\'...', l7policy_id)
        self.worker.delete_l7policy(l7policy_id)

    def create_l7rule(self, context, l7rule_id):
        LOG.info('Creating l7rule \'%s\'...', l7rule_id)
        self.worker.create_l7rule(l7rule_id)

    def update_l7rule(self, context, l7rule_id, l7rule_updates):
        LOG.info('Updating l7rule \'%s\'...', l7rule_id)
        self.worker.update_l7rule(l7rule_id, l7rule_updates)

    def delete_l7rule(self, context, l7rule_id):
        LOG.info('Deleting l7rule \'%s\'...', l7rule_id)
        self.worker.delete_l7rule(l7rule_id)

    def update_amphora_agent_config(self, context, amphora_id):
        LOG.info('Updating amphora \'%s\' agent configuration...',
                 amphora_id)
        self.worker.update_amphora_agent_config(amphora_id)
