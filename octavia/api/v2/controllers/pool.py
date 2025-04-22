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

from octavia_lib.api.drivers import data_models as driver_dm
from octavia_lib.common import constants as lib_consts
from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from pecan import expose as pecan_expose
from pecan import request as pecan_request
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.controllers import health_monitor
from octavia.api.v2.controllers import member
from octavia.api.v2.types import pool as pool_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import prepare as db_prepare
from octavia.i18n import _


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PoolsController(base.BaseController):
    RBAC_TYPE = constants.RBAC_POOL

    def __init__(self):
        super().__init__()

    @wsme_pecan.wsexpose(pool_types.PoolRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a pool's details."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_pool = self._get_db_pool(context.session, id,
                                        show_deleted=False)

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
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        with context.session.begin():
            db_pools, links = self.repositories.pool.get_all_API_list(
                context.session, show_deleted=False,
                pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
                **query_filter)
        result = self._convert_db_to_type(db_pools, [pool_types.PoolResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return pool_types.PoolsRootResponse(pools=result, pools_links=links)

    def _get_affected_listener_ids(self, pool):
        """Gets a list of all listeners this request potentially affects."""
        listener_ids = [li.id for li in pool.listeners]
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

    def _validate_create_pool(self, lock_session, pool_dict, listener_id=None):
        """Validate creating pool on load balancer.

        Update database for load balancer and (optional) listener based on
        provisioning status.
        """
        # Make sure we have a client CA if they specify a CRL
        if (pool_dict.get('crl_container_id') and
                not pool_dict.get('ca_tls_certificate_id')):
            raise exceptions.ValidationException(detail=_(
                "A CA certificate reference is required to "
                "specify a revocation list."))

        tls_certificate_id = pool_dict.get('tls_certificate_id', None)
        tls_refs = [tls_certificate_id] if tls_certificate_id else []
        self._validate_tls_refs(tls_refs)

        # Validate the client CA cert and optional client CRL
        if pool_dict.get('ca_tls_certificate_id'):
            self._validate_client_ca_and_crl_refs(
                pool_dict.get('ca_tls_certificate_id'),
                pool_dict.get('crl_container_id', None))

        # Check TLS cipher prohibit list and allow list
        if 'tls_ciphers' in pool_dict and pool_dict['tls_ciphers']:
            rejected_ciphers = validate.check_cipher_prohibit_list(
                pool_dict['tls_ciphers'])
            rejected_ciphers.extend(validate.check_cipher_allow_list(
                pool_dict['tls_ciphers']))
            if rejected_ciphers:
                detail = 'The following ciphers have been prohibited by an '\
                         'administrator: ' + ', '.join(rejected_ciphers)
                if CONF.api_settings.tls_cipher_allow_list is not None:
                    detail += '. The allowed cipher suites are defined by this cipher string: '\
                              + CONF.api_settings.tls_cipher_allow_list
                raise exceptions.ValidationException(detail=detail)

        if pool_dict['tls_enabled']:
            # Validate TLS version list
            validate.check_tls_version_list(pool_dict['tls_versions'])
            # Validate TLS versions against minimum
            validate.check_tls_version_min(pool_dict['tls_versions'])
            # Validate ALPN protocol list
            validate.check_alpn_protocols(pool_dict['alpn_protocols'])

        try:
            ret = self.repositories.create_pool_on_load_balancer(
                lock_session, pool_dict,
                listener_id=listener_id)
            lock_session.flush()
            return ret
        except odb_exceptions.DBDuplicateEntry as e:
            raise exceptions.IDAlreadyExists() from e
        except odb_exceptions.DBReferenceError as e:
            raise exceptions.InvalidOption(value=pool_dict.get(e.key),
                                           option=e.key) from e
        except odb_exceptions.DBError as e:
            raise exceptions.APIException() from e

    def _is_only_specified_in_request(self, request, **kwargs):
        request_attrs = []
        check_attrs = kwargs['check_exist_attrs']
        escaped_attrs = ['from_data_model', 'translate_key_to_data_model',
                         'translate_dict_keys_to_data_model', 'to_dict']

        for attr in dir(request):
            if attr.startswith('_') or attr in escaped_attrs:
                continue
            request_attrs.append(attr)

        for req_attr in request_attrs:
            if (getattr(request, req_attr) and req_attr not in check_attrs):
                return False
        return True

    def _validate_pool_request_for_udp_sctp(self, request):
        if request.session_persistence:
            if (request.session_persistence.type ==
                    constants.SESSION_PERSISTENCE_SOURCE_IP and
                    not self._is_only_specified_in_request(
                        request.session_persistence,
                        check_exist_attrs=['type', 'persistence_timeout',
                                           'persistence_granularity'])):
                raise exceptions.ValidationException(detail=_(
                    "session_persistence %s type for UDP and SCTP protocols "
                    "only accepts: type, persistence_timeout, "
                    "persistence_granularity.") % (
                        constants.SESSION_PERSISTENCE_SOURCE_IP))
            if request.session_persistence.cookie_name:
                raise exceptions.ValidationException(detail=_(
                    "Cookie names are not supported for %s pools.") %
                    "/".join((constants.PROTOCOL_UDP,
                              lib_consts.PROTOCOL_SCTP)))
            if request.session_persistence.type in [
                constants.SESSION_PERSISTENCE_HTTP_COOKIE,
                    constants.SESSION_PERSISTENCE_APP_COOKIE]:
                raise exceptions.ValidationException(detail=_(
                    "Session persistence of type %(type)s is not supported "
                    "for %(protocol)s protocol pools.") % {
                    'type': request.session_persistence.type,
                    'protocol': "/".join((constants.PROTOCOL_UDP,
                                          lib_consts.PROTOCOL_SCTP))})

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
        context = pecan_request.context.get('octavia_context')
        listener = None
        with context.session.begin():
            if pool.loadbalancer_id:
                pool.project_id, provider = self._get_lb_project_id_provider(
                    context.session, pool.loadbalancer_id)
            elif pool.listener_id:
                listener = self.repositories.listener.get(
                    context.session, id=pool.listener_id)
                pool.loadbalancer_id = listener.load_balancer_id
                pool.project_id, provider = self._get_lb_project_id_provider(
                    context.session, pool.loadbalancer_id)
            else:
                msg = _("Must provide at least one of: "
                        "loadbalancer_id, listener_id")
                raise exceptions.ValidationException(detail=msg)

        self._auth_validate_action(context, pool.project_id,
                                   constants.RBAC_POST)

        if pool.listener_id and listener:
            if listener.protocol == lib_consts.PROTOCOL_PROMETHEUS:
                raise exceptions.ListenerNoChildren(
                    protocol=lib_consts.PROTOCOL_PROMETHEUS)
            self._validate_protocol(listener.protocol, pool.protocol)
            self._validate_tls_option_proto(
                listener.protocol, pool.protocol, pool.tls_enabled)

        if pool.protocol in (constants.PROTOCOL_UDP,
                             lib_consts.PROTOCOL_SCTP):
            self._validate_pool_request_for_udp_sctp(pool)
        else:
            if (pool.session_persistence and (
                    pool.session_persistence.persistence_timeout or
                    pool.session_persistence.persistence_granularity)):
                raise exceptions.ValidationException(detail=_(
                    "persistence_timeout and persistence_granularity "
                    "is only for UDP and SCTP protocol pools."))

        if pool.session_persistence:
            sp_dict = pool.session_persistence.to_dict(render_unsets=False)
            validate.check_session_persistence(sp_dict)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        context.session.begin()
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    data_models.Pool,
                    pool.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.Pool._name())

            listener_repo = self.repositories.listener
            pool_dict = db_prepare.create_pool(
                pool.to_dict(render_unsets=True))

            listener_id = pool_dict.pop('listener_id', None)
            if listener_id:
                if listener_repo.has_default_pool(context.session,
                                                  listener_id):
                    raise exceptions.DuplicatePoolEntry()

            self._test_lb_and_listener_statuses(
                context.session, lb_id=pool_dict['load_balancer_id'],
                listener_ids=[listener_id] if listener_id else [])

            db_pool = self._validate_create_pool(
                context.session, pool_dict, listener_id)

            # Prepare the data for the driver data model
            provider_pool = (
                driver_utils.db_pool_to_provider_pool(db_pool))

            # Dispatch to the driver
            LOG.info("Sending create Pool %s to provider %s",
                     db_pool.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.pool_create, provider_pool)

            context.session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                context.session.rollback()

        with context.session.begin():
            db_pool = self._get_db_pool(context.session, db_pool.id)
        result = self._convert_db_to_type(db_pool, pool_types.PoolResponse)
        return pool_types.PoolRootResponse(pool=result)

    def _graph_create(self, session, pool_dict):
        load_balancer_id = pool_dict['load_balancer_id']
        pool_dict = db_prepare.create_pool(
            pool_dict, load_balancer_id)
        members = pool_dict.pop('members', []) or []
        hm = pool_dict.pop('health_monitor', None)
        db_pool = self._validate_create_pool(
            session, pool_dict)

        # Check quotas for healthmonitors
        if hm and self.repositories.check_quota_met(
                session, data_models.HealthMonitor,
                db_pool.project_id):
            raise exceptions.QuotaException(
                resource=data_models.HealthMonitor._name())

        # Now possibly create a healthmonitor
        if hm:
            hm[constants.POOL_ID] = db_pool.id
            hm[constants.PROJECT_ID] = db_pool.project_id
            new_hm = health_monitor.HealthMonitorController()._graph_create(
                session, hm)
            if db_pool.protocol in (constants.PROTOCOL_UDP,
                                    lib_consts.PROTOCOL_SCTP):
                health_monitor.HealthMonitorController(
                )._validate_healthmonitor_request_for_udp_sctp(new_hm,
                                                               db_pool)
            else:
                if new_hm.type in (constants.HEALTH_MONITOR_UDP_CONNECT,
                                   lib_consts.HEALTH_MONITOR_SCTP):
                    raise exceptions.ValidationException(detail=_(
                        "The %(type)s type is only supported for pools of "
                        "type %(protocol)s.") % {
                            'type': new_hm.type,
                            'protocol': '/'.join((constants.PROTOCOL_UDP,
                                                  lib_consts.PROTOCOL_SCTP))})
            db_pool.health_monitor = new_hm

        # Now check quotas for members
        if members and self.repositories.check_quota_met(
                session, data_models.Member,
                db_pool.project_id, count=len(members)):
            raise exceptions.QuotaException(
                resource=data_models.Member._name())

        # Now create members
        new_members = []
        for m in members:
            validate.ip_not_reserved(m["ip_address"])

            m['project_id'] = db_pool.project_id
            new_members.append(
                member.MembersController(db_pool.id)._graph_create(
                    session, m))
        db_pool.members = new_members
        return db_pool

    def _validate_pool_PUT(self, pool, db_pool):

        if db_pool.protocol in (constants.PROTOCOL_UDP,
                                lib_consts.PROTOCOL_SCTP):
            self._validate_pool_request_for_udp_sctp(pool)
        else:
            if (pool.session_persistence and (
                    pool.session_persistence.persistence_timeout or
                    pool.session_persistence.persistence_granularity)):
                raise exceptions.ValidationException(detail=_(
                    "persistence_timeout and persistence_granularity "
                    "is only for UDP protocol pools."))

        if pool.session_persistence:
            sp_dict = pool.session_persistence.to_dict(render_unsets=False)
            validate.check_session_persistence(sp_dict)

        crl_ref = None
        # If we got a crl_ref and it's not unset, use it
        if (pool.crl_container_ref and
                pool.crl_container_ref != wtypes.Unset):
            crl_ref = pool.crl_container_ref
        # If we got Unset and a CRL exists in the DB, use the DB crl_ref
        elif (db_pool.crl_container_id and
              pool.crl_container_ref == wtypes.Unset):
            crl_ref = db_pool.crl_container_id

        ca_ref = None
        db_ca_ref = db_pool.ca_tls_certificate_id
        if pool.ca_tls_container_ref != wtypes.Unset:
            if not pool.ca_tls_container_ref and db_ca_ref and crl_ref:
                raise exceptions.ValidationException(detail=_(
                    "A CA reference cannot be removed when a "
                    "certificate revocation list is present."))

            if not pool.ca_tls_container_ref and not db_ca_ref and crl_ref:
                raise exceptions.ValidationException(detail=_(
                    "A CA reference is required to "
                    "specify a certificate revocation list."))
            if pool.ca_tls_container_ref:
                ca_ref = pool.ca_tls_container_ref
        elif db_ca_ref and pool.ca_tls_container_ref == wtypes.Unset:
            ca_ref = db_ca_ref
        elif crl_ref and not db_ca_ref:
            raise exceptions.ValidationException(detail=_(
                "A CA reference is required to "
                "specify a certificate revocation list."))

        if pool.tls_container_ref:
            self._validate_tls_refs([pool.tls_container_ref])

        # Validate the client CA cert and optional client CRL
        if ca_ref:
            self._validate_client_ca_and_crl_refs(ca_ref, crl_ref)

        # Check TLS cipher prohibit list and allow list
        if pool.tls_ciphers:
            rejected_ciphers = validate.check_cipher_prohibit_list(
                pool.tls_ciphers)
            rejected_ciphers.extend(validate.check_cipher_allow_list(
                pool.tls_ciphers))
            if rejected_ciphers:
                detail = 'The following ciphers have been prohibited by an '\
                         'administrator: ' + ', '.join(rejected_ciphers)
                if CONF.api_settings.tls_cipher_allow_list is not None:
                    detail += '. The allowed cipher suites are defined by this cipher string: '\
                              + CONF.api_settings.tls_cipher_allow_list
                raise exceptions.ValidationException(detail=detail)

        if pool.tls_versions is not wtypes.Unset:
            # Validate TLS version list
            validate.check_tls_version_list(pool.tls_versions)
            # Validate TLS version against minimum
            validate.check_tls_version_min(pool.tls_versions)

        if pool.alpn_protocols is not wtypes.Unset:
            # Validate ALPN protocol list
            validate.check_alpn_protocols(pool.alpn_protocols)

    @wsme_pecan.wsexpose(pool_types.PoolRootResponse, wtypes.text,
                         body=pool_types.PoolRootPut, status_code=200)
    def put(self, id, pool_):
        """Updates a pool on a load balancer."""
        pool = pool_.pool
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_pool = self._get_db_pool(context.session, id,
                                        show_deleted=False)

            project_id, provider = self._get_lb_project_id_provider(
                context.session, db_pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        if pool.tls_versions is None:
            pool.tls_versions = CONF.api_settings.default_pool_tls_versions
        if pool.tls_ciphers is None:
            pool.tls_ciphers = CONF.api_settings.default_pool_ciphers

        if (pool.session_persistence and
                not pool.session_persistence.type and
                db_pool.session_persistence and
                db_pool.session_persistence.type):
            pool.session_persistence.type = db_pool.session_persistence.type

        self._validate_pool_PUT(pool, db_pool)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with context.session.begin():
            self._test_lb_and_listener_statuses(
                context.session, lb_id=db_pool.load_balancer_id,
                listener_ids=self._get_affected_listener_ids(db_pool))

            # Prepare the data for the driver data model
            pool_dict = pool.to_dict(render_unsets=False)
            pool_dict['id'] = id
            provider_pool_dict = (
                driver_utils.pool_dict_to_provider_dict(pool_dict))

            # Also prepare the baseline object data
            old_provider_pool = driver_utils.db_pool_to_provider_pool(
                db_pool, for_delete=True)

            # Dispatch to the driver
            LOG.info("Sending update Pool %s to provider %s", id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.pool_update,
                old_provider_pool,
                driver_dm.Pool.from_dict(provider_pool_dict))

            # Update the database to reflect what the driver just accepted
            pool.provisioning_status = constants.PENDING_UPDATE
            db_pool_dict = pool.to_dict(render_unsets=False)
            self.repositories.update_pool_and_sp(context.session, id,
                                                 db_pool_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        with context.session.begin():
            db_pool = self._get_db_pool(context.session, id)
        result = self._convert_db_to_type(db_pool, pool_types.PoolResponse)
        return pool_types.PoolRootResponse(pool=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a pool from a load balancer."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_pool = self._get_db_pool(context.session, id,
                                        show_deleted=False)

            project_id, provider = self._get_lb_project_id_provider(
                context.session, db_pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        if db_pool.l7policies:
            raise exceptions.PoolInUseByL7Policy(
                id=db_pool.id, l7policy_id=db_pool.l7policies[0].id)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with context.session.begin():
            self._test_lb_and_listener_statuses(
                context.session, lb_id=db_pool.load_balancer_id,
                listener_ids=self._get_affected_listener_ids(db_pool))
            self.repositories.pool.update(
                context.session, db_pool.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete Pool %s to provider %s", id, driver.name)
            provider_pool = (
                driver_utils.db_pool_to_provider_pool(db_pool,
                                                      for_delete=True))
            driver_utils.call_provider(driver.name, driver.pool_delete,
                                       provider_pool)

    @pecan_expose()
    def _lookup(self, pool_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the pool passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan_request.context.get('octavia_context')
        if pool_id and remainder and remainder[0] == 'members':
            remainder = remainder[1:]
            with context.session.begin():
                db_pool = self.repositories.pool.get(context.session,
                                                     id=pool_id)
            if not db_pool:
                LOG.info("Pool %s not found.", pool_id)
                raise exceptions.NotFound(resource=data_models.Pool._name(),
                                          id=pool_id)
            if remainder:
                return member.MemberController(pool_id=db_pool.id), remainder
            return member.MembersController(pool_id=db_pool.id), remainder
        return None
