#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
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

import logging

from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.controllers import health_monitor
from octavia.api.v2.controllers import member
from octavia.api.v2.types import pool as pool_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare
from octavia.i18n import _


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PoolsController(base.BaseController):
    RBAC_TYPE = constants.RBAC_POOL

    def __init__(self):
        super(PoolsController, self).__init__()
        self.handler = self.handler.pool

    @wsme_pecan.wsexpose(pool_types.PoolRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a pool's details."""
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)

        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(db_pool, pool_types.PoolResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return pool_types.PoolRootResponse(pool=result)

    @wsme_pecan.wsexpose(pool_types.PoolsRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, project_id=None, fields=None):
        """Lists all pools."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        db_pools, links = self.repositories.pool.get_all(
            context.session, show_deleted=False,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
            **query_filter)
        result = self._convert_db_to_type(db_pools, [pool_types.PoolResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return pool_types.PoolsRootResponse(pools=result, pools_links=links)

    def _get_affected_listener_ids(self, pool):
        """Gets a list of all listeners this request potentially affects."""
        listener_ids = [l.id for l in pool.listeners]
        return listener_ids

    def _test_lb_and_listener_statuses(self, session, lb_id, listener_ids):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this pool are also
        # mutable
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, lb_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=listener_ids):
            LOG.info("Pool cannot be created or modified because the Load "
                     "Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource=_('Load Balancer'),
                                             id=lb_id)

    def _reset_lb_and_listener_statuses(self, session, lb_id, listener_ids):
        # Setting LB + listeners back to active because this should be a
        # recoverable error
        self.repositories.load_balancer.update(
            session, lb_id,
            provisioning_status=constants.ACTIVE)
        for listener in listener_ids:
            self.repositories.listener.update(
                session, listener,
                provisioning_status=constants.ACTIVE)

    def _validate_create_pool(self, lock_session, pool_dict, listener_id=None):
        """Validate creating pool on load balancer.

        Update database for load balancer and (optional) listener based on
        provisioning status.
        """
        try:
            return self.repositories.create_pool_on_load_balancer(
                lock_session, pool_dict,
                listener_id=listener_id)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.IDAlreadyExists()
        except odb_exceptions.DBError:
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')

    def _send_pool_to_handler(self, session, db_pool, listener_id):
        try:
            LOG.info("Sending Creation of Pool %s to handler", db_pool.id)
            self.handler.create(db_pool)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_and_listener_statuses(
                    lock_session, lb_id=db_pool.load_balancer_id,
                    listener_ids=[listener_id] if listener_id else [])
                # Pool now goes to ERROR
                self.repositories.pool.update(
                    lock_session, db_pool.id,
                    provisioning_status=constants.ERROR)
        db_pool = self._get_db_pool(session, db_pool.id)
        result = self._convert_db_to_type(db_pool, pool_types.PoolResponse)
        return pool_types.PoolRootResponse(pool=result)

    @wsme_pecan.wsexpose(pool_types.PoolRootResponse,
                         body=pool_types.PoolRootPOST, status_code=201)
    def post(self, pool_):
        """Creates a pool on a load balancer or listener.

        Note that this can optionally take a listener_id with which the pool
        should be associated as the listener's default_pool. If specified,
        the pool creation will fail if the listener specified already has
        a default_pool.
        """
        # For some API requests the listener_id will be passed in the
        # pool_dict:
        pool = pool_.pool
        context = pecan.request.context.get('octavia_context')

        if pool.loadbalancer_id:
            pool.project_id = self._get_lb_project_id(context.session,
                                                      pool.loadbalancer_id)
        elif pool.listener_id:
            listener = self.repositories.listener.get(
                context.session, id=pool.listener_id)
            pool.project_id = listener.project_id
            pool.loadbalancer_id = listener.load_balancer_id
        else:
            msg = _("Must provide at least one of: "
                    "loadbalancer_id, listener_id")
            raise exceptions.ValidationException(detail=msg)

        self._auth_validate_action(context, pool.project_id,
                                   constants.RBAC_POST)

        if pool.session_persistence:
            sp_dict = pool.session_persistence.to_dict(render_unsets=False)
            validate.check_session_persistence(sp_dict)

        lock_session = db_api.get_session(autocommit=False)
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    lock_session,
                    data_models.Pool,
                    pool.project_id):
                raise exceptions.QuotaException

            listener_repo = self.repositories.listener
            pool_dict = db_prepare.create_pool(
                pool.to_dict(render_unsets=True))

            listener_id = pool_dict.pop('listener_id', None)
            if listener_id:
                if listener_repo.has_default_pool(lock_session,
                                                  listener_id):
                    raise exceptions.DuplicatePoolEntry()

            self._test_lb_and_listener_statuses(
                lock_session, lb_id=pool_dict['load_balancer_id'],
                listener_ids=[listener_id] if listener_id else [])

            db_pool = self._validate_create_pool(
                lock_session, pool_dict, listener_id)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        return self._send_pool_to_handler(context.session, db_pool,
                                          listener_id=listener_id)

    def _graph_create(self, session, lock_session, pool_dict):
        load_balancer_id = pool_dict['load_balancer_id']
        pool_dict = db_prepare.create_pool(
            pool_dict, load_balancer_id)
        members = pool_dict.pop('members', []) or []
        hm = pool_dict.pop('health_monitor', None)
        db_pool = self._validate_create_pool(
            lock_session, pool_dict)

        # Check quotas for healthmonitors
        if hm and self.repositories.check_quota_met(
                session, lock_session, data_models.HealthMonitor,
                db_pool.project_id):
            raise exceptions.QuotaException

        # Now possibly create a healthmonitor
        new_hm = None
        if hm:
            hm['pool_id'] = db_pool.id
            hm['project_id'] = db_pool.project_id
            new_hm = health_monitor.HealthMonitorController()._graph_create(
                lock_session, hm)

        # Now check quotas for members
        if members and self.repositories.check_quota_met(
                session, lock_session, data_models.Member,
                db_pool.project_id, count=len(members)):
            raise exceptions.QuotaException

        # Now create members
        new_members = []
        for m in members:
            validate.ip_not_reserved(m["ip_address"])

            m['project_id'] = db_pool.project_id
            new_members.append(
                member.MembersController(db_pool.id)._graph_create(
                    lock_session, m))
        return db_pool, new_hm, new_members

    @wsme_pecan.wsexpose(pool_types.PoolRootResponse, wtypes.text,
                         body=pool_types.PoolRootPut, status_code=200)
    def put(self, id, pool_):
        """Updates a pool on a load balancer."""
        pool = pool_.pool
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)

        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_PUT)

        if pool.session_persistence:
            sp_dict = pool.session_persistence.to_dict(render_unsets=False)
            validate.check_session_persistence(sp_dict)

        self._test_lb_and_listener_statuses(
            context.session, lb_id=db_pool.load_balancer_id,
            listener_ids=self._get_affected_listener_ids(db_pool))
        self.repositories.pool.update(
            context.session, db_pool.id,
            provisioning_status=constants.PENDING_UPDATE)

        try:
            LOG.info("Sending Update of Pool %s to handler", id)
            self.handler.update(db_pool, pool)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_and_listener_statuses(
                    lock_session, lb_id=db_pool.load_balancer_id,
                    listener_ids=self._get_affected_listener_ids(db_pool))
                # Pool now goes to ERROR
                self.repositories.pool.update(
                    lock_session, db_pool.id,
                    provisioning_status=constants.ERROR)
        db_pool = self._get_db_pool(context.session, id)
        result = self._convert_db_to_type(db_pool, pool_types.PoolResponse)
        return pool_types.PoolRootResponse(pool=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a pool from a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)
        if len(db_pool.l7policies) > 0:
            raise exceptions.PoolInUseByL7Policy(
                id=db_pool.id, l7policy_id=db_pool.l7policies[0].id)

        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_DELETE)

        if db_pool.provisioning_status == constants.DELETED:
            return

        self._test_lb_and_listener_statuses(
            context.session, lb_id=db_pool.load_balancer_id,
            listener_ids=self._get_affected_listener_ids(db_pool))
        self.repositories.pool.update(
            context.session, db_pool.id,
            provisioning_status=constants.PENDING_DELETE)

        try:
            LOG.info("Sending Deletion of Pool %s to handler", db_pool.id)
            self.handler.delete(db_pool)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_and_listener_statuses(
                    lock_session, lb_id=db_pool.load_balancer_id,
                    listener_ids=self._get_affected_listener_ids(db_pool))
                # Pool now goes to ERROR
                self.repositories.pool.update(
                    lock_session, db_pool.id,
                    provisioning_status=constants.ERROR)

    @pecan.expose()
    def _lookup(self, pool_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the pool passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if pool_id and len(remainder) and remainder[0] == 'members':
            remainder = remainder[1:]
            db_pool = self.repositories.pool.get(context.session, id=pool_id)
            if not db_pool:
                LOG.info("Pool %s not found.", pool_id)
                raise exceptions.NotFound(resource=data_models.Pool._name(),
                                          id=pool_id)
            if remainder:
                return member.MemberController(pool_id=db_pool.id), remainder
            else:
                return member.MembersController(pool_id=db_pool.id), remainder
