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

from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from sqlalchemy.orm import exc as db_exceptions
from stevedore import driver as stevedore_driver
import tenacity

from octavia.api.drivers import utils as provider_utils
from octavia.common import base_taskflow
from octavia.common import constants
from octavia.common import exceptions
from octavia.common import utils
from octavia.controller.worker.v2.flows import flow_utils
from octavia.controller.worker.v2 import taskflow_jobboard_driver as tsk_driver
from octavia.db import api as db_apis
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def _is_provisioning_status_pending_update(lb_obj):
    return not lb_obj.provisioning_status == constants.PENDING_UPDATE


class ControllerWorker(object):

    def __init__(self):

        self._amphora_repo = repo.AmphoraRepository()
        self._amphora_health_repo = repo.AmphoraHealthRepository()
        self._health_mon_repo = repo.HealthMonitorRepository()
        self._lb_repo = repo.LoadBalancerRepository()
        self._listener_repo = repo.ListenerRepository()
        self._member_repo = repo.MemberRepository()
        self._pool_repo = repo.PoolRepository()
        self._l7policy_repo = repo.L7PolicyRepository()
        self._l7rule_repo = repo.L7RuleRepository()
        self._flavor_repo = repo.FlavorRepository()
        self._az_repo = repo.AvailabilityZoneRepository()

        persistence = tsk_driver.MysqlPersistenceDriver()

        self.jobboard_driver = stevedore_driver.DriverManager(
            namespace='octavia.worker.jobboard_driver',
            name=CONF.task_flow.jobboard_backend_driver,
            invoke_args=(persistence,),
            invoke_on_load=True).driver

    @tenacity.retry(
        retry=(
            tenacity.retry_if_result(_is_provisioning_status_pending_update) |
            tenacity.retry_if_exception_type()),
        wait=tenacity.wait_incrementing(
            CONF.haproxy_amphora.api_db_commit_retry_initial_delay,
            CONF.haproxy_amphora.api_db_commit_retry_backoff,
            CONF.haproxy_amphora.api_db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.haproxy_amphora.api_db_commit_retry_attempts))
    def _get_db_obj_until_pending_update(self, repo, id):

        return repo.get(db_apis.get_session(), id=id)

    @property
    def services_controller(self):
        return base_taskflow.TaskFlowServiceController(self.jobboard_driver)

    def create_amphora(self, availability_zone=None):
        """Creates an Amphora.

        This is used to create spare amphora.

        :returns: uuid
        """
        try:
            store = {constants.BUILD_TYPE_PRIORITY:
                     constants.LB_CREATE_SPARES_POOL_PRIORITY,
                     constants.FLAVOR: None,
                     constants.SERVER_GROUP_ID: None,
                     constants.AVAILABILITY_ZONE: None}
            if availability_zone:
                store[constants.AVAILABILITY_ZONE] = (
                    self._az_repo.get_availability_zone_metadata_dict(
                        db_apis.get_session(), availability_zone))
            job_id = self.services_controller.run_poster(
                flow_utils.get_create_amphora_flow,
                store=store, wait=True)

            return job_id
        except Exception as e:
            LOG.error('Failed to create an amphora due to: %s', str(e))

    def delete_amphora(self, amphora_id):
        """Deletes an existing Amphora.

        :param amphora_id: ID of the amphora to delete
        :returns: None
        :raises AmphoraNotFound: The referenced Amphora was not found
        """
        amphora = self._amphora_repo.get(db_apis.get_session(),
                                         id=amphora_id)
        store = {constants.AMPHORA: amphora.to_dict()}
        self.services_controller.run_poster(
            flow_utils.get_delete_amphora_flow,
            store=store)

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(db_exceptions.NoResultFound),
        wait=tenacity.wait_incrementing(
            CONF.haproxy_amphora.api_db_commit_retry_initial_delay,
            CONF.haproxy_amphora.api_db_commit_retry_backoff,
            CONF.haproxy_amphora.api_db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.haproxy_amphora.api_db_commit_retry_attempts))
    def create_health_monitor(self, health_monitor):
        """Creates a health monitor.

        :param health_monitor: Provider health monitor dict
        :returns: None
        :raises NoResultFound: Unable to find the object
        """
        db_health_monitor = self._health_mon_repo.get(
            db_apis.get_session(),
            id=health_monitor[constants.HEALTHMONITOR_ID])

        if not db_health_monitor:
            LOG.warning('Failed to fetch %s %s from DB. Retrying for up to '
                        '60 seconds.', 'healthmonitor',
                        health_monitor[constants.HEALTHMONITOR_ID])
            raise db_exceptions.NoResultFound

        pool = db_health_monitor.pool
        pool.health_monitor = db_health_monitor
        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))

        store = {constants.HEALTH_MON: health_monitor,
                 constants.POOL_ID: pool.id,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.LOADBALANCER: provider_lb}
        self.services_controller.run_poster(
            flow_utils.get_create_health_monitor_flow,
            store=store)

    def delete_health_monitor(self, health_monitor):
        """Deletes a health monitor.

        :param health_monitor: Provider health monitor dict
        :returns: None
        :raises HMNotFound: The referenced health monitor was not found
        """
        db_health_monitor = self._health_mon_repo.get(
            db_apis.get_session(),
            id=health_monitor[constants.HEALTHMONITOR_ID])

        pool = db_health_monitor.pool
        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))

        store = {constants.HEALTH_MON: health_monitor,
                 constants.POOL_ID: pool.id,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.LOADBALANCER: provider_lb,
                 constants.PROJECT_ID: load_balancer.project_id}
        self.services_controller.run_poster(
            flow_utils.get_delete_health_monitor_flow,
            store=store)

    def update_health_monitor(self, original_health_monitor,
                              health_monitor_updates):
        """Updates a health monitor.

        :param original_health_monitor: Provider health monitor dict
        :param health_monitor_updates: Dict containing updated health monitor
        :returns: None
        :raises HMNotFound: The referenced health monitor was not found
        """
        try:
            db_health_monitor = self._get_db_obj_until_pending_update(
                self._health_mon_repo,
                original_health_monitor[constants.HEALTHMONITOR_ID])
        except tenacity.RetryError as e:
            LOG.warning('Health monitor did not go into %s in 60 seconds. '
                        'This either due to an in-progress Octavia upgrade '
                        'or an overloaded and failing database. Assuming '
                        'an upgrade is in progress and continuing.',
                        constants.PENDING_UPDATE)
            db_health_monitor = e.last_attempt.result()

        pool = db_health_monitor.pool

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))

        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        store = {constants.HEALTH_MON: original_health_monitor,
                 constants.POOL_ID: pool.id,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.LOADBALANCER: provider_lb,
                 constants.UPDATE_DICT: health_monitor_updates}
        self.services_controller.run_poster(
            flow_utils.get_update_health_monitor_flow,
            store=store)

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(db_exceptions.NoResultFound),
        wait=tenacity.wait_incrementing(
            CONF.haproxy_amphora.api_db_commit_retry_initial_delay,
            CONF.haproxy_amphora.api_db_commit_retry_backoff,
            CONF.haproxy_amphora.api_db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.haproxy_amphora.api_db_commit_retry_attempts))
    def create_listener(self, listener):
        """Creates a listener.

        :param listener: A listener provider dictionary.
        :returns: None
        :raises NoResultFound: Unable to find the object
        """
        db_listener = self._listener_repo.get(
            db_apis.get_session(), id=listener[constants.LISTENER_ID])
        if not db_listener:
            LOG.warning('Failed to fetch %s %s from DB. Retrying for up to '
                        '60 seconds.', 'listener',
                        listener[constants.LISTENER_ID])
            raise db_exceptions.NoResultFound

        load_balancer = db_listener.load_balancer
        listeners = load_balancer.listeners
        dict_listeners = []
        for li in listeners:
            dict_listeners.append(
                provider_utils.db_listener_to_provider_listener(li).to_dict())
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        store = {constants.LISTENERS: dict_listeners,
                 constants.LOADBALANCER: provider_lb,
                 constants.LOADBALANCER_ID: load_balancer.id}

        self.services_controller.run_poster(
            flow_utils.get_create_listener_flow,
            store=store)

    def delete_listener(self, listener):
        """Deletes a listener.

        :param listener: A listener provider dictionary to delete
        :returns: None
        :raises ListenerNotFound: The referenced listener was not found
        """
        store = {constants.LISTENER: listener,
                 constants.LOADBALANCER_ID:
                     listener[constants.LOADBALANCER_ID],
                 constants.PROJECT_ID: listener[constants.PROJECT_ID]}
        self.services_controller.run_poster(
            flow_utils.get_delete_listener_flow,
            store=store)

    def update_listener(self, listener, listener_updates):
        """Updates a listener.

        :param listener: A listener provider dictionary to update
        :param listener_updates: Dict containing updated listener attributes
        :returns: None
        :raises ListenerNotFound: The referenced listener was not found
        """
        db_lb = self._lb_repo.get(db_apis.get_session(),
                                  id=listener[constants.LOADBALANCER_ID])
        store = {constants.LISTENER: listener,
                 constants.UPDATE_DICT: listener_updates,
                 constants.LOADBALANCER_ID: db_lb.id,
                 constants.LISTENERS: [listener]}
        self.services_controller.run_poster(
            flow_utils.get_update_listener_flow,
            store=store)

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(db_exceptions.NoResultFound),
        wait=tenacity.wait_incrementing(
            CONF.haproxy_amphora.api_db_commit_retry_initial_delay,
            CONF.haproxy_amphora.api_db_commit_retry_backoff,
            CONF.haproxy_amphora.api_db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.haproxy_amphora.api_db_commit_retry_attempts))
    def create_load_balancer(self, loadbalancer, flavor=None,
                             availability_zone=None):
        """Creates a load balancer by allocating Amphorae.

        First tries to allocate an existing Amphora in READY state.
        If none are available it will attempt to build one specifically
        for this load balancer.

        :param loadbalancer: The dict of load balancer to create
        :returns: None
        :raises NoResultFound: Unable to find the object
        """
        lb = self._lb_repo.get(db_apis.get_session(),
                               id=loadbalancer[constants.LOADBALANCER_ID])
        if not lb:
            LOG.warning('Failed to fetch %s %s from DB. Retrying for up to '
                        '60 seconds.', 'load_balancer',
                        loadbalancer[constants.LOADBALANCER_ID])
            raise db_exceptions.NoResultFound

        store = {lib_consts.LOADBALANCER_ID:
                 loadbalancer[lib_consts.LOADBALANCER_ID],
                 constants.BUILD_TYPE_PRIORITY:
                 constants.LB_CREATE_NORMAL_PRIORITY,
                 lib_consts.FLAVOR: flavor,
                 lib_consts.AVAILABILITY_ZONE: availability_zone}

        topology = lb.topology
        if (not CONF.nova.enable_anti_affinity or
                topology == constants.TOPOLOGY_SINGLE):
            store[constants.SERVER_GROUP_ID] = None

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                lb.listeners)
        )

        store[constants.UPDATE_DICT] = {
            constants.TOPOLOGY: topology
        }
        self.services_controller.run_poster(
            flow_utils.get_create_load_balancer_flow,
            topology, listeners=listeners_dicts,
            store=store)

    def delete_load_balancer(self, load_balancer, cascade=False):
        """Deletes a load balancer by de-allocating Amphorae.

        :param load_balancer: Dict of the load balancer to delete
        :returns: None
        :raises LBNotFound: The referenced load balancer was not found
        """
        loadbalancer_id = load_balancer[constants.LOADBALANCER_ID]
        db_lb = self._lb_repo.get(db_apis.get_session(), id=loadbalancer_id)
        store = {constants.LOADBALANCER: load_balancer,
                 constants.LOADBALANCER_ID: loadbalancer_id,
                 constants.SERVER_GROUP_ID: db_lb.server_group_id,
                 constants.PROJECT_ID: db_lb.project_id}
        if cascade:
            listeners = flow_utils.get_listeners_on_lb(db_lb)
            pools = flow_utils.get_pools_on_lb(db_lb)
            self.services_controller.run_poster(
                flow_utils.get_cascade_delete_load_balancer_flow,
                load_balancer, listeners, pools, store=store)
        else:
            self.services_controller.run_poster(
                flow_utils.get_delete_load_balancer_flow,
                load_balancer, store=store)

    def update_load_balancer(self, original_load_balancer,
                             load_balancer_updates):
        """Updates a load balancer.

        :param original_load_balancer: Dict of the load balancer to update
        :param load_balancer_updates: Dict containing updated load balancer
        :returns: None
        :raises LBNotFound: The referenced load balancer was not found
        """
        store = {constants.LOADBALANCER: original_load_balancer,
                 constants.LOADBALANCER_ID:
                     original_load_balancer[constants.LOADBALANCER_ID],
                 constants.UPDATE_DICT: load_balancer_updates}

        self.services_controller.run_poster(
            flow_utils.get_update_load_balancer_flow,
            store=store)

    def create_member(self, member):
        """Creates a pool member.

        :param member: A member provider dictionary to create
        :returns: None
        :raises NoSuitablePool: Unable to find the node pool
        """
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=member[constants.POOL_ID])
        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))

        store = {
            constants.MEMBER: member,
            constants.LISTENERS: listeners_dicts,
            constants.LOADBALANCER_ID: load_balancer.id,
            constants.LOADBALANCER: provider_lb,
            constants.POOL_ID: pool.id}
        if load_balancer.availability_zone:
            store[constants.AVAILABILITY_ZONE] = (
                self._az_repo.get_availability_zone_metadata_dict(
                    db_apis.get_session(), load_balancer.availability_zone))
        else:
            store[constants.AVAILABILITY_ZONE] = {}

        self.services_controller.run_poster(
            flow_utils.get_create_member_flow,
            store=store)

    def delete_member(self, member):
        """Deletes a pool member.

        :param member: A member provider dictionary to delete
        :returns: None
        :raises MemberNotFound: The referenced member was not found
        """
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=member[constants.POOL_ID])

        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))

        store = {
            constants.MEMBER: member,
            constants.LISTENERS: listeners_dicts,
            constants.LOADBALANCER_ID: load_balancer.id,
            constants.LOADBALANCER: provider_lb,
            constants.POOL_ID: pool.id,
            constants.PROJECT_ID: load_balancer.project_id}
        if load_balancer.availability_zone:
            store[constants.AVAILABILITY_ZONE] = (
                self._az_repo.get_availability_zone_metadata_dict(
                    db_apis.get_session(), load_balancer.availability_zone))
        else:
            store[constants.AVAILABILITY_ZONE] = {}

        self.services_controller.run_poster(
            flow_utils.get_delete_member_flow,
            store=store)

    def batch_update_members(self, old_members, new_members,
                             updated_members):
        updated_members = [
            (provider_utils.db_member_to_provider_member(
                self._member_repo.get(db_apis.get_session(),
                                      id=m.get(constants.ID))).to_dict(),
             m)
            for m in updated_members]
        provider_old_members = [
            provider_utils.db_member_to_provider_member(
                self._member_repo.get(db_apis.get_session(),
                                      id=m.get(constants.ID))).to_dict()
            for m in old_members]
        if old_members:
            pool = self._pool_repo.get(db_apis.get_session(),
                                       id=old_members[0][constants.POOL_ID])
        elif new_members:
            pool = self._pool_repo.get(db_apis.get_session(),
                                       id=new_members[0][constants.POOL_ID])
        else:
            pool = self._pool_repo.get(
                db_apis.get_session(),
                id=updated_members[0][0][constants.POOL_ID])
        load_balancer = pool.load_balancer

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        store = {
            constants.LISTENERS: listeners_dicts,
            constants.LOADBALANCER_ID: load_balancer.id,
            constants.LOADBALANCER: provider_lb,
            constants.POOL_ID: pool.id,
            constants.PROJECT_ID: load_balancer.project_id}
        if load_balancer.availability_zone:
            store[constants.AVAILABILITY_ZONE] = (
                self._az_repo.get_availability_zone_metadata_dict(
                    db_apis.get_session(), load_balancer.availability_zone))
        else:
            store[constants.AVAILABILITY_ZONE] = {}

        self.services_controller.run_poster(
            flow_utils.get_batch_update_members_flow,
            provider_old_members, new_members, updated_members,
            store=store)

    def update_member(self, member, member_updates):
        """Updates a pool member.

        :param member_id: A member provider dictionary  to update
        :param member_updates: Dict containing updated member attributes
        :returns: None
        :raises MemberNotFound: The referenced member was not found
        """
        # TODO(ataraday) when other flows will use dicts - revisit this
        pool = self._pool_repo.get(db_apis.get_session(),
                                   id=member[constants.POOL_ID])
        load_balancer = pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                pool.listeners))
        store = {
            constants.MEMBER: member,
            constants.LISTENERS: listeners_dicts,
            constants.LOADBALANCER_ID: load_balancer.id,
            constants.LOADBALANCER: provider_lb,
            constants.POOL_ID: pool.id,
            constants.UPDATE_DICT: member_updates}
        if load_balancer.availability_zone:
            store[constants.AVAILABILITY_ZONE] = (
                self._az_repo.get_availability_zone_metadata_dict(
                    db_apis.get_session(), load_balancer.availability_zone))
        else:
            store[constants.AVAILABILITY_ZONE] = {}

        self.services_controller.run_poster(
            flow_utils.get_update_member_flow,
            store=store)

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(db_exceptions.NoResultFound),
        wait=tenacity.wait_incrementing(
            CONF.haproxy_amphora.api_db_commit_retry_initial_delay,
            CONF.haproxy_amphora.api_db_commit_retry_backoff,
            CONF.haproxy_amphora.api_db_commit_retry_max),
        stop=tenacity.stop_after_attempt(
            CONF.haproxy_amphora.api_db_commit_retry_attempts))
    def create_pool(self, pool):
        """Creates a node pool.

        :param pool: Provider pool dict to create
        :returns: None
        :raises NoResultFound: Unable to find the object
        """

        # TODO(ataraday) It seems we need to get db pool here anyway to get
        # proper listeners
        db_pool = self._pool_repo.get(db_apis.get_session(),
                                      id=pool[constants.POOL_ID])
        if not db_pool:
            LOG.warning('Failed to fetch %s %s from DB. Retrying for up to '
                        '60 seconds.', 'pool', pool[constants.POOL_ID])
            raise db_exceptions.NoResultFound

        load_balancer = db_pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                db_pool.listeners))

        store = {constants.POOL_ID: pool[constants.POOL_ID],
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.LOADBALANCER: provider_lb}
        self.services_controller.run_poster(
            flow_utils.get_create_pool_flow,
            store=store)

    def delete_pool(self, pool):
        """Deletes a node pool.

        :param pool: Provider pool dict to delete
        :returns: None
        :raises PoolNotFound: The referenced pool was not found
        """
        db_pool = self._pool_repo.get(db_apis.get_session(),
                                      id=pool[constants.POOL_ID])

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                db_pool.listeners))
        load_balancer = db_pool.load_balancer

        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        store = {constants.POOL_ID: pool[constants.POOL_ID],
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER: provider_lb,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.PROJECT_ID: db_pool.project_id}
        self.services_controller.run_poster(
            flow_utils.get_delete_pool_flow,
            store=store)

    def update_pool(self, origin_pool, pool_updates):
        """Updates a node pool.

        :param origin_pool: Provider pool dict to update
        :param pool_updates: Dict containing updated pool attributes
        :returns: None
        :raises PoolNotFound: The referenced pool was not found
        """
        try:
            db_pool = self._get_db_obj_until_pending_update(
                self._pool_repo, origin_pool[constants.POOL_ID])
        except tenacity.RetryError as e:
            LOG.warning('Pool did not go into %s in 60 seconds. '
                        'This either due to an in-progress Octavia upgrade '
                        'or an overloaded and failing database. Assuming '
                        'an upgrade is in progress and continuing.',
                        constants.PENDING_UPDATE)
            db_pool = e.last_attempt.result()

        load_balancer = db_pool.load_balancer
        provider_lb = provider_utils.db_loadbalancer_to_provider_loadbalancer(
            load_balancer).to_dict()

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                db_pool.listeners))

        store = {constants.POOL_ID: db_pool.id,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER: provider_lb,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.UPDATE_DICT: pool_updates}
        self.services_controller.run_poster(
            flow_utils.get_update_pool_flow,
            store=store)

    def create_l7policy(self, l7policy):
        """Creates an L7 Policy.

        :param l7policy: Provider dict of the l7policy to create
        :returns: None
        :raises NoResultFound: Unable to find the object
        """
        db_listener = self._listener_repo.get(
            db_apis.get_session(), id=l7policy[constants.LISTENER_ID])

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_listener]))

        store = {constants.L7POLICY: l7policy,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: db_listener.load_balancer.id
                 }
        self.services_controller.run_poster(
            flow_utils.get_create_l7policy_flow,
            store=store)

    def delete_l7policy(self, l7policy):
        """Deletes an L7 policy.

        :param l7policy: Provider dict of the l7policy to delete
        :returns: None
        :raises L7PolicyNotFound: The referenced l7policy was not found
        """
        db_listener = self._listener_repo.get(
            db_apis.get_session(), id=l7policy[constants.LISTENER_ID])
        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_listener]))

        store = {constants.L7POLICY: l7policy,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: db_listener.load_balancer.id
                 }
        self.services_controller.run_poster(
            flow_utils.get_delete_l7policy_flow,
            store=store)

    def update_l7policy(self, original_l7policy, l7policy_updates):
        """Updates an L7 policy.

        :param l7policy: Provider dict of the l7policy to update
        :param l7policy_updates: Dict containing updated l7policy attributes
        :returns: None
        :raises L7PolicyNotFound: The referenced l7policy was not found
        """
        db_listener = self._listener_repo.get(
            db_apis.get_session(), id=original_l7policy[constants.LISTENER_ID])

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_listener]))

        store = {constants.L7POLICY: original_l7policy,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: db_listener.load_balancer.id,
                 constants.UPDATE_DICT: l7policy_updates}
        self.services_controller.run_poster(
            flow_utils.get_update_l7policy_flow,
            store=store)

    def create_l7rule(self, l7rule):
        """Creates an L7 Rule.

        :param l7rule: Provider dict l7rule
        :returns: None
        :raises NoResultFound: Unable to find the object
        """
        db_l7policy = self._l7policy_repo.get(db_apis.get_session(),
                                              id=l7rule[constants.L7POLICY_ID])

        load_balancer = db_l7policy.listener.load_balancer

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_l7policy.listener]))
        l7policy_dict = provider_utils.db_l7policy_to_provider_l7policy(
            db_l7policy)

        store = {constants.L7RULE: l7rule,
                 constants.L7POLICY: l7policy_dict.to_dict(),
                 constants.L7POLICY_ID: db_l7policy.id,
                 constants.LISTENERS: listeners_dicts,
                 constants.LOADBALANCER_ID: load_balancer.id
                 }
        self.services_controller.run_poster(
            flow_utils.get_create_l7rule_flow,
            store=store)

    def delete_l7rule(self, l7rule):
        """Deletes an L7 rule.

        :param l7rule: Provider dict of the l7rule to delete
        :returns: None
        :raises L7RuleNotFound: The referenced l7rule was not found
        """
        db_l7policy = self._l7policy_repo.get(db_apis.get_session(),
                                              id=l7rule[constants.L7POLICY_ID])
        l7policy = provider_utils.db_l7policy_to_provider_l7policy(db_l7policy)
        load_balancer = db_l7policy.listener.load_balancer

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_l7policy.listener]))

        store = {constants.L7RULE: l7rule,
                 constants.L7POLICY: l7policy.to_dict(),
                 constants.LISTENERS: listeners_dicts,
                 constants.L7POLICY_ID: db_l7policy.id,
                 constants.LOADBALANCER_ID: load_balancer.id
                 }
        self.services_controller.run_poster(
            flow_utils.get_delete_l7rule_flow,
            store=store)

    def update_l7rule(self, original_l7rule, l7rule_updates):
        """Updates an L7 rule.

        :param l7rule: Origin dict of the l7rule to update
        :param l7rule_updates: Dict containing updated l7rule attributes
        :returns: None
        :raises L7RuleNotFound: The referenced l7rule was not found
        """
        db_l7policy = self._l7policy_repo.get(
            db_apis.get_session(), id=original_l7rule[constants.L7POLICY_ID])
        load_balancer = db_l7policy.listener.load_balancer

        listeners_dicts = (
            provider_utils.db_listeners_to_provider_dicts_list_of_dicts(
                [db_l7policy.listener]))
        l7policy_dict = provider_utils.db_l7policy_to_provider_l7policy(
            db_l7policy)

        store = {constants.L7RULE: original_l7rule,
                 constants.L7POLICY: l7policy_dict.to_dict(),
                 constants.LISTENERS: listeners_dicts,
                 constants.L7POLICY_ID: db_l7policy.id,
                 constants.LOADBALANCER_ID: load_balancer.id,
                 constants.UPDATE_DICT: l7rule_updates}
        self.services_controller.run_poster(
            flow_utils.get_update_l7rule_flow,
            store=store)

    def failover_amphora(self, amphora_id):
        """Perform failover operations for an amphora.

        Note: This expects the load balancer to already be in
        provisioning_status=PENDING_UPDATE state.

        :param amphora_id: ID for amphora to failover
        :returns: None
        :raises octavia.common.exceptions.NotFound: The referenced amphora was
                                                    not found
        """
        amphora = None
        try:
            amphora = self._amphora_repo.get(db_apis.get_session(),
                                             id=amphora_id)
            if amphora is None:
                LOG.error('Amphora failover for amphora %s failed because '
                          'there is no record of this amphora in the '
                          'database. Check that the [house_keeping] '
                          'amphora_expiry_age configuration setting is not '
                          'too short. Skipping failover.', amphora_id)
                raise exceptions.NotFound(resource=constants.AMPHORA,
                                          id=amphora_id)

            if amphora.status == constants.DELETED:
                LOG.warning('Amphora %s is marked DELETED in the database but '
                            'was submitted for failover. Deleting it from the '
                            'amphora health table to exclude it from health '
                            'checks and skipping the failover.', amphora.id)
                self._amphora_health_repo.delete(db_apis.get_session(),
                                                 amphora_id=amphora.id)
                return

            loadbalancer = None
            if amphora.load_balancer_id:
                loadbalancer = self._lb_repo.get(db_apis.get_session(),
                                                 id=amphora.load_balancer_id)
            lb_amp_count = None
            if loadbalancer:
                if loadbalancer.topology == constants.TOPOLOGY_ACTIVE_STANDBY:
                    lb_amp_count = 2
                elif loadbalancer.topology == constants.TOPOLOGY_SINGLE:
                    lb_amp_count = 1

            az_metadata = {}
            flavor_dict = {}
            lb_id = None
            vip_dict = {}
            server_group_id = None
            if loadbalancer:
                lb_id = loadbalancer.id
                # Even if the LB doesn't have a flavor, create one and
                # pass through the topology.
                if loadbalancer.flavor_id:
                    flavor_dict = self._flavor_repo.get_flavor_metadata_dict(
                        db_apis.get_session(), loadbalancer.flavor_id)
                    flavor_dict[constants.LOADBALANCER_TOPOLOGY] = (
                        loadbalancer.topology)
                else:
                    flavor_dict = {constants.LOADBALANCER_TOPOLOGY:
                                   loadbalancer.topology}
                if loadbalancer.availability_zone:
                    az_metadata = (
                        self._az_repo.get_availability_zone_metadata_dict(
                            db_apis.get_session(),
                            loadbalancer.availability_zone))
                vip_dict = loadbalancer.vip.to_dict()
                server_group_id = loadbalancer.server_group_id
            provider_lb_dict = (provider_utils.
                                db_loadbalancer_to_provider_loadbalancer)(
                loadbalancer).to_dict() if loadbalancer else loadbalancer

            stored_params = {constants.AVAILABILITY_ZONE: az_metadata,
                             constants.BUILD_TYPE_PRIORITY:
                                 constants.LB_CREATE_FAILOVER_PRIORITY,
                             constants.FLAVOR: flavor_dict,
                             constants.LOADBALANCER: provider_lb_dict,
                             constants.SERVER_GROUP_ID: server_group_id,
                             constants.LOADBALANCER_ID: lb_id,
                             constants.VIP: vip_dict}

            self.services_controller.run_poster(
                flow_utils.get_failover_amphora_flow,
                amphora.to_dict(), lb_amp_count,
                store=stored_params, wait=True)

            LOG.info("Successfully completed the failover for an amphora: %s",
                     {"id": amphora_id,
                      "load_balancer_id": lb_id,
                      "lb_network_ip": amphora.lb_network_ip,
                      "compute_id": amphora.compute_id,
                      "role": amphora.role})

        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=False):
                LOG.exception("Amphora %s failover exception: %s",
                              amphora_id, str(e))
                self._amphora_repo.update(db_apis.get_session(),
                                          amphora_id, status=constants.ERROR)
                if amphora and amphora.load_balancer_id:
                    self._lb_repo.update(
                        db_apis.get_session(), amphora.load_balancer_id,
                        provisioning_status=constants.ERROR)

    @staticmethod
    def _get_amphorae_for_failover(load_balancer):
        """Returns an ordered list of amphora to failover.

        :param load_balancer: The load balancer being failed over.
        :returns: An ordered list of amphora to failover,
                  first amp to failover is last in the list
        :raises octavia.common.exceptions.InvalidTopology: LB has an unknown
                                                           topology.
        """
        if load_balancer.topology == constants.TOPOLOGY_SINGLE:
            # In SINGLE topology, amp failover order does not matter
            return [a.to_dict() for a in load_balancer.amphorae
                    if a.status != constants.DELETED]

        if load_balancer.topology == constants.TOPOLOGY_ACTIVE_STANDBY:
            # In Active/Standby we should preference the standby amp
            # for failover first in case the Active is still able to pass
            # traffic.
            # Note: The active amp can switch at any time and in less than a
            #       second, so this is "best effort".
            amphora_driver = utils.get_amphora_driver()
            timeout_dict = {
                constants.CONN_MAX_RETRIES:
                    CONF.haproxy_amphora.failover_connection_max_retries,
                constants.CONN_RETRY_INTERVAL:
                    CONF.haproxy_amphora.failover_connection_retry_interval}
            amps = []
            selected_amp = None
            for amp in load_balancer.amphorae:
                if amp.status == constants.DELETED:
                    continue
                if selected_amp is None:
                    try:
                        if amphora_driver.get_interface_from_ip(
                                amp, load_balancer.vip.ip_address,
                                timeout_dict):
                            # This is a potential ACTIVE, add it to the list
                            amps.append(amp.to_dict())
                        else:
                            # This one doesn't have the VIP IP, so start
                            # failovers here.
                            selected_amp = amp
                            LOG.debug("Selected amphora %s as the initial "
                                      "failover amphora.", amp.id)
                    except Exception:
                        # This amphora is broken, so start failovers here.
                        selected_amp = amp
                else:
                    # We have already found a STANDBY, so add the rest to the
                    # list without querying them.
                    amps.append(amp.to_dict())
            # Put the selected amphora at the end of the list so it is
            # first to failover.
            if selected_amp:
                amps.append(selected_amp.to_dict())
            return amps

        LOG.error('Unknown load balancer topology found: %s, aborting '
                  'failover.', load_balancer.topology)
        raise exceptions.InvalidTopology(topology=load_balancer.topology)

    def failover_loadbalancer(self, load_balancer_id):
        """Perform failover operations for a load balancer.

        Note: This expects the load balancer to already be in
        provisioning_status=PENDING_UPDATE state.

        :param load_balancer_id: ID for load balancer to failover
        :returns: None
        :raises octavia.commom.exceptions.NotFound: The load balancer was not
                                                    found.
        """
        try:
            lb = self._lb_repo.get(db_apis.get_session(),
                                   id=load_balancer_id)
            if lb is None:
                raise exceptions.NotFound(resource=constants.LOADBALANCER,
                                          id=load_balancer_id)

            # Get the ordered list of amphorae to failover for this LB.
            amps = self._get_amphorae_for_failover(lb)

            if lb.topology == constants.TOPOLOGY_SINGLE:
                if len(amps) != 1:
                    LOG.warning('%d amphorae found on load balancer %s where '
                                'one should exist. Repairing.', len(amps),
                                load_balancer_id)
            elif lb.topology == constants.TOPOLOGY_ACTIVE_STANDBY:

                if len(amps) != 2:
                    LOG.warning('%d amphorae found on load balancer %s where '
                                'two should exist. Repairing.', len(amps),
                                load_balancer_id)
            else:
                LOG.error('Unknown load balancer topology found: %s, aborting '
                          'failover!', lb.topology)
                raise exceptions.InvalidTopology(topology=lb.topology)

            # We must provide a topology in the flavor definition
            # here for the amphora to be created with the correct
            # configuration.
            if lb.flavor_id:
                flavor = self._flavor_repo.get_flavor_metadata_dict(
                    db_apis.get_session(), lb.flavor_id)
                flavor[constants.LOADBALANCER_TOPOLOGY] = lb.topology
            else:
                flavor = {constants.LOADBALANCER_TOPOLOGY: lb.topology}

            provider_lb_dict = (
                provider_utils.db_loadbalancer_to_provider_loadbalancer(
                    lb).to_dict() if lb else lb)

            provider_lb_dict[constants.FLAVOR] = flavor

            stored_params = {constants.LOADBALANCER: provider_lb_dict,
                             constants.BUILD_TYPE_PRIORITY:
                                 constants.LB_CREATE_FAILOVER_PRIORITY,
                             constants.SERVER_GROUP_ID: lb.server_group_id,
                             constants.LOADBALANCER_ID: lb.id,
                             constants.FLAVOR: flavor}

            if lb.availability_zone:
                stored_params[constants.AVAILABILITY_ZONE] = (
                    self._az_repo.get_availability_zone_metadata_dict(
                        db_apis.get_session(), lb.availability_zone))
            else:
                stored_params[constants.AVAILABILITY_ZONE] = {}

            self.services_controller.run_poster(
                flow_utils.get_failover_LB_flow, amps, provider_lb_dict,
                store=stored_params, wait=True)

            LOG.info('Failover of load balancer %s completed successfully.',
                     lb.id)

        except Exception as e:
            with excutils.save_and_reraise_exception(reraise=False):
                LOG.exception("LB %(lbid)s failover exception: %(exc)s",
                              {'lbid': load_balancer_id, 'exc': str(e)})
                self._lb_repo.update(
                    db_apis.get_session(), load_balancer_id,
                    provisioning_status=constants.ERROR)

    def amphora_cert_rotation(self, amphora_id):
        """Perform cert rotation for an amphora.

        :param amphora_id: ID for amphora to rotate
        :returns: None
        :raises AmphoraNotFound: The referenced amphora was not found
        """

        amp = self._amphora_repo.get(db_apis.get_session(),
                                     id=amphora_id)
        LOG.info("Start amphora cert rotation, amphora's id is: %s",
                 amphora_id)

        store = {constants.AMPHORA: amp.to_dict(),
                 constants.AMPHORA_ID: amphora_id}

        self.services_controller.run_poster(
            flow_utils.cert_rotate_amphora_flow,
            store=store)
        LOG.info("Finished amphora cert rotation, amphora's id was: %s",
                 amphora_id)

    def update_amphora_agent_config(self, amphora_id):
        """Update the amphora agent configuration.

        Note: This will update the amphora agent configuration file and
              update the running configuration for mutatable configuration
              items.

        :param amphora_id: ID of the amphora to update.
        :returns: None
        """
        LOG.info("Start amphora agent configuration update, amphora's id "
                 "is: %s", amphora_id)
        amp = self._amphora_repo.get(db_apis.get_session(), id=amphora_id)
        lb = self._amphora_repo.get_lb_for_amphora(db_apis.get_session(),
                                                   amphora_id)
        flavor = {}
        if lb.flavor_id:
            flavor = self._flavor_repo.get_flavor_metadata_dict(
                db_apis.get_session(), lb.flavor_id)

        store = {constants.AMPHORA: amp.to_dict(),
                 constants.FLAVOR: flavor}

        self.services_controller.run_poster(
            flow_utils.update_amphora_config_flow,
            store=store)
        LOG.info("Finished amphora agent configuration update, amphora's id "
                 "was: %s", amphora_id)
