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

from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.api.drivers import data_models
from octavia.api.drivers import provider_base as driver_base

LOG = logging.getLogger(__name__)


class NoopManager(object):
    def __init__(self):
        super(NoopManager, self).__init__()
        self.driverconfig = {}

    # Load Balancer
    def create_vip_port(self, loadbalancer_id, project_id, vip_dictionary):
        LOG.debug('Provider %s no-op, create_vip_port loadbalancer %s',
                  self.__class__.__name__, loadbalancer_id)

        self.driverconfig[loadbalancer_id] = (loadbalancer_id, project_id,
                                              vip_dictionary,
                                              'create_vip_port')

        vip_address = vip_dictionary.get('vip_address', '198.0.2.5')
        vip_network_id = vip_dictionary.get('vip_network_id',
                                            uuidutils.generate_uuid())
        vip_port_id = vip_dictionary.get('vip_port_id',
                                         uuidutils.generate_uuid())
        vip_subnet_id = vip_dictionary.get('vip_subnet_id',
                                           uuidutils.generate_uuid())

        return data_models.VIP(vip_address=vip_address,
                               vip_network_id=vip_network_id,
                               vip_port_id=vip_port_id,
                               vip_subnet_id=vip_subnet_id).to_dict()

    def loadbalancer_create(self, loadbalancer):
        LOG.debug('Provider %s no-op, loadbalancer_create loadbalancer %s',
                  self.__class__.__name__, loadbalancer.loadbalancer_id)

        self.driverconfig[loadbalancer.loadbalancer_id] = (
            loadbalancer, 'loadbalancer_create')

    def loadbalancer_delete(self, loadbalancer_id, cascade=False):
        LOG.debug('Provider %s no-op, loadbalancer_delete loadbalancer %s',
                  self.__class__.__name__, loadbalancer_id)

        self.driverconfig[loadbalancer_id] = (loadbalancer_id, cascade,
                                              'loadbalancer_delete')

    def loadbalancer_failover(self, loadbalancer_id):
        LOG.debug('Provider %s no-op, loadbalancer_failover loadbalancer %s',
                  self.__class__.__name__, loadbalancer_id)

        self.driverconfig[loadbalancer_id] = (loadbalancer_id,
                                              'loadbalancer_failover')

    def loadbalancer_update(self, loadbalancer):
        LOG.debug('Provider %s no-op, loadbalancer_update loadbalancer %s',
                  self.__class__.__name__, loadbalancer.loadbalancer_id)

        self.driverconfig[loadbalancer.loadbalancer_id] = (
            loadbalancer, 'loadbalancer_update')

    # Listener
    def listener_create(self, listener):
        LOG.debug('Provider %s no-op, listener_create listener %s',
                  self.__class__.__name__, listener.listener_id)

        self.driverconfig[listener.listener_id] = (listener, 'listener_create')

    def listener_delete(self, listener_id):
        LOG.debug('Provider %s no-op, listener_delete listener %s',
                  self.__class__.__name__, listener_id)

        self.driverconfig[listener_id] = (listener_id, 'listener_delete')

    def listener_update(self, listener):
        LOG.debug('Provider %s no-op, listener_update listener %s',
                  self.__class__.__name__, listener.listener_id)

        self.driverconfig[listener.listener_id] = (listener, 'listener_update')

    # Pool
    def pool_create(self, pool):
        LOG.debug('Provider %s no-op, pool_create pool %s',
                  self.__class__.__name__, pool.pool_id)

        self.driverconfig[pool.pool_id] = (pool, 'pool_create')

    def pool_delete(self, pool_id):
        LOG.debug('Provider %s no-op, pool_delete pool %s',
                  self.__class__.__name__, pool_id)

        self.driverconfig[pool_id] = (pool_id, 'pool_delete')

    def pool_update(self, pool):
        LOG.debug('Provider %s no-op, pool_update pool %s',
                  self.__class__.__name__, pool.pool_id)

        self.driverconfig[pool.pool_id] = (pool, 'pool_update')

    # Member
    def member_create(self, member):
        LOG.debug('Provider %s no-op, member_create member %s',
                  self.__class__.__name__, member.member_id)

        self.driverconfig[member.member_id] = (member, 'member_create')

    def member_delete(self, member_id):
        LOG.debug('Provider %s no-op, member_delete member %s',
                  self.__class__.__name__, member_id)

        self.driverconfig[member_id] = (member_id, 'member_delete')

    def member_update(self, member):
        LOG.debug('Provider %s no-op, member_update member %s',
                  self.__class__.__name__, member.member_id)

        self.driverconfig[member.member_id] = (member, 'member_update')

    def member_batch_update(self, members):
        for member in members:
            LOG.debug('Provider %s no-op, member_batch_update member %s',
                      self.__class__.__name__, member.member_id)

            self.driverconfig[member.member_id] = (member,
                                                   'member_batch_update')

    # Health Monitor
    def health_monitor_create(self, healthmonitor):
        LOG.debug('Provider %s no-op, health_monitor_create healthmonitor %s',
                  self.__class__.__name__, healthmonitor.healthmonitor_id)

        self.driverconfig[healthmonitor.healthmonitor_id] = (
            healthmonitor, 'health_monitor_create')

    def health_monitor_delete(self, healthmonitor_id):
        LOG.debug('Provider %s no-op, health_monitor_delete healthmonitor %s',
                  self.__class__.__name__, healthmonitor_id)

        self.driverconfig[healthmonitor_id] = (healthmonitor_id,
                                               'health_monitor_delete')

    def health_monitor_update(self, healthmonitor):
        LOG.debug('Provider %s no-op, health_monitor_update healthmonitor %s',
                  self.__class__.__name__, healthmonitor.healthmonitor_id)

        self.driverconfig[healthmonitor.healthmonitor_id] = (
            healthmonitor, 'health_monitor_update')

    # L7 Policy
    def l7policy_create(self, l7policy):
        LOG.debug('Provider %s no-op, l7policy_create l7policy %s',
                  self.__class__.__name__, l7policy.l7policy_id)

        self.driverconfig[l7policy.l7policy_id] = (l7policy, 'l7policy_create')

    def l7policy_delete(self, l7policy_id):
        LOG.debug('Provider %s no-op, l7policy_delete l7policy %s',
                  self.__class__.__name__, l7policy_id)

        self.driverconfig[l7policy_id] = (l7policy_id, 'l7policy_delete')

    def l7policy_update(self, l7policy):
        LOG.debug('Provider %s no-op, l7policy_update l7policy %s',
                  self.__class__.__name__, l7policy.l7policy_id)

        self.driverconfig[l7policy.l7policy_id] = (l7policy, 'l7policy_update')

    # L7 Rule
    def l7rule_create(self, l7rule):
        LOG.debug('Provider %s no-op, l7rule_create l7rule %s',
                  self.__class__.__name__, l7rule.l7rule_id)

        self.driverconfig[l7rule.l7rule_id] = (l7rule, 'l7rule_create')

    def l7rule_delete(self, l7rule_id):
        LOG.debug('Provider %s no-op, l7rule_delete l7rule %s',
                  self.__class__.__name__, l7rule_id)

        self.driverconfig[l7rule_id] = (l7rule_id, 'l7rule_delete')

    def l7rule_update(self, l7rule):
        LOG.debug('Provider %s no-op, l7rule_update l7rule %s',
                  self.__class__.__name__, l7rule.l7rule_id)

        self.driverconfig[l7rule.l7rule_id] = (l7rule, 'l7rule_update')

    # Flavor
    def get_supported_flavor_metadata(self):
        LOG.debug('Provider %s no-op, get_supported_flavor_metadata',
                  self.__class__.__name__)

        return {'amp_image_tag': 'The glance image tag to use for this load '
                'balancer.'}

    def validate_flavor(self, flavor_metadata):
        LOG.debug('Provider %s no-op, validate_flavor metadata: %s',
                  self.__class__.__name__, flavor_metadata)

        flavor_hash = hash(frozenset(flavor_metadata.items()))
        self.driverconfig[flavor_hash] = (flavor_metadata, 'validate_flavor')


