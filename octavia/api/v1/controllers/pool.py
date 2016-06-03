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

from oslo_db import exception as odb_exceptions
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.controllers import health_monitor
from octavia.api.v1.controllers import member
from octavia.api.v1.types import pool as pool_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import prepare as db_prepare
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class PoolsController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id=None):
        super(PoolsController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.handler = self.handler.pool

    @wsme_pecan.wsexpose(pool_types.PoolResponse, wtypes.text)
    def get(self, id):
        """Gets a pool's details."""
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose([pool_types.PoolResponse], wtypes.text)
    def get_all(self, listener_id=None):
        """Lists all pools on a listener or loadbalancer."""
        context = pecan.request.context.get('octavia_context')
        if listener_id is not None:
            self.listener_id = listener_id
        if self.listener_id:
            pools = self._get_db_listener(context.session,
                                          self.listener_id).pools
        else:
            pools = self.repositories.pool.get_all(
                context.session, load_balancer_id=self.load_balancer_id)
        return self._convert_db_to_type(pools, [pool_types.PoolResponse])

    def _get_affected_listener_ids(self, session, pool=None):
        """Gets a list of all listeners this request potentially affects."""
        listener_ids = []
        if pool:
            listener_ids = [l.id for l in pool.listeners]
        if self.listener_id and self.listener_id not in listener_ids:
            listener_ids.append(self.listener_id)
        return listener_ids

    def _test_lb_and_listener_statuses(self, session, pool=None):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this pool are also
        # mutable
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, self.load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, pool)):
            LOG.info(_LI("Pool cannot be created or modified because the Load "
                         "Balancer is in an immutable state"))
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    def _validate_create_pool(self, session, pool_dict):
        """Validate creating pool on load balancer.

        Update database for load balancer and (optional) listener based on
        provisioning status.
        """
        try:
            db_pool = self.repositories.create_pool_on_load_balancer(
                session, pool_dict, listener_id=self.listener_id)
        except odb_exceptions.DBDuplicateEntry as de:
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
        except odb_exceptions.DBError:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            for listener_id in self._get_affected_listener_ids(session):
                self.repositories.listener.update(
                    session, listener_id, provisioning_status=constants.ACTIVE)
            self.repositories.load_balancer.update(
                session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')
        try:
            LOG.info(_LI("Sending Creation of Pool %s to handler"),
                     db_pool.id)
            self.handler.create(db_pool)
        except Exception:
            for listener_id in self._get_affected_listener_ids(session):
                with excutils.save_and_reraise_exception(reraise=False):
                    self.repositories.listener.update(
                        session, listener_id, operating_status=constants.ERROR)
        db_pool = self._get_db_pool(session, db_pool.id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose(pool_types.PoolResponse, body=pool_types.PoolPOST,
                         status_code=202)
    def post(self, pool):
        """Creates a pool on a load balancer or listener.

        Note that this can optionally take a listener_id with which the pool
        should be associated as the listener's default_pool. If specified,
        the pool creation will fail if the listener specified already has
        a default_pool.
        """
        # For some API requests the listener_id will be passed in the
        # pool_dict:
        context = pecan.request.context.get('octavia_context')
        pool_dict = db_prepare.create_pool(pool.to_dict(render_unsets=True))
        if 'listener_id' in pool_dict:
            if pool_dict['listener_id'] is not None:
                self.listener_id = pool_dict.pop('listener_id')
            else:
                del pool_dict['listener_id']
        if self.listener_id and self.repositories.listener.has_default_pool(
                context.session, self.listener_id):
            raise exceptions.DuplicatePoolEntry()
        self._test_lb_and_listener_statuses(context.session)

        pool_dict['operating_status'] = constants.OFFLINE
        pool_dict['load_balancer_id'] = self.load_balancer_id

        return self._validate_create_pool(context.session, pool_dict)

    @wsme_pecan.wsexpose(pool_types.PoolResponse, wtypes.text,
                         body=pool_types.PoolPUT, status_code=202)
    def put(self, id, pool):
        """Updates a pool on a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)
        self._test_lb_and_listener_statuses(context.session, pool=db_pool)

        try:
            LOG.info(_LI("Sending Update of Pool %s to handler"), id)
            self.handler.update(db_pool, pool)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener in db_pool.listeners:
                    self.repositories.listener.update(
                        context.session, listener.id,
                        operating_status=constants.ERROR)
                self.repositories.pool.update(
                    context.session, db_pool.id,
                    operating_status=constants.ERROR)
        db_pool = self._get_db_pool(context.session, id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a pool from a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_pool = self._get_db_pool(context.session, id)
        if len(db_pool.l7policies) > 0:
            raise exceptions.PoolInUseByL7Policy(
                id=db_pool.id, l7policy_id=db_pool.l7policies[0].id)
        self._test_lb_and_listener_statuses(context.session, pool=db_pool)

        try:
            LOG.info(_LI("Sending Deletion of Pool %s to handler"),
                     db_pool.id)
            self.handler.delete(db_pool)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener in db_pool.listeners:
                    self.repositories.listener.update(
                        context.session, listener.id,
                        operating_status=constants.ERROR)
                self.repositories.pool.update(
                    context.session, db_pool.id,
                    operating_status=constants.ERROR)
        db_pool = self.repositories.pool.get(context.session, id=db_pool.id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @pecan.expose()
    def _lookup(self, pool_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the pool passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if pool_id and len(remainder) and (remainder[0] == 'members' or
                                           remainder[0] == 'healthmonitor'):
            controller = remainder[0]
            remainder = remainder[1:]
            db_pool = self.repositories.pool.get(context.session, id=pool_id)
            if not db_pool:
                LOG.info(_LI("Pool %s not found."), pool_id)
                raise exceptions.NotFound(resource=data_models.Pool._name(),
                                          id=pool_id)
            if controller == 'members':
                return member.MembersController(
                    load_balancer_id=self.load_balancer_id,
                    pool_id=db_pool.id,
                    listener_id=self.listener_id), remainder
            elif controller == 'healthmonitor':
                return health_monitor.HealthMonitorController(
                    load_balancer_id=self.load_balancer_id,
                    pool_id=db_pool.id,
                    listener_id=self.listener_id), remainder
