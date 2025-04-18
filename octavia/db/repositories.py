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
from typing import Optional

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exception
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils
from sqlalchemy.orm import noload
from sqlalchemy.orm import Session
from sqlalchemy.orm import subqueryload
from sqlalchemy import select
from sqlalchemy.sql.expression import false
from sqlalchemy.sql import func
from sqlalchemy import text
from sqlalchemy import update

from octavia.common import constants as consts
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import utils
from octavia.common import validate
from octavia.db import api as db_api
from octavia.db import models

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class BaseRepository:
    model_class = None

    def count(self, session, **filters):
        """Retrieves a count of entities from the database.

        :param session: A Sql Alchemy database session.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: int
        """
        deleted = filters.pop('show_deleted', True)
        model = session.query(self.model_class).filter_by(**filters)

        if not deleted:
            if hasattr(self.model_class, 'status'):
                model = model.filter(
                    self.model_class.status != consts.DELETED)
            else:
                model = model.filter(
                    self.model_class.provisioning_status != consts.DELETED)

        return model.count()

    def create(self, session, **model_kwargs):
        """Base create method for a database entity.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Attributes of the model to insert.
        :returns: octavia.common.data_model
        """
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
        session.delete(model)
        session.flush()

    def delete_batch(self, session, ids=None):
        """Batch deletes by entity ids."""
        ids = ids or []
        for id in ids:
            self.delete(session, id=id)

    def update(self, session, id, **model_kwargs):
        """Updates an entity in the database.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Entity attributes that should be updates.
        :returns: octavia.common.data_model
        """
        tags = model_kwargs.pop('tags', None)
        if tags is not None:
            resource = session.get(self.model_class, id)
            resource.tags = tags
        session.query(self.model_class).filter_by(
            id=id).update(model_kwargs)

    def get(self, session, limited_graph=False, **filters):
        """Retrieves an entity from the database.

        :param session: A Sql Alchemy database session.
        :param limited_graph: Option controls number of processed nodes
                              in the graph. Default (with False) behaviour
                              is recursion iteration through all nodes
                              in the graph via to_data_model. With True value
                              recursion will stop at the first child node.
                              It means, that only limited number of nodes be
                              converted. This logic could be used for specific
                              cases, where information about full graph
                              is unnecessary.
        :param filters: Filters to decide which entity should be retrieved.
        :returns: octavia.common.data_model
        """
        deleted = filters.pop('show_deleted', True)
        model = session.query(self.model_class).filter_by(**filters)

        if not deleted:
            if hasattr(self.model_class, 'status'):
                model = model.filter(
                    self.model_class.status != consts.DELETED)
            else:
                model = model.filter(
                    self.model_class.provisioning_status != consts.DELETED)

        model = model.first()

        if not model:
            return None

        recursion_depth = 0 if limited_graph else None
        return model.to_data_model(recursion_depth=recursion_depth)

    def get_all(self, session, pagination_helper=None,
                query_options=None, limited_graph=False, **filters):

        """Retrieves a list of entities from the database.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param query_options: Optional query options to apply.
        :param limited_graph: Option controls number of processed nodes
                              in the graph. Default (with False) behaviour
                              is recursion iteration through all nodes
                              in the graph via to_data_model. With True value
                              recursion will stop at the first child node.
                              It means, that only limited number of nodes be
                              converted. This logic could be used for specific
                              cases, where information about full graph
                              is unnecessary.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """
        deleted = filters.pop('show_deleted', True)
        query = session.query(self.model_class).filter_by(**filters)
        if query_options:
            query = query.options(query_options)

        if not deleted:
            if hasattr(self.model_class, 'status'):
                query = query.filter(
                    self.model_class.status != consts.DELETED)
            else:
                query = query.filter(
                    self.model_class.provisioning_status != consts.DELETED)

        if pagination_helper:
            model_list, links = pagination_helper.apply(
                query, self.model_class)
        else:
            links = None
            model_list = query.all()
        recursion_depth = 1 if limited_graph else None
        data_model_list = [
            model.to_data_model(recursion_depth=recursion_depth)
            for model in model_list
        ]
        return data_model_list, links

    def exists(self, session, id):
        """Determines whether an entity exists in the database by its id.

        :param session: A Sql Alchemy database session.
        :param id: id of entity to check for existence.
        :returns: octavia.common.data_model
        """
        return bool(session.query(self.model_class).filter_by(id=id).first())

    def get_all_deleted_expiring(self, session, exp_age):
        """Get all previously deleted resources that are now expiring.

        :param session: A Sql Alchemy database session.
        :param exp_age: A standard datetime delta which is used to see for how
                        long can a resource live without updates before
                        it is considered expired
        :returns: A list of resource IDs
                """

        expiry_time = datetime.datetime.utcnow() - exp_age

        query = session.query(self.model_class).filter(
            self.model_class.updated_at < expiry_time)
        if hasattr(self.model_class, 'status'):
            query = query.filter_by(status=consts.DELETED)
        else:
            query = query.filter_by(provisioning_status=consts.DELETED)
        # Do not load any relationship
        query = query.options(noload('*'))
        model_list = query.all()

        id_list = [model.id for model in model_list]
        return id_list


