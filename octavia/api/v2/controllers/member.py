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
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.types import member as member_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import validate
from octavia.db import prepare as db_prepare
from octavia.i18n import _


LOG = logging.getLogger(__name__)


class MemberController(base.BaseController):
    RBAC_TYPE = constants.RBAC_MEMBER

    def __init__(self, pool_id):
        super().__init__()
        self.pool_id = pool_id

    @wsme_pecan.wsexpose(member_types.MemberRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get(self, id, fields=None):
        """Gets a single pool member's details."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
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
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')

        with context.session.begin():
            pool = self._get_db_pool(context.session, self.pool_id,
                                     show_deleted=False, limited_graph=True)

            self._auth_validate_action(context, pool.project_id,
                                       constants.RBAC_GET_ALL)

            db_members, links = self.repositories.member.get_all_API_list(
                context.session, show_deleted=False,
                pool_id=self.pool_id,
                pagination_helper=pcontext.get(constants.PAGINATION_HELPER),
                limited_graph=True)
        result = self._convert_db_to_type(
            db_members, [member_types.MemberResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return member_types.MembersRootResponse(
            members=result, members_links=links)

    def _get_affected_listener_ids(self, session, member=None):
        """Gets a list of all listeners this request potentially affects."""
        if member:
            listener_ids = [li.id for li in member.pool.listeners]
        else:
            pool = self._get_db_pool(session, self.pool_id)
            listener_ids = [li.id for li in pool.listeners]
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
            ret = self.repositories.member.create(lock_session, **member_dict)
            lock_session.flush()
            return ret
        except odb_exceptions.DBDuplicateEntry as e:
            raise exceptions.DuplicateMemberEntry(
                ip_address=member_dict.get('ip_address'),
                port=member_dict.get('protocol_port')) from e
        except odb_exceptions.DBReferenceError as e:
            raise exceptions.InvalidOption(value=member_dict.get(e.key),
                                           option=e.key) from e
        except odb_exceptions.DBError as e:
            raise exceptions.APIException() from e
        return None

    def _validate_pool_id(self, member_id, db_member_pool_id):
        if db_member_pool_id != self.pool_id:
            raise exceptions.NotFound(resource='Member', id=member_id)

    @wsme_pecan.wsexpose(member_types.MemberRootResponse,
                         body=member_types.MemberRootPOST, status_code=201)
    def post(self, member_):
        """Creates a pool member on a pool."""
        member = member_.member
        context = pecan_request.context.get('octavia_context')

        validate.ip_not_reserved(member.address)

        # Validate member subnet
        """ CCloud: disable subnet validation since it's not used by the f5 backend driver and just impose
             a risk of failure due to failed keystone / neutron calls """
        #if (member.subnet_id and
        #        not validate.subnet_exists(member.subnet_id, context=context)):
        #    raise exceptions.NotFound(resource='Subnet', id=member.subnet_id)

        flavor_dict = {}
        with context.session.begin():
            pool = self.repositories.pool.get(context.session, id=self.pool_id)
            member.project_id, provider = self._get_lb_project_id_provider(
                context.session, pool.load_balancer_id)
            if pool.load_balancer.flavor_id:
                try:
                    flavor_dict = (
                        self.repositories.flavor.get_flavor_metadata_dict(
                            context.session, pool.load_balancer.flavor_id))
                except sa_exception.NoResultFound:
                    LOG.error("load balancer has a flavor ID: %s that was not "
                              "found in the database. Assuming no flavor.",
                              pool.load_balancer.flavor_id)

        self._auth_validate_action(context, member.project_id,
                                   constants.RBAC_POST)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        context.session.begin()
        try:
            if self.repositories.check_quota_met(
                    context.session,
                    data_models.Member,
                    member.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.Member._name())

            db_member_dict = member.to_dict(render_unsets=True)

            # Validate and store port SR-IOV vnic_type
            request_sriov = db_member_dict.pop('request_sriov')
            if (request_sriov and not
                    flavor_dict.get(constants.ALLOW_MEMBER_SRIOV, False)):
                raise exceptions.MemberSRIOVDisabled
            if request_sriov:
                db_member_dict[constants.VNIC_TYPE] = (
                    constants.VNIC_TYPE_DIRECT)
            else:
                db_member_dict[constants.VNIC_TYPE] = (
                    constants.VNIC_TYPE_NORMAL)

            member_dict = db_prepare.create_member(db_member_dict,
                                                   self.pool_id,
                                                   bool(pool.health_monitor))

            self._test_lb_and_listener_and_pool_statuses(context.session)

            db_member = self._validate_create_member(context.session,
                                                     member_dict)

            # Prepare the data for the driver data model
            provider_member = (
                driver_utils.db_member_to_provider_member(db_member))

            # Dispatch to the driver
            LOG.info("Sending create Member %s to provider %s",
                     db_member.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.member_create, provider_member)

            context.session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                context.session.rollback()

        with context.session.begin():
            db_member = self._get_db_member(context.session, db_member.id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

    def _graph_create(self, lock_session, member_dict):
        pool = self.repositories.pool.get(lock_session, id=self.pool_id)

        # Validate and store port SR-IOV vnic_type
        request_sriov = member_dict.pop('request_sriov')
        flavor_dict = {}
        if pool.load_balancer.flavor_id:
            try:
                flavor_dict = (
                    self.repositories.flavor.get_flavor_metadata_dict(
                        lock_session, pool.load_balancer.flavor_id))
            except sa_exception.NoResultFound:
                LOG.error("load balancer has a flavor ID: %s that was not "
                          "found in the database. Assuming no flavor.",
                          pool.load_balancer.flavor_id)
        if (request_sriov and not
                flavor_dict.get(constants.ALLOW_MEMBER_SRIOV, False)):
            raise exceptions.MemberSRIOVDisabled

        if request_sriov:
            member_dict[constants.VNIC_TYPE] = constants.VNIC_TYPE_DIRECT
        else:
            member_dict[constants.VNIC_TYPE] = constants.VNIC_TYPE_NORMAL

        member_dict = db_prepare.create_member(
            member_dict, self.pool_id, bool(pool.health_monitor))
        db_member = self._validate_create_member(lock_session, member_dict)

        return db_member

    def _set_default_on_none(self, member):
        """Reset settings to their default values if None/null was passed in

        A None/null value can be passed in to clear a value. PUT values
        that were not provided by the user have a type of wtypes.UnsetType.
        If the user is attempting to clear values, they should either
        be set to None (for example in the name field) or they should be
        reset to their default values.
        This method is intended to handle those values that need to be set
        back to a default value.
        """
        if member.backup is None:
            member.backup = False
        if member.weight is None:
            member.weight = constants.DEFAULT_WEIGHT

    @wsme_pecan.wsexpose(member_types.MemberRootResponse,
                         wtypes.text, body=member_types.MemberRootPUT,
                         status_code=200)
    def put(self, id, member_):
        """Updates a pool member."""
        member = member_.member
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_member = self._get_db_member(context.session, id,
                                            show_deleted=False)
            pool = self.repositories.pool.get(context.session,
                                              id=db_member.pool_id)
            project_id, provider = self._get_lb_project_id_provider(
                context.session, pool.load_balancer_id)

        self._auth_validate_action(context, project_id, constants.RBAC_PUT)

        self._validate_pool_id(id, db_member.pool_id)

        self._set_default_on_none(member)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with context.session.begin():
            self._test_lb_and_listener_and_pool_statuses(context.session,
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
            self.repositories.member.update(context.session, id,
                                            **db_member_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        with context.session.begin():
            db_member = self._get_db_member(context.session, id)
        result = self._convert_db_to_type(db_member,
                                          member_types.MemberResponse)
        return member_types.MemberRootResponse(member=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a pool member."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
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

        with context.session.begin():
            self._test_lb_and_listener_and_pool_statuses(context.session,
                                                         member=db_member)
            self.repositories.member.update(
                context.session, db_member.id,
                provisioning_status=constants.PENDING_DELETE)

            LOG.info("Sending delete Member %s to provider %s", id,
                     driver.name)
            provider_member = (
                driver_utils.db_member_to_provider_member(db_member))
            driver_utils.call_provider(driver.name, driver.member_delete,
                                       provider_member)


class MembersController(MemberController):

    def __init__(self, pool_id):
        super().__init__(pool_id)

    @wsme_pecan.wsexpose(None, wtypes.text,
                         body=member_types.MembersRootPUT, status_code=202)
    def put(self, additive_only=False, members_=None):
        """Updates all members."""
        members = members_.members
        additive_only = strutils.bool_from_string(additive_only)
        context = pecan_request.context.get('octavia_context')

        with context.session.begin():
            db_pool = self._get_db_pool(context.session, self.pool_id)

            project_id, provider = self._get_lb_project_id_provider(
                context.session, db_pool.load_balancer_id)

        # Check POST+PUT+DELETE since this operation is all of 'CUD'
        self._auth_validate_action(context, project_id, constants.RBAC_POST)
        self._auth_validate_action(context, project_id, constants.RBAC_PUT)
        if not additive_only:
            self._auth_validate_action(context, project_id,
                                       constants.RBAC_DELETE)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        with context.session.begin():
            self._test_lb_and_listener_and_pool_statuses(context.session)

            # Reload the pool, the members may have been updated between the
            # first query in this function and the lock of the loadbalancer
            db_pool = self._get_db_pool(context.session, self.pool_id)
            old_members = db_pool.members

            old_member_uniques = {
                (m.ip_address, m.protocol_port): m.id for m in old_members}
            new_member_uniques = [
                (m.address, m.protocol_port) for m in members]

            # Find members that are brand new or updated
            new_members = []
            updated_members = []
            updated_member_uniques = set()
            for m in members:
                key = (m.address, m.protocol_port)
                if key not in old_member_uniques:
                    validate.ip_not_reserved(m.address)
                    new_members.append(m)
                else:
                    m.id = old_member_uniques[key]
                    if key in updated_member_uniques:
                        LOG.error("Member %s is updated multiple times in "
                                  "the same batch request.", m.id)
                        raise exceptions.ValidationException(
                            detail=_("Member must be updated only once in the "
                                     "same request."))
                    updated_member_uniques.add(key)
                    updated_members.append(m)

            # Find members that are deleted
            deleted_members = []
            for m in old_members:
                if (m.ip_address, m.protocol_port) not in new_member_uniques:
                    deleted_members.append(m)

            if not (deleted_members or new_members or updated_members):
                LOG.info("Member batch update is a noop, rolling back and "
                         "returning early.")
                context.session.rollback()
                return

            if additive_only:
                member_count_diff = len(new_members)
            else:
                member_count_diff = len(new_members) - len(deleted_members)
            if member_count_diff > 0 and self.repositories.check_quota_met(
                    context.session, data_models.Member,
                    db_pool.project_id, count=member_count_diff):
                raise exceptions.QuotaException(
                    resource=data_models.Member._name())

            provider_members = []
            valid_subnets = set()
            # Create new members
            for m in new_members:
                # NOTE(mnaser): In order to avoid hitting the Neutron API hard
                # when creating many new members, we cache the
                # validation results. We also validate new
                # members only since subnet ID is immutable.
                # If the member doesn't have a subnet, or the subnet is
                # already valid, move on. Run validate and add it to
                # cache otherwise.
                if m.subnet_id and m.subnet_id not in valid_subnets:
                    # If the subnet does not exist,
                    # raise an exception and get out.
                    if not validate.subnet_exists(
                            m.subnet_id, context=context):
                        raise exceptions.NotFound(
                            resource='Subnet', id=m.subnet_id)

                    # Mark the subnet as valid for future runs.
                    valid_subnets.add(m.subnet_id)

                m = m.to_dict(render_unsets=False)
                m['project_id'] = db_pool.project_id
                created_member = self._graph_create(context.session, m)
                provider_member = driver_utils.db_member_to_provider_member(
                    created_member)
                provider_members.append(provider_member)
            # Update old members
            for m in updated_members:
                m.provisioning_status = constants.PENDING_UPDATE
                m.project_id = db_pool.project_id
                db_member_dict = m.to_dict(render_unsets=False)
                db_member_dict.pop('id')
                # We don't allow updating the vnic_type
                # TODO(johnsom) Give the user an error once we change the
                #               wsme type for batch member update to not use
                #               the MemberPOST type
                db_member_dict.pop(constants.REQUEST_SRIOV)
                self.repositories.member.update(
                    context.session, m.id, **db_member_dict)

                m.pool_id = self.pool_id
                provider_members.append(
                    driver_utils.db_member_to_provider_member(m))
            # Delete old members
            for m in deleted_members:
                if additive_only:
                    # Members are appended to the dict and their status remains
                    # unchanged, because they are logically "untouched".
                    db_member_dict = m.to_dict(render_unsets=False)
                    db_member_dict.pop('id')
                    m.pool_id = self.pool_id
                    provider_members.append(
                        driver_utils.db_member_to_provider_member(m))
                else:
                    # Members are changed to PENDING_DELETE and not passed.
                    self.repositories.member.update(
                        context.session, m.id,
                        provisioning_status=constants.PENDING_DELETE)

            # Dispatch to the driver
            LOG.info("Sending Pool %s batch member update to provider %s",
                     db_pool.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.member_batch_update, db_pool.id,
                provider_members)
