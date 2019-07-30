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
from octavia.api.v2.types import l7rule as l7rule_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare


LOG = logging.getLogger(__name__)


class L7RuleController(base.BaseController):
    RBAC_TYPE = constants.RBAC_L7RULE

    def __init__(self, l7policy_id):
        super(L7RuleController, self).__init__()
        self.l7policy_id = l7policy_id

    @wsme_pecan.wsexpose(l7rule_types.L7RuleRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a single l7rule's details."""
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id,
                                        show_deleted=False)

        self._auth_validate_action(context, db_l7rule.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            db_l7rule, l7rule_types.L7RuleResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return l7rule_types.L7RuleRootResponse(rule=result)

    @wsme_pecan.wsexpose(l7rule_types.L7RulesRootResponse, [wtypes.text],
                         ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all l7rules of a l7policy."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        l7policy = self._get_db_l7policy(context.session, self.l7policy_id,
                                         show_deleted=False)

        self._auth_validate_action(context, l7policy.project_id,
                                   constants.RBAC_GET_ALL)

        db_l7rules, links = self.repositories.l7rule.get_all_API_list(
            context.session, show_deleted=False, l7policy_id=self.l7policy_id,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_l7rules, [l7rule_types.L7RuleResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return l7rule_types.L7RulesRootResponse(
            rules=result, rules_links=links)

    def _test_lb_listener_policy_statuses(self, session):
        """Verify load balancer is in a mutable state."""
        l7policy = self._get_db_l7policy(session, self.l7policy_id)
        listener_id = l7policy.listener_id
        load_balancer_id = l7policy.listener.load_balancer_id
        # Check the parent is not locked for some reason (ERROR, etc.)
        if l7policy.provisioning_status not in constants.MUTABLE_STATUSES:
            raise exceptions.ImmutableObject(resource='L7Policy',
                                             id=self.l7policy_id)
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=[listener_id], l7policy_id=self.l7policy_id):
            LOG.info("L7Rule cannot be created or modified because the "
                     "Load Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource='Load Balancer',
                                             id=load_balancer_id)

    def _check_l7policy_max_rules(self, session):
        """Checks to make sure the L7Policy doesn't have too many rules."""
        count = self.repositories.l7rule.count(
            session, l7policy_id=self.l7policy_id)
        if count >= constants.MAX_L7RULES_PER_L7POLICY:
            raise exceptions.TooManyL7RulesOnL7Policy(id=self.l7policy_id)

    def _validate_create_l7rule(self, lock_session, l7rule_dict):
        try:
            return self.repositories.l7rule.create(lock_session, **l7rule_dict)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.IDAlreadyExists()
        except odb_exceptions.DBError:
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')

    @wsme_pecan.wsexpose(l7rule_types.L7RuleRootResponse,
                         body=l7rule_types.L7RuleRootPOST, status_code=201)
    def post(self, rule_):
        """Creates a l7rule on an l7policy."""
        l7rule = rule_.rule
        try:
            validate.l7rule_data(l7rule)
        except Exception as e:
            raise exceptions.L7RuleValidation(error=e)
        context = pecan.request.context.get('octavia_context')

        db_l7policy = self._get_db_l7policy(context.session, self.l7policy_id,
                                            show_deleted=False)
        load_balancer_id, listener_id = self._get_listener_and_loadbalancer_id(
            db_l7policy)
        l7rule.project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)

        self._check_l7policy_max_rules(context.session)

        self._auth_validate_action(context, l7rule.project_id,
                                   constants.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        lock_session = db_api.get_session(autocommit=False)
        try:
            l7rule_dict = db_prepare.create_l7rule(
                l7rule.to_dict(render_unsets=True), self.l7policy_id)

            self._test_lb_listener_policy_statuses(context.session)

            db_l7rule = self._validate_create_l7rule(lock_session, l7rule_dict)

            # Prepare the data for the driver data model
            provider_l7rule = (
                driver_utils.db_l7rule_to_provider_l7rule(db_l7rule))

            # Dispatch to the driver
            LOG.info("Sending create L7 Rule %s to provider %s",
                     db_l7rule.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.l7rule_create, provider_l7rule)

            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        db_l7rule = self._get_db_l7rule(context.session, db_l7rule.id)
        result = self._convert_db_to_type(db_l7rule,
                                          l7rule_types.L7RuleResponse)
        return l7rule_types.L7RuleRootResponse(rule=result)

    def _graph_create(self, lock_session, rule_dict):
        try:
            validate.l7rule_data(l7rule_types.L7RulePOST(**rule_dict))
        except Exception as e:
            raise exceptions.L7RuleValidation(error=e)
        rule_dict = db_prepare.create_l7rule(rule_dict, self.l7policy_id)
        db_rule = self._validate_create_l7rule(lock_session, rule_dict)

        return db_rule

    @wsme_pecan.wsexpose(l7rule_types.L7RuleRootResponse,
                         wtypes.text, body=l7rule_types.L7RuleRootPUT,
                         status_code=200)
    def put(self, id, l7rule_):
        """Updates a l7rule."""
        l7rule = l7rule_.rule
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id,
                                        show_deleted=False)

        # Handle the invert unset
        if l7rule.invert is None:
            l7rule.invert = False

        new_l7rule = db_l7rule.to_dict()
        new_l7rule.update(l7rule.to_dict())
        new_l7rule = data_models.L7Rule.from_dict(new_l7rule)

        db_l7policy = self._get_db_l7policy(context.session, self.l7policy_id,
                                            show_deleted=False)
        load_balancer_id, listener_id = self._get_listener_and_loadbalancer_id(
            db_l7policy)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        try:
            validate.l7rule_data(new_l7rule)
        except Exception as e:
            raise exceptions.L7RuleValidation(error=e)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_listener_policy_statuses(lock_session)

            # Prepare the data for the driver data model
            l7rule_dict = l7rule.to_dict(render_unsets=False)
            l7rule_dict['id'] = id
            provider_l7rule_dict = (
                driver_utils.l7rule_dict_to_provider_dict(l7rule_dict))

            # Also prepare the baseline object data
            old_provider_l7rule = driver_utils.db_l7rule_to_provider_l7rule(
                db_l7rule)

            # Dispatch to the driver
            LOG.info("Sending update L7 Rule %s to provider %s", id,
                     driver.name)
            driver_utils.call_provider(
                driver.name, driver.l7rule_update,
                old_provider_l7rule,
                driver_dm.L7Rule.from_dict(provider_l7rule_dict))

            # Update the database to reflect what the driver just accepted
            l7rule.provisioning_status = constants.PENDING_UPDATE
            db_l7rule_dict = l7rule.to_dict(render_unsets=False)
            self.repositories.l7rule.update(lock_session, id, **db_l7rule_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_l7rule = self._get_db_l7rule(context.session, id)
        result = self._convert_db_to_type(db_l7rule,
                                          l7rule_types.L7RuleResponse)
        return l7rule_types.L7RuleRootResponse(rule=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a l7rule."""
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id,
                                        show_deleted=False)

        db_l7policy = self._get_db_l7policy(context.session, self.l7policy_id,
                                            show_deleted=False)
        load_balancer_id, listener_id = self._get_listener_and_loadbalancer_id(
            db_l7policy)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        if db_l7rule.provisioning_status == constants.DELETED:
            return

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:

            self._test_lb_listener_policy_statuses(lock_session)

            self.repositories.l7rule.update(
                lock_session, db_l7rule.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete L7 Rule %s to provider %s", id,
                     driver.name)
            provider_l7rule = (
                driver_utils.db_l7rule_to_provider_l7rule(db_l7rule))
            driver_utils.call_provider(driver.name, driver.l7rule_delete,
                                       provider_l7rule)