class Repositories:
    def __init__(self):
        self.load_balancer = LoadBalancerRepository()
        self.vip = VipRepository()
        self.additional_vip = AdditionalVipRepository()
        self.health_monitor = HealthMonitorRepository()
        self.session_persistence = SessionPersistenceRepository()
        self.pool = PoolRepository()
        self.member = MemberRepository()
        self.listener = ListenerRepository()
        self.listener_cidr = ListenerCidrRepository()
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
        self.flavor = FlavorRepository()
        self.flavor_profile = FlavorProfileRepository()
        self.availability_zone = AvailabilityZoneRepository()
        self.availability_zone_profile = AvailabilityZoneProfileRepository()
        self.amphora_member_port = AmphoraMemberPortRepository()

    def create_load_balancer_and_vip(self, session, lb_dict, vip_dict,
                                     additional_vip_dicts=None):
        """Inserts load balancer and vip entities into the database.

        Inserts load balancer and vip entities into the database in one
        transaction and returns the data model of the load balancer.

        :param session: A Sql Alchemy database session.
        :param lb_dict: Dictionary representation of a load balancer
        :param vip_dict: Dictionary representation of a vip
        :param additional_vip_dicts: Dict representations of additional vips
        :returns: octavia.common.data_models.LoadBalancer
        """
        additional_vip_dicts = additional_vip_dicts or []
        if not lb_dict.get('id'):
            lb_dict['id'] = uuidutils.generate_uuid()
        lb = models.LoadBalancer(**lb_dict)
        session.add(lb)
        vip_sg_ids = vip_dict.pop(consts.SG_IDS, [])
        vip_dict['load_balancer_id'] = lb_dict['id']
        vip = models.Vip(**vip_dict)
        session.add(vip)
        if vip_sg_ids:
            vip_dict[consts.SG_IDS] = vip_sg_ids
            for vip_sg_id in vip_sg_ids:
                vip_sg = models.VipSecurityGroup(
                    load_balancer_id=lb_dict['id'],
                    sg_id=vip_sg_id)
                session.add(vip_sg)
        for add_vip_dict in additional_vip_dicts:
            add_vip_dict['load_balancer_id'] = lb_dict['id']
            add_vip_dict['network_id'] = vip_dict.get('network_id')
            add_vip_dict['port_id'] = vip_dict.get('port_id')
            add_vip = models.AdditionalVip(**add_vip_dict)
            session.add(add_vip)

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

        # Immediate refresh, as we have found that sqlalchemy will sometimes
        # cache the above query and the pool object may miss the listener_id
        # information
        if listener_id:
            pool = session.query(models.Pool).filter_by(id=db_pool.id).first()
            session.refresh(pool)
        return self.pool.get(session, id=db_pool.id)

    def update_pool_and_sp(self, session, pool_id, pool_dict):
        """Updates a pool and session persistence entity in the database.

        :param session: A Sql Alchemy database session.
        :param pool_dict: Dictionary representation of a pool
        :returns: octavia.common.data_models.Pool
        """
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
        if pool_dict:
            self.pool.update(session, pool_id, **pool_dict)
        session.flush()
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

    def check_quota_met(self, session: Session, _class, project_id, count=1):
        """Checks and updates object quotas.

        This method makes sure the project has available quota
        for the resource and updates the quota to reflect the
        new ussage.

        :param session: Context database session
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

        self.quotas.ensure_project_exists(project_id)

        # Lock the project record in the database to block other quota checks
        #
        # Note: You cannot just use the current count as the in-use
        # value as we don't want to lock the whole resource table
        try:
            quotas = (session.query(models.Quotas)
                      .filter_by(project_id=project_id)
                      .populate_existing()
                      .with_for_update()
                      .first())
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
                return True
            if _class == data_models.Listener:
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
                return True
            if _class == data_models.Pool:
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
                return True
            if _class == data_models.HealthMonitor:
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
                return True
            if _class == data_models.Member:
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
                return True
            if _class == data_models.L7Policy:
                # Decide which quota to use
                if quotas.l7policy is None:
                    l7policy_quota = CONF.quotas.default_l7policy_quota
                else:
                    l7policy_quota = quotas.l7policy
                # Get the current in use count
                if not quotas.in_use_l7policy:
                    # This is to handle the upgrade case
                    l7policy_count = session.query(models.L7Policy).filter(
                        models.L7Policy.project_id == project_id,
                        models.L7Policy.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    l7policy_count = quotas.in_use_l7policy + count
                # Decide if the quota is met
                if (l7policy_count <= l7policy_quota or
                        l7policy_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_l7policy = l7policy_count
                    return False
                return True
            if _class == data_models.L7Rule:
                # Decide which quota to use
                if quotas.l7rule is None:
                    l7rule_quota = CONF.quotas.default_l7rule_quota
                else:
                    l7rule_quota = quotas.l7rule
                # Get the current in use count
                if not quotas.in_use_l7rule:
                    # This is to handle the upgrade case
                    l7rule_count = session.query(models.L7Rule).filter(
                        models.L7Rule.project_id == project_id,
                        models.L7Rule.provisioning_status !=
                        consts.DELETED).count() + count
                else:
                    l7rule_count = quotas.in_use_l7rule + count
                # Decide if the quota is met
                if (l7rule_count <= l7rule_quota or
                        l7rule_quota == consts.QUOTA_UNLIMITED):
                    quotas.in_use_l7rule = l7rule_count
                    return False
                return True
        except db_exception.DBDeadlock as e:
            LOG.warning('Quota project lock timed out for project: %(proj)s',
                        {'proj': project_id})
            raise exceptions.ProjectBusyException() from e
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
            quotas = (lock_session.query(models.Quotas)
                      .filter_by(project_id=project_id)
                      .populate_existing()
                      .with_for_update()
                      .first())
            if not quotas:
                if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                    LOG.error('Quota decrement on %(clss)s called on '
                              'project: %(proj)s with no quota record in '
                              'the database.',
                              {'clss': _class, 'proj': project_id})
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
                                    {'clss': _class, 'proj': project_id})
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
                                    {'clss': _class, 'proj': project_id})
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
                                    {'clss': _class, 'proj': project_id})
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
                                    {'clss': _class, 'proj': project_id})
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
                                    {'clss': _class, 'proj': project_id})
            if _class == data_models.L7Policy:
                if (quotas.in_use_l7policy is not None and
                        quotas.in_use_l7policy > 0):
                    quotas.in_use_l7policy = (
                        quotas.in_use_l7policy - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': _class, 'proj': project_id})
            if _class == data_models.L7Rule:
                if (quotas.in_use_l7rule is not None and
                        quotas.in_use_l7rule > 0):
                    quotas.in_use_l7rule = (
                        quotas.in_use_l7rule - quantity)
                else:
                    if not CONF.api_settings.auth_strategy == consts.NOAUTH:
                        LOG.warning('Quota decrement on %(clss)s called on '
                                    'project: %(proj)s that would cause a '
                                    'negative quota.',
                                    {'clss': _class, 'proj': project_id})
        except db_exception.DBDeadlock as e:
            LOG.warning('Quota project lock timed out for project: %(proj)s',
                        {'proj': project_id})
            raise exceptions.ProjectBusyException() from e

    def get_amphora_stats(self, session, amp_id):
        """Gets the statistics for all listeners on an amphora.

        :param session: A Sql Alchemy database session.
        :param amp_id: The amphora ID to query.
        :returns: An amphora stats dictionary
        """
        columns = (list(models.ListenerStatistics.__table__.columns) +
                   [models.Amphora.load_balancer_id])
        amp_records = (
            session.query(*columns)
            .filter(models.ListenerStatistics.amphora_id == amp_id)
            .filter(models.ListenerStatistics.amphora_id ==
                    models.Amphora.id).all())
        amp_stats = []
        for amp in amp_records:
            amp_stat = {consts.LOADBALANCER_ID: amp.load_balancer_id,
                        consts.LISTENER_ID: amp.listener_id,
                        'id': amp.amphora_id,
                        consts.ACTIVE_CONNECTIONS: amp.active_connections,
                        consts.BYTES_IN: amp.bytes_in,
                        consts.BYTES_OUT: amp.bytes_out,
                        consts.REQUEST_ERRORS: amp.request_errors,
                        consts.TOTAL_CONNECTIONS: amp.total_connections}
            amp_stats.append(amp_stat)
        return amp_stats


class LoadBalancerRepository(BaseRepository):
    model_class = models.LoadBalancer

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of load balancers for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API load
        balancer list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.LoadBalancer.vip),
            subqueryload(models.LoadBalancer.additional_vips),
            (subqueryload(models.LoadBalancer.vip).
             subqueryload(models.Vip.sgs)),
            subqueryload(models.LoadBalancer.amphorae),
            subqueryload(models.LoadBalancer.pools),
            subqueryload(models.LoadBalancer.listeners),
            subqueryload(models.LoadBalancer._tags),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)

    @oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
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
        lb = (session.query(self.model_class)
              .populate_existing()
              .with_for_update()
              .filter_by(id=id).one())
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

    def set_status_for_failover(self, session, id, status,
                                raise_exception=False):
        """Tests and sets a load balancer provisioning status.

        Puts a lock on the load balancer table to check the status of a
        load balancer.  If the status is ACTIVE or ERROR then the status of
        the load balancer is updated and the method returns True.  If the
        status is not ACTIVE, then nothing is done and False is returned.

        :param session: A Sql Alchemy database session.
        :param id: id of Load Balancer
        :param status: Status to set Load Balancer if check passes.
        :param raise_exception: If True, raise ImmutableObject on failure
        :returns: bool
        """
        lb = (session.query(self.model_class)
              .populate_existing()
              .with_for_update()
              .filter_by(id=id).one())
        if lb.provisioning_status not in consts.FAILOVERABLE_STATUSES:
            if raise_exception:
                raise exceptions.ImmutableObject(
                    resource='Load Balancer', id=id)
            return False
        lb.provisioning_status = status
        session.add(lb)
        return True


class VipRepository(BaseRepository):
    model_class = models.Vip

    def update(self, session, load_balancer_id, **model_kwargs):
        """Updates a vip entity in the database by load_balancer_id."""
        sg_ids = model_kwargs.pop(consts.SG_IDS, None)

        vip = session.query(self.model_class).filter_by(
            load_balancer_id=load_balancer_id)
        if model_kwargs:
            vip.update(model_kwargs)

        # NOTE(gthiemonge) the vip must be updated when sg_ids is []
        # (removal of current sg_ids)
        if sg_ids is not None:
            vip = vip.first()
            vip.sgs = [
                models.VipSecurityGroup(
                    load_balancer_id=load_balancer_id,
                    sg_id=sg_id)
                for sg_id in sg_ids]

        session.flush()


class AdditionalVipRepository(BaseRepository):
    model_class = models.AdditionalVip

    def update(self, session, load_balancer_id, subnet_id,
               **model_kwargs):
        """Updates an additional vip entity in the database.

        Uses load_balancer_id + subnet_id.
        """
        session.query(self.model_class).filter_by(
            load_balancer_id=load_balancer_id,
            subnet_id=subnet_id).update(model_kwargs)


class HealthMonitorRepository(BaseRepository):
    model_class = models.HealthMonitor

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of health monitors for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API health
        monitor list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.HealthMonitor.pool),
            subqueryload(models.HealthMonitor._tags),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)


class SessionPersistenceRepository(BaseRepository):
    model_class = models.SessionPersistence

    def update(self, session, pool_id, **model_kwargs):
        """Updates a session persistence entity in the database by pool_id."""
        session.query(self.model_class).filter_by(
            pool_id=pool_id).update(model_kwargs)

    def exists(self, session, pool_id):
        """Checks if session persistence exists on a pool."""
        return bool(session.query(self.model_class).filter_by(
            pool_id=pool_id).first())


class ListenerCidrRepository(BaseRepository):
    model_class = models.ListenerCidr

    def create(self, session, listener_id, allowed_cidrs):
        if allowed_cidrs:
            for cidr in set(allowed_cidrs):
                cidr_dict = {'listener_id': listener_id, 'cidr': cidr}
                model = self.model_class(**cidr_dict)
                session.add(model)

    def update(self, session, listener_id, allowed_cidrs):
        """Updates allowed CIDRs in the database by listener_id."""
        session.query(self.model_class).filter_by(
            listener_id=listener_id).delete()
        self.create(session, listener_id, allowed_cidrs)


class PoolRepository(BaseRepository):
    model_class = models.Pool

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of pools for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API pool
        list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.Pool._default_listeners),
            subqueryload(models.Pool.health_monitor),
            subqueryload(models.Pool.l7policies),
            (subqueryload(models.Pool.l7policies).
             subqueryload(models.L7Policy.l7rules)),
            (subqueryload(models.Pool.l7policies).
             subqueryload(models.L7Policy.listener)),
            subqueryload(models.Pool.load_balancer),
            subqueryload(models.Pool.members),
            subqueryload(models.Pool.session_persistence),
            subqueryload(models.Pool._tags),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)

    def get_children_count(self, session, pool_id):
        hm_count = session.query(models.HealthMonitor).filter(
            models.HealthMonitor.pool_id == pool_id,
            models.HealthMonitor.provisioning_status != consts.DELETED).count()
        member_count = session.query(models.Member).filter(
            models.Member.pool_id == pool_id,
            models.Member.provisioning_status != consts.DELETED).count()

        return (hm_count, member_count)


class MemberRepository(BaseRepository):
    model_class = models.Member

    def get_all_API_list(self, session, pagination_helper=None,
                         limited_graph=False, **filters):
        """Get a list of members for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API member
        list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param limited_graph: Option to avoid recursion iteration through all
                              nodes in the graph via to_data_model
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.Member.pool),
            subqueryload(models.Member._tags),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, limited_graph=limited_graph,
            **filters)

    def delete_members(self, session, member_ids):
        """Batch deletes members from a pool."""
        self.delete_batch(session, member_ids)

    def update_pool_members(self, session, pool_id, **model_kwargs):
        """Updates all of the members of a pool.

        :param session: A Sql Alchemy database session.
        :param pool_id: ID of the pool to update members on.
        :param model_kwargs: Entity attributes that should be updates.
        :returns: octavia.common.data_model
        """
        session.query(self.model_class).filter_by(
            pool_id=pool_id).update(model_kwargs)


