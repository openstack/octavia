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

from oslo_db import exception as odb_exceptions
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import member as member_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
import octavia.common.validate as validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare


LOG = logging.getLogger(__name__)


class MemberController(base.BaseController):
    RBAC_TYPE = constants.RBAC_MEMBER

    def __init__(self, pool_id):
        super(MemberController, self).__init__()
        self.pool_id = pool_id
        self.handler = self.handler.member

    @wsme_pecan.wsexpose(member_types.MemberRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a single pool member's details."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)

        self._auth_validate_action(context, db_member.project_id,
                                   constants.RBAC_GET_ONE)

        self._validate_pool_id(id, db_member.pool_id)

        result = self._convert_db_to_type(
            db_member, member_types.MemberResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return member_types.MemberRootResponse(member=result)

    @wsme_pecan.wsexpose(member_types.MembersRootResponse, [wtypes.text],
                         ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all pool members of a pool."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')

        pool = self._get_db_pool(context.session, self.pool_id)

        self._auth_validate_action(context, pool.project_id,
                                   constants.RBAC_GET_ALL)

        db_members, links = self.repositories.member.get_all_API_list(
            context.session, show_deleted=False,
            pool_id=self.pool_id,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_members, [member_types.MemberResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return member_types.MembersRootResponse(
            members=result, members_links=links)

    def _get_affected_listener_ids(self, session, member=None):
        """Gets a list of all listeners this request potentially affects."""
        if member:
            listener_ids = [l.id for l in member.pool.listeners]
        else:
            pool = self._get_db_pool(session, self.pool_id)
            listener_ids = [l.id for l in pool.listeners]
        return listener_ids

    def _test_lb_and_listener_and_pool_statuses(self, session, member=None):
        """Verify load balancer is in a mutable state."""
        # We need to verify that any listeners referencing this member's
        # pool are also mutable
        pool = self._get_db_pool(session, self.pool_id)
        # Check the parent is not locked for some reason (ERROR, etc.)
        if pool.provisioning_status not in constants.MUTABLE_STATUSES:
            raise exceptions.ImmutableObject(resource='Pool', id=self.pool_id)
        load_balancer_id = pool.load_balancer_id
        if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                session, load_balancer_id,
                constants.PENDING_UPDATE, constants.PENDING_UPDATE,
                listener_ids=self._get_affected_listener_ids(session, member),
                pool_id=self.pool_id):
            LOG.info("Member cannot be created or modified because the "
                     "Load Balancer is in an immutable state")
            raise exceptions.ImmutableObject(resource='Load Balancer',
                                             id=load_balancer_id)

    def _reset_lb_listener_pool_statuses(self, session, member=None):
        # Setting LB + listener + pool back to active because this should be a
        # recoverable error
        pool = self._get_db_pool(session, self.pool_id)
        load_balancer_id = pool.load_balancer_id
        self.repositories.load_balancer.update(
            session, load_balancer_id,
            provisioning_status=constants.ACTIVE)
        for listener in self._get_affected_listener_ids(session, member):
            self.repositories.listener.update(
                session, listener,
                provisioning_status=constants.ACTIVE)
        self.repositories.pool.update(session, self.pool_id,
                                      provisioning_status=constants.ACTIVE)

    def _validate_create_member(self, lock_session, member_dict):
        """Validate creating member on pool."""
        try:
            return self.repositories.member.create(lock_session, **member_dict)
        except odb_exceptions.DBDuplicateEntry as de:
            column_list = ['pool_id', 'ip_address', 'protocol_port']
            constraint_list = ['uq_member_pool_id_address_protocol_port']
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
            elif (set(column_list) == set(de.columns) or
                  set(constraint_list) == set(de.columns)):
                raise exceptions.DuplicateMemberEntry(
                    ip_address=member_dict.get('ip_address'),
                    port=member_dict.get('protocol_port'))
        except odb_exceptions.DBError:
            # TODO(blogan): will have to do separate validation protocol
            # before creation or update since the exception messages
            # do not give any information as to what constraint failed
            raise exceptions.InvalidOption(value='', option='')

    def _send_member_to_handler(self, session, db_member):
        try:
            LOG.info("Sending Creation of Member %s to handler", db_member.id)
            self.handler.create(db_member)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, member=db_member)
                # Member now goes to ERROR
                self.repositories.member.update(
                    lock_session, db_member.id,
                    provisioning_status=constants.ERROR)
        db_member = self._get_db_member(session, db_member.id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

    def _validate_pool_id(self, member_id, db_member_pool_id):
        if db_member_pool_id != self.pool_id:
            raise exceptions.NotFound(resource='Member', id=member_id)

    @wsme_pecan.wsexpose(member_types.MemberRootResponse,
                         body=member_types.MemberRootPOST, status_code=201)
    def post(self, member_):
        """Creates a pool member on a pool."""
        member = member_.member
        context = pecan.request.context.get('octavia_context')

        validate.ip_not_reserved(member.address)

        # Validate member subnet
        if member.subnet_id and not validate.subnet_exists(member.subnet_id):
            raise exceptions.NotFound(resource='Subnet',
                                      id=member.subnet_id)
        pool = self.repositories.pool.get(context.session, id=self.pool_id)
        member.project_id = self._get_lb_project_id(context.session,
                                                    pool.load_balancer_id)

        self._auth_validate_action(context, member.project_id,
                                   constants.RBAC_POST)

        lock_session = db_api.get_session(autocommit=False)
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    lock_session,
                    data_models.Member,
                    member.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.Member._name())

            member_dict = db_prepare.create_member(member.to_dict(
                render_unsets=True), self.pool_id, bool(pool.health_monitor))

            self._test_lb_and_listener_and_pool_statuses(lock_session)

            db_member = self._validate_create_member(lock_session, member_dict)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        return self._send_member_to_handler(context.session, db_member)

    def _graph_create(self, lock_session, member_dict):
        pool = self.repositories.pool.get(lock_session, id=self.pool_id)
        member_dict = db_prepare.create_member(
            member_dict, self.pool_id, bool(pool.health_monitor))
        db_member = self._validate_create_member(lock_session, member_dict)

        return db_member

    @wsme_pecan.wsexpose(member_types.MemberRootResponse,
                         wtypes.text, body=member_types.MemberRootPUT,
                         status_code=200)
    def put(self, id, member_):
        """Updates a pool member."""
        member = member_.member
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)

        self._auth_validate_action(context, db_member.project_id,
                                   constants.RBAC_PUT)

        self._test_lb_and_listener_and_pool_statuses(context.session,
                                                     member=db_member)
        self.repositories.member.update(
            context.session, db_member.id,
            provisioning_status=constants.PENDING_UPDATE)

        self._validate_pool_id(id, db_member.pool_id)

        try:
            LOG.info("Sending Update of Member %s to handler", id)
            self.handler.update(db_member, member)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, member=db_member)
                # Member now goes to ERROR
                self.repositories.member.update(
                    lock_session, db_member.id,
                    provisioning_status=constants.ERROR)
        db_member = self._get_db_member(context.session, id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a pool member."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id)

        self._auth_validate_action(context, db_member.project_id,
                                   constants.RBAC_DELETE)

        if db_member.provisioning_status == constants.DELETED:
            return

        self._validate_pool_id(id, db_member.pool_id)

        self._test_lb_and_listener_and_pool_statuses(context.session,
                                                     member=db_member)
        self.repositories.member.update(
            context.session, db_member.id,
            provisioning_status=constants.PENDING_DELETE)

        try:
            LOG.info("Sending Deletion of Member %s to handler", db_member.id)
            self.handler.delete(db_member)
        except Exception:
            with excutils.save_and_reraise_exception(
                    reraise=False), db_api.get_lock_session() as lock_session:
                self._reset_lb_listener_pool_statuses(
                    lock_session, member=db_member)
                # Member now goes to ERROR
                self.repositories.member.update(
                    lock_session, db_member.id,
                    provisioning_status=constants.ERROR)


class MembersController(MemberController):

    def __init__(self, pool_id):
        super(MembersController, self).__init__(pool_id)

    @wsme_pecan.wsexpose(None, wtypes.text,
                         body=member_types.MembersRootPUT, status_code=202)
    def put(self, members_):
        """Updates all members."""
        members = members_.members
        context = pecan.request.context.get('octavia_context')

        db_pool = self._get_db_pool(context.session, self.pool_id)
        old_members = db_pool.members

        # Check POST+PUT+DELETE since this operation is all of 'CUD'
        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_POST)
        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_PUT)
        self._auth_validate_action(context, db_pool.project_id,
                                   constants.RBAC_DELETE)

        with db_api.get_lock_session() as lock_session:
            self._test_lb_and_listener_and_pool_statuses(lock_session)

            member_count_diff = len(members) - len(old_members)
            if member_count_diff > 0 and self.repositories.check_quota_met(
                    context.session, lock_session, data_models.Member,
                    db_pool.project_id, count=member_count_diff):
                raise exceptions.QuotaException(
                    resource=data_models.Member._name())

            old_member_uniques = {
                (m.ip_address, m.protocol_port): m.id for m in old_members}
            new_member_uniques = [
                (m.address, m.protocol_port) for m in members]

            # Find members that are brand new or updated
            new_members = []
            updated_members = []
            for m in members:
                if (m.address, m.protocol_port) not in old_member_uniques:
                    validate.ip_not_reserved(m.address)
                    new_members.append(m)
                else:
                    m.id = old_member_uniques[(m.address, m.protocol_port)]
                    updated_members.append(m)

            # Find members that are deleted
            deleted_members = []
            for m in old_members:
                if (m.ip_address, m.protocol_port) not in new_member_uniques:
                    deleted_members.append(m)

            # Create new members
            new_members_created = []
            for m in new_members:
                m = m.to_dict(render_unsets=False)
                m['project_id'] = db_pool.project_id
                new_members_created.append(self._graph_create(lock_session, m))
            # Update old members
            for m in updated_members:
                self.repositories.member.update(
                    lock_session, m.id,
                    provisioning_status=constants.PENDING_UPDATE)
            # Delete old members
            for m in deleted_members:
                self.repositories.member.update(
                    lock_session, m.id,
                    provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending Full Member Update to handler")
            new_member_ids = [m.id for m in new_members_created]
            old_member_ids = [m.id for m in deleted_members]
            self.handler.batch_update(
                old_member_ids, new_member_ids, updated_members)
