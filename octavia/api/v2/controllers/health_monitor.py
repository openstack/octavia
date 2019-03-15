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
from octavia.api.v2.types import health_monitor as hm_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HealthMonitorController(base.BaseController):
    RBAC_TYPE = constants.RBAC_HEALTHMONITOR

    def __init__(self):
        super(HealthMonitorController, self).__init__()
        self.handler = self.handler.health_monitor

    def _get_db_hm(self, session, hm_id):
        """Gets the current health monitor object from the database."""
        db_hm = self.repositories.health_monitor.get(
            session, id=hm_id)
        if not db_hm:
            LOG.info("Health Monitor %s was not found", hm_id)
            raise exceptions.NotFound(
                resource=data_models.HealthMonitor._name(),
                id=hm_id)
        return db_hm

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single healthmonitor's details."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session, id)

        self._auth_validate_action(context, db_hm.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            db_hm, hm_types.HealthMonitorResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return hm_types.HealthMonitorRootResponse(healthmonitor=result)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorsRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, project_id=None, fields=None):
        """Gets all health monitors."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        db_hm, links = self.repositories.health_monitor.get_all_API_list(
            context.session, show_deleted=False,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
            **query_filter)
        result = self._convert_db_to_type(
            db_hm, [hm_types.HealthMonitorResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return hm_types.HealthMonitorsRootResponse(
            healthmonitors=result, healthmonitors_links=links)

    def _get_affected_listener_ids(self, session, hm):
        """Gets a list of all listeners this request potentially affects."""
        pool = self.repositories.pool.get(session, id=hm.pool_id)
        listener_ids = [l.id for l in pool.listeners]
        return listener_ids

    def _test_lb_and_listener_and_pool_statuses(self, session, hm):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this pool are also
        # mutable
        pool = self.repositories.pool.get(session, id=hm.pool_id)
        load_balancer_id = pool.load_balancer_id
        # Check the parent is not locked for some reason (ERROR, etc.)
        if pool.provisioning_status not in constants.MUTABLE_STATUSES:
            raise exceptions.ImmutableObject(resource='Pool', id=hm.pool_id)
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, hm),
                pool_id=hm.pool_id):
            LOG.info("Health Monitor cannot be created or modified because "
                     "the Load Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource='Load Balancer',
                                             id=load_balancer_id)

    def _reset_lb_listener_pool_statuses(self, session, hm):
        # Setting LB + listener + pool back to active because this should be a
        # recoverable error
        pool = self._get_db_pool(session, hm.pool_id)
        load_balancer_id = pool.load_balancer_id
        self.repositories.load_balancer.update(
            session, load_balancer_id,
            provisioning_status=constants.ACTIVE)
        for listener in self._get_affected_listener_ids(session, hm):
            self.repositories.listener.update(
                session, listener,
                provisioning_status=constants.ACTIVE)
        self.repositories.pool.update(session, hm.pool_id,
                                      provisioning_status=constants.ACTIVE)

    def _validate_create_hm(self, lock_session, hm_dict):
        """Validate creating health monitor on pool."""
        try:
            return self.repositories.health_monitor.create(
                lock_session, **hm_dict)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.DuplicateHealthMonitor()
        except odb_exceptions.DBError:
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')

    def _send_hm_to_handler(self, session, db_hm):
        try:
            LOG.info("Sending Creation of Health Monitor %s to handler",
                     db_hm.id)
            self.handler.create(db_hm)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, db_hm)
                # Health Monitor now goes to ERROR
                self.repositories.health_monitor.update(
                    lock_session, db_hm.id,
                    provisioning_status=constants.ERROR)
        db_hm = self._get_db_hm(session, db_hm.id)
        result = self._convert_db_to_type(
            db_hm, hm_types.HealthMonitorResponse)
        return hm_types.HealthMonitorRootResponse(healthmonitor=result)

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse,
                         body=hm_types.HealthMonitorRootPOST, status_code=201)
    def post(self, health_monitor_):
        """Creates a health monitor on a pool."""
        context = pecan.request.context.get('octavia_context')
        health_monitor = health_monitor_.healthmonitor
        pool = self._get_db_pool(context.session, health_monitor.pool_id)
        health_monitor.project_id = pool.project_id

        self._auth_validate_action(context, health_monitor.project_id,
                                   constants.RBAC_POST)

        lock_session = db_api.get_session(autocommit=False)
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    lock_session,
                    data_models.HealthMonitor,
                    health_monitor.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.HealthMonitor._name())

            hm_dict = db_prepare.create_health_monitor(
                health_monitor.to_dict(render_unsets=True))

            self._test_lb_and_listener_and_pool_statuses(
                lock_session, health_monitor)
            db_hm = self._validate_create_hm(lock_session, hm_dict)
            lock_session.commit()
        except odb_exceptions.DBError:
            lock_session.rollback()
            raise exceptions.InvalidOption(
                value=hm_dict.get('type'), option='type')
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        return self._send_hm_to_handler(context.session, db_hm)

    def _graph_create(self, lock_session, hm_dict):
        hm_dict = db_prepare.create_health_monitor(hm_dict)
        db_hm = self._validate_create_hm(lock_session, hm_dict)

        return db_hm

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse, wtypes.text,
                         body=hm_types.HealthMonitorRootPUT, status_code=200)
    def put(self, id, health_monitor_):
        """Updates a health monitor."""
        context = pecan.request.context.get('octavia_context')
        health_monitor = health_monitor_.healthmonitor
        db_hm = self._get_db_hm(context.session, id)

        self._auth_validate_action(context, db_hm.project_id,
                                   constants.RBAC_PUT)

        self._test_lb_and_listener_and_pool_statuses(context.session, db_hm)

        self.repositories.health_monitor.update(
            context.session, db_hm.id,
            provisioning_status=constants.PENDING_UPDATE)

        try:
            LOG.info("Sending Update of Health Monitor for Pool %s to "
                     "handler", id)
            self.handler.update(db_hm, health_monitor)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, db_hm)
                # Health Monitor now goes to ERROR
                self.repositories.health_monitor.update(
                    lock_session, db_hm.id,
                    provisioning_status=constants.ERROR)
        db_hm = self._get_db_hm(context.session, id)
        result = self._convert_db_to_type(
            db_hm, hm_types.HealthMonitorResponse)
        return hm_types.HealthMonitorRootResponse(healthmonitor=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a health monitor."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session, id)

        self._auth_validate_action(context, db_hm.project_id,
                                   constants.RBAC_DELETE)

        if db_hm.provisioning_status == constants.DELETED:
            return

        self._test_lb_and_listener_and_pool_statuses(context.session, db_hm)

        self.repositories.health_monitor.update(
            context.session, db_hm.id,
            provisioning_status=constants.PENDING_DELETE)

        try:
            LOG.info("Sending Deletion of Health Monitor for Pool %s to "
                     "handler", id)
            self.handler.delete(db_hm)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, db_hm)
                # Health Monitor now goes to ERROR
                self.repositories.health_monitor.update(
                    lock_session, db_hm.id,
                    provisioning_status=constants.ERROR)