class ListenerRepository(BaseRepository):
    model_class = models.Listener

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of listeners for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API listener
        list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.Listener.l7policies),
            subqueryload(models.Listener.load_balancer),
            subqueryload(models.Listener.sni_containers),
            subqueryload(models.Listener._tags),
            subqueryload(models.Listener.allowed_cidrs),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)

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
        listener_db = session.query(self.model_class).filter_by(
            id=id).first()
        if not listener_db:
            raise exceptions.NotFound(
                resource=data_models.Listener._name(), id=id)
        tags = model_kwargs.pop('tags', None)
        if tags is not None:
            resource = session.get(self.model_class, id)
            resource.tags = tags
        # Verify any newly specified default_pool_id exists
        default_pool_id = model_kwargs.get('default_pool_id')
        if default_pool_id:
            self._pool_check(session, default_pool_id, listener_id=id)
        if 'sni_containers' in model_kwargs:
            # sni_container_refs is being updated. It is either being set
            # or unset/cleared. We need to update in DB side.
            containers = model_kwargs.pop('sni_containers', []) or []
            listener_db.sni_containers = []
            if containers:
                listener_db.sni_containers = [
                    models.SNI(listener_id=id,
                               tls_container_id=container_ref)
                    for container_ref in containers]
        if 'allowed_cidrs' in model_kwargs:
            # allowed_cidrs is being updated. It is either being set or
            # unset/cleared. We need to update in DB side.
            allowed_cidrs = model_kwargs.pop('allowed_cidrs', []) or []
            listener_db.allowed_cidrs = []
            if allowed_cidrs:
                listener_db.allowed_cidrs = [
                    models.ListenerCidr(listener_id=id, cidr=cidr)
                    for cidr in allowed_cidrs]
        listener_db.update(model_kwargs)

    def create(self, session, **model_kwargs):
        """Creates a new Listener with some validation."""
        listener_id = model_kwargs.get('id')
        allowed_cidrs = set(model_kwargs.pop('allowed_cidrs', []) or [])
        model_kwargs['allowed_cidrs'] = [
            models.ListenerCidr(listener_id=listener_id, cidr=cidr)
            for cidr in allowed_cidrs]
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

    def prov_status_active_if_not_error(self, session, listener_id):
        """Update provisioning_status to ACTIVE if not already in ERROR."""
        (session.query(self.model_class).filter_by(id=listener_id).
         # Don't mark ERROR or already ACTIVE as ACTIVE
         filter(~self.model_class.provisioning_status.in_(
             [consts.ERROR, consts.ACTIVE])).
         update({self.model_class.provisioning_status: consts.ACTIVE},
                synchronize_session='fetch'))

    def get_port_protocol_cidr_for_lb(self, session, loadbalancer_id):
        # readability variables
        Listener = self.model_class
        ListenerCidr = models.ListenerCidr

        stmt = (select(Listener.protocol,
                       ListenerCidr.cidr,
                       Listener.protocol_port.label(consts.PORT))
                .select_from(Listener)
                .join(models.ListenerCidr,
                      Listener.id == ListenerCidr.listener_id, isouter=True)
                .where(Listener.load_balancer_id == loadbalancer_id))
        rows = session.execute(stmt)

        return [utils.map_protocol_to_nftable_protocol(u._asdict()) for u
                in rows.all()]


