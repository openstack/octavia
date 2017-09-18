# Copyright 2014 Rackspace
# Copyright 2016 Blue Box, an IBM Company
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

"""
Defines interface for DB access that Resource or Octavia Controllers may
reference
"""

import datetime

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils
from sqlalchemy.orm import joinedload

from octavia.common import constants as consts
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import models

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class BaseRepository(object):
    model_class = None

    def count(self, session, **filters):
        """Retrieves a count of entities from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: int
        """
        return session.query(self.model_class).filter_by(**filters).count()

    def create(self, session, **model_kwargs):
        """Base create method for a database entity.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Attributes of the model to insert.
        :returns: octavia.common.data_model
        """
        with session.begin(subtransactions=True):
            model = self.model_class(**model_kwargs)
            session.add(model)
        return model.to_data_model()

    def delete(self, session, **filters):
        """Deletes an entity from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entity should be deleted.
        :returns: None
        :raises: sqlalchemy.orm.exc.NoResultFound
        """
        model = session.query(self.model_class).filter_by(**filters).one()
        with session.begin(subtransactions=True):
            session.delete(model)
            session.flush()

    def delete_batch(self, session, ids=None):
        """Batch deletes by entity ids."""
        ids = ids or []
        [self.delete(session, id) for id in ids]

    def update(self, session, id, **model_kwargs):
        """Updates an entity in the database.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Entity attributes that should be updates.
        :returns: octavia.common.data_model
        """
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                id=id).update(model_kwargs)

    def get(self, session, **filters):
        """Retrieves an entity from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entity should be retrieved.
        :returns: octavia.common.data_model
        """
        model = session.query(self.model_class).filter_by(**filters).first()
        if not model:
            return
        return model.to_data_model()

    def get_all(self, session, pagination_helper=None, **filters):

        """Retrieves a list of entities from the database.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """
        deleted = filters.pop('show_deleted', True)
        query = session.query(self.model_class).filter_by(**filters)
        # Only make one trip to the database
        query = query.options(joinedload('*'))

        if not deleted:
            query = query.filter(
                self.model_class.provisioning_status != consts.DELETED)

        if pagination_helper:
            model_list, links = pagination_helper.apply(
                query, self.model_class)
        else:
            links = None
            model_list = query.all()

        data_model_list = [model.to_data_model() for model in model_list]
        return data_model_list, links

    def exists(self, session, id):
        """Determines whether an entity exists in the database by its id.

        :param session: A Sql Alchemy database session.
        :param id: id of entity to check for existence.
        :returns: octavia.common.data_model
        """
        return bool(session.query(self.model_class).filter_by(id=id).first())


