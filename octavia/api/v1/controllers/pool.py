#    Copyright 2014 Rackspace
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
from octavia.db import api as db_api
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class PoolsController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id):
        super(PoolsController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.handler = self.handler.pool

    @wsme_pecan.wsexpose(pool_types.PoolResponse, wtypes.text)
    def get(self, id):
        """Gets a pool's details."""
        session = db_api.get_session()
        db_pool = self.repositories.pool.get(session, id=id)
        if not db_pool:
            LOG.info(_LI("Pool %s not found.") % id)
            raise exceptions.NotFound(resource=data_models.Pool._name(), id=id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose([pool_types.PoolResponse])
    def get_all(self):
        """Lists all pools on a listener."""
        session = db_api.get_session()
        default_pool = self.repositories.listener.get(
            session, id=self.listener_id).default_pool
        if default_pool:
            default_pool = [default_pool]
        else:
            default_pool = []
        return self._convert_db_to_type(default_pool,
                                        [pool_types.PoolResponse])

    def _test_lb_status(self, session):
        """Verify load balancer is in a mutable status."""
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Pool cannot be created because the Load "
                         "Balancer is in an immutable state"))
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    def _validate_create_pool(self, session, sp_dict, pool_dict):
        """Validate creating pool on load balancer.

        Update database for load balancer and listener based on provisioning
        status.
        """
        try:
            db_pool = self.repositories.create_pool_on_listener(
                session, self.listener_id, pool_dict, sp_dict=sp_dict)
        except odb_exceptions.DBDuplicateEntry as de:
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
        except odb_exceptions.DBError:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            self.repositories.load_balancer.update(
                session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            self.repositories.listener.update(
                session, self.listener_id,
                provisioning_status=constants.ACTIVE)
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')
        try:
            LOG.info(_LI("Sending Creation of Pool %s to handler") %
                     db_pool.id)
            self.handler.create(db_pool)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_pool = self.repositories.pool.get(session, id=db_pool.id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose(pool_types.PoolResponse, body=pool_types.PoolPOST,
                         status_code=202)
    def post(self, pool):
        """Creates a pool on a listener.

        This does not allow more than one pool to be on a listener so once one
        is created, another cannot be created until the first one has been
        deleted.
        """
        session = db_api.get_session()
        if self.repositories.listener.has_pool(session, self.listener_id):
            raise exceptions.DuplicatePoolEntry()
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.

        self._test_lb_status(session)
        pool_dict = pool.to_dict()
        sp_dict = pool_dict.pop('session_persistence', None)
        pool_dict['operating_status'] = constants.OFFLINE

        return self._validate_create_pool(session, sp_dict, pool_dict)

    def _test_lb_status_put(self, session):
        """Verify load balancer is in a mutable status for put method."""
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Pool %s cannot be updated because the Load "
                         "Balancer is in an immutable state") % id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    @wsme_pecan.wsexpose(pool_types.PoolResponse, wtypes.text,
                         body=pool_types.PoolPUT, status_code=202)
    def put(self, id, pool):
        """Updates a pool on a listener."""
        session = db_api.get_session()
        db_pool = self.repositories.pool.get(session, id=id)
        if not db_pool:
            LOG.info(_LI("Pool %s not found.") % id)
            raise exceptions.NotFound(resource=data_models.Pool._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        self._test_lb_status_put(session)

        try:
            LOG.info(_LI("Sending Update of Pool %s to handler") % id)
            self.handler.update(db_pool, pool)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_pool = self.repositories.pool.get(session, id=id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a pool from a listener."""
        session = db_api.get_session()
        db_pool = self.repositories.pool.get(session, id=id)
        if not db_pool:
            LOG.info(_LI("Pool %s not found.") % id)
            raise exceptions.NotFound(resource=data_models.Pool._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Pool %s cannot be deleted because the Load "
                         "Balancer is in an immutable state") % id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        db_pool = self.repositories.pool.get(session, id=id)
        try:
            LOG.info(_LI("Sending Deletion of Pool %s to handler") %
                     db_pool.id)
            self.handler.delete(db_pool)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
                self.repositories.pool.update(
                    session, db_pool.id,
                    operating_status=constants.ERROR)
        db_pool = self.repositories.pool.get(session, id=db_pool.id)
        return self._convert_db_to_type(db_pool, pool_types.PoolResponse)

    @pecan.expose()
    def _lookup(self, pool_id, *remainder):
        """Overriden pecan _lookup method for custom routing.

        Verifies that the pool passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        session = db_api.get_session()
        if pool_id and len(remainder) and remainder[0] == 'members':
            remainder = remainder[1:]
            db_pool = self.repositories.pool.get(session, id=pool_id)
            if not db_pool:
                LOG.info(_LI("Pool %s not found.") % pool_id)
                raise exceptions.NotFound(resource=data_models.Pool._name(),
                                          id=pool_id)
            return member.MembersController(
                load_balancer_id=self.load_balancer_id,
                listener_id=self.listener_id,
                pool_id=db_pool.id), remainder
        if pool_id and len(remainder) and remainder[0] == 'healthmonitor':
            remainder = remainder[1:]
            db_pool = self.repositories.pool.get(session, id=pool_id)
            if not db_pool:
                LOG.info(_LI("Pool %s not found.") % pool_id)
                raise exceptions.NotFound(resource=data_models.Pool._name(),
                                          id=pool_id)
            return health_monitor.HealthMonitorController(
                load_balancer_id=self.load_balancer_id,
                listener_id=self.listener_id,
                pool_id=db_pool.id), remainder
