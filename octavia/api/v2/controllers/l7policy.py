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
from octavia.api.v2.controllers import l7rule
from octavia.api.v2.types import l7policy as l7policy_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class L7PolicyController(base.BaseController):
    RBAC_TYPE = constants.RBAC_L7POLICY

    def __init__(self):
        super(L7PolicyController, self).__init__()

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a single l7policy's details."""
        context = pecan.request.context.get('octavia_context')
        db_l7policy = self._get_db_l7policy(context.session, id,
                                            show_deleted=False)

        self._auth_validate_action(context, db_l7policy.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            db_l7policy, l7policy_types.L7PolicyResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return l7policy_types.L7PolicyRootResponse(l7policy=result)

    @wsme_pecan.wsexpose(l7policy_types.L7PoliciesRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, project_id=None, fields=None):
        """Lists all l7policies of a listener."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        db_l7policies, links = self.repositories.l7policy.get_all_API_list(
            context.session, show_deleted=False,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
            **query_filter)
        result = self._convert_db_to_type(
            db_l7policies, [l7policy_types.L7PolicyResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return l7policy_types.L7PoliciesRootResponse(
            l7policies=result, l7policies_links=links)

    def _test_lb_and_listener_statuses(self, session, lb_id, listener_ids):
        """Verify load balancer is in a mutable state."""
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, lb_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=listener_ids):
            LOG.info("L7Policy cannot be created or modified because the "
                     "Load Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource='Load Balancer',
                                             id=lb_id)

    def _validate_create_l7policy(self, lock_session, l7policy_dict):
        try:
            # Set the default HTTP redirect code here so it's explicit
            if ((l7policy_dict.get('redirect_url') or
                l7policy_dict.get('redirect_prefix')) and
                    not l7policy_dict.get('redirect_http_code')):
                l7policy_dict['redirect_http_code'] = 302

            return self.repositories.l7policy.create(lock_session,
                                                     **l7policy_dict)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.IDAlreadyExists()
        except odb_exceptions.DBError:
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyRootResponse,
                         body=l7policy_types.L7PolicyRootPOST, status_code=201)
    def post(self, l7policy_):
        """Creates a l7policy on a listener."""
        l7policy = l7policy_.l7policy
        context = pecan.request.context.get('octavia_context')
        # Verify the parent listener exists
        listener_id = l7policy.listener_id
        listener = self._get_db_listener(
            context.session, listener_id)
        load_balancer_id = listener.load_balancer_id
        l7policy.project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)
        # Make sure any pool specified by redirect_pool_id exists
        if l7policy.redirect_pool_id:
            db_pool = self._get_db_pool(
                context.session, l7policy.redirect_pool_id)
            self._validate_protocol(listener.protocol, db_pool.protocol)

        self._auth_validate_action(context, l7policy.project_id,
                                   constants.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        lock_session = db_api.get_session(autocommit=False)
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    lock_session,
                    data_models.L7Policy,
                    l7policy.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.L7Policy._name())

            l7policy_dict = db_prepare.create_l7policy(
                l7policy.to_dict(render_unsets=True),
                load_balancer_id, listener_id)

            self._test_lb_and_listener_statuses(
                lock_session, lb_id=load_balancer_id,
                listener_ids=[listener_id])
            db_l7policy = self._validate_create_l7policy(
                lock_session, l7policy_dict)

            # Prepare the data for the driver data model
            provider_l7policy = (
                driver_utils.db_l7policy_to_provider_l7policy(db_l7policy))

            # Dispatch to the driver
            LOG.info("Sending create L7 Policy %s to provider %s",
                     db_l7policy.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.l7policy_create, provider_l7policy)

            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        db_l7policy = self._get_db_l7policy(context.session, db_l7policy.id)
        result = self._convert_db_to_type(db_l7policy,
                                          l7policy_types.L7PolicyResponse)
        return l7policy_types.L7PolicyRootResponse(l7policy=result)

    def _graph_create(self, lock_session, policy_dict):
        load_balancer_id = policy_dict.pop('load_balancer_id', None)
        listener_id = policy_dict['listener_id']
        policy_dict = db_prepare.create_l7policy(
            policy_dict, load_balancer_id, listener_id)
        rules = policy_dict.pop('l7rules', []) or []
        db_policy = self._validate_create_l7policy(lock_session, policy_dict)

        new_rules = []
        for r in rules:
            r['project_id'] = db_policy.project_id
            new_rules.append(
                l7rule.L7RuleController(db_policy.id)._graph_create(
                    lock_session, r))

        db_policy.l7rules = new_rules
        return db_policy

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyRootResponse,
                         wtypes.text, body=l7policy_types.L7PolicyRootPUT,
                         status_code=200)
    def put(self, id, l7policy_):
        """Updates a l7policy."""
        l7policy = l7policy_.l7policy
        l7policy_dict = validate.sanitize_l7policy_api_args(
            l7policy.to_dict(render_unsets=False))
        # Reset renamed attributes
        for attr, val in l7policy_types.L7PolicyPUT._type_to_model_map.items():
            if val in l7policy_dict:
                l7policy_dict[attr] = l7policy_dict.pop(val)
        sanitized_l7policy = l7policy_types.L7PolicyPUT(**l7policy_dict)
        context = pecan.request.context.get('octavia_context')

        db_l7policy = self._get_db_l7policy(context.session, id,
                                            show_deleted=False)
        listener = self._get_db_listener(
            context.session, db_l7policy.listener_id)
        # Make sure any specified redirect_pool_id exists
        if l7policy_dict.get('redirect_pool_id'):
            db_pool = self._get_db_pool(
                context.session, l7policy_dict['redirect_pool_id'])
            self._validate_protocol(listener.protocol, db_pool.protocol)
        load_balancer_id, listener_id = self._get_listener_and_loadbalancer_id(
            db_l7policy)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_statuses(lock_session,
                                                lb_id=load_balancer_id,
                                                listener_ids=[listener_id])

            # Prepare the data for the driver data model
            l7policy_dict = sanitized_l7policy.to_dict(render_unsets=False)
            l7policy_dict['id'] = id
            provider_l7policy_dict = (
                driver_utils.l7policy_dict_to_provider_dict(l7policy_dict))

            # Also prepare the baseline object data
            old_provider_l7policy = (
                driver_utils.db_l7policy_to_provider_l7policy(db_l7policy))

            # Dispatch to the driver
            LOG.info("Sending update L7 Policy %s to provider %s",
                     id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.l7policy_update,
                old_provider_l7policy,
                driver_dm.L7Policy.from_dict(provider_l7policy_dict))

            # Update the database to reflect what the driver just accepted
            sanitized_l7policy.provisioning_status = constants.PENDING_UPDATE
            db_l7policy_dict = sanitized_l7policy.to_dict(render_unsets=False)
            self.repositories.l7policy.update(lock_session, id,
                                              **db_l7policy_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_l7policy = self._get_db_l7policy(context.session, id)
        result = self._convert_db_to_type(db_l7policy,
                                          l7policy_types.L7PolicyResponse)
        return l7policy_types.L7PolicyRootResponse(l7policy=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a l7policy."""
        context = pecan.request.context.get('octavia_context')
        db_l7policy = self._get_db_l7policy(context.session, id,
                                            show_deleted=False)
        load_balancer_id, listener_id = self._get_listener_and_loadbalancer_id(
            db_l7policy)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        if db_l7policy.provisioning_status == constants.DELETED:
            return

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_and_listener_statuses(lock_session,
                                                lb_id=load_balancer_id,
                                                listener_ids=[listener_id])
            self.repositories.l7policy.update(
                lock_session, db_l7policy.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete L7 Policy %s to provider %s",
                     id, driver.name)
            provider_l7policy = driver_utils.db_l7policy_to_provider_l7policy(
                db_l7policy)
            driver_utils.call_provider(driver.name, driver.l7policy_delete,
                                       provider_l7policy)

    @pecan.expose()
    def _lookup(self, l7policy_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the l7policy passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if l7policy_id and remainder and remainder[0] == 'rules':
            remainder = remainder[1:]
            db_l7policy = self.repositories.l7policy.get(
                context.session, id=l7policy_id)
            if not db_l7policy:
                LOG.info("L7Policy %s not found.", l7policy_id)
                raise exceptions.NotFound(
                    resource='L7Policy', id=l7policy_id)
            return l7rule.L7RuleController(
                l7policy_id=db_l7policy.id), remainder
        return None
