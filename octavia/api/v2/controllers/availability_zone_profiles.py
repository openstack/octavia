#    Copyright 2019 Verizon Media
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
from oslo_serialization import jsonutils
from oslo_utils import excutils
from oslo_utils import uuidutils
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.types import availability_zone_profile as profile_types
from octavia.common import constants
from octavia.common import exceptions

LOG = logging.getLogger(__name__)


class AvailabilityZoneProfileController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AVAILABILITY_ZONE_PROFILE

    def __init__(self):
        super().__init__()

    @wsme_pecan.wsexpose(profile_types.AvailabilityZoneProfileRootResponse,
                         wtypes.text, [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets an Availability Zone Profile's detail."""
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ONE)
        if id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone Profile',
                                      id=constants.NIL_UUID)
        with context.session.begin():
            db_availability_zone_profile = (
                self._get_db_availability_zone_profile(context.session, id))
        result = self._convert_db_to_type(
            db_availability_zone_profile,
            profile_types.AvailabilityZoneProfileResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return profile_types.AvailabilityZoneProfileRootResponse(
            availability_zone_profile=result)

    @wsme_pecan.wsexpose(profile_types.AvailabilityZoneProfilesRootResponse,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all Availability Zone Profiles."""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)
        with context.session.begin():
            db_availability_zone_profiles, links = (
                self.repositories.availability_zone_profile.get_all(
                    context.session,
                    pagination_helper=pcontext.get(
                        constants.PAGINATION_HELPER)))
        result = self._convert_db_to_type(
            db_availability_zone_profiles,
            [profile_types.AvailabilityZoneProfileResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return profile_types.AvailabilityZoneProfilesRootResponse(
            availability_zone_profiles=result,
            availability_zone_profile_links=links)

    @wsme_pecan.wsexpose(profile_types.AvailabilityZoneProfileRootResponse,
                         body=profile_types.AvailabilityZoneProfileRootPOST,
                         status_code=201)
    def post(self, availability_zone_profile_):
        """Creates an Availability Zone Profile."""
        availability_zone_profile = (
            availability_zone_profile_.availability_zone_profile)
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_POST)
        # Do a basic JSON validation on the metadata
        try:
            availability_zone_data_dict = jsonutils.loads(
                availability_zone_profile.availability_zone_data)
        except Exception as e:
            raise exceptions.InvalidOption(
                value=availability_zone_profile.availability_zone_data,
                option=constants.AVAILABILITY_ZONE_DATA) from e

        # Validate that the provider driver supports the metadata
        driver = driver_factory.get_driver(
            availability_zone_profile.provider_name)
        driver_utils.call_provider(
            driver.name, driver.validate_availability_zone,
            availability_zone_data_dict)

        context.session.begin()
        try:
            availability_zone_profile_dict = availability_zone_profile.to_dict(
                render_unsets=True)
            availability_zone_profile_dict['id'] = uuidutils.generate_uuid()
            db_availability_zone_profile = (
                self.repositories.availability_zone_profile.create(
                    context.session, **availability_zone_profile_dict))
            context.session.commit()
        except odb_exceptions.DBDuplicateEntry as e:
            context.session.rollback()
            raise exceptions.IDAlreadyExists() from e
        except Exception:
            with excutils.save_and_reraise_exception():
                context.session.rollback()
        result = self._convert_db_to_type(
            db_availability_zone_profile,
            profile_types.AvailabilityZoneProfileResponse)
        return profile_types.AvailabilityZoneProfileRootResponse(
            availability_zone_profile=result)

    def _validate_update_azp(self, context, id, availability_zone_profile):
        if availability_zone_profile.name is None:
            raise exceptions.InvalidOption(value=None, option=constants.NAME)
        if availability_zone_profile.provider_name is None:
            raise exceptions.InvalidOption(
                value=None, option=constants.PROVIDER_NAME)
        if availability_zone_profile.availability_zone_data is None:
            raise exceptions.InvalidOption(
                value=None, option=constants.AVAILABILITY_ZONE_DATA)

        # Don't allow changes to the availability_zone_data or provider_name if
        # it is in use.
        if (not isinstance(availability_zone_profile.availability_zone_data,
                           wtypes.UnsetType) or
                not isinstance(availability_zone_profile.provider_name,
                               wtypes.UnsetType)):
            if self.repositories.availability_zone.count(
                    context.session, availability_zone_profile_id=id) > 0:
                raise exceptions.ObjectInUse(
                    object='Availability Zone Profile', id=id)

    @wsme_pecan.wsexpose(profile_types.AvailabilityZoneProfileRootResponse,
                         wtypes.text, status_code=200,
                         body=profile_types.AvailabilityZoneProfileRootPUT)
    def put(self, id, availability_zone_profile_):
        """Updates an Availability Zone Profile."""
        availability_zone_profile = (
            availability_zone_profile_.availability_zone_profile)
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_PUT)

        with context.session.begin():
            self._validate_update_azp(context, id, availability_zone_profile)
        if id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone Profile',
                                      id=constants.NIL_UUID)

        if not isinstance(availability_zone_profile.availability_zone_data,
                          wtypes.UnsetType):
            # Do a basic JSON validation on the metadata
            try:
                availability_zone_data_dict = jsonutils.loads(
                    availability_zone_profile.availability_zone_data)
            except Exception as e:
                raise exceptions.InvalidOption(
                    value=availability_zone_profile.availability_zone_data,
                    option=constants.FLAVOR_DATA) from e

            if isinstance(availability_zone_profile.provider_name,
                          wtypes.UnsetType):
                with context.session.begin():
                    db_availability_zone_profile = (
                        self._get_db_availability_zone_profile(
                            context.session, id))
                provider_driver = db_availability_zone_profile.provider_name
            else:
                provider_driver = availability_zone_profile.provider_name

            # Validate that the provider driver supports the metadata
            driver = driver_factory.get_driver(provider_driver)
            driver_utils.call_provider(
                driver.name, driver.validate_availability_zone,
                availability_zone_data_dict)

        context.session.begin()
        try:
            availability_zone_profile_dict = availability_zone_profile.to_dict(
                render_unsets=False)
            if availability_zone_profile_dict:
                self.repositories.availability_zone_profile.update(
                    context.session, id, **availability_zone_profile_dict)
            context.session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                context.session.rollback()

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        with context.session.begin():
            db_availability_zone_profile = (
                self._get_db_availability_zone_profile(context.session,
                                                       id))
        result = self._convert_db_to_type(
            db_availability_zone_profile,
            profile_types.AvailabilityZoneProfileResponse)
        return profile_types.AvailabilityZoneProfileRootResponse(
            availability_zone_profile=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, availability_zone_profile_id):
        """Deletes an Availability Zone Profile"""
        context = pecan_request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_DELETE)
        if availability_zone_profile_id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone Profile',
                                      id=constants.NIL_UUID)
        # Don't allow it to be deleted if it is in use by an availability zone
        with context.session.begin():
            if self.repositories.availability_zone.count(
                    context.session,
                    availability_zone_profile_id=availability_zone_profile_id
            ) > 0:
                raise exceptions.ObjectInUse(
                    object='Availability Zone Profile',
                    id=availability_zone_profile_id)
            try:
                self.repositories.availability_zone_profile.delete(
                    context.session, id=availability_zone_profile_id)
            except sa_exception.NoResultFound as e:
                raise exceptions.NotFound(
                    resource='Availability Zone Profile',
                    id=availability_zone_profile_id) from e