class ListenerStatisticsRepository(BaseRepository):
    model_class = models.ListenerStatistics

    def replace(self, session, stats_obj):
        """Create or override a listener's statistics (insert/update)

        :param session: A Sql Alchemy database session
        :param stats_obj: Listener statistics object to store
        :type stats_obj: octavia.common.data_models.ListenerStatistics
        """
        if not stats_obj.amphora_id:
            # amphora_id can't be null, so clone the listener_id
            stats_obj.amphora_id = stats_obj.listener_id

        # TODO(johnsom): This can be simplified/optimized using an "upsert"
        count = session.query(self.model_class).filter_by(
            listener_id=stats_obj.listener_id,
            amphora_id=stats_obj.amphora_id).count()
        if count:
            session.query(self.model_class).filter_by(
                listener_id=stats_obj.listener_id,
                amphora_id=stats_obj.amphora_id).update(
                stats_obj.get_stats(),
                synchronize_session=False)
        else:
            self.create(session, **stats_obj.db_fields())

    def increment(self, session, delta_stats):
        """Updates a listener's statistics, incrementing by the passed deltas.

        :param session: A Sql Alchemy database session
        :param delta_stats: Listener statistics deltas to add
        :type delta_stats: octavia.common.data_models.ListenerStatistics
        """
        if not delta_stats.amphora_id:
            # amphora_id can't be null, so clone the listener_id
            delta_stats.amphora_id = delta_stats.listener_id

        # TODO(johnsom): This can be simplified/optimized using an "upsert"
        count = session.query(self.model_class).filter_by(
            listener_id=delta_stats.listener_id,
            amphora_id=delta_stats.amphora_id).count()
        if count:
            existing_stats = (
                session.query(self.model_class)
                .populate_existing()
                .with_for_update()
                .filter_by(
                    listener_id=delta_stats.listener_id,
                    amphora_id=delta_stats.amphora_id).one())
            existing_stats += delta_stats
            existing_stats.active_connections = (
                delta_stats.active_connections)
        else:
            self.create(session, **delta_stats.db_fields())

    def update(self, session, listener_id, **model_kwargs):
        """Updates a listener's statistics, overriding with the passed values.

        :param session: A Sql Alchemy database session
        :param listener_id: The UUID of the listener to update
        :type listener_id: str
        :param model_kwargs: Entity attributes that should be updated

        """
        session.query(self.model_class).filter_by(
            listener_id=listener_id).update(model_kwargs)


