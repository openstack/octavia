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

from cryptography.hazmat.backends import default_backend
from cryptography import x509
from oslo_config import cfg
from oslo_log import log as logging
import pecan
from stevedore import driver as stevedore_driver
from wsme import types as wtypes

from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import policy
from octavia.db import repositories
from octavia.i18n import _

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseController(pecan.rest.RestController):
    RBAC_TYPE = None

    def __init__(self):
        super(BaseController, self).__init__()
        self.cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver

        self.repositories = repositories.Repositories()

    @staticmethod
    def _convert_db_to_type(db_entity, to_type, children=False):
        """Converts a data model into an Octavia WSME type

        :param db_entity: data model to convert
        :param to_type: converts db_entity to this type
        """
        if isinstance(to_type, list):
            to_type = to_type[0]

        def _convert(db_obj):
            return to_type.from_data_model(db_obj, children=children)
        if isinstance(db_entity, list):
            converted = [_convert(db_obj) for db_obj in db_entity]
        else:
            converted = _convert(db_entity)
        return converted

    @staticmethod
    def _get_db_obj(session, repo, data_model, id, show_deleted=True):
        """Gets an object from the database and returns it."""
        db_obj = repo.get(session, id=id, show_deleted=show_deleted)
        if not db_obj:
            LOG.debug('%(name)s %(id)s not found',
                      {'name': data_model._name(), 'id': id})
            raise exceptions.NotFound(
                resource=data_model._name(), id=id)
        return db_obj

    def _get_db_lb(self, session, id, show_deleted=True):
        """Get a load balancer from the database."""
        return self._get_db_obj(session, self.repositories.load_balancer,
                                data_models.LoadBalancer, id,
                                show_deleted=show_deleted)

    def _get_db_listener(self, session, id, show_deleted=True):
        """Get a listener from the database."""
        return self._get_db_obj(session, self.repositories.listener,
                                data_models.Listener, id,
                                show_deleted=show_deleted)

    def _get_listener_and_loadbalancer_id(self, db_l7policy):
        """Get listener and loadbalancer ids from the l7policy db_model."""
        load_balancer_id = db_l7policy.listener.load_balancer_id
        listener_id = db_l7policy.listener_id
        return load_balancer_id, listener_id

    def _get_db_pool(self, session, id, show_deleted=True):
        """Get a pool from the database."""
        return self._get_db_obj(session, self.repositories.pool,
                                data_models.Pool, id,
                                show_deleted=show_deleted)

    def _get_db_member(self, session, id, show_deleted=True):
        """Get a member from the database."""
        return self._get_db_obj(session, self.repositories.member,
                                data_models.Member, id,
                                show_deleted=show_deleted)

    def _get_db_hm(self, session, id, show_deleted=True):
        """Get a health monitor from the database."""
        return self._get_db_obj(session, self.repositories.health_monitor,
                                data_models.HealthMonitor, id,
                                show_deleted=show_deleted)

    def _get_db_flavor(self, session, id):
        """Get a flavor from the database."""
        return self._get_db_obj(session, self.repositories.flavor,
                                data_models.Flavor, id)

    def _get_db_flavor_profile(self, session, id):
        """Get a flavor profile from the database."""
        return self._get_db_obj(session, self.repositories.flavor_profile,
                                data_models.FlavorProfile, id)

    def _get_db_l7policy(self, session, id, show_deleted=True):
        """Get a L7 Policy from the database."""
        return self._get_db_obj(session, self.repositories.l7policy,
                                data_models.L7Policy, id,
                                show_deleted=show_deleted)

    def _get_db_l7rule(self, session, id, show_deleted=True):
        """Get a L7 Rule from the database."""
        return self._get_db_obj(session, self.repositories.l7rule,
                                data_models.L7Rule, id,
                                show_deleted=show_deleted)

    def _get_db_amp(self, session, id, show_deleted=True):
        """Gets an Amphora from the database."""
        return self._get_db_obj(session, self.repositories.amphora,
                                data_models.Amphora, id,
                                show_deleted=show_deleted)

    def _get_lb_project_id(self, session, id, show_deleted=True):
        """Get the project_id of the load balancer from the database."""
        lb = self._get_db_obj(session, self.repositories.load_balancer,
                              data_models.LoadBalancer, id,
                              show_deleted=show_deleted)
        return lb.project_id

    def _get_lb_project_id_provider(self, session, id, show_deleted=True):
        """Get the project_id of the load balancer from the database."""
        lb = self._get_db_obj(session, self.repositories.load_balancer,
                              data_models.LoadBalancer, id,
                              show_deleted=show_deleted)
        return lb.project_id, lb.provider

    def _get_l7policy_project_id(self, session, id, show_deleted=True):
        """Get the project_id of the load balancer from the database."""
        l7policy = self._get_db_obj(session, self.repositories.l7policy,
                                    data_models.LoadBalancer, id,
                                    show_deleted=show_deleted)
        return l7policy.project_id

    def _get_default_quotas(self, project_id):
        """Gets the project's default quotas."""
        quotas = data_models.Quotas(
            project_id=project_id,
            load_balancer=CONF.quotas.default_load_balancer_quota,
            listener=CONF.quotas.default_listener_quota,
            pool=CONF.quotas.default_pool_quota,
            health_monitor=CONF.quotas.default_health_monitor_quota,
            member=CONF.quotas.default_member_quota)
        return quotas

    def _get_db_quotas(self, session, project_id):
        """Gets the project's quotas from the database, or responds with the

        default quotas.
        """
        # At this point project_id should not ever be None or Unset
        db_quotas = self.repositories.quotas.get(
            session, project_id=project_id)
        if not db_quotas:
            LOG.debug("No custom quotas for project %s. Returning "
                      "defaults...", project_id)
            db_quotas = self._get_default_quotas(project_id=project_id)
        else:
            # Fill in any that are using the configured defaults
            if db_quotas.load_balancer is None:
                db_quotas.load_balancer = (CONF.quotas.
                                           default_load_balancer_quota)
            if db_quotas.listener is None:
                db_quotas.listener = CONF.quotas.default_listener_quota
            if db_quotas.pool is None:
                db_quotas.pool = CONF.quotas.default_pool_quota
            if db_quotas.health_monitor is None:
                db_quotas.health_monitor = (CONF.quotas.
                                            default_health_monitor_quota)
            if db_quotas.member is None:
                db_quotas.member = CONF.quotas.default_member_quota
        return db_quotas

    def _auth_get_all(self, context, project_id):
        # Check authorization to list objects under all projects
        action = '{rbac_obj}{action}'.format(
            rbac_obj=self.RBAC_TYPE, action=constants.RBAC_GET_ALL_GLOBAL)
        target = {'project_id': project_id}
        if not policy.get_enforcer().authorize(action, target,
                                               context, do_raise=False):
            # Not a global observer or admin
            if project_id is None:
                project_id = context.project_id

            # Check authorization to list objects under this project
            self._auth_validate_action(context, project_id,
                                       constants.RBAC_GET_ALL)
        if project_id is None:
            query_filter = {}
        else:
            query_filter = {'project_id': project_id}
        return query_filter

    def _auth_validate_action(self, context, project_id, action):
        # Check that the user is authorized to do an action in this object
        action = '{rbac_obj}{action}'.format(
            rbac_obj=self.RBAC_TYPE, action=action)
        target = {'project_id': project_id}
        policy.get_enforcer().authorize(action, target, context)

    def _filter_fields(self, object_list, fields):
        if CONF.api_settings.allow_field_selection:
            for index, obj in enumerate(object_list):
                members = self._get_attrs(obj)
                for member in members:
                    if member not in fields:
                        setattr(obj, member, wtypes.Unset)
        return object_list

    @staticmethod
    def _get_attrs(obj):
        attrs = [attr for attr in dir(obj) if not callable(
            getattr(obj, attr)) and not attr.startswith("_")]
        return attrs

    def _validate_tls_refs(self, tls_refs):
        context = pecan.request.context.get('octavia_context')
        bad_refs = []
        for ref in tls_refs:
            try:
                self.cert_manager.set_acls(context, ref)
                self.cert_manager.get_cert(context, ref, check_only=True)
            except exceptions.UnreadablePKCS12:
                raise
            except Exception:
                bad_refs.append(ref)

        if bad_refs:
            raise exceptions.CertificateRetrievalException(ref=bad_refs)

    def _validate_client_ca_and_crl_refs(self, client_ca_ref, crl_ref):
        context = pecan.request.context.get('octavia_context')
        bad_refs = []
        try:
            self.cert_manager.set_acls(context, client_ca_ref)
            ca_pem = self.cert_manager.get_secret(context, client_ca_ref)
        except Exception:
            bad_refs.append(client_ca_ref)

        pem_crl = None
        if crl_ref:
            try:
                self.cert_manager.set_acls(context, crl_ref)
                pem_crl = self.cert_manager.get_secret(context, crl_ref)
            except Exception:
                bad_refs.append(crl_ref)
        if bad_refs:
            raise exceptions.CertificateRetrievalException(ref=bad_refs)

        ca_cert = None
        try:
            # Test if it needs to be UTF-8 encoded
            try:
                ca_pem = ca_pem.encode('utf-8')
            except AttributeError:
                pass
            ca_cert = x509.load_pem_x509_certificate(ca_pem, default_backend())
        except Exception as e:
            raise exceptions.ValidationException(detail=_(
                "The client authentication CA certificate is invalid. "
                "It must be a valid x509 PEM format certificate. "
                "Error: %s") % str(e))

        # Validate the CRL is for the client CA
        if pem_crl:
            ca_pub_key = ca_cert.public_key()
            crl = None
            # Test if it needs to be UTF-8 encoded
            try:
                pem_crl = pem_crl.encode('utf-8')
            except AttributeError:
                pass
            try:
                crl = x509.load_pem_x509_crl(pem_crl, default_backend())
            except Exception as e:
                raise exceptions.ValidationException(detail=_(
                    "The client authentication certificate revocation list "
                    "is invalid. It must be a valid x509 PEM format "
                    "certificate revocation list. Error: %s") % str(e))
            if not crl.is_signature_valid(ca_pub_key):
                raise exceptions.ValidationException(detail=_(
                    "The CRL specified is not valid for client certificate "
                    "authority reference supplied."))

    @staticmethod
    def _validate_protocol(listener_protocol, pool_protocol):
        proto_map = constants.VALID_LISTENER_POOL_PROTOCOL_MAP
        for valid_pool_proto in proto_map[listener_protocol]:
            if pool_protocol == valid_pool_proto:
                return
        detail = _("The pool protocol '%(pool_protocol)s' is invalid while "
                   "the listener protocol is '%(listener_protocol)s'.") % {
                       "pool_protocol": pool_protocol,
                       "listener_protocol": listener_protocol}
        raise exceptions.ValidationException(detail=detail)
