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

from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import data_models as driver_dm
from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.types import health_monitor as hm_types
from octavia.common import constants as consts
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare
from octavia.i18n import _


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class HealthMonitorController(base.BaseController):
    RBAC_TYPE = consts.RBAC_HEALTHMONITOR

    def __init__(self):
        super(HealthMonitorController, self).__init__()

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single healthmonitor's details."""
        context = pecan.request.context.get('octavia_context')
        db_hm = self._get_db_hm(context.session, id, show_deleted=False)

        self._auth_validate_action(context, db_hm.project_id,
                                   consts.RBAC_GET_ONE)

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
            pagination_helper=pcontext.get(consts.PAGINATION_HELPER),
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
        if pool.provisioning_status not in consts.MUTABLE_STATUSES:
            raise exceptions.ImmutableObject(resource='Pool', id=hm.pool_id)
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, load_balancer_id,
                consts.PENDING_UPDATE, consts.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, hm),
                pool_id=hm.pool_id):
            LOG.info("Health Monitor cannot be created or modified because "
                     "the Load Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource='Load Balancer',
                                             id=load_balancer_id)

    def _validate_create_hm(self, lock_session, hm_dict):
        """Validate creating health monitor on pool."""
        mandatory_fields = (consts.TYPE, consts.DELAY, consts.TIMEOUT,
                            consts.POOL_ID)
        for field in mandatory_fields:
            if hm_dict.get(field, None) is None:
                raise exceptions.InvalidOption(value='None', option=field)
        # MAX_RETRIES is renamed fall_threshold so handle is special
        if hm_dict.get(consts.RISE_THRESHOLD, None) is None:
            raise exceptions.InvalidOption(value='None',
                                           option=consts.MAX_RETRIES)

        if hm_dict[consts.TYPE] != consts.HEALTH_MONITOR_HTTP:
            if hm_dict.get(consts.HTTP_METHOD, None):
                raise exceptions.InvalidOption(
                    value=consts.HTTP_METHOD, option='health monitors of '
                    'type {}'.format(hm_dict[consts.TYPE]))
            if hm_dict.get(consts.URL_PATH, None):
                raise exceptions.InvalidOption(
                    value=consts.URL_PATH, option='health monitors of '
                    'type {}'.format(hm_dict[consts.TYPE]))
            if hm_dict.get(consts.EXPECTED_CODES, None):
                raise exceptions.InvalidOption(
                    value=consts.EXPECTED_CODES, option='health monitors of '
                    'type {}'.format(hm_dict[consts.TYPE]))
        else:
            if not hm_dict.get(consts.HTTP_METHOD, None):
                hm_dict[consts.HTTP_METHOD] = (
                    consts.HEALTH_MONITOR_HTTP_DEFAULT_METHOD)
            if not hm_dict.get(consts.URL_PATH, None):
                hm_dict[consts.URL_PATH] = (
                    consts.HEALTH_MONITOR_DEFAULT_URL_PATH)
            if not hm_dict.get(consts.EXPECTED_CODES, None):
                hm_dict[consts.EXPECTED_CODES] = (
                    consts.HEALTH_MONITOR_DEFAULT_EXPECTED_CODES)

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

    def _validate_healthmonitor_request_for_udp(self, request):
        invalid_fields = (request.http_method or request.url_path or
                          request.expected_codes)
        is_invalid = (hasattr(request, 'type') and
                      (request.type != consts.HEALTH_MONITOR_UDP_CONNECT or
                       invalid_fields))
        if is_invalid:
            raise exceptions.ValidationException(detail=_(
                "The associated pool protocol is %(pool_protocol)s, so only "
                "a %(type)s health monitor is supported.") % {
                'pool_protocol': consts.PROTOCOL_UDP,
                'type': consts.HEALTH_MONITOR_UDP_CONNECT})
        # if the logic arrives here, that means the validation of request above
        # is OK. type is UDP-CONNECT, then here we check the healthmonitor
        # delay value is matched.
        if request.delay:
            conf_set = (CONF.api_settings.
                        udp_connect_min_interval_health_monitor)
            if conf_set < 0:
                return
            elif request.delay < conf_set:
                raise exceptions.ValidationException(detail=_(
                    "The request delay value %(delay)s should be larger than "
                    "%(conf_set)s for %(type)s health monitor type.") % {
                    'delay': request.delay,
                    'conf_set': conf_set,
                    'type': consts.HEALTH_MONITOR_UDP_CONNECT})

    @wsme_pecan.wsexpose(hm_types.HealthMonitorRootResponse,
                         body=hm_types.HealthMonitorRootPOST, status_code=201)
    def post(self, health_monitor_):
        """Creates a health monitor on a pool."""
        context = pecan.request.context.get('octavia_context')
        health_monitor = health_monitor_.healthmonitor

        if (not CONF.api_settings.allow_ping_health_monitors and
                health_monitor.type == consts.HEALTH_MONITOR_PING):
            raise exceptions.DisabledOption(
                option='type', value=consts.HEALTH_MONITOR_PING)

        pool = self._get_db_pool(context.session, health_monitor.pool_id)

        health_monitor.project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        if pool.protocol == consts.PROTOCOL_UDP:
            self._validate_healthmonitor_request_for_udp(health_monitor)
        else:
            if health_monitor.type == consts.HEALTH_MONITOR_UDP_CONNECT:
                raise exceptions.ValidationException(detail=_(
                    "The %(type)s type is only supported for pools of type "
                    "%(protocol)s.") % {'type': health_monitor.type,
                                        'protocol': consts.PROTOCOL_UDP})

        self._auth_validate_action(context, health_monitor.project_id,
                                   consts.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

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

    def _validate_update_hm(self, db_hm, health_monitor):
        if db_hm.type != consts.HEALTH_MONITOR_HTTP:
            if health_monitor.http_method != wtypes.Unset:
                raise exceptions.InvalidOption(
                    value=consts.HTTP_METHOD, option='health monitors of '
                    'type {}'.format(db_hm.type))
            if health_monitor.url_path != wtypes.Unset:
                raise exceptions.InvalidOption(
                    value=consts.URL_PATH, option='health monitors of '
                    'type {}'.format(db_hm.type))
            if health_monitor.expected_codes != wtypes.Unset:
                raise exceptions.InvalidOption(
                    value=consts.URL_PATH, option='health monitors of '
                    'type {}'.format(db_hm.type))
        else:
            # For HTTP health monitor these cannot be null/None
            if health_monitor.http_method is None:
                health_monitor.http_method = wtypes.Unset
            if health_monitor.url_path is None:
                health_monitor.url_path = wtypes.Unset
            if health_monitor.expected_codes is None:
                health_monitor.expected_codes = wtypes.Unset

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

        self._auth_validate_action(context, project_id, consts.RBAC_PUT)

        self._validate_update_hm(db_hm, health_monitor)
        # Validate health monitor update options for UDP-CONNECT type.
        if (pool.protocol == consts.PROTOCOL_UDP and
                db_hm.type == consts.HEALTH_MONITOR_UDP_CONNECT):
            self._validate_healthmonitor_request_for_udp(health_monitor)
        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_and_pool_statuses(lock_session, db_hm)

            # Prepare the data for the driver data model
            healthmon_dict = health_monitor.to_dict(render_unsets=False)
            healthmon_dict['id'] = id
            provider_healthmon_dict = (
                driver_utils.hm_dict_to_provider_dict(healthmon_dict))

            # Also prepare the baseline object data
            old_provider_healthmon = driver_utils.db_HM_to_provider_HM(db_hm)

            # Dispatch to the driver
            LOG.info("Sending update Health Monitor %s to provider %s",
                     id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.health_monitor_update,
                old_provider_healthmon,
                driver_dm.HealthMonitor.from_dict(provider_healthmon_dict))

            # Update the database to reflect what the driver just accepted
            health_monitor.provisioning_status = consts.PENDING_UPDATE
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

        self._auth_validate_action(context, project_id, consts.RBAC_DELETE)

        if db_hm.provisioning_status == consts.DELETED:
            return

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_and_pool_statuses(lock_session, db_hm)

            self.repositories.health_monitor.update(
                lock_session, db_hm.id,
                provisioning_status=consts.PENDING_DELETE)

            LOG.info("Sending delete Health Monitor %s to provider %s",
                     id, driver.name)
            provider_healthmon = driver_utils.db_HM_to_provider_HM(db_hm)
            driver_utils.call_provider(
                driver.name, driver.health_monitor_delete, provider_healthmon)
