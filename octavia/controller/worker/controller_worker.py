# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import logging

from octavia.common import base_taskflow
from octavia.common import constants
from octavia.controller.worker.flows import amphora_flows
from octavia.controller.worker.flows import health_monitor_flows
from octavia.controller.worker.flows import l7policy_flows
from octavia.controller.worker.flows import l7rule_flows
from octavia.controller.worker.flows import listener_flows
from octavia.controller.worker.flows import load_balancer_flows
from octavia.controller.worker.flows import member_flows
from octavia.controller.worker.flows import pool_flows
from octavia.db import api as db_apis
from octavia.db import repositories as repo

from oslo_config import cfg
from oslo_utils import excutils
from taskflow.listeners import logging as tf_logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class ControllerWorker(base_taskflow.BaseTaskFlowEngine):

    def __init__(self):

        self._amphora_flows = amphora_flows.AmphoraFlows()
        self._health_monitor_flows = health_monitor_flows.HealthMonitorFlows()
        self._lb_flows = load_balancer_flows.LoadBalancerFlows()
        self._listener_flows = listener_flows.ListenerFlows()
        self._member_flows = member_flows.MemberFlows()
        self._pool_flows = pool_flows.PoolFlows()
        self._l7policy_flows = l7policy_flows.L7PolicyFlows()
        self._l7rule_flows = l7rule_flows.L7RuleFlows()

        self._amphora_repo = repo.AmphoraRepository()
        self._amphora_health_repo = repo.AmphoraHealthRepository()
        self._health_mon_repo = repo.HealthMonitorRepository()
        self._lb_repo = repo.LoadBalancerRepository()
        self._listener_repo = repo.ListenerRepository()
        self._member_repo = repo.MemberRepository()
        self._pool_repo = repo.PoolRepository()
        self._l7policy_repo = repo.L7PolicyRepository()
        self._l7rule_repo = repo.L7RuleRepository()

        self._exclude_result_logging_tasks = (
            constants.ROLE_STANDALONE + '-' +
            constants.CREATE_AMP_FOR_LB_SUBFLOW + '-' +
            constants.GENERATE_SERVER_PEM,
            constants.ROLE_BACKUP + '-' +
            constants.CREATE_AMP_FOR_LB_SUBFLOW + '-' +
            constants.GENERATE_SERVER_PEM,
            constants.ROLE_MASTER + '-' +
            constants.CREATE_AMP_FOR_LB_SUBFLOW + '-' +
            constants.GENERATE_SERVER_PEM,
            constants.GENERATE_SERVER_PEM_TASK,
            constants.FAILOVER_AMPHORA_FLOW + '-' +
            constants.CREATE_AMP_FOR_LB_SUBFLOW + '-' +
            constants.GENERATE_SERVER_PEM,
            constants.CREATE_AMP_FOR_LB_SUBFLOW + '-' +
            constants.UPDATE_CERT_EXPIRATION)

        super(ControllerWorker, self).__init__()

    def create_amphora(self):
        """Creates an Amphora.

        This is used to create spare amphora.

        :returns: amphora_id
        """
        create_amp_tf = self._taskflow_load(
            self._amphora_flows.get_create_amphora_flow(),
            store={constants.BUILD_TYPE_PRIORITY:
                   constants.LB_CREATE_SPARES_POOL_PRIORITY}
        )
        with tf_logging.DynamicLoggingListener(
                create_amp_tf, log=LOG,
                hide_inputs_outputs_of=self._exclude_result_logging_tasks):

            create_amp_tf.run()

        return create_amp_tf.storage.fetch('amphora')

    def delete_amphora(self, amphora_id):
        """Deletes an existing Amphora.

        :param amphora_id: ID of the amphora to delete
        :returns: None
        :raises AmphoraNotFound: The referenced Amphora was not found
        """
        amphora = self._amphora_repo.get(db_apis.get_session(),
                                         id=amphora_id)
        delete_amp_tf = self._taskflow_load(self._amphora_flows.
                                            get_delete_amphora_flow(),
                                            store={constants.AMPHORA: amphora})
        with tf_logging.DynamicLoggingListener(delete_amp_tf,
                                               log=LOG):
            delete_amp_tf.run()

    def create_health_monitor(self, health_monitor_id):
        """Creates a health monitor.

        :param pool_id: ID of the pool to create a health monitor on
        :returns: None
        :raises NoSuitablePool: Unable to find the node pool
        """
        health_mon = self._health_mon_repo.get(db_apis.get_session(),
                                               id=health_monitor_id)

        pool = health_mon.pool
        listeners = pool.listeners
        pool.health_monitor = health_mon
        load_balancer = pool.load_balancer

        create_hm_tf = self._taskflow_load(
            self._health_monitor_flows.get_create_health_monitor_flow(),
            store={constants.HEALTH_MON: health_mon,
                   constants.POOL: pool,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(create_hm_tf,
                                               log=LOG):
            create_hm_tf.run()

    def delete_health_monitor(self, health_monitor_id):
        """Deletes a health monitor.

        :param pool_id: ID of the pool to delete its health monitor
        :returns: None
        :raises HMNotFound: The referenced health monitor was not found
        """
        health_mon = self._health_mon_repo.get(db_apis.get_session(),
                                               id=health_monitor_id)

        pool = health_mon.pool
        listeners = pool.listeners
        load_balancer = pool.load_balancer

        delete_hm_tf = self._taskflow_load(
            self._health_monitor_flows.get_delete_health_monitor_flow(),
            store={constants.HEALTH_MON: health_mon,
                   constants.POOL: pool,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(delete_hm_tf,
                                               log=LOG):
            delete_hm_tf.run()

    def update_health_monitor(self, health_monitor_id, health_monitor_updates):
        """Updates a health monitor.

        :param pool_id: ID of the pool to have it's health monitor updated
        :param health_monitor_updates: Dict containing updated health monitor
        :returns: None
        :raises HMNotFound: The referenced health monitor was not found
        """
        health_mon = self._health_mon_repo.get(db_apis.get_session(),
                                               id=health_monitor_id)

        pool = health_mon.pool
        listeners = pool.listeners
        pool.health_monitor = health_mon
        load_balancer = pool.load_balancer

        update_hm_tf = self._taskflow_load(
            self._health_monitor_flows.get_update_health_monitor_flow(),
            store={constants.HEALTH_MON: health_mon,
                   constants.POOL: pool,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer,
                   constants.UPDATE_DICT: health_monitor_updates})
        with tf_logging.DynamicLoggingListener(update_hm_tf,
                                               log=LOG):
            update_hm_tf.run()

    def create_listener(self, listener_id):
        """Creates a listener.

        :param listener_id: ID of the listener to create
        :returns: None
        :raises NoSuitableLB: Unable to find the load balancer
        """
        listener = self._listener_repo.get(db_apis.get_session(),
                                           id=listener_id)
        load_balancer = listener.load_balancer

        create_listener_tf = self._taskflow_load(self._listener_flows.
                                                 get_create_listener_flow(),
                                                 store={constants.LOADBALANCER:
                                                        load_balancer,
                                                        constants.LISTENERS:
                                                            [listener]})
        with tf_logging.DynamicLoggingListener(create_listener_tf,
                                               log=LOG):
            create_listener_tf.run()

    def delete_listener(self, listener_id):
        """Deletes a listener.

        :param listener_id: ID of the listener to delete
        :returns: None
        :raises ListenerNotFound: The referenced listener was not found
        """
        listener = self._listener_repo.get(db_apis.get_session(),
                                           id=listener_id)
        load_balancer = listener.load_balancer

        delete_listener_tf = self._taskflow_load(
            self._listener_flows.get_delete_listener_flow(),
            store={constants.LOADBALANCER: load_balancer,
                   constants.LISTENER: listener})
        with tf_logging.DynamicLoggingListener(delete_listener_tf,
                                               log=LOG):
            delete_listener_tf.run()

    def update_listener(self, listener_id, listener_updates):
        """Updates a listener.

        :param listener_id: ID of the listener to update
        :param listener_updates: Dict containing updated listener attributes
        :returns: None
        :raises ListenerNotFound: The referenced listener was not found
        """
        listener = self._listener_repo.get(db_apis.get_session(),
                                           id=listener_id)

        load_balancer = listener.load_balancer

        update_listener_tf = self._taskflow_load(self._listener_flows.
                                                 get_update_listener_flow(),
                                                 store={constants.LISTENER:
                                                        listener,
                                                        constants.LOADBALANCER:
                                                            load_balancer,
                                                        constants.UPDATE_DICT:
                                                            listener_updates,
                                                        constants.LISTENERS:
                                                            [listener]})
        with tf_logging.DynamicLoggingListener(update_listener_tf, log=LOG):
            update_listener_tf.run()

    def create_load_balancer(self, load_balancer_id):
        """Creates a load balancer by allocating Amphorae.

        First tries to allocate an existing Amphora in READY state.
        If none are available it will attempt to build one specifically
        for this load balancer.

        :param load_balancer_id: ID of the load balancer to create
        :returns: None
        :raises NoSuitableAmphoraException: Unable to allocate an Amphora.
        """

        store = {constants.LOADBALANCER_ID: load_balancer_id,
                 constants.BUILD_TYPE_PRIORITY:
                 constants.LB_CREATE_NORMAL_PRIORITY}

        topology = CONF.controller_worker.loadbalancer_topology

        store[constants.UPDATE_DICT] = {
            constants.LOADBALANCER_TOPOLOGY: topology
        }

        lb = self._lb_repo.get(db_apis.get_session(), id=load_balancer_id)
        create_lb_flow = self._lb_flows.get_create_load_balancer_flow(
            topology=topology, listeners=lb.listeners)

        create_lb_tf = self._taskflow_load(create_lb_flow, store=store)
        with tf_logging.DynamicLoggingListener(
                create_lb_tf, log=LOG,
                hide_inputs_outputs_of=self._exclude_result_logging_tasks):
            create_lb_tf.run()

    def delete_load_balancer(self, load_balancer_id, cascade=False):
        """Deletes a load balancer by de-allocating Amphorae.

        :param load_balancer_id: ID of the load balancer to delete
        :returns: None
        :raises LBNotFound: The referenced load balancer was not found
        """
        lb = self._lb_repo.get(db_apis.get_session(),
                               id=load_balancer_id)

        if cascade:
            (flow,
             store) = self._lb_flows.get_cascade_delete_load_balancer_flow(lb)
        else:
            (flow, store) = self._lb_flows.get_delete_load_balancer_flow(lb)
        store.update({constants.LOADBALANCER: lb,
                      constants.SERVER_GROUP_ID: lb.server_group_id})
        delete_lb_tf = self._taskflow_load(flow, store=store)

        with tf_logging.DynamicLoggingListener(delete_lb_tf,
                                               log=LOG):
            delete_lb_tf.run()

    def update_load_balancer(self, load_balancer_id, load_balancer_updates):
        """Updates a load balancer.

        :param load_balancer_id: ID of the load balancer to update
        :param load_balancer_updates: Dict containing updated load balancer
        :returns: None
        :raises LBNotFound: The referenced load balancer was not found
        """
        lb = self._lb_repo.get(db_apis.get_session(),
                               id=load_balancer_id)
        listeners, _ = self._listener_repo.get_all(
            db_apis.get_session(),
            load_balancer_id=load_balancer_id)

        update_lb_tf = self._taskflow_load(
            self._lb_flows.get_update_load_balancer_flow(),
            store={constants.LOADBALANCER: lb,
                   constants.LISTENERS: listeners,
                   constants.UPDATE_DICT: load_balancer_updates})

        with tf_logging.DynamicLoggingListener(update_lb_tf,
                                               log=LOG):
            update_lb_tf.run()

    def create_member(self, member_id):
        """Creates a pool member.

        :param member_id: ID of the member to create
        :returns: None
        :raises NoSuitablePool: Unable to find the node pool
        """
        member = self._member_repo.get(db_apis.get_session(),
                                       id=member_id)
        pool = member.pool
        listeners = pool.listeners
        load_balancer = pool.load_balancer

        create_member_tf = self._taskflow_load(self._member_flows.
                                               get_create_member_flow(),
                                               store={constants.MEMBER: member,
                                                      constants.LISTENERS:
                                                          listeners,
                                                      constants.LOADBALANCER:
                                                          load_balancer,
                                                      constants.POOL: pool})
        with tf_logging.DynamicLoggingListener(create_member_tf,
                                               log=LOG):
            create_member_tf.run()

    def delete_member(self, member_id):
        """Deletes a pool member.

        :param member_id: ID of the member to delete
        :returns: None
        :raises MemberNotFound: The referenced member was not found
        """
        member = self._member_repo.get(db_apis.get_session(),
                                       id=member_id)
        pool = member.pool
        listeners = pool.listeners
        load_balancer = pool.load_balancer

        delete_member_tf = self._taskflow_load(
            self._member_flows.get_delete_member_flow(),
            store={constants.MEMBER: member, constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer, constants.POOL: pool}
        )
        with tf_logging.DynamicLoggingListener(delete_member_tf,
                                               log=LOG):
            delete_member_tf.run()

    def update_member(self, member_id, member_updates):
        """Updates a pool member.

        :param member_id: ID of the member to update
        :param member_updates: Dict containing updated member attributes
        :returns: None
        :raises MemberNotFound: The referenced member was not found
        """
        member = self._member_repo.get(db_apis.get_session(),
                                       id=member_id)
        pool = member.pool
        listeners = pool.listeners
        load_balancer = pool.load_balancer

        update_member_tf = self._taskflow_load(self._member_flows.
                                               get_update_member_flow(),
                                               store={constants.MEMBER: member,
                                                      constants.LISTENERS:
                                                          listeners,
                                                      constants.LOADBALANCER:
                                                          load_balancer,
                                                      constants.POOL:
                                                          pool,
                                                      constants.UPDATE_DICT:
                                                          member_updates})
        with tf_logging.DynamicLoggingListener(update_member_tf,
                                               log=LOG):
            update_member_tf.run()

    def create_pool(self, pool_id):
        """Creates a node pool.

        :param pool_id: ID of the pool to create
        :returns: None
        :raises NoSuitableLB: Unable to find the load balancer
        """
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=pool_id)

        listeners = pool.listeners
        load_balancer = pool.load_balancer

        create_pool_tf = self._taskflow_load(self._pool_flows.
                                             get_create_pool_flow(),
                                             store={constants.POOL: pool,
                                                    constants.LISTENERS:
                                                        listeners,
                                                    constants.LOADBALANCER:
                                                        load_balancer})
        with tf_logging.DynamicLoggingListener(create_pool_tf,
                                               log=LOG):
            create_pool_tf.run()

    def delete_pool(self, pool_id):
        """Deletes a node pool.

        :param pool_id: ID of the pool to delete
        :returns: None
        :raises PoolNotFound: The referenced pool was not found
        """
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=pool_id)

        load_balancer = pool.load_balancer
        listeners = pool.listeners

        delete_pool_tf = self._taskflow_load(
            self._pool_flows.get_delete_pool_flow(),
            store={constants.POOL: pool, constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(delete_pool_tf,
                                               log=LOG):
            delete_pool_tf.run()

    def update_pool(self, pool_id, pool_updates):
        """Updates a node pool.

        :param pool_id: ID of the pool to update
        :param pool_updates: Dict containing updated pool attributes
        :returns: None
        :raises PoolNotFound: The referenced pool was not found
        """
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=pool_id)

        listeners = pool.listeners
        load_balancer = pool.load_balancer

        update_pool_tf = self._taskflow_load(self._pool_flows.
                                             get_update_pool_flow(),
                                             store={constants.POOL: pool,
                                                    constants.LISTENERS:
                                                        listeners,
                                                    constants.LOADBALANCER:
                                                        load_balancer,
                                                    constants.UPDATE_DICT:
                                                        pool_updates})
        with tf_logging.DynamicLoggingListener(update_pool_tf,
                                               log=LOG):
            update_pool_tf.run()

    def create_l7policy(self, l7policy_id):
        """Creates an L7 Policy.

        :param l7policy_id: ID of the l7policy to create
        :returns: None
        :raises NoSuitableLB: Unable to find the load balancer
        """
        l7policy = self._l7policy_repo.get(db_apis.get_session(),
                                           id=l7policy_id)

        listeners = [l7policy.listener]
        load_balancer = l7policy.listener.load_balancer

        create_l7policy_tf = self._taskflow_load(
            self._l7policy_flows.get_create_l7policy_flow(),
            store={constants.L7POLICY: l7policy,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(create_l7policy_tf,
                                               log=LOG):
            create_l7policy_tf.run()

    def delete_l7policy(self, l7policy_id):
        """Deletes an L7 policy.

        :param l7policy_id: ID of the l7policy to delete
        :returns: None
        :raises L7PolicyNotFound: The referenced l7policy was not found
        """
        l7policy = self._l7policy_repo.get(db_apis.get_session(),
                                           id=l7policy_id)

        load_balancer = l7policy.listener.load_balancer
        listeners = [l7policy.listener]

        delete_l7policy_tf = self._taskflow_load(
            self._l7policy_flows.get_delete_l7policy_flow(),
            store={constants.L7POLICY: l7policy,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(delete_l7policy_tf,
                                               log=LOG):
            delete_l7policy_tf.run()

    def update_l7policy(self, l7policy_id, l7policy_updates):
        """Updates an L7 policy.

        :param l7policy_id: ID of the l7policy to update
        :param l7policy_updates: Dict containing updated l7policy attributes
        :returns: None
        :raises L7PolicyNotFound: The referenced l7policy was not found
        """
        l7policy = self._l7policy_repo.get(db_apis.get_session(),
                                           id=l7policy_id)

        listeners = [l7policy.listener]
        load_balancer = l7policy.listener.load_balancer

        update_l7policy_tf = self._taskflow_load(
            self._l7policy_flows.get_update_l7policy_flow(),
            store={constants.L7POLICY: l7policy,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer,
                   constants.UPDATE_DICT: l7policy_updates})
        with tf_logging.DynamicLoggingListener(update_l7policy_tf,
                                               log=LOG):
            update_l7policy_tf.run()

    def create_l7rule(self, l7rule_id):
        """Creates an L7 Rule.

        :param l7rule_id: ID of the l7rule to create
        :returns: None
        :raises NoSuitableLB: Unable to find the load balancer
        """
        l7rule = self._l7rule_repo.get(db_apis.get_session(),
                                       id=l7rule_id)

        listeners = [l7rule.l7policy.listener]
        load_balancer = l7rule.l7policy.listener.load_balancer

        create_l7rule_tf = self._taskflow_load(
            self._l7rule_flows.get_create_l7rule_flow(),
            store={constants.L7RULE: l7rule,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(create_l7rule_tf,
                                               log=LOG):
            create_l7rule_tf.run()

    def delete_l7rule(self, l7rule_id):
        """Deletes an L7 rule.

        :param l7rule_id: ID of the l7rule to delete
        :returns: None
        :raises L7RuleNotFound: The referenced l7rule was not found
        """
        l7rule = self._l7rule_repo.get(db_apis.get_session(),
                                       id=l7rule_id)

        load_balancer = l7rule.l7policy.listener.load_balancer
        listeners = [l7rule.l7policy.listener]

        delete_l7rule_tf = self._taskflow_load(
            self._l7rule_flows.get_delete_l7rule_flow(),
            store={constants.L7RULE: l7rule,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer})
        with tf_logging.DynamicLoggingListener(delete_l7rule_tf,
                                               log=LOG):
            delete_l7rule_tf.run()

    def update_l7rule(self, l7rule_id, l7rule_updates):
        """Updates an L7 rule.

        :param l7rule_id: ID of the l7rule to update
        :param l7rule_updates: Dict containing updated l7rule attributes
        :returns: None
        :raises L7RuleNotFound: The referenced l7rule was not found
        """
        l7rule = self._l7rule_repo.get(db_apis.get_session(),
                                       id=l7rule_id)

        listeners = [l7rule.l7policy.listener]
        load_balancer = l7rule.l7policy.listener.load_balancer

        update_l7rule_tf = self._taskflow_load(
            self._l7rule_flows.get_update_l7rule_flow(),
            store={constants.L7RULE: l7rule,
                   constants.LISTENERS: listeners,
                   constants.LOADBALANCER: load_balancer,
                   constants.UPDATE_DICT: l7rule_updates})
        with tf_logging.DynamicLoggingListener(update_l7rule_tf,
                                               log=LOG):
            update_l7rule_tf.run()

    def failover_amphora(self, amphora_id):
        """Perform failover operations for an amphora.

        :param amphora_id: ID for amphora to failover
        :returns: None
        :raises AmphoraNotFound: The referenced amphora was not found
        """

        try:
            amp = self._amphora_repo.get(db_apis.get_session(),
                                         id=amphora_id)
            stored_params = {constants.FAILED_AMPHORA: amp,
                             constants.LOADBALANCER_ID: amp.load_balancer_id,
                             constants.BUILD_TYPE_PRIORITY:
                                 constants.LB_CREATE_FAILOVER_PRIORITY}

            if amp.status == constants.DELETED:
                LOG.warning('Amphora %s is marked DELETED in the database '
                            'but was submitted for failover. Marking it busy '
                            'in the amphora health table to exclude it from '
                            'health checks and skipping the failover.',
                            amp.id)
                self._amphora_health_repo.update(db_apis.get_session(), amp.id,
                                                 busy=True)
                return

            # if we run with anti-affinity we need to set the server group
            # as well
            if CONF.nova.enable_anti_affinity:
                lb = self._amphora_repo.get_all_lbs_on_amphora(
                    db_apis.get_session(), amp.id)
                if lb:
                    stored_params[constants.SERVER_GROUP_ID] = (
                        lb[0].server_group_id)

            failover_amphora_tf = self._taskflow_load(
                self._amphora_flows.get_failover_flow(
                    role=amp.role,
                    status=amp.status),
                store=stored_params)
            with tf_logging.DynamicLoggingListener(
                    failover_amphora_tf, log=LOG,
                    hide_inputs_outputs_of=self._exclude_result_logging_tasks):

                failover_amphora_tf.run()

        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error("Failover exception: %s", e)

    def amphora_cert_rotation(self, amphora_id):
        """Perform cert rotation for an amphora.

        :param amphora_id: ID for amphora to rotate
        :returns: None
        :raises AmphoraNotFound: The referenced amphora was not found
        """

        amp = self._amphora_repo.get(db_apis.get_session(),
                                     id=amphora_id)
        LOG.info("Start amphora cert rotation, amphora's id is: %s", amp.id)

        certrotation_amphora_tf = self._taskflow_load(
            self._amphora_flows.cert_rotate_amphora_flow(),
            store={constants.AMPHORA: amp,
                   constants.AMPHORA_ID: amp.id})

        with tf_logging.DynamicLoggingListener(certrotation_amphora_tf,
                                               log=LOG):
            certrotation_amphora_tf.run()
