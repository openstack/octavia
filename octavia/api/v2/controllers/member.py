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

    @wsme_pecan.wsexpose(member_types.MemberRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a single pool member's details."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id,
                                        show_deleted=False)

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

        pool = self._get_db_pool(context.session, self.pool_id,
                                 show_deleted=False)

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
        member.project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, member.project_id,
                                   constants.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

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

            # Prepare the data for the driver data model
            provider_member = (
                driver_utils.db_member_to_provider_member(db_member))

            # Dispatch to the driver
            LOG.info("Sending create Member %s to provider %s",
                     db_member.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.member_create, provider_member)

            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        db_member = self._get_db_member(context.session, db_member.id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

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
        db_member = self._get_db_member(context.session, id,
                                        show_deleted=False)

        pool = self.repositories.pool.get(context.session,
                                          id=db_member.pool_id)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        self._validate_pool_id(id, db_member.pool_id)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:
            self._test_lb_and_listener_and_pool_statuses(lock_session,
                                                         member=db_member)

            # Prepare the data for the driver data model
            member_dict = member.to_dict(render_unsets=False)
            member_dict['id'] = id
            provider_member_dict = (
                driver_utils.member_dict_to_provider_dict(member_dict))

            # Also prepare the baseline object data
            old_provider_member = driver_utils.db_member_to_provider_member(
                db_member)

            # Dispatch to the driver
            LOG.info("Sending update Member %s to provider %s", id,
                     driver.name)
            driver_utils.call_provider(
                driver.name, driver.member_update,
                old_provider_member,
                driver_dm.Member.from_dict(provider_member_dict))

            # Update the database to reflect what the driver just accepted
            member.provisioning_status = constants.PENDING_UPDATE
            db_member_dict = member.to_dict(render_unsets=False)
            self.repositories.member.update(lock_session, id, **db_member_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_member = self._get_db_member(context.session, id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a pool member."""
        context = pecan.request.context.get('octavia_context')
        db_member = self._get_db_member(context.session, id,
                                        show_deleted=False)

        pool = self.repositories.pool.get(context.session,
                                          id=db_member.pool_id)
        project_id, provider = self._get_lb_project_id_provider(
            context.session, pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        self._validate_pool_id(id, db_member.pool_id)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with db_api.get_lock_session() as lock_session:
            self._test_lb_and_listener_and_pool_statuses(lock_session,
                                                         member=db_member)
            self.repositories.member.update(
                lock_session, db_member.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete Member %s to provider %s", id,
                     driver.name)
            provider_member = (
                driver_utils.db_member_to_provider_member(db_member))
            driver_utils.call_provider(driver.name, driver.member_delete,
                                       provider_member)


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

        project_id, provider = self._get_lb_project_id_provider(
            context.session, db_pool.load_balancer_id)

        # Check POST+PUT+DELETE since this operation is all of 'CUD'
        self._auth_validate_action(context, project_id, constants.RBAC_POST)
        self._auth_validate_action(context, project_id, constants.RBAC_PUT)
        self._auth_validate_action(context, project_id, constants.RBAC_DELETE)

        # Validate member subnets
        for member in members:
            if member.subnet_id and not validate.subnet_exists(
                    member.subnet_id):
                raise exceptions.NotFound(resource='Subnet',
                                          id=member.subnet_id)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

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

            provider_members = []
            # Create new members
            for m in new_members:
                m = m.to_dict(render_unsets=False)
                m['project_id'] = db_pool.project_id
                created_member = self._graph_create(lock_session, m)
                provider_member = driver_utils.db_member_to_provider_member(
                    created_member)
                provider_members.append(provider_member)
            # Update old members
            for m in updated_members:
                m.provisioning_status = constants.PENDING_UPDATE
                db_member_dict = m.to_dict(render_unsets=False)
                db_member_dict.pop('id')
                self.repositories.member.update(
                    lock_session, m.id, **db_member_dict)

                m.pool_id = self.pool_id
                provider_members.append(
                    driver_utils.db_member_to_provider_member(m))
            # Delete old members
            for m in deleted_members:
                self.repositories.member.update(
                    lock_session, m.id,
                    provisioning_status=constants.PENDING_DELETE)

            # Dispatch to the driver
            LOG.info("Sending Pool %s batch member update to provider %s",
                     db_pool.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.member_batch_update, provider_members)
