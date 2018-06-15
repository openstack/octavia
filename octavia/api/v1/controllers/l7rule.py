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

import oslo_db.exception as oslo_exc
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import l7rule as l7rule_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import prepare as db_prepare

LOG = logging.getLogger(__name__)


class L7RuleController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id, l7policy_id):
        super(L7RuleController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.l7policy_id = l7policy_id
        self.handler = self.handler.l7rule

    @wsme_pecan.wsexpose(l7rule_types.L7RuleResponse, wtypes.text)
    def get(self, id):
        """Gets a single l7rule's details."""
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id)
        return self._convert_db_to_type(db_l7rule,
                                        l7rule_types.L7RuleResponse)

    @wsme_pecan.wsexpose([l7rule_types.L7RuleResponse])
    def get_all(self):
        """Lists all l7rules of a l7policy."""
        context = pecan.request.context.get('octavia_context')
        db_l7rules, _ = self.repositories.l7rule.get_all(
            context.session, l7policy_id=self.l7policy_id)
        return self._convert_db_to_type(db_l7rules,
                                        [l7rule_types.L7RuleResponse])

    def _test_lb_and_listener_statuses(self, session):
        """Verify load balancer is in a mutable state."""
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, self.load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=[self.listener_id]):
            LOG.info("L7Rule cannot be created or modified because the "
                     "Load Balancer is in an immutable state")
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    def _check_l7policy_max_rules(self, session):
        """Checks to make sure the L7Policy doesn't have too many rules."""
        count = self.repositories.l7rule.count(
            session, l7policy_id=self.l7policy_id)
        if count >= constants.MAX_L7RULES_PER_L7POLICY:
            raise exceptions.TooManyL7RulesOnL7Policy(id=self.l7policy_id)

    @wsme_pecan.wsexpose(l7rule_types.L7RuleResponse,
                         body=l7rule_types.L7RulePOST, status_code=202)
    def post(self, l7rule):
        """Creates a l7rule on an l7policy."""
        try:
            validate.l7rule_data(l7rule)
        except Exception as e:
            raise exceptions.L7RuleValidation(error=e)
        context = pecan.request.context.get('octavia_context')

        self._check_l7policy_max_rules(context.session)
        l7rule_dict = db_prepare.create_l7rule(
            l7rule.to_dict(render_unsets=True), self.l7policy_id)
        self._test_lb_and_listener_statuses(context.session)

        try:
            db_l7rule = self.repositories.l7rule.create(context.session,
                                                        **l7rule_dict)
        except oslo_exc.DBDuplicateEntry as de:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            self.repositories.load_balancer.update(
                context.session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            self.repositories.listener.update(
                context.session, self.listener_id,
                provisioning_status=constants.ACTIVE)
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
        try:
            LOG.info("Sending Creation of L7Rule %s to handler",
                     db_l7rule.id)
            self.handler.create(db_l7rule)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7rule = self._get_db_l7rule(context.session, db_l7rule.id)
        return self._convert_db_to_type(db_l7rule,
                                        l7rule_types.L7RuleResponse)

    @wsme_pecan.wsexpose(l7rule_types.L7RuleResponse,
                         wtypes.text, body=l7rule_types.L7RulePUT,
                         status_code=202)
    def put(self, id, l7rule):
        """Updates a l7rule."""
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id)
        new_l7rule = db_l7rule.to_dict()
        new_l7rule.update(l7rule.to_dict())
        new_l7rule = data_models.L7Rule.from_dict(new_l7rule)
        try:
            validate.l7rule_data(new_l7rule)
        except Exception as e:
            raise exceptions.L7RuleValidation(error=e)
        self._test_lb_and_listener_statuses(context.session)

        self.repositories.l7rule.update(
            context.session, id, provisioning_status=constants.PENDING_UPDATE)

        try:
            LOG.info("Sending Update of L7Rule %s to handler", id)
            self.handler.update(db_l7rule, l7rule)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7rule = self._get_db_l7rule(context.session, id)
        return self._convert_db_to_type(db_l7rule,
                                        l7rule_types.L7RuleResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a l7rule."""
        context = pecan.request.context.get('octavia_context')
        db_l7rule = self._get_db_l7rule(context.session, id)
        self._test_lb_and_listener_statuses(context.session)

        try:
            LOG.info("Sending Deletion of L7Rule %s to handler",
                     db_l7rule.id)
            self.handler.delete(db_l7rule)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7rule = self.repositories.l7rule.get(context.session, id=id)
        return self._convert_db_to_type(db_l7rule,
                                        l7rule_types.L7RuleResponse)
