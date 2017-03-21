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
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import health_monitor as hm_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare

LOG = logging.getLogger(__name__)


class HealthMonitorController(base.BaseController):

    def __init__(self, load_balancer_id, pool_id, listener_id=None):
        super(HealthMonitorController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.pool_id = pool_id
        self.handler = self.handler.health_monitor

    def _get_db_hm(self, session):
        """Gets the current health monitor object from the database."""
        db_hm = self.repositories.health_monitor.get(
            session, pool_id=self.pool_id)
        if not db_hm:
            LOG.info("Health Monitor for Pool %s was not found",
                     self.pool_id)
            raise exceptions.NotFound(
                resource=data_models.HealthMonitor._name(),
                id=self.pool_id)
        return db_hm

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse)
    def get_all(self):
        """Gets a single health monitor's details."""
        # NOTE(blogan): since a pool can only have one health monitor
        # we are using the get_all method to only get the single health monitor
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)

    def _get_affected_listener_ids(self, session, hm=None):
        """Gets a list of all listeners this request potentially affects."""
        listener_ids = []
        if hm:
            listener_ids = [l.id for l in hm.pool.listeners]
        else:
            pool = self._get_db_pool(session, self.pool_id)
            listener_ids = [listener.id for listener in pool.listeners]
        if self.listener_id and self.listener_id not in listener_ids:
            listener_ids.append(self.listener_id)
        return listener_ids

    def _test_lb_and_listener_statuses(self, session, hm=None):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this pool are also
        # mutable
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, self.load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, hm)):
            LOG.info("Health Monitor cannot be created or modified "
                     "because the Load Balancer is in an immutable state")
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse,
                         body=hm_types.HealthMonitorPOST, status_code=202)
    def post(self, health_monitor):
        """Creates a health monitor on a pool."""
        context = pecan.request.context.get('octavia_context')

        health_monitor.project_id = self._get_lb_project_id(
            context.session, self.load_balancer_id)

        try:
            db_hm = self.repositories.health_monitor.get(
                context.session, pool_id=self.pool_id)
            if db_hm:
                raise exceptions.DuplicateHealthMonitor()
        except exceptions.NotFound:
            pass

        lock_session = db_api.get_session(autocommit=False)
        if self.repositories.check_quota_met(
                context.session,
                lock_session,
                data_models.HealthMonitor,
                health_monitor.project_id):
            lock_session.rollback()
            raise exceptions.QuotaException

        try:
            hm_dict = db_prepare.create_health_monitor(
                health_monitor.to_dict(render_unsets=True), self.pool_id)
            self._test_lb_and_listener_statuses(lock_session)

            db_hm = self.repositories.health_monitor.create(lock_session,
                                                            **hm_dict)
            db_new_hm = self._get_db_hm(lock_session)
            lock_session.commit()
        except odb_exceptions.DBError:
            lock_session.rollback()
            raise exceptions.InvalidOption(value=hm_dict.get('type'),
                                           option='type')
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        try:
            LOG.info("Sending Creation of Health Monitor for Pool %s to "
                     "handler", self.pool_id)
            self.handler.create(db_hm)
        except Exception:
            for listener_id in self._get_affected_listener_ids(
                    context.session):
                with excutils.save_and_reraise_exception(reraise=False):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        return self._convert_db_to_type(db_new_hm,
                                        hm_types.HealthMonitorResponse)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorResponse,
                         body=hm_types.HealthMonitorPUT, status_code=202)
    def put(self, health_monitor):
        """Updates a health monitor.

        Updates a health monitor on a pool if it exists.  Only one health
        monitor is allowed per pool so there is no need for a health monitor
        id.
        """
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session)
        self._test_lb_and_listener_statuses(context.session, hm=db_hm)

        try:
            LOG.info("Sending Update of Health Monitor for Pool %s to handler",
                     self.pool_id)
            self.handler.update(db_hm, health_monitor)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener_id in self._get_affected_listener_ids(
                        context.session, db_hm):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        db_hm = self._get_db_hm(context.session)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)

    @wsme_pecan.wsexpose(None, status_code=202)
    def delete(self):
        """Deletes a health monitor."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session)
        self._test_lb_and_listener_statuses(context.session, hm=db_hm)

        try:
            LOG.info("Sending Deletion of Health Monitor for Pool %s to "
                     "handler", self.pool_id)
            self.handler.delete(db_hm)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener_id in self._get_affected_listener_ids(
                        context.session, db_hm):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        db_hm = self.repositories.health_monitor.get(
            context.session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_hm, hm_types.HealthMonitorResponse)