class Repositories(object):
    def __init__(self):
        self.load_balancer = LoadBalancerRepository()
        self.vip = VipRepository()
        self.health_monitor = HealthMonitorRepository()
        self.session_persistence = SessionPersistenceRepository()
        self.pool = PoolRepository()
        self.member = MemberRepository()
        self.listener = ListenerRepository()
        self.listener_stats = ListenerStatisticsRepository()
        self.amphora = AmphoraRepository()
        self.sni = SNIRepository()
        self.amphorahealth = AmphoraHealthRepository()
        self.vrrpgroup = VRRPGroupRepository()
        self.l7rule = L7RuleRepository()
        self.l7policy = L7PolicyRepository()
        self.amp_build_slots = AmphoraBuildSlotsRepository()
        self.amp_build_req = AmphoraBuildReqRepository()
        self.quotas = QuotasRepository()

    def create_load_balancer_and_vip(self, session, lb_dict, vip_dict):
        """Inserts load balancer and vip entities into the database.

        Inserts load balancer and vip entities into the database in one
        transaction and returns the data model of the load balancer.

        :param session: A Sql Alchemy database session.
        :param lb_dict: Dictionary representation of a load balancer
        :param vip_dict: Dictionary representation of a vip
        :returns: octava.common.data_models.LoadBalancer
        """
        with session.begin(subtransactions=True):
            if not lb_dict.get('id'):
                lb_dict['id'] = uuidutils.generate_uuid()
            lb = models.LoadBalancer(**lb_dict)
            session.add(lb)
            vip_dict['load_balancer_id'] = lb_dict['id']
            vip = models.Vip(**vip_dict)
            session.add(vip)
        return self.load_balancer.get(session, id=lb.id)

    def create_pool_on_load_balancer(self, session, pool_dict,
                                     listener_id=None):
        """Inserts a pool and session persistence entity into the database.

        :param session: A Sql Alchemy database session.
        :param pool_dict: Dictionary representation of a pool
        :param listener_id: Optional listener id that will
                             reference this pool as its default_pool_id
        :returns: octavia.common.data_models.Pool
        """
        with session.begin(subtransactions=True):
            if not pool_dict.get('id'):
                pool_dict['id'] = uuidutils.generate_uuid()
            sp_dict = pool_dict.pop('session_persistence', None)
            db_pool = self.pool.create(session, **pool_dict)
            if sp_dict is not None and sp_dict != {}:
                sp_dict['pool_id'] = pool_dict['id']
                self.session_persistence.create(session, **sp_dict)
            if listener_id:
                self.listener.update(session, listener_id,
                                     default_pool_id=pool_dict['id'])
        return self.pool.get(session, id=db_pool.id)

    def update_pool_and_sp(self, session, pool_id, pool_dict):
        """Updates a pool and session persistence entity in the database.

        :param session: A Sql Alchemy database session.
        :param pool_dict: Dictionary representation of a pool
        :returns: octavia.common.data_models.Pool
        """
        with session.begin(subtransactions=True):
            if 'session_persistence' in pool_dict.keys():
                sp_dict = pool_dict.pop('session_persistence')
                if sp_dict is None or sp_dict == {}:
                    if self.session_persistence.exists(session, pool_id):
                        self.session_persistence.delete(session,
                                                        pool_id=pool_id)
                elif self.session_persistence.exists(session, pool_id):
                    self.session_persistence.update(session, pool_id,
                                                    **sp_dict)
                else:
                    sp_dict['pool_id'] = pool_id
                    self.session_persistence.create(session, **sp_dict)
            # If only the session_persistence is being updated, this will be
            # empty
            if len(pool_dict.keys()) > 0:
                self.pool.update(session, pool_id, **pool_dict)
        return self.pool.get(session, id=pool_id)

    def test_and_set_lb_and_listeners_prov_status(self, session, lb_id,
                                                  lb_prov_status,
                                                  listener_prov_status,
                                                  listener_ids=None,
                                                  pool_id=None,
                                                  l7policy_id=None):
        """Tests and sets a load balancer and listener provisioning status.

        Puts a lock on the load balancer table to check the status of a
        load balancer.  If the status is ACTIVE then the status of the load
        balancer and listener is updated and the method returns True.  If the
        status is not ACTIVE, then nothing is done and False is returned.

        :param session: A Sql Alchemy database session.
        :param lb_id: ID of the Load Balancer to check and lock
        :param lb_prov_status: Status to set Load Balancer and Listener if
                               check passes.
        :param listener_prov_status: Status to set Listeners if check passes
        :param listener_ids: List of IDs of listeners to check and lock
                             (only use this when relevant to the operation)
        :param pool_id: ID of the Pool to check and lock (only use this when
                        relevant to the operation)
        :param l7policy_id: ID of the L7Policy to check and lock (only use this
                            when relevant to the operation)
        :returns: bool
        """
        listener_ids = listener_ids or []
        # Always set the status requested, regardless of whether we have
        # listeners-- sometimes pools will be disassociated with a listener
        # and we still need the LB locked when Pools or subordinate objects
        # are changed.
        success = self.load_balancer.test_and_set_provisioning_status(
            session, lb_id, lb_prov_status)
        if not success:
            return success
        for listener_id in listener_ids:
            self.listener.update(session, listener_id,
                                 provisioning_status=listener_prov_status)
        if pool_id:
            self.pool.update(session, pool_id,
                             provisioning_status=lb_prov_status)
        if l7policy_id:
            self.l7policy.update(session, l7policy_id,
                                 provisioning_status=lb_prov_status)
        return success

    def check_quota_met(self, session, lock_session, _class, project_id,
                        count=1):
        """Checks and updates object quotas.

        This method makes sure the project has available quota
        for the resource and updates the quota to reflect the
        new ussage.

        :param session: Context database session
        :param lock_session: Locking database session (autocommit=False)
        :param _class: Data model object requesting quota
        :param project_id: Project ID requesting quota
        :param count: Number of objects we're going to create (default=1)
        :returns: True if quota is met, False if quota was available
        """
        LOG.debug('Checking quota for project: %(proj)s object: %(obj)s',
                  {'proj': project_id, 'obj': _class})

        # Under noauth everything is admin, so no quota
        if CONF.api_settings.auth_strategy == consts.NOAUTH:
            LOG.debug('Auth strategy is NOAUTH, skipping quota check.')
            return False

        if not project_id:
            raise exceptions.MissingProjectID()

        quotas = self.quotas.get(session, project_id=project_id)
        if not quotas:
            # Make sure we have a record to lock
            self.quotas.update(
                session,
                project_id,
                quota={})
        # Lock the project record in the database to block other quota checks
        #
        # Note: You cannot just use the current count as the in-use
        # value as we don't want to lock the whole resource table
        try:
            quotas = lock_session.query(models.Quotas).filter_by(
                project_id=project_id).with_for_update().first()
            if _class == data_models.LoadBalancer:
                # Decide which quota to use
                if quotas.load_balancer is None:
                    lb_quota = CONF.quotas.default_load_balancer_quota
                else:
                    lb_quota = quotas.load_balancer
                # Get the current in use count
                if not quotas.in_use_load_balancer:
                    # This is to handle the upgrade case
                    lb_count = session.query(models.LoadBalancer).filter(
                        models.LoadBalancer.project_id == project_id,
                        models.LoadBalancer.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    lb_count = quotas.in_use_load_balancer + count
                # Decide if the quota is met
                if lb_count <= lb_quota or lb_quota == consts.QUOTA_UNLIMITED:
                    quotas.in_use_load_balancer = lb_count
                    return False
                else:
                    return True
            elif _class == data_models.Listener:
                # Decide which quota to use
                if quotas.listener is None:
                    listener_quota = CONF.quotas.default_listener_quota
                else:
                    listener_quota = quotas.listener
                # Get the current in use count
                if not quotas.in_use_listener:
                    # This is to handle the upgrade case
                    listener_count = session.query(models.Listener).filter(
                        models.Listener.project_id == project_id,
                        models.Listener.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    listener_count = quotas.in_use_listener + count
                # Decide if the quota is met
                if (listener_count <= listener_quota or
                        listener_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_listener = listener_count
                    return False
                else:
                    return True
            elif _class == data_models.Pool:
                # Decide which quota to use
                if quotas.pool is None:
                    pool_quota = CONF.quotas.default_pool_quota
                else:
                    pool_quota = quotas.pool
                # Get the current in use count
                if not quotas.in_use_pool:
                    # This is to handle the upgrade case
                    pool_count = session.query(models.Pool).filter(
                        models.Pool.project_id == project_id,
                        models.Pool.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    pool_count = quotas.in_use_pool + count
                # Decide if the quota is met
                if (pool_count <= pool_quota or
                        pool_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_pool = pool_count
                    return False
                else:
                    return True
            elif _class == data_models.HealthMonitor:
                # Decide which quota to use
                if quotas.health_monitor is None:
                    hm_quota = CONF.quotas.default_health_monitor_quota
                else:
                    hm_quota = quotas.health_monitor
                # Get the current in use count
                if not quotas.in_use_health_monitor:
                    # This is to handle the upgrade case
                    hm_count = session.query(models.HealthMonitor).filter(
                        models.HealthMonitor.project_id == project_id,
                        models.HealthMonitor.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    hm_count = quotas.in_use_health_monitor + count
                # Decide if the quota is met
                if (hm_count <= hm_quota or
                        hm_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_health_monitor = hm_count
                    return False
                else:
                    return True
            elif _class == data_models.Member:
                # Decide which quota to use
                if quotas.member is None:
                    member_quota = CONF.quotas.default_member_quota
                else:
                    member_quota = quotas.member
                # Get the current in use count
                if not quotas.in_use_member:
                    # This is to handle the upgrade case
                    member_count = session.query(models.Member).filter(
                        models.Member.project_id == project_id,
                        models.Member.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    member_count = quotas.in_use_member + count
                # Decide if the quota is met
                if (member_count <= member_quota or
                        member_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_member = member_count
                    return False
                else:
                    return True
        except db_exception.DBDeadlock:
            LOG.warning('Quota project lock timed out for project: %(proj)s',
                        {'proj': project_id})
            raise exceptions.ProjectBusyException()
        return False

    def decrement_quota(self, lock_session, _class, project_id, quantity=1):
        """Decrements the object quota for a project

        :param lock_session: Locking database session (autocommit=False)
        :param _class: Data model object to decrement quota
        :param project_id: Project ID to decrement quota on
        :param quantity: Quantity of quota to decrement
        :returns: None
        """
        LOG.debug('Decrementing quota by: %(quant)s for project: %(proj)s '
                  'object: %(obj)s',
                  {'quant': quantity, 'proj': project_id, 'obj': _class})

        # Lock the project record in the database to block other quota checks
        try:
            quotas = lock_session.query(models.Quotas).filter_by(
                project_id=project_id).with_for_update().first()
            if not quotas:
                if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                    LOG.error('Quota decrement on %(clss)s called on '
                              'project: %(proj)s with no quota record in '
                              'the database.',
                              {'clss': type(_class), 'proj': project_id})
                return
            if _class == data_models.LoadBalancer:
                if (quotas.in_use_load_balancer is not None and
                        quotas.in_use_load_balancer > 0):
                    quotas.in_use_load_balancer = (
                        quotas.in_use_load_balancer - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': type(_class), 'proj': project_id})
            if _class == data_models.Listener:
                if (quotas.in_use_listener is not None and
                        quotas.in_use_listener > 0):
                    quotas.in_use_listener = (
                        quotas.in_use_listener - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': type(_class), 'proj': project_id})
            if _class == data_models.Pool:
                if (quotas.in_use_pool is not None and
                        quotas.in_use_pool > 0):
                    quotas.in_use_pool = (
                        quotas.in_use_pool - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': type(_class), 'proj': project_id})
            if _class == data_models.HealthMonitor:
                if (quotas.in_use_health_monitor is not None and
                        quotas.in_use_health_monitor > 0):
                    quotas.in_use_health_monitor = (
                        quotas.in_use_health_monitor - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': type(_class), 'proj': project_id})
            if _class == data_models.Member:
                if (quotas.in_use_member is not None and
                        quotas.in_use_member > 0):
                    quotas.in_use_member = (
                        quotas.in_use_member - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': type(_class), 'proj': project_id})
        except db_exception.DBDeadlock:
            LOG.warning('Quota project lock timed out for project: %(proj)s',
                        {'proj': project_id})
            raise exceptions.ProjectBusyException()

    def create_load_balancer_tree(self, session, lock_session, lb_dict):
        listener_dicts = lb_dict.pop('listeners', [])
        vip_dict = lb_dict.pop('vip')
        try:
            if self.check_quota_met(session,
                                    lock_session,
                                    data_models.LoadBalancer,
                                    lb_dict['project_id']):
                raise exceptions.QuotaException
            lb_dm = self.create_load_balancer_and_vip(
                lock_session, lb_dict, vip_dict)
            for listener_dict in listener_dicts:
                # Add listener quota check
                if self.check_quota_met(session,
                                        lock_session,
                                        data_models.Listener,
                                        lb_dict['project_id']):
                    raise exceptions.QuotaException
                pool_dict = listener_dict.pop('default_pool', None)
                l7policies_dict = listener_dict.pop('l7policies', None)
                sni_containers = listener_dict.pop('sni_containers', [])
                if pool_dict:
                    # Add pool quota check
                    if self.check_quota_met(session,
                                            lock_session,
                                            data_models.Pool,
                                            lb_dict['project_id']):
                        raise exceptions.QuotaException
                    hm_dict = pool_dict.pop('health_monitor', None)
                    member_dicts = pool_dict.pop('members', [])
                    sp_dict = pool_dict.pop('session_persistence', None)
                    pool_dict['load_balancer_id'] = lb_dm.id
                    del pool_dict['listener_id']
                    pool_dm = self.pool.create(lock_session, **pool_dict)
                    if sp_dict:
                        sp_dict['pool_id'] = pool_dm.id
                        self.session_persistence.create(lock_session,
                                                        **sp_dict)
                    if hm_dict:
                        # Add hm quota check
                        if self.check_quota_met(session,
                                                lock_session,
                                                data_models.HealthMonitor,
                                                lb_dict['project_id']):
                            raise exceptions.QuotaException
                        hm_dict['id'] = pool_dm.id
                        hm_dict['pool_id'] = pool_dm.id
                        self.health_monitor.create(lock_session, **hm_dict)
                    for r_member_dict in member_dicts:
                        # Add member quota check
                        if self.check_quota_met(session,
                                                lock_session,
                                                data_models.Member,
                                                lb_dict['project_id']):
                            raise exceptions.QuotaException
                        r_member_dict['pool_id'] = pool_dm.id
                        self.member.create(lock_session, **r_member_dict)
                    listener_dict['default_pool_id'] = pool_dm.id
                self.listener.create(lock_session, **listener_dict)
                for sni_container in sni_containers:
                    self.sni.create(lock_session, **sni_container)
                if l7policies_dict:
                    for policy_dict in l7policies_dict:
                        l7rules_dict = policy_dict.pop('l7rules')
                        if policy_dict.get('redirect_pool'):
                            # Add pool quota check
                            if self.check_quota_met(session,
                                                    lock_session,
                                                    data_models.Pool,
                                                    lb_dict['project_id']):
                                raise exceptions.QuotaException
                            r_pool_dict = policy_dict.pop(
                                'redirect_pool')
                            r_hm_dict = r_pool_dict.pop('health_monitor',
                                                        None)
                            r_sp_dict = r_pool_dict.pop(
                                'session_persistence', None)
                            r_member_dicts = r_pool_dict.pop('members', [])
                            if 'listener_id' in r_pool_dict.keys():
                                del r_pool_dict['listener_id']
                            r_pool_dm = self.pool.create(lock_session,
                                                         **r_pool_dict)
                            if r_sp_dict:
                                r_sp_dict['pool_id'] = r_pool_dm.id
                                self.session_persistence.create(lock_session,
                                                                **r_sp_dict)
                            if r_hm_dict:
                                # Add hm quota check
                                if self.check_quota_met(
                                        session,
                                        lock_session,
                                        data_models.HealthMonitor,
                                        lb_dict['project_id']):
                                    raise exceptions.QuotaException
                                r_hm_dict['id'] = r_pool_dm.id
                                r_hm_dict['pool_id'] = r_pool_dm.id
                                self.health_monitor.create(lock_session,
                                                           **r_hm_dict)
                            for r_member_dict in r_member_dicts:
                                # Add member quota check
                                if self.check_quota_met(
                                        session,
                                        lock_session,
                                        data_models.Member,
                                        lb_dict['project_id']):
                                    raise exceptions.QuotaException
                                r_member_dict['pool_id'] = r_pool_dm.id
                                self.member.create(lock_session,
                                                   **r_member_dict)
                            policy_dict['redirect_pool_id'] = r_pool_dm.id
                        policy_dm = self.l7policy.create(lock_session,
                                                         **policy_dict)
                        for rule_dict in l7rules_dict:
                            rule_dict['l7policy_id'] = policy_dm.id
                            self.l7rule.create(lock_session, **rule_dict)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        session.expire_all()
        return self.load_balancer.get(session, id=lb_dm.id)


class LoadBalancerRepository(BaseRepository):
    model_class = models.LoadBalancer

    def test_and_set_provisioning_status(self, session, id, status,
                                         raise_exception=False):
        """Tests and sets a load balancer and provisioning status.

        Puts a lock on the load balancer table to check the status of a
        load balancer.  If the status is ACTIVE then the status of the load
        balancer is updated and the method returns True.  If the
        status is not ACTIVE, then nothing is done and False is returned.

        :param session: A Sql Alchemy database session.
        :param id: id of Load Balancer
        :param status: Status to set Load Balancer if check passes.
        :param raise_exception: If True, raise ImmutableObject on failure
        :returns: bool
        """
        with session.begin(subtransactions=True):
            lb = session.query(self.model_class).with_for_update().filter_by(
                id=id).one()
            is_delete = status == consts.PENDING_DELETE
            acceptable_statuses = (
                consts.DELETABLE_STATUSES
                if is_delete else consts.MUTABLE_STATUSES
            )
            if lb.provisioning_status not in acceptable_statuses:
                if raise_exception:
                    raise exceptions.ImmutableObject(
                        resource='Load Balancer', id=id)
                return False
            lb.provisioning_status = status
            session.add(lb)
            return True

    def check_load_balancer_expired(self, session, lb_id, exp_age=None):
        """Checks if a given load balancer is expired.

        :param session: A Sql Alchemy database session.
        :param lb_id: id of an load balancer object
        :param exp_age: A standard datetime delta which is used to see for how
                        long can a load balancer live without updates before
                        it is considered expired (default:
                        CONF.house_keeping.load_balancer_expiry_age)
        :returns: boolean
        """
        if not exp_age:
            exp_age = datetime.timedelta(
                seconds=CONF.house_keeping.load_balancer_expiry_age)

        timestamp = datetime.datetime.utcnow() - exp_age
        lb = self.get(session, id=lb_id)
        if lb:
            # If a load balancer was never updated use its creation timestamp
            last_update = lb.updated_at or lb.created_at
            return last_update < timestamp
        else:
            # Load balancer was just deleted.
            return True


class VipRepository(BaseRepository):
    model_class = models.Vip

    def update(self, session, load_balancer_id, **model_kwargs):
        """Updates a vip entity in the database by load_balancer_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                load_balancer_id=load_balancer_id).update(model_kwargs)


class HealthMonitorRepository(BaseRepository):
    model_class = models.HealthMonitor


class SessionPersistenceRepository(BaseRepository):
    model_class = models.SessionPersistence

    def update(self, session, pool_id, **model_kwargs):
        """Updates a session persistence entity in the database by pool_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                pool_id=pool_id).update(model_kwargs)

    def exists(self, session, pool_id):
        """Checks if session persistence exists on a pool."""
        return bool(session.query(self.model_class).filter_by(
            pool_id=pool_id).first())


class PoolRepository(BaseRepository):
    model_class = models.Pool


class MemberRepository(BaseRepository):
    model_class = models.Member

    def delete_members(self, session, member_ids):
        """Batch deletes members from a pool."""
        self.delete_batch(session, member_ids)


class ListenerRepository(BaseRepository):
    model_class = models.Listener

    def _find_next_peer_port(self, session, lb_id):
        """Finds the next available peer port on the load balancer."""
        max_peer_port = 0
        load_balancer = session.query(models.LoadBalancer).filter_by(
            id=lb_id).first()
        for listener in load_balancer.listeners:
            if (listener.peer_port is not None and
                    listener.peer_port > max_peer_port):
                max_peer_port = listener.peer_port
        if max_peer_port == 0:
            return consts.HAPROXY_BASE_PEER_PORT
        else:
            return max_peer_port + 1

    def _pool_check(self, session, pool_id, listener_id=None,
                    lb_id=None):
        """Sanity checks for default_pool_id if specified."""
        # Pool must exist on same loadbalancer as listener
        pool_db = None
        if listener_id:
            lb_subquery = (session.query(self.model_class.load_balancer_id).
                           filter_by(id=listener_id).subquery())
            pool_db = (session.query(models.Pool).
                       filter_by(id=pool_id).
                       filter(models.LoadBalancer.id.in_(lb_subquery)).first())
        elif lb_id:
            pool_db = (session.query(models.Pool).
                       filter_by(id=pool_id).
                       filter_by(load_balancer_id=lb_id).first())
        if not pool_db:
            raise exceptions.NotFound(
                resource=data_models.Pool._name(), id=pool_id)
        return pool_db

    def has_default_pool(self, session, id):
        """Checks if a listener has a default pool."""
        listener = self.get(session, id=id)
        return bool(listener.default_pool)

    def update(self, session, id, **model_kwargs):
        with session.begin(subtransactions=True):
            listener_db = session.query(self.model_class).filter_by(
                id=id).first()
            # Verify any newly specified default_pool_id exists
            default_pool_id = model_kwargs.get('default_pool_id')
            if default_pool_id:
                self._pool_check(session, default_pool_id, listener_id=id)
            sni_containers = model_kwargs.pop('sni_containers', [])
            for container_ref in sni_containers:
                sni = models.SNI(listener_id=id,
                                 tls_certificate_id=container_ref)
                listener_db.sni_containers.append(sni)
            listener_db.update(model_kwargs)

    def create(self, session, **model_kwargs):
        """Creates a new Listener with some validation."""
        with session.begin(subtransactions=True):
            model = self.model_class(**model_kwargs)
            if model.default_pool_id:
                model.default_pool = self._pool_check(
                    session, model.default_pool_id,
                    lb_id=model.load_balancer_id)
            if model.peer_port is None:
                model.peer_port = self._find_next_peer_port(
                    session, lb_id=model.load_balancer_id)
            session.add(model)
        return model.to_data_model()


class ListenerStatisticsRepository(BaseRepository):
    model_class = models.ListenerStatistics

    def replace(self, session, listener_id, amphora_id, **model_kwargs):
        """replace or insert listener into database."""
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                listener_id=listener_id, amphora_id=amphora_id).count()
            if count:
                session.query(self.model_class).filter_by(
                    listener_id=listener_id,
                    amphora_id=amphora_id).update(
                    model_kwargs,
                    synchronize_session=False)
            else:
                model_kwargs['listener_id'] = listener_id
                model_kwargs['amphora_id'] = amphora_id
                self.create(session, **model_kwargs)

    def update(self, session, listener_id, **model_kwargs):
        """Updates a listener's statistics by a listener's id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                listener_id=listener_id).update(model_kwargs)


class AmphoraRepository(BaseRepository):
    model_class = models.Amphora

    def associate(self, session, load_balancer_id, amphora_id):
        """Associates an amphora with a load balancer.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :param amphora_id: The amphora id to associate
        """
        with session.begin(subtransactions=True):
            load_balancer = session.query(models.LoadBalancer).filter_by(
                id=load_balancer_id).first()
            amphora = session.query(self.model_class).filter_by(
                id=amphora_id).first()
            load_balancer.amphorae.append(amphora)

    def allocate_and_associate(self, session, load_balancer_id):
        """Allocate an amphora for a load balancer.

        For v0.5 this is simple, find a free amp and
        associate the lb.  In the future this needs to be
        enhanced.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :returns: The amphora ID for the load balancer or None
        """
        with session.begin(subtransactions=True):
            amp = session.query(self.model_class).with_for_update().filter_by(
                status='READY', load_balancer_id=None).first()

            if amp is None:
                return None

            amp.status = 'ALLOCATED'
            amp.load_balancer_id = load_balancer_id

        return amp.to_data_model()

    def get_all_lbs_on_amphora(self, session, amphora_id):
        """Get all of the load balancers on an amphora.

        :param session: A Sql Alchemy database session.
        :param amphora_id: The amphora id to list the load balancers from
        :returns: [octavia.common.data_model]
        """
        with session.begin(subtransactions=True):
            lb_subquery = (session.query(self.model_class.load_balancer_id).
                           filter_by(id=amphora_id).subquery())
            lb_list = (session.query(models.LoadBalancer).
                       filter(models.LoadBalancer.id.in_(lb_subquery)).
                       options(joinedload('*')).all())
            data_model_list = [model.to_data_model() for model in lb_list]
            return data_model_list

    def get_spare_amphora_count(self, session):
        """Get the count of the spare amphora.

        :returns: Number of current spare amphora.
        """
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                status=consts.AMPHORA_READY, load_balancer_id=None).count()

        return count

    def get_cert_expiring_amphora(self, session):
        """Retrieves an amphora whose cert is close to expiring..

        :param session: A Sql Alchemy database session.
        :returns: one amphora with expiring certificate
        """
        # get amphorae with certs that will expire within the
        # configured buffer period, so we can rotate their certs ahead of time
        expired_seconds = CONF.house_keeping.cert_expiry_buffer
        expired_date = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=expired_seconds)

        with session.begin(subtransactions=True):
            amp = session.query(self.model_class).with_for_update().filter_by(
                cert_busy=False).filter(
                self.model_class.cert_expiration < expired_date).first()

            if amp is None:
                return None

            amp.cert_busy = True

        return amp.to_data_model()


class AmphoraBuildReqRepository(BaseRepository):
    model_class = models.AmphoraBuildRequest

    def add_to_build_queue(self, session, amphora_id=None, priority=None):
        """Adds the build request to the table."""
        with session.begin(subtransactions=True):
            model = self.model_class(amphora_id=amphora_id, priority=priority)
            session.add(model)

    def update_req_status(self, session, amphora_id=None):
        """Updates the request status."""
        with session.begin(subtransactions=True):
            (session.query(self.model_class)
             .filter_by(amphora_id=amphora_id)
             .update({self.model_class.status: 'BUILDING'}))

    def get_highest_priority_build_req(self, session):
        """Fetches build request with highest priority and least created_time.

        priority 20 = failover (highest)
        priority 40 = create_loadbalancer
        priority 60 = sparespool (least)
        :param session: A Sql Alchemy database session.
        :returns amphora_id corresponding to highest priority and least created
        time in 'WAITING' status.
        """
        with session.begin(subtransactions=True):
            return (session.query(self.model_class.amphora_id)
                    .order_by(self.model_class.status.desc())
                    .order_by(self.model_class.priority.asc())
                    .order_by(self.model_class.created_time.asc())
                    .first())[0]

    def delete_all(self, session):
        "Deletes all the build requests."
        with session.begin(subtransactions=True):
            session.query(self.model_class).delete()


class AmphoraBuildSlotsRepository(BaseRepository):
    model_class = models.AmphoraBuildSlots

    def get_used_build_slots_count(self, session):
        """Gets the number of build slots in use.

             :returns: Number of current build slots.
        """
        with session.begin(subtransactions=True):
            count = session.query(self.model_class.slots_used).one()
        return count[0]

    def update_count(self, session, action='increment'):
        """Increments/Decrements/Resets the number of build_slots used."""
        with session.begin(subtransactions=True):
            if action == 'increment':
                session.query(self.model_class).filter_by(id=1).update(
                    {self.model_class.slots_used:
                     self.get_used_build_slots_count(session) + 1})
            elif action == 'decrement':
                session.query(self.model_class).filter_by(id=1).update(
                    {self.model_class.slots_used:
                     self.get_used_build_slots_count(session) - 1})
            elif action == 'reset':
                session.query(self.model_class).filter_by(id=1).update(
                    {self.model_class.slots_used: 0})


class SNIRepository(BaseRepository):
    model_class = models.SNI

    def update(self, session, listener_id=None, tls_container_id=None,
               **model_kwargs):
        """Updates an SNI entity in the database."""
        if not listener_id and tls_container_id:
            raise exceptions.MissingArguments
        with session.begin(subtransactions=True):
            if listener_id:
                session.query(self.model_class).filter_by(
                    listener_id=listener_id).update(model_kwargs)
            elif tls_container_id:
                session.query(self.model_class).filter_by(
                    tls_container_id=tls_container_id).update(model_kwargs)


class AmphoraHealthRepository(BaseRepository):
    model_class = models.AmphoraHealth

    def update(self, session, amphora_id, **model_kwargs):
        """Updates a healthmanager entity in the database by amphora_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                amphora_id=amphora_id).update(model_kwargs)

    def replace(self, session, amphora_id, **model_kwargs):
        """replace or insert amphora into database."""
        with session.begin(subtransactions=True):
            count = session.query(self.model_class).filter_by(
                amphora_id=amphora_id).count()
            if count:
                session.query(self.model_class).filter_by(
                    amphora_id=amphora_id).update(model_kwargs,
                                                  synchronize_session=False)
            else:
                model_kwargs['amphora_id'] = amphora_id
                self.create(session, **model_kwargs)

    def check_amphora_expired(self, session, amphora_id, exp_age=None):
        """check if a specific amphora is expired

        :param session: A Sql Alchemy database session.
        :param amphora_id: id of an amphora object
        :param exp_age: A standard datetime delta which is used to see for how
                        long can an amphora live without updates before it is
                        considered expired (default:
                        CONF.house_keeping.amphora_expiry_age)
        :returns: boolean
        """
        if not exp_age:
            exp_age = datetime.timedelta(
                seconds=CONF.house_keeping.amphora_expiry_age)

        timestamp = datetime.datetime.utcnow() - exp_age
        amphora_health = self.get(session, amphora_id=amphora_id)
        if amphora_health is not None:
            return amphora_health.last_update < timestamp
        else:
            # Amphora was just destroyed.
            return True

    def get_stale_amphora(self, session):
        """Retrieves a staled amphora from the health manager database.

        :param session: A Sql Alchemy database session.
        :returns: [octavia.common.data_model]
        """

        timeout = CONF.health_manager.heartbeat_timeout
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=timeout)

        amp = session.query(self.model_class).with_for_update().filter_by(
            busy=False).filter(
            self.model_class.last_update < expired_time).first()

        if amp is None:
            return None

        amp.busy = True

        return amp.to_data_model()


class VRRPGroupRepository(BaseRepository):
    model_class = models.VRRPGroup

    def update(self, session, load_balancer_id, **model_kwargs):
        """Updates a VRRPGroup entry for by load_balancer_id."""
        with session.begin(subtransactions=True):
            session.query(self.model_class).filter_by(
                load_balancer_id=load_balancer_id).update(model_kwargs)


class L7RuleRepository(BaseRepository):
    model_class = models.L7Rule

    def update(self, session, id, **model_kwargs):
        with session.begin(subtransactions=True):
            l7rule_db = session.query(self.model_class).filter_by(
                id=id).first()
            if not l7rule_db:
                raise exceptions.NotFound(
                    resource=data_models.L7Rule._name(), id=id)

            l7rule_dict = l7rule_db.to_data_model().to_dict()
            # Ignore values that are None
            for k, v in model_kwargs.items():
                if v is not None:
                    l7rule_dict.update({k: v})
            # Clear out the 'key' attribute for rule types that don't use it.
            if ('type' in l7rule_dict.keys() and
                l7rule_dict['type'] in (consts.L7RULE_TYPE_HOST_NAME,
                                        consts.L7RULE_TYPE_PATH,
                                        consts.L7RULE_TYPE_FILE_TYPE)):
                l7rule_dict['key'] = None
                model_kwargs.update({'key': None})
            validate.l7rule_data(self.model_class(**l7rule_dict))
            l7rule_db.update(model_kwargs)

        l7rule_db = self.get(session, id=id)
        return l7rule_db

    def create(self, session, **model_kwargs):
        with session.begin(subtransactions=True):
            if not model_kwargs.get('id'):
                model_kwargs.update(id=uuidutils.generate_uuid())
            l7rule = self.model_class(**model_kwargs)
            validate.l7rule_data(l7rule)
            session.add(l7rule)

        l7rule_db = self.get(session, id=l7rule.id)
        return l7rule_db


class L7PolicyRepository(BaseRepository):
    model_class = models.L7Policy

    def _pool_check(self, session, pool_id, lb_id, project_id):
        """Sanity checks for the redirect_pool if specified."""
        pool_db = (session.query(models.Pool).
                   filter_by(id=pool_id).
                   filter_by(project_id=project_id).
                   filter_by(load_balancer_id=lb_id).first())
        if not pool_db:
            raise exceptions.NotFound(
                resource=data_models.Pool._name(), id=pool_id)

    def _validate_l7policy_pool_data(self, session, l7policy):
        """Does validations on a given L7 policy."""
        if l7policy.action == consts.L7POLICY_ACTION_REDIRECT_TO_POOL:
            session.expire(session.query(models.Listener).filter_by(
                id=l7policy.listener_id).first())
            listener = (session.query(models.Listener).
                        filter_by(id=l7policy.listener_id).first())
            self._pool_check(session, l7policy.redirect_pool_id,
                             listener.load_balancer_id, listener.project_id)

    def get_all(self, session, pagination_helper=None, **filters):
        deleted = filters.pop('show_deleted', True)
        query = session.query(self.model_class).filter_by(
            **filters)

        if not deleted:
            query = query.filter(
                self.model_class.provisioning_status != consts.DELETED)

        if pagination_helper:
            model_list, links = pagination_helper.apply(
                query, self.model_class)
        else:
            links = None
            model_list = query.order_by(self.model_class.position).all()

        data_model_list = [model.to_data_model() for model in model_list]
        return data_model_list, links

    def update(self, session, id, **model_kwargs):
        with session.begin(subtransactions=True):
            l7policy_db = session.query(self.model_class).filter_by(
                id=id).first()
            if not l7policy_db:
                raise exceptions.NotFound(
                    resource=data_models.L7Policy._name(), id=id)

            # Necessary to work around unexpected / idiotic behavior of
            # the SQLAlchemy Orderinglist extension if the position changes.
            position = model_kwargs.pop('position', None)
            if position == l7policy_db.position:
                position = None

            model_kwargs.update(listener_id=l7policy_db.listener_id)
            l7policy = self.model_class(
                **validate.sanitize_l7policy_api_args(model_kwargs))
            self._validate_l7policy_pool_data(session, l7policy)

            if l7policy.action:
                model_kwargs.update(action=l7policy.action)
                if l7policy.action == consts.L7POLICY_ACTION_REJECT:
                    model_kwargs.update(redirect_url=None)
                    model_kwargs.update(redirect_pool_id=None)
                elif (l7policy.action ==
                        consts.L7POLICY_ACTION_REDIRECT_TO_URL):
                    model_kwargs.update(redirect_pool_id=None)
                elif (l7policy.action ==
                        consts.L7POLICY_ACTION_REDIRECT_TO_POOL):
                    model_kwargs.update(redirect_url=None)

            l7policy_db.update(model_kwargs)

        # Position manipulation must happen outside the other alterations
        # in the previous transaction
        if position is not None:
            listener = (session.query(models.Listener).
                        filter_by(id=l7policy_db.listener_id).first())
            # Immediate refresh, as we have found that sqlalchemy will
            # sometimes cache the above query
            session.refresh(listener)
            with session.begin(subtransactions=True):
                l7policy_db = listener.l7policies.pop(l7policy_db.position - 1)
                listener.l7policies.insert(position - 1, l7policy_db)
            listener.l7policies.reorder()
            session.flush()

        return self.get(session, id=id)

    def create(self, session, **model_kwargs):
        with session.begin(subtransactions=True):
            # We must append the new policy to the end of the collection. We
            # later re-insert it wherever it was requested to appear in order.
            # This is to work around unexpected / idiotic behavior of the
            # SQLAlchemy orderinglist extension.
            position = model_kwargs.pop('position', None)
            model_kwargs.update(position=consts.MAX_POLICY_POSITION)
            if not model_kwargs.get('id'):
                model_kwargs.update(id=uuidutils.generate_uuid())
            if model_kwargs.get('redirect_pool_id'):
                pool_db = session.query(models.Pool).filter_by(
                    id=model_kwargs.get('redirect_pool_id')).first()
                model_kwargs.update(redirect_pool=pool_db)
            l7policy = self.model_class(
                **validate.sanitize_l7policy_api_args(model_kwargs,
                                                      create=True))
            self._validate_l7policy_pool_data(session, l7policy)
            session.add(l7policy)
            session.flush()

        # Must be done outside the transaction which creates the L7Policy
        listener = (session.query(models.Listener).
                    filter_by(id=l7policy.listener_id).first())
        # Immediate refresh, as we have found that sqlalchemy will sometimes
        # cache the above query
        session.refresh(listener)
        session.refresh(l7policy)

        if position is not None and position < len(listener.l7policies) + 1:
            with session.begin(subtransactions=True):
                # New L7Policy will always be at the end of the list
                l7policy_db = listener.l7policies.pop()
                listener.l7policies.insert(position - 1, l7policy_db)

        listener.l7policies.reorder()
        session.flush()
        l7policy.updated_at = None
        return self.get(session, id=l7policy.id)

    def delete(self, session, id, **filters):
        with session.begin(subtransactions=True):
            l7policy_db = session.query(self.model_class).filter_by(
                id=id).first()
            if not l7policy_db:
                raise exceptions.NotFound(
                    resource=data_models.L7Policy._name(), id=id)
            listener_id = l7policy_db.listener_id
            session.delete(l7policy_db)
            session.flush()

        # Must do reorder outside of the delete transaction.
        listener = (session.query(models.Listener).
                    filter_by(id=listener_id).first())
        # Immediate refresh, as we have found that sqlalchemy will sometimes
        # cache the above query
        session.refresh(listener)
        listener.l7policies.reorder()
        session.flush()


class QuotasRepository(BaseRepository):
    model_class = models.Quotas

    def update(self, session, project_id, **model_kwargs):
        with session.begin(subtransactions=True):
            kwargs_quota = model_kwargs['quota']
            quotas = session.query(self.model_class).filter_by(
                project_id=project_id).with_for_update().first()
            if not quotas:
                quotas = models.Quotas(project_id=project_id)

            for key, val in kwargs_quota.items():
                setattr(quotas, key, val)
            session.add(quotas)
            session.flush()
        return self.get(session, project_id=project_id)

    def delete(self, session, project_id):
        with session.begin(subtransactions=True):
            quotas = session.query(self.model_class).filter_by(
                project_id=project_id).with_for_update().first()
            if not quotas:
                raise exceptions.NotFound(
                    resource=data_models.Quotas._name(), id=project_id)
            quotas.health_monitor = None
            quotas.load_balancer = None
            quotas.listener = None
            quotas.member = None
            quotas.pool = None
            session.flush()