class NoopProviderDriver(driver_base.ProviderDriver):
    def __init__(self):
        super(NoopProviderDriver, self).__init__()
        self.driver = NoopManager()

    # Load Balancer
    def create_vip_port(self, loadbalancer_id, project_id, vip_dictionary):
        return self.driver.create_vip_port(loadbalancer_id, project_id,
                                           vip_dictionary)

    def loadbalancer_create(self, loadbalancer):
        self.driver.loadbalancer_create(loadbalancer)

    def loadbalancer_delete(self, loadbalancer_id, cascade=False):
        self.driver.loadbalancer_delete(loadbalancer_id, cascade)

    def loadbalancer_failover(self, loadbalancer_id):
        self.driver.loadbalancer_failover(loadbalancer_id)

    def loadbalancer_update(self, loadbalancer):
        self.driver.loadbalancer_update(loadbalancer)

    # Listener
    def listener_create(self, listener):
        self.driver.listener_create(listener)

    def listener_delete(self, listener_id):
        self.driver.listener_delete(listener_id)

    def listener_update(self, listener):
        self.driver.listener_update(listener)

    # Pool
    def pool_create(self, pool):
        self.driver.pool_create(pool)

    def pool_delete(self, pool_id):
        self.driver.pool_delete(pool_id)

    def pool_update(self, pool):
        self.driver.pool_update(pool)

    # Member
    def member_create(self, member):
        self.driver.member_create(member)

    def member_delete(self, member_id):
        self.driver.member_delete(member_id)

    def member_update(self, member):
        self.driver.member_update(member)

    def member_batch_update(self, members):
        self.driver.member_batch_update(members)

    # Health Monitor
    def health_monitor_create(self, healthmonitor):
        self.driver.health_monitor_create(healthmonitor)

    def health_monitor_delete(self, healthmonitor_id):
        self.driver.health_monitor_delete(healthmonitor_id)

    def health_monitor_update(self, healthmonitor):
        self.driver.health_monitor_update(healthmonitor)

    # L7 Policy
    def l7policy_create(self, l7policy):
        self.driver.l7policy_create(l7policy)

    def l7policy_delete(self, l7policy_id):
        self.driver.l7policy_delete(l7policy_id)

    def l7policy_update(self, l7policy):
        self.driver.l7policy_update(l7policy)

    # L7 Rule
    def l7rule_create(self, l7rule):
        self.driver.l7rule_create(l7rule)

    def l7rule_delete(self, l7rule_id):
        self.driver.l7rule_delete(l7rule_id)

    def l7rule_update(self, l7rule):
        self.driver.l7rule_update(l7rule)

    # Flavor
    def get_supported_flavor_metadata(self):
        return self.driver.get_supported_flavor_metadata()

    def validate_flavor(self, flavor_metadata):
        self.driver.validate_flavor(flavor_metadata)
