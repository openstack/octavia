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
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import health_monitor as hm_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class HealthMonitorController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id, pool_id):
        super(HealthMonitorController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.pool_id = pool_id
        self.handler = self.handler.health_monitor

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse)
    def get_all(self):
        """Gets a single health monitor's details."""
        # NOTE(blogan): since a pool can only have one health monitor
        # we are using the get_all method to only get the single health monitor
        session = db_api.get_session()
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        if not db_hm:
            LOG.info(_LI("Health Monitor for Pool %s was not found") %
                     self.pool_id)
            raise exceptions.NotFound(
                resource=data_models.HealthMonitor._name(), id=id)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse,
                         body=hm_types.HealthMonitorPOST, status_code=202)
    def post(self, health_monitor):
        """Creates a health monitor on a pool."""
        session = db_api.get_session()
        try:
            db_hm = self.repositories.health_monitor.get(
                session, pool_id=self.pool_id)
            if db_hm:
                raise exceptions.DuplicateHealthMonitor()
        except exceptions.NotFound:
            pass
        hm_dict = health_monitor.to_dict()
        hm_dict['pool_id'] = self.pool_id
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Health Monitor for Pool %s cannot be updated "
                         "because the Load Balancer is immutable.") %
                     self.pool_id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        try:
            db_hm = self.repositories.health_monitor.create(session, **hm_dict)
        except odb_exceptions.DBError:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            self.repositories.load_balancer.update(
                session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            self.repositories.listener.update(
                session, self.listener_id,
                provisioning_status=constants.ACTIVE)
            raise exceptions.InvalidOption(value=hm_dict.get('type'),
                                           option='type')
        try:
            LOG.info(_LI("Sending Creation of Health Monitor for Pool %s to "
                         "handler") % self.pool_id)
            self.handler.create(db_hm)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse,
                         body=hm_types.HealthMonitorPUT, status_code=202)
    def put(self, health_monitor):
        """Updates a health monitor.

        Updates a health monitor on a pool if it exists.  Only one health
        monitor is allowed per pool so there is no need for a health monitor
        id.
        """
        session = db_api.get_session()
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        if not db_hm:
            LOG.info(_LI("Health Monitor for Pool %s was not found") %
                     self.pool_id)
            raise exceptions.NotFound(
                resource=data_models.HealthMonitor._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Health Monitor for Pool %s cannot be updated "
                         "because the Load Balancer is immutable.") %
                     self.pool_id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        try:
            LOG.info(_LI("Sending Update of Health Monitor for Pool %s to "
                         "handler") % self.pool_id)
            self.handler.update(db_hm, health_monitor)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)

    @wsme_pecan.wsexpose(None, status_code=202)
    def delete(self):
        """Deletes a health monitor."""
        session = db_api.get_session()
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        if not db_hm:
            LOG.info(_LI("Health Monitor for Pool %s cannot be updated "
                         "because the Load Balancer is immutable.") %
                     self.pool_id)
            raise exceptions.NotFound(
                resource=data_models.HealthMonitor._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        db_hm = self.repositories.health_monitor.get(session,
                                                     pool_id=self.pool_id)
        try:
            LOG.info(_LI("Sending Deletion of Health Monitor for Pool %s to "
                         "handler") % self.pool_id)
            self.handler.delete(db_hm)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)
