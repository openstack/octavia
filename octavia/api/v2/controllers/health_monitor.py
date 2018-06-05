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

from octavia.api.drivers import data_models as driver_dm
from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
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

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single healthmonitor's details."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session, id, show_deleted=False)

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

        db_hm, links = self.repositories.health_monitor.get_all(
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

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse,
                         body=hm_types.HealthMonitorRootPOST, status_code=201)
    def post(self, health_monitor_):
        """Creates a health monitor on a pool."""
        context = pecan.request.context.get('octavia_context')
        health_monitor = health_monitor_.healthmonitor

        if (not CONF.api_settings.allow_ping_health_monitors and
                health_monitor.type == constants.HEALTH_MONITOR_PING):
            raise exceptions.DisabledOption(
                option='type', value=constants.HEALTH_MONITOR_PING)

        pool = self._get_db_pool(context.session, health_monitor.pool_id)

        health_monitor.project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, health_monitor.project_id,
                                   constants.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        lock_session = db_api.get_session(autocommit=False)
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    lock_session,
                    data_models.HealthMonitor,
                    health_monitor.project_id):
                raise exceptions.QuotaException

            hm_dict = db_prepare.create_health_monitor(
                health_monitor.to_dict(render_unsets=True))

            self._test_lb_and_listener_and_pool_statuses(
                lock_session, health_monitor)
            db_hm = self._validate_create_hm(lock_session, hm_dict)

            # Prepare the data for the driver data model
            provider_healthmon = (driver_utils.db_HM_to_provider_HM(db_hm))

            # Dispatch to the driver
            LOG.info("Sending create Health Monitor %s to provider %s",
                     db_hm.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.health_monitor_create, provider_healthmon)

            lock_session.commit()
        except odb_exceptions.DBError:
            lock_session.rollback()
            raise exceptions.InvalidOption(
                value=hm_dict.get('type'), option='type')
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        db_hm = self._get_db_hm(context.session, db_hm.id)
        result = self._convert_db_to_type(
            db_hm, hm_types.HealthMonitorResponse)
        return hm_types.HealthMonitorRootResponse(healthmonitor=result)

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
        db_hm = self._get_db_hm(context.session, id, show_deleted=False)

        pool = self._get_db_pool(context.session, db_hm.pool_id)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_and_pool_statuses(lock_session, db_hm)

            # Prepare the data for the driver data model
            healthmon_dict = health_monitor.to_dict(render_unsets=False)
            healthmon_dict['id'] = id
            provider_healthmon_dict = (
                driver_utils.hm_dict_to_provider_dict(healthmon_dict))

            # Dispatch to the driver
            LOG.info("Sending update Health Monitor %s to provider %s",
                     id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.health_monitor_update,
                driver_dm.HealthMonitor.from_dict(provider_healthmon_dict))

            # Update the database to reflect what the driver just accepted
            health_monitor.provisioning_status = constants.PENDING_UPDATE
            db_hm_dict = health_monitor.to_dict(render_unsets=False)
            self.repositories.health_monitor.update(lock_session, id,
                                                    **db_hm_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_hm = self._get_db_hm(context.session, id)
        result = self._convert_db_to_type(
            db_hm, hm_types.HealthMonitorResponse)
        return hm_types.HealthMonitorRootResponse(healthmonitor=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a health monitor."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session, id, show_deleted=False)

        pool = self._get_db_pool(context.session, db_hm.pool_id)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        if db_hm.provisioning_status == constants.DELETED:
            return

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_and_pool_statuses(lock_session, db_hm)

            self.repositories.health_monitor.update(
                lock_session, db_hm.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete Health Monitor %s to provider %s",
                     id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.health_monitor_delete, id)
