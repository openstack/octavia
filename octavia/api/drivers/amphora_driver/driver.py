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
from octavia.db import api as db_apis
from octavia.db import repositories
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
        self.repositories = repositories.Repositories()

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

    def loadbalancer_delete(self, loadbalancer, cascade=False):
        loadbalancer_id = loadbalancer.loadbalancer_id
        payload = {consts.LOAD_BALANCER_ID: loadbalancer_id,
                   'cascade': cascade}
        self.client.cast({}, 'delete_load_balancer', **payload)

    def loadbalancer_failover(self, loadbalancer_id):
        payload = {consts.LOAD_BALANCER_ID: loadbalancer_id}
        self.client.cast({}, 'failover_load_balancer', **payload)

    def loadbalancer_update(self, old_loadbalancer, new_loadbalancer):
        # Adapt the provider data model to the queue schema
        lb_dict = new_loadbalancer.to_dict()
        if 'admin_state_up' in lb_dict:
            lb_dict['enabled'] = lb_dict.pop('admin_state_up')
        lb_id = lb_dict.pop('loadbalancer_id')
        # Put the qos_policy_id back under the vip element the controller
        # expects
        vip_qos_policy_id = lb_dict.pop('vip_qos_policy_id', None)
        if vip_qos_policy_id:
            vip_dict = {"qos_policy_id": vip_qos_policy_id}
            lb_dict["vip"] = vip_dict

        payload = {consts.LOAD_BALANCER_ID: lb_id,
                   consts.LOAD_BALANCER_UPDATES: lb_dict}
        self.client.cast({}, 'update_load_balancer', **payload)

    # Listener
    def listener_create(self, listener):
        payload = {consts.LISTENER_ID: listener.listener_id}
        self.client.cast({}, 'create_listener', **payload)

    def listener_delete(self, listener):
        listener_id = listener.listener_id
        payload = {consts.LISTENER_ID: listener_id}
        self.client.cast({}, 'delete_listener', **payload)

    def listener_update(self, old_listener, new_listener):
        listener_dict = new_listener.to_dict()
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

    def pool_delete(self, pool):
        pool_id = pool.pool_id
        payload = {consts.POOL_ID: pool_id}
        self.client.cast({}, 'delete_pool', **payload)

    def pool_update(self, old_pool, new_pool):
        pool_dict = new_pool.to_dict()
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

    def member_delete(self, member):
        member_id = member.member_id
        payload = {consts.MEMBER_ID: member_id}
        self.client.cast({}, 'delete_member', **payload)

    def member_update(self, old_member, new_member):
        member_dict = new_member.to_dict()
        if 'admin_state_up' in member_dict:
            member_dict['enabled'] = member_dict.pop('admin_state_up')
        member_id = member_dict.pop('member_id')

        payload = {consts.MEMBER_ID: member_id,
                   consts.MEMBER_UPDATES: member_dict}
        self.client.cast({}, 'update_member', **payload)

    def member_batch_update(self, members):
        # Get a list of existing members
        pool_id = members[0].pool_id
        # The DB should not have updated yet, so we can still use the pool
        db_pool = self.repositories.pool.get(db_apis.get_session(), id=pool_id)
        old_members = db_pool.members

        old_member_ids = [m.id for m in old_members]
        # The driver will always pass objects with IDs.
        new_member_ids = [m.member_id for m in members]

        # Find members that are brand new or updated
        new_members = []
        updated_members = []
        for m in members:
            if m.member_id not in old_member_ids:
                new_members.append(m)
            else:
                member_dict = m.to_dict(render_unsets=False)
                member_dict['id'] = member_dict.pop('member_id')
                if 'address' in member_dict:
                    member_dict['ip_address'] = member_dict.pop('address')
                if 'admin_state_up' in member_dict:
                    member_dict['enabled'] = member_dict.pop('admin_state_up')
                updated_members.append(member_dict)

        # Find members that are deleted
        deleted_members = []
        for m in old_members:
            if m.id not in new_member_ids:
                deleted_members.append(m)

        payload = {'old_member_ids': [m.id for m in deleted_members],
                   'new_member_ids': [m.member_id for m in new_members],
                   'updated_members': updated_members}
        self.client.cast({}, 'batch_update_members', **payload)

    # Health Monitor
    def health_monitor_create(self, healthmonitor):
        payload = {consts.HEALTH_MONITOR_ID: healthmonitor.healthmonitor_id}
        self.client.cast({}, 'create_health_monitor', **payload)

    def health_monitor_delete(self, healthmonitor):
        healthmonitor_id = healthmonitor.healthmonitor_id
        payload = {consts.HEALTH_MONITOR_ID: healthmonitor_id}
        self.client.cast({}, 'delete_health_monitor', **payload)

    def health_monitor_update(self, old_healthmonitor, new_healthmonitor):
        healthmon_dict = new_healthmonitor.to_dict()
        if 'admin_state_up' in healthmon_dict:
            healthmon_dict['enabled'] = healthmon_dict.pop('admin_state_up')
        if 'max_retries_down' in healthmon_dict:
            healthmon_dict['fall_threshold'] = healthmon_dict.pop(
                'max_retries_down')
        if 'max_retries' in healthmon_dict:
            healthmon_dict['rise_threshold'] = healthmon_dict.pop(
                'max_retries')
        healthmon_id = healthmon_dict.pop('healthmonitor_id')

        payload = {consts.HEALTH_MONITOR_ID: healthmon_id,
                   consts.HEALTH_MONITOR_UPDATES: healthmon_dict}
        self.client.cast({}, 'update_health_monitor', **payload)

    # L7 Policy
    def l7policy_create(self, l7policy):
        payload = {consts.L7POLICY_ID: l7policy.l7policy_id}
        self.client.cast({}, 'create_l7policy', **payload)

    def l7policy_delete(self, l7policy):
        l7policy_id = l7policy.l7policy_id
        payload = {consts.L7POLICY_ID: l7policy_id}
        self.client.cast({}, 'delete_l7policy', **payload)

    def l7policy_update(self, old_l7policy, new_l7policy):
        l7policy_dict = new_l7policy.to_dict()
        if 'admin_state_up' in l7policy_dict:
            l7policy_dict['enabled'] = l7policy_dict.pop('admin_state_up')
        l7policy_id = l7policy_dict.pop('l7policy_id')

        payload = {consts.L7POLICY_ID: l7policy_id,
                   consts.L7POLICY_UPDATES: l7policy_dict}
        self.client.cast({}, 'update_l7policy', **payload)

    # L7 Rule
    def l7rule_create(self, l7rule):
        payload = {consts.L7RULE_ID: l7rule.l7rule_id}
        self.client.cast({}, 'create_l7rule', **payload)

    def l7rule_delete(self, l7rule):
        l7rule_id = l7rule.l7rule_id
        payload = {consts.L7RULE_ID: l7rule_id}
        self.client.cast({}, 'delete_l7rule', **payload)

    def l7rule_update(self, old_l7rule, new_l7rule):
        l7rule_dict = new_l7rule.to_dict()
        if 'admin_state_up' in l7rule_dict:
            l7rule_dict['enabled'] = l7rule_dict.pop('admin_state_up')
        l7rule_id = l7rule_dict.pop('l7rule_id')

        payload = {consts.L7RULE_ID: l7rule_id,
                   consts.L7RULE_UPDATES: l7rule_dict}
        self.client.cast({}, 'update_l7rule', **payload)