class AmphoraRepository(BaseRepository):
    model_class = models.Amphora

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of amphorae for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API amphora
        list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.Amphora.load_balancer),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)

    def associate(self, session, load_balancer_id, amphora_id):
        """Associates an amphora with a load balancer.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :param amphora_id: The amphora id to associate
        """
        load_balancer = session.query(models.LoadBalancer).filter_by(
            id=load_balancer_id).first()
        amphora = session.query(self.model_class).filter_by(
            id=amphora_id).first()
        load_balancer.amphorae.append(amphora)

    @oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
    def allocate_and_associate(self, session, load_balancer_id,
                               availability_zone=None):
        """Allocate an amphora for a load balancer.

        For v0.5 this is simple, find a free amp and
        associate the lb.  In the future this needs to be
        enhanced.

        :param session: A Sql Alchemy database session.
        :param load_balancer_id: The load balancer id to associate
        :returns: The amphora ID for the load balancer or None
        """
        filters = {
            'status': 'READY',
            'load_balancer_id': None
        }
        if availability_zone:
            LOG.debug("Filtering amps by zone: %s", availability_zone)
            filters['cached_zone'] = availability_zone

        amp = (session.query(self.model_class)
               .populate_existing()
               .with_for_update()
               .filter_by(**filters).first())

        if amp is None:
            return None

        if availability_zone:
            LOG.debug("Found amp: %s in %s", amp.id, amp.cached_zone)
        amp.status = 'ALLOCATED'
        amp.load_balancer_id = load_balancer_id

        return amp.to_data_model()

    @staticmethod
    def get_lb_for_amphora(session, amphora_id):
        """Get all of the load balancers on an amphora.

        :param session: A Sql Alchemy database session.
        :param amphora_id: The amphora id to list the load balancers from
        :returns: [octavia.common.data_model]
        """
        db_lb = (
            # Get LB records
            session.query(models.LoadBalancer)
            # Joined to amphora records
            .filter(models.LoadBalancer.id ==
                    models.Amphora.load_balancer_id)
            # For just this amphora
            .filter(models.Amphora.id == amphora_id)
            # Where the amphora is not DELETED
            .filter(models.Amphora.status != consts.DELETED)
            # And the LB is also not DELETED
            .filter(models.LoadBalancer.provisioning_status !=
                    consts.DELETED)).first()
        if db_lb:
            return db_lb.to_data_model()
        return None

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

        amp = (session.query(self.model_class)
               .populate_existing()
               .with_for_update()
               .filter(
                   self.model_class.status.notin_(
                       [consts.DELETED, consts.PENDING_DELETE]),
                   self.model_class.cert_busy == false(),
                   self.model_class.cert_expiration < expired_date)
               .first())

        if amp is None:
            return None

        amp.cert_busy = True

        return amp.to_data_model()

    def get_lb_for_health_update(self, session, amphora_id):
        """This method is for the health manager status update process.

        This is a time sensitive query that occurs often.
        It is an explicit query as the ORM produces a poorly
        optimized query.

        Use extreme caution making any changes to this query
        as it can impact the scalability of the health manager.
        All changes should be analyzed using SQL "EXPLAIN" to
        make sure only indexes are being used.
        Changes should also be evaluated using the stressHM tool.

        Note: The returned object is flat and not a graph representation
              of the load balancer as it is not needed. This is on
              purpose to optimize the processing time. This is not in
              the normal data model objects.

        :param session: A Sql Alchemy database session.
        :param amphora_id: The amphora ID to lookup the load balancer for.
        :returns: A dictionary containing the required load balancer details.
        """
        rows = session.execute(text(
            "SELECT load_balancer.id, load_balancer.enabled, "
            "load_balancer.provisioning_status AS lb_prov_status, "
            "load_balancer.operating_status AS lb_op_status, "
            "listener.id AS list_id, "
            "listener.operating_status AS list_op_status, "
            "listener.enabled AS list_enabled, "
            "listener.protocol AS list_protocol, "
            "pool.id AS pool_id, "
            "pool.operating_status AS pool_op_status, "
            "member.id AS member_id, "
            "member.operating_status AS mem_op_status from "
            "amphora JOIN load_balancer ON "
            "amphora.load_balancer_id = load_balancer.id LEFT JOIN "
            "listener ON load_balancer.id = listener.load_balancer_id "
            "LEFT JOIN pool ON load_balancer.id = pool.load_balancer_id "
            "LEFT JOIN member ON pool.id = member.pool_id WHERE "
            "amphora.id = :amp_id AND amphora.status != :deleted AND "
            "load_balancer.provisioning_status != :deleted;").bindparams(
                amp_id=amphora_id, deleted=consts.DELETED))

        lb = {}
        listeners = {}
        pools = {}
        for row in rows.mappings():
            if not lb:
                lb['id'] = row['id']
                lb['enabled'] = row['enabled'] == 1
                lb['provisioning_status'] = row['lb_prov_status']
                lb['operating_status'] = row['lb_op_status']
            if row['list_id'] and row['list_id'] not in listeners:
                listener = {'operating_status': row['list_op_status'],
                            'protocol': row['list_protocol'],
                            'enabled': row['list_enabled']}
                listeners[row['list_id']] = listener
            if row['pool_id']:
                if row['pool_id'] in pools and row['member_id']:
                    member = {'operating_status': row['mem_op_status']}
                    pools[row['pool_id']]['members'][row['member_id']] = member
                else:
                    pool = {'operating_status': row['pool_op_status'],
                            'members': {}}
                    if row['member_id']:
                        member = {'operating_status': row['mem_op_status']}
                        pool['members'][row['member_id']] = member
                    pools[row['pool_id']] = pool

        if listeners:
            lb['listeners'] = listeners
        if pools:
            lb['pools'] = pools

        return lb

    def test_and_set_status_for_delete(self, lock_session, id):
        """Tests and sets an amphora status.

        Puts a lock on the amphora table to check the status of the
        amphora. The status must be either AMPHORA_READY or ERROR to
        successfully update the amphora status.

        :param lock_session: A Sql Alchemy database session.
        :param id: id of Load Balancer
        :raises ImmutableObject: The amphora is not in a state that can be
                                 deleted.
        :raises NoResultFound: The amphora was not found or already deleted.
        :returns: None
        """
        amp = (lock_session.query(self.model_class)
               .populate_existing()
               .with_for_update()
               .filter_by(id=id)
               .filter(self.model_class.status != consts.DELETED).one())
        if amp.status not in [consts.AMPHORA_READY, consts.ERROR]:
            raise exceptions.ImmutableObject(resource=consts.AMPHORA, id=id)
        amp.status = consts.PENDING_DELETE
        lock_session.flush()

    def get_amphorae_ids_on_lb(self, session, lb_id):
        """Returns a list of amphora IDs associated with the load balancer

        :param session: A Sql Alchemy database session.
        :param lb_id: A load balancer ID.
        :returns: A list of amphora IDs
        """
        return session.scalars(
            select(
                self.model_class.id
            ).where(
                self.model_class.load_balancer_id == lb_id
            )).all()


