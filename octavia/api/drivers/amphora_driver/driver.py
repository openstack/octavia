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

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

from octavia.api.drivers import exceptions
from octavia.api.drivers import provider_base as driver_base
from octavia.api.drivers import utils as driver_utils
from octavia.common import constants as consts
from octavia.common import data_models
from octavia.common import utils
from octavia.network import base as network_base

CONF = cfg.CONF
CONF.import_group('oslo_messaging', 'octavia.common.config')
LOG = logging.getLogger(__name__)


class AmphoraProviderDriver(driver_base.ProviderDriver):
    def __init__(self):
        super(AmphoraProviderDriver, self).__init__()
        topic = cfg.CONF.oslo_messaging.topic
        self.transport = messaging.get_rpc_transport(cfg.CONF)
        self.target = messaging.Target(
            namespace=consts.RPC_NAMESPACE_CONTROLLER_AGENT,
            topic=topic, version="1.0", fanout=False)
        self.client = messaging.RPCClient(self.transport, target=self.target)

    # Load Balancer
    def create_vip_port(self, loadbalancer_id, project_id, vip_dictionary):
        vip_obj = driver_utils.provider_vip_dict_to_vip_obj(vip_dictionary)
        lb_obj = data_models.LoadBalancer(id=loadbalancer_id,
                                          project_id=project_id, vip=vip_obj)

        network_driver = utils.get_network_driver()
        try:
            vip = network_driver.allocate_vip(lb_obj)
        except network_base.AllocateVIPException as e:
            raise exceptions.DriverError(user_fault_string=e.orig_msg,
                                         operator_fault_string=e.orig_msg)

        LOG.info('Amphora provider created VIP port %s for load balancer %s.',
                 vip.port_id, loadbalancer_id)
        return driver_utils.vip_dict_to_provider_dict(vip.to_dict())

    def loadbalancer_create(self, loadbalancer):
        payload = {consts.LOAD_BALANCER_ID: loadbalancer.loadbalancer_id}
        self.client.cast({}, 'create_load_balancer', **payload)

    def loadbalancer_delete(self, loadbalancer_id, cascade=False):
        payload = {consts.LOAD_BALANCER_ID: loadbalancer_id,
                   'cascade': cascade}
        self.client.cast({}, 'delete_load_balancer', **payload)

    def loadbalancer_failover(self, loadbalancer_id):
        payload = {consts.LOAD_BALANCER_ID: loadbalancer_id}
        self.client.cast({}, 'failover_load_balancer', **payload)

    def loadbalancer_update(self, loadbalancer):
        # Adapt the provider data model to the queue schema
        lb_dict = loadbalancer.to_dict()
        if 'admin_state_up' in lb_dict:
            lb_dict['enabled'] = lb_dict.pop('admin_state_up')
        lb_id = lb_dict.pop('loadbalancer_id')

        payload = {consts.LOAD_BALANCER_ID: lb_id,
                   consts.LOAD_BALANCER_UPDATES: lb_dict}
        self.client.cast({}, 'update_load_balancer', **payload)

    # Listener
    def listener_create(self, listener):
        payload = {consts.LISTENER_ID: listener.listener_id}
        self.client.cast({}, 'create_listener', **payload)

    def listener_delete(self, listener_id):
        payload = {consts.LISTENER_ID: listener_id}
        self.client.cast({}, 'delete_listener', **payload)

    def listener_update(self, listener):
        listener_dict = listener.to_dict()
        if 'admin_state_up' in listener_dict:
            listener_dict['enabled'] = listener_dict.pop('admin_state_up')
        listener_id = listener_dict.pop('listener_id')

        payload = {consts.LISTENER_ID: listener_id,
                   consts.LISTENER_UPDATES: listener_dict}
        self.client.cast({}, 'update_listener', **payload)

    # Pool
    def pool_create(self, pool):
        payload = {consts.POOL_ID: pool.pool_id}
        self.client.cast({}, 'create_pool', **payload)

    def pool_delete(self, pool_id):
        payload = {consts.POOL_ID: pool_id}
        self.client.cast({}, 'delete_pool', **payload)

    def pool_update(self, pool):
        pool_dict = pool.to_dict()
        if 'admin_state_up' in pool_dict:
            pool_dict['enabled'] = pool_dict.pop('admin_state_up')
        pool_id = pool_dict.pop('pool_id')

        payload = {consts.POOL_ID: pool_id,
                   consts.POOL_UPDATES: pool_dict}
        self.client.cast({}, 'update_pool', **payload)

    # Member
    def member_create(self, member):
        payload = {consts.MEMBER_ID: member.member_id}
        self.client.cast({}, 'create_member', **payload)

    def member_delete(self, member_id):
        payload = {consts.MEMBER_ID: member_id}
        self.client.cast({}, 'delete_member', **payload)

    def member_update(self, member):
        pass

    def member_batch_update(self, members):
        pass

    # Health Monitor
    def health_monitor_create(self, healthmonitor):
        payload = {consts.HEALTH_MONITOR_ID: healthmonitor.healthmonitor_id}
        self.client.cast({}, 'create_health_monitor', **payload)

    def health_monitor_delete(self, healthmonitor_id):
        payload = {consts.HEALTH_MONITOR_ID: healthmonitor_id}
        self.client.cast({}, 'delete_health_monitor', **payload)

    def health_monitor_update(self, healthmonitor):
        pass

    # L7 Policy
    def l7policy_create(self, l7policy):
        payload = {consts.L7POLICY_ID: l7policy.l7policy_id}
        self.client.cast({}, 'create_l7policy', **payload)

    def l7policy_delete(self, l7policy_id):
        payload = {consts.L7POLICY_ID: l7policy_id}
        self.client.cast({}, 'delete_l7policy', **payload)

    def l7policy_update(self, l7policy):
        pass

    # L7 Rule
    def l7rule_create(self, l7rule):
        payload = {consts.L7RULE_ID: l7rule.l7rule_id}
        self.client.cast({}, 'create_l7rule', **payload)

    def l7rule_delete(self, l7rule_id):
        payload = {consts.L7RULE_ID: l7rule_id}
        self.client.cast({}, 'delete_l7rule', **payload)

    def l7rule_update(self, l7rule):
        pass

    # Flavor
    def get_supported_flavor_metadata(self):
        pass

    def validate_flavor(self, flavor_metadata):
        pass
