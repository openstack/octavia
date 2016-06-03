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

import oslo_db.exception as oslo_exc
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import member as member_types
from octavia.common import constants
from octavia.common import exceptions
import octavia.common.validate as validate
from octavia.db import prepare as db_prepare
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class MembersController(base.BaseController):

    def __init__(self, load_balancer_id, pool_id, listener_id=None):
        super(MembersController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.pool_id = pool_id
        self.handler = self.handler.member

    @wsme_pecan.wsexpose(member_types.MemberResponse, wtypes.text)
    def get(self, id):
        """Gets a single pool member's details."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose([member_types.MemberResponse])
    def get_all(self):
        """Lists all pool members of a pool."""
        context = pecan.request.context.get('octavia_context')
        db_members = self.repositories.member.get_all(
            context.session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_members,
                                        [member_types.MemberResponse])

    def _get_affected_listener_ids(self, session, member=None):
        """Gets a list of all listeners this request potentially affects."""
        listener_ids = []
        if member:
            listener_ids = [l.id for l in member.pool.listeners]
        else:
            pool = self._get_db_pool(session, self.pool_id)
            for listener in pool.listeners:
                if listener.id not in listener_ids:
                    listener_ids.append(listener.id)
        if self.listener_id and self.listener_id not in listener_ids:
            listener_ids.append(self.listener_id)
        return listener_ids

    def _test_lb_and_listener_statuses(self, session, member=None):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this member's
        # pool are also mutable
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, self.load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, member)):
            LOG.info(_LI("Member cannot be created or modified because the "
                         "Load Balancer is in an immutable state"))
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    @wsme_pecan.wsexpose(member_types.MemberResponse,
                         body=member_types.MemberPOST, status_code=202)
    def post(self, member):
        """Creates a pool member on a pool."""
        context = pecan.request.context.get('octavia_context')
        # Validate member subnet
        if member.subnet_id and not validate.subnet_exists(member.subnet_id):
            raise exceptions.NotFound(resource='Subnet',
                                      id=member.subnet_id)
        member_dict = db_prepare.create_member(member.to_dict(
            render_unsets=True), self.pool_id)
        self._test_lb_and_listener_statuses(context.session)

        try:
            db_member = self.repositories.member.create(context.session,
                                                        **member_dict)
        except oslo_exc.DBDuplicateEntry as de:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            self.repositories.load_balancer.update(
                context.session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            for listener_id in self._get_affected_listener_ids(
                    context.session):
                self.repositories.listener.update(
                    context.session, listener_id,
                    provisioning_status=constants.ACTIVE)
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
            elif (set(['pool_id', 'ip_address', 'protocol_port']) ==
                  set(de.columns)):
                raise exceptions.DuplicateMemberEntry(
                    ip_address=member_dict.get('ip_address'),
                    port=member_dict.get('protocol_port'))
        try:
            LOG.info(_LI("Sending Creation of Member %s to handler"),
                     db_member.id)
            self.handler.create(db_member)
        except Exception:
            for listener_id in self._get_affected_listener_ids(
                    context.session):
                with excutils.save_and_reraise_exception(reraise=False):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        db_member = self._get_db_member(context.session, db_member.id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose(member_types.MemberResponse,
                         wtypes.text, body=member_types.MemberPUT,
                         status_code=202)
    def put(self, id, member):
        """Updates a pool member."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)
        self._test_lb_and_listener_statuses(context.session, member=db_member)

        try:
            LOG.info(_LI("Sending Update of Member %s to handler"), id)
            self.handler.update(db_member, member)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener_id in self._get_affected_listener_ids(
                        context.session, db_member):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        db_member = self._get_db_member(context.session, id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a pool member."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)
        self._test_lb_and_listener_statuses(context.session, member=db_member)

        try:
            LOG.info(_LI("Sending Deletion of Member %s to handler"),
                     db_member.id)
            self.handler.delete(db_member)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                for listener_id in self._get_affected_listener_ids(
                        context.session, db_member):
                    self.repositories.listener.update(
                        context.session, listener_id,
                        operating_status=constants.ERROR)
        db_member = self.repositories.member.get(context.session, id=id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)