class AmphoraBuildReqRepository(BaseRepository):
    model_class = models.AmphoraBuildRequest

    def add_to_build_queue(self, session, amphora_id=None, priority=None):
        """Adds the build request to the table."""
        model = self.model_class(amphora_id=amphora_id, priority=priority)
        session.add(model)

    def update_req_status(self, session, amphora_id=None):
        """Updates the request status."""
        (session.query(self.model_class)
         .filter_by(amphora_id=amphora_id)
         .update({self.model_class.status: 'BUILDING'}))

    def get_highest_priority_build_req(self, session):
        """Fetches build request with highest priority and least created_time.

        priority 20 = failover (highest)
        priority 40 = create_loadbalancer (lowest)
        :param session: A Sql Alchemy database session.
        :returns amphora_id corresponding to highest priority and least created
        time in 'WAITING' status.
        """
        return (session.query(self.model_class.amphora_id)
                .order_by(self.model_class.status.desc())
                .order_by(self.model_class.priority.asc())
                .order_by(self.model_class.created_time.asc())
                .first())[0]

    def delete_all(self, session):
        "Deletes all the build requests."
        session.query(self.model_class).delete()


class AmphoraBuildSlotsRepository(BaseRepository):
    model_class = models.AmphoraBuildSlots

    def get_used_build_slots_count(self, session):
        """Gets the number of build slots in use.

             :returns: Number of current build slots.
        """
        count = session.query(self.model_class.slots_used).one()
        return count[0]

    def update_count(self, session, action='increment'):
        """Increments/Decrements/Resets the number of build_slots used."""
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
        session.query(self.model_class).filter_by(
            amphora_id=amphora_id).update(model_kwargs)

    def replace(self, session, amphora_id, **model_kwargs):
        """replace or insert amphora into database."""
        count = session.query(self.model_class).filter_by(
            amphora_id=amphora_id).count()
        if count:
            session.query(self.model_class).filter_by(
                amphora_id=amphora_id).update(model_kwargs,
                                              synchronize_session=False)
        else:
            model_kwargs['amphora_id'] = amphora_id
            self.create(session, **model_kwargs)

    def check_amphora_health_expired(self, session, amphora_id, exp_age=None):
        """check if a specific amphora is expired in the amphora_health table

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

        expiry_time = datetime.datetime.utcnow() - exp_age

        amphora_model = (
            session.query(models.AmphoraHealth)
            .filter_by(amphora_id=amphora_id)
            .filter(models.AmphoraHealth.last_update > expiry_time)
        ).first()
        # This will return a value if:
        # * there is an entry in the table for this amphora_id
        # AND
        # * the entry was last updated more recently than our expiry_time
        # Receiving any value means that the amp is unexpired.

        # In contrast, we receive no value if:
        # * there is no entry for this amphora_id
        # OR
        # * the entry was last updated before our expiry_time
        # In this case, the amphora is expired.
        return amphora_model is None

    def get_stale_amphora(self,
                          lock_session: Session) -> Optional[models.Amphora]:
        """Retrieves a stale amphora from the health manager database.

        :param lock_session: A Sql Alchemy database autocommit session.
        :returns: [octavia.common.data_model]
        """
        timeout = CONF.health_manager.heartbeat_timeout
        expired_time = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=timeout)

        # Update any amphora that were previously FAILOVER_STOPPED
        # but are no longer expired.
        self.update_failover_stopped(lock_session, expired_time)

        # Handle expired amphora
        expired_ids_query = select(self.model_class.amphora_id).where(
            self.model_class.busy == false()).where(
                self.model_class.last_update < expired_time).subquery()

        expired_count = lock_session.scalar(
            select(func.count()).select_from(expired_ids_query))

        threshold = CONF.health_manager.failover_threshold
        if threshold is not None and expired_count >= threshold:
            LOG.error('Stale amphora count reached the threshold '
                      '(%(th)s). %(count)s amphorae were set into '
                      'FAILOVER_STOPPED status.',
                      {'th': threshold, 'count': expired_count})
            lock_session.execute(
                update(
                    models.Amphora
                ).where(
                    models.Amphora.status.notin_(
                        [consts.DELETED, consts.PENDING_DELETE])
                ).where(
                    models.Amphora.id.in_(expired_ids_query)
                ).values(
                    status=consts.AMPHORA_FAILOVER_STOPPED
                ).execution_options(synchronize_session="fetch"))
            return None

        # We don't want to attempt to failover amphora that are not
        # currently in the ALLOCATED or FAILOVER_STOPPED state.
        # i.e. Not DELETED, PENDING_*, etc.
        allocated_amp_ids_subquery = (
            select(models.Amphora.id).where(
                models.Amphora.status.in_(
                    [consts.AMPHORA_ALLOCATED,
                     consts.AMPHORA_FAILOVER_STOPPED])))

        # Pick one expired amphora for automatic failover
        amp_health = lock_session.query(
            self.model_class
        ).populate_existing(
        ).with_for_update(
        ).filter(
            self.model_class.amphora_id.in_(expired_ids_query)
        ).filter(
            self.model_class.amphora_id.in_(allocated_amp_ids_subquery)
        ).order_by(
            func.random()
        ).limit(1).first()

        if amp_health is None:
            return None

        amp_health.busy = True

        return amp_health.to_data_model()

    def update_failover_stopped(self, lock_session: Session,
                                expired_time: datetime) -> None:
        """Updates the status of amps that are FAILOVER_STOPPED."""
        # Update any FAILOVER_STOPPED amphora that are no longer stale
        # back to ALLOCATED.
        # Note: This uses sqlalchemy 2.0 syntax
        not_expired_ids_subquery = (
            select(self.model_class.amphora_id).where(
                self.model_class.busy == false()
            ).where(
                self.model_class.last_update >= expired_time
            ))

        # Note: mysql and sqlite do not support RETURNING, so we cannot
        #       get back the affected amphora IDs. (09/2022)
        lock_session.execute(
            update(models.Amphora).where(
                models.Amphora.status == consts.AMPHORA_FAILOVER_STOPPED
            ).where(
                models.Amphora.id.in_(not_expired_ids_subquery)
            ).values(
                status=consts.AMPHORA_ALLOCATED
            ).execution_options(synchronize_session="fetch"))


class VRRPGroupRepository(BaseRepository):
    model_class = models.VRRPGroup

    def update(self, session, load_balancer_id, **model_kwargs):
        """Updates a VRRPGroup entry for by load_balancer_id."""
        session.query(self.model_class).filter_by(
            load_balancer_id=load_balancer_id).update(model_kwargs)


class L7RuleRepository(BaseRepository):
    model_class = models.L7Rule

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        """Get a list of L7 Rules for the API list call.

        This get_all returns a data set that is only one level deep
        in the data graph. This is an optimized query for the API L7 Rule
        list method.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """

        # sub-query load the tables we need
        # no-load (blank) the tables we don't need
        query_options = (
            subqueryload(models.L7Rule.l7policy),
            subqueryload(models.L7Rule._tags),
            noload('*'))

        return super().get_all(
            session, pagination_helper=pagination_helper,
            query_options=query_options, **filters)

    def update(self, session, id, **model_kwargs):
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
        if not model_kwargs.get('id'):
            model_kwargs.update(id=uuidutils.generate_uuid())
        if model_kwargs.get('l7policy_id'):
            l7policy_db = session.query(models.L7Policy).filter_by(
                id=model_kwargs.get('l7policy_id')).first()
            model_kwargs.update(l7policy=l7policy_db)
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

    def get_all_API_list(self, session, pagination_helper=None, **filters):
        deleted = filters.pop('show_deleted', True)
        query = session.query(self.model_class).filter_by(
            **filters)

        query = query.options(
            subqueryload(models.L7Policy.l7rules),
            subqueryload(models.L7Policy.listener),
            subqueryload(models.L7Policy.redirect_pool),
            subqueryload(models.L7Policy._tags),
            noload('*'))

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
                model_kwargs.update(redirect_prefix=None)
                model_kwargs.update(redirect_http_code=None)
            elif (l7policy.action ==
                    consts.L7POLICY_ACTION_REDIRECT_TO_URL):
                model_kwargs.update(redirect_pool_id=None)
                model_kwargs.update(redirect_prefix=None)
            elif (l7policy.action ==
                    consts.L7POLICY_ACTION_REDIRECT_TO_POOL):
                model_kwargs.update(redirect_url=None)
                model_kwargs.update(redirect_prefix=None)
                model_kwargs.update(redirect_http_code=None)
            elif (l7policy.action ==
                    consts.L7POLICY_ACTION_REDIRECT_PREFIX):
                model_kwargs.update(redirect_url=None)
                model_kwargs.update(redirect_pool_id=None)

        l7policy_db.update(model_kwargs)

        # Position manipulation must happen outside the other alterations
        # in the previous transaction
        if position is not None:
            listener = (session.query(models.Listener).
                        filter_by(id=l7policy_db.listener_id).first())
            # Immediate refresh, as we have found that sqlalchemy will
            # sometimes cache the above query
            session.refresh(listener)
            l7policy_db = listener.l7policies.pop(l7policy_db.position - 1)
            listener.l7policies.insert(position - 1, l7policy_db)
            listener.l7policies.reorder()
            session.flush()

        return self.get(session, id=id)

    def create(self, session, **model_kwargs):
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
        if model_kwargs.get('listener_id'):
            listener_db = session.query(models.Listener).filter_by(
                id=model_kwargs.get('listener_id')).first()
            model_kwargs.update(listener=listener_db)
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
            # New L7Policy will always be at the end of the list
            l7policy_db = listener.l7policies.pop()
            listener.l7policies.insert(position - 1, l7policy_db)

        listener.l7policies.reorder()
        session.flush()
        l7policy.updated_at = None
        return self.get(session, id=l7policy.id)

    def delete(self, session, id, **filters):
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
        # Immediate refresh, as we have found that sqlalchemy will
        # sometimes cache the above query
        session.refresh(listener)
        listener.l7policies.reorder()
        session.flush()


class QuotasRepository(BaseRepository):
    model_class = models.Quotas

    def update(self, session, project_id, **model_kwargs):
        kwargs_quota = model_kwargs['quota']
        quotas = (
            session.query(self.model_class)
            .filter_by(project_id=project_id)
            .populate_existing()
            .with_for_update().first())
        if not quotas:
            quotas = models.Quotas(project_id=project_id)

        for key, val in kwargs_quota.items():
            setattr(quotas, key, val)
        session.add(quotas)
        session.flush()
        return self.get(session, project_id=project_id)

    # Since this is for the initial quota record creation it locks the table
    # which can lead to recoverable deadlocks. Thus we use the deadlock
    # retry wrapper here. This may not be appropriate for other sessions
    # and or queries. Use with caution.
    @oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
    def ensure_project_exists(self, project_id):
        with db_api.session().begin() as session:
            quotas = self.get(session, project_id=project_id)
            if not quotas:
                # Make sure we have a record to lock
                self.update(session, project_id, quota={})
            session.commit()

    def delete(self, session, project_id):
        quotas = (
            session.query(self.model_class)
            .filter_by(project_id=project_id)
            .populate_existing()
            .with_for_update().first())
        if not quotas:
            raise exceptions.NotFound(
                resource=data_models.Quotas._name(), id=project_id)
        quotas.health_monitor = None
        quotas.load_balancer = None
        quotas.listener = None
        quotas.member = None
        quotas.pool = None
        quotas.l7policy = None
        quotas.l7rule = None
        session.flush()


class _GetALLExceptDELETEDIdMixin:

    def get_all(self, session, pagination_helper=None,
                query_options=None, **filters):

        """Retrieves a list of entities from the database.

        This filters the "DELETED" placeholder from the list.

        :param session: A Sql Alchemy database session.
        :param pagination_helper: Helper to apply pagination and sorting.
        :param query_options: Optional query options to apply.
        :param filters: Filters to decide which entities should be retrieved.
        :returns: [octavia.common.data_model]
        """
        query = session.query(self.model_class).filter_by(**filters)
        if query_options:
            query = query.options(query_options)

        if hasattr(self.model_class, 'id'):
            query = query.filter(self.model_class.id != consts.NIL_UUID)
        else:
            query = query.filter(self.model_class.name != consts.NIL_UUID)

        if pagination_helper:
            model_list, links = pagination_helper.apply(
                query, self.model_class)
        else:
            links = None
            model_list = query.all()

        data_model_list = [model.to_data_model() for model in model_list]
        return data_model_list, links


class FlavorRepository(_GetALLExceptDELETEDIdMixin, BaseRepository):
    model_class = models.Flavor

    def get_flavor_metadata_dict(self, session, flavor_id):
        flavor_metadata_json = (
            session.query(models.FlavorProfile.flavor_data)
            .filter(models.Flavor.id == flavor_id)
            .filter(
                models.Flavor.flavor_profile_id == models.FlavorProfile.id)
            .one()[0])
        result_dict = ({} if flavor_metadata_json is None
                       else jsonutils.loads(flavor_metadata_json))
        return result_dict

    def get_flavor_provider(self, session, flavor_id):
        return (session.query(models.FlavorProfile.provider_name)
                .filter(models.Flavor.id == flavor_id)
                .filter(models.Flavor.flavor_profile_id ==
                        models.FlavorProfile.id).one()[0])

    def delete(self, serial_session, **filters):
        """Sets DELETED LBs flavor_id to NIL_UUID, then removes the flavor

        :param serial_session: A Sql Alchemy database transaction session.
        :param filters: Filters to decide which entity should be deleted.
        :returns: None
        :raises: odb_exceptions.DBReferenceError
        :raises: sqlalchemy.orm.exc.NoResultFound
        """
        (serial_session.query(models.LoadBalancer).
         filter(models.LoadBalancer.flavor_id == filters['id']).
         filter(models.LoadBalancer.provisioning_status == consts.DELETED).
         update({models.LoadBalancer.flavor_id: consts.NIL_UUID},
                synchronize_session=False))
        flavor = (serial_session.query(self.model_class).
                  filter_by(**filters).one())
        serial_session.delete(flavor)


class FlavorProfileRepository(_GetALLExceptDELETEDIdMixin, BaseRepository):
    model_class = models.FlavorProfile


class AvailabilityZoneRepository(_GetALLExceptDELETEDIdMixin, BaseRepository):
    model_class = models.AvailabilityZone

    def get_availability_zone_metadata_dict(self, session,
                                            availability_zone_name):
        availability_zone_metadata_json = (
            session.query(
                models.AvailabilityZoneProfile.availability_zone_data)
            .filter(models.AvailabilityZone.name == availability_zone_name)
            .filter(models.AvailabilityZone.availability_zone_profile_id ==
                    models.AvailabilityZoneProfile.id)
            .one()[0])
        result_dict = (
            {} if availability_zone_metadata_json is None
            else jsonutils.loads(availability_zone_metadata_json))
        return result_dict

    def get_availability_zone_provider(self, session, availability_zone_name):
        return (session.query(models.AvailabilityZoneProfile.provider_name)
                .filter(
                models.AvailabilityZone.name == availability_zone_name)
                .filter(
                models.AvailabilityZone.availability_zone_profile_id ==
                models.AvailabilityZoneProfile.id).one()[0])

    def update(self, session, name, **model_kwargs):
        """Updates an entity in the database.

        :param session: A Sql Alchemy database session.
        :param model_kwargs: Entity attributes that should be updates.
        :returns: octavia.common.data_model
        """
        session.query(self.model_class).filter_by(
            name=name).update(model_kwargs)

    def delete(self, serial_session, **filters):
        """Special delete method for availability_zone.

        Sets DELETED LBs availability_zone to NIL_UUID, then removes the
        availability_zone.

        :param serial_session: A Sql Alchemy database transaction session.
        :param filters: Filters to decide which entity should be deleted.
        :returns: None
        :raises: odb_exceptions.DBReferenceError
        :raises: sqlalchemy.orm.exc.NoResultFound
        """
        (serial_session.query(models.LoadBalancer).
         filter(models.LoadBalancer.availability_zone == filters[consts.NAME]).
         filter(models.LoadBalancer.provisioning_status == consts.DELETED).
         update({models.LoadBalancer.availability_zone: consts.NIL_UUID},
                synchronize_session=False))
        availability_zone = (
            serial_session.query(self.model_class).filter_by(**filters).one())
        serial_session.delete(availability_zone)


class AvailabilityZoneProfileRepository(_GetALLExceptDELETEDIdMixin,
                                        BaseRepository):
    model_class = models.AvailabilityZoneProfile


class AmphoraMemberPortRepository(BaseRepository):
    model_class = models.AmphoraMemberPort

    def get_port_ids(self, session, amphora_id):
        return session.scalars(
            select(
                self.model_class.port_id
            ).where(
                self.model_class.amphora_id == amphora_id
            )).all()
