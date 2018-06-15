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
from octavia.api.v1.controllers import l7rule
from octavia.api.v1.types import l7policy as l7policy_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import prepare as db_prepare

LOG = logging.getLogger(__name__)


class L7PolicyController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id):
        super(L7PolicyController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.handler = self.handler.l7policy

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyResponse, wtypes.text)
    def get(self, id):
        """Gets a single l7policy's details."""
        context = pecan.request.context.get('octavia_context')
        db_l7policy = self._get_db_l7policy(context.session, id)
        return self._convert_db_to_type(db_l7policy,
                                        l7policy_types.L7PolicyResponse)

    @wsme_pecan.wsexpose([l7policy_types.L7PolicyResponse])
    def get_all(self):
        """Lists all l7policies of a listener."""
        context = pecan.request.context.get('octavia_context')
        db_l7policies, _ = self.repositories.l7policy.get_all(
            context.session, listener_id=self.listener_id)
        return self._convert_db_to_type(db_l7policies,
                                        [l7policy_types.L7PolicyResponse])

    def _test_lb_and_listener_statuses(self, session):
        """Verify load balancer is in a mutable state."""
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, self.load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=[self.listener_id]):
            LOG.info("L7Policy cannot be created or modified because the "
                     "Load Balancer is in an immutable state")
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyResponse,
                         body=l7policy_types.L7PolicyPOST, status_code=202)
    def post(self, l7policy):
        """Creates a l7policy on a listener."""
        context = pecan.request.context.get('octavia_context')

        l7policy_dict = validate.sanitize_l7policy_api_args(
            l7policy.to_dict(render_unsets=True), create=True)
        # Make sure any pool specified by redirect_pool_id exists
        if l7policy_dict.get('redirect_pool_id'):
            self._get_db_pool(
                context.session, l7policy_dict['redirect_pool_id'])
        l7policy_dict = db_prepare.create_l7policy(l7policy_dict,
                                                   self.load_balancer_id,
                                                   self.listener_id)
        self._test_lb_and_listener_statuses(context.session)

        try:
            db_l7policy = self.repositories.l7policy.create(context.session,
                                                            **l7policy_dict)
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
            LOG.info("Sending Creation of L7Policy %s to handler",
                     db_l7policy.id)
            self.handler.create(db_l7policy)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7policy = self._get_db_l7policy(context.session, db_l7policy.id)
        return self._convert_db_to_type(db_l7policy,
                                        l7policy_types.L7PolicyResponse)

    @wsme_pecan.wsexpose(l7policy_types.L7PolicyResponse,
                         wtypes.text, body=l7policy_types.L7PolicyPUT,
                         status_code=202)
    def put(self, id, l7policy):
        """Updates a l7policy."""
        l7policy_dict = validate.sanitize_l7policy_api_args(
            l7policy.to_dict(render_unsets=False))
        context = pecan.request.context.get('octavia_context')
        # Make sure any specified redirect_pool_id exists
        if l7policy_dict.get('redirect_pool_id'):
            self._get_db_pool(
                context.session, l7policy_dict['redirect_pool_id'])
        db_l7policy = self._get_db_l7policy(context.session, id)
        self._test_lb_and_listener_statuses(context.session)

        self.repositories.l7policy.update(
            context.session, id, provisioning_status=constants.PENDING_UPDATE)

        try:
            LOG.info("Sending Update of L7Policy %s to handler", id)
            self.handler.update(
                db_l7policy, l7policy_types.L7PolicyPUT(**l7policy_dict))
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7policy = self._get_db_l7policy(context.session, id)
        return self._convert_db_to_type(db_l7policy,
                                        l7policy_types.L7PolicyResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a l7policy."""
        context = pecan.request.context.get('octavia_context')
        db_l7policy = self._get_db_l7policy(context.session, id)
        self._test_lb_and_listener_statuses(context.session)

        try:
            LOG.info("Sending Deletion of L7Policy %s to handler",
                     db_l7policy.id)
            self.handler.delete(db_l7policy)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, self.listener_id,
                    operating_status=constants.ERROR)
        db_l7policy = self.repositories.l7policy.get(context.session, id=id)
        return self._convert_db_to_type(db_l7policy,
                                        l7policy_types.L7PolicyResponse)

    @pecan.expose()
    def _lookup(self, l7policy_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the l7policy passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if l7policy_id and remainder and remainder[0] == 'l7rules':
            remainder = remainder[1:]
            db_l7policy = self.repositories.l7policy.get(
                context.session, id=l7policy_id)
            if not db_l7policy:
                LOG.info("L7Policy %s not found.", l7policy_id)
                raise exceptions.NotFound(
                    resource=data_models.L7Policy._name(), id=l7policy_id)
            return l7rule.L7RuleController(
                load_balancer_id=self.load_balancer_id,
                listener_id=self.listener_id,
                l7policy_id=db_l7policy.id), remainder
        return None
