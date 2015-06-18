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

import logging

import oslo_db.exception as oslo_exc
from oslo_utils import excutils
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.types import member as member_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class MembersController(base.BaseController):

    def __init__(self, load_balancer_id, listener_id, pool_id):
        super(MembersController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.listener_id = listener_id
        self.pool_id = pool_id
        self.handler = self.handler.member

    @wsme_pecan.wsexpose(member_types.MemberResponse, wtypes.text)
    def get(self, id):
        """Gets a single pool member's details."""
        session = db_api.get_session()
        db_member = self.repositories.member.get(session, id=id)
        if not db_member:
            LOG.info(_LI("Member %s not found") % id)
            raise exceptions.NotFound(
                resource=data_models.Member._name(), id=id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose([member_types.MemberResponse])
    def get_all(self):
        """Lists all pool members of a pool."""
        session = db_api.get_session()
        db_members = self.repositories.member.get_all(
            session, pool_id=self.pool_id)
        return self._convert_db_to_type(db_members,
                                        [member_types.MemberResponse])

    @wsme_pecan.wsexpose(member_types.MemberResponse,
                         body=member_types.MemberPOST, status_code=202)
    def post(self, member):
        """Creates a pool member on a pool."""
        session = db_api.get_session()
        member_dict = member.to_dict()
        member_dict['pool_id'] = self.pool_id
        member_dict['operating_status'] = constants.OFFLINE
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all its listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Member cannot be created because its Load "
                         "Balancer is in an immutable state."))
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        try:
            db_member = self.repositories.member.create(session, **member_dict)
        except oslo_exc.DBDuplicateEntry as de:
            # Setting LB and Listener back to active because this is just a
            # validation failure
            self.repositories.load_balancer.update(
                session, self.load_balancer_id,
                provisioning_status=constants.ACTIVE)
            self.repositories.listener.update(
                session, self.listener_id,
                provisioning_status=constants.ACTIVE)
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
            elif (set(['pool_id', 'ip_address', 'protocol_port']) ==
                  set(de.columns)):
                raise exceptions.DuplicateMemberEntry(
                    ip_address=member_dict.get('ip_address'),
                    port=member_dict.get('protocol_port'))
        try:
            LOG.info(_LI("Sending Creation of Member %s to handler") %
                     db_member.id)
            self.handler.create(db_member)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_member = self.repositories.member.get(session, id=db_member.id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose(member_types.MemberResponse,
                         wtypes.text, body=member_types.MemberPUT,
                         status_code=202)
    def put(self, id, member):
        """Updates a pool member."""
        session = db_api.get_session()
        db_member = self.repositories.member.get(session, id=id)
        if not db_member:
            LOG.info(_LI("Member %s cannot be updated because its Load "
                         "Balancer is in an immutable state.") % id)
            LOG.info(_LI("Member %s not found") % id)
            raise exceptions.NotFound(
                resource=data_models.Member._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all its listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        try:
            LOG.info(_LI("Sending Update of Member %s to handler") % id)
            self.handler.update(db_member, member)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_member = self.repositories.member.get(session, id=id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a pool member."""
        session = db_api.get_session()
        db_member = self.repositories.member.get(session, id=id)
        if not db_member:
            LOG.info(_LI("Member %s not found") % id)
            raise exceptions.NotFound(
                resource=data_models.Member._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all its listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, self.listener_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE):
            LOG.info(_LI("Member %s cannot be deleted because its Load "
                         "Balancer is in an immutable state.") % id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        db_member = self.repositories.member.get(session, id=id)
        try:
            LOG.info(_LI("Sending Deletion of Member %s to handler") %
                     db_member.id)
            self.handler.delete(db_member)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, self.listener_id,
                    operating_status=constants.ERROR)
        db_member = self.repositories.member.get(session, id=id)
        return self._convert_db_to_type(db_member, member_types.MemberResponse)
