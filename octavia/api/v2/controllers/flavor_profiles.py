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
from oslo_serialization import jsonutils
from oslo_utils import excutils
from oslo_utils import uuidutils
import pecan
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.types import flavor_profile as profile_types
from octavia.common import constants
from octavia.common import exceptions
from octavia.db import api as db_api

LOG = logging.getLogger(__name__)


class FlavorProfileController(base.BaseController):
    RBAC_TYPE = constants.RBAC_FLAVOR_PROFILE

    def __init__(self):
        super(FlavorProfileController, self).__init__()

    @wsme_pecan.wsexpose(profile_types.FlavorProfileRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a flavor profile's detail."""
        context = pecan.request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ONE)
        db_flavor_profile = self._get_db_flavor_profile(context.session, id)
        result = self._convert_db_to_type(db_flavor_profile,
                                          profile_types.FlavorProfileResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return profile_types.FlavorProfileRootResponse(flavorprofile=result)

    @wsme_pecan.wsexpose(profile_types.FlavorProfilesRootResponse,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all flavor profiles."""
        pcontext = pecan.request.context
        context = pcontext.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)
        db_flavor_profiles, links = self.repositories.flavor_profile.get_all(
            context.session,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_flavor_profiles, [profile_types.FlavorProfileResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return profile_types.FlavorProfilesRootResponse(
            flavorprofiles=result, flavorprofile_links=links)

    @wsme_pecan.wsexpose(profile_types.FlavorProfileRootResponse,
                         body=profile_types.FlavorProfileRootPOST,
                         status_code=201)
    def post(self, flavor_profile_):
        """Creates a flavor Profile."""
        flavorprofile = flavor_profile_.flavorprofile
        context = pecan.request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_POST)
        # Do a basic JSON validation on the metadata
        try:
            flavor_data_dict = jsonutils.loads(flavorprofile.flavor_data)
        except Exception:
            raise exceptions.InvalidOption(
                value=flavorprofile.flavor_data,
                option=constants.FLAVOR_DATA)

        # Validate that the provider driver supports the metadata
        driver = driver_factory.get_driver(flavorprofile.provider_name)
        driver_utils.call_provider(driver.name, driver.validate_flavor,
                                   flavor_data_dict)

        lock_session = db_api.get_session(autocommit=False)
        try:
            flavorprofile_dict = flavorprofile.to_dict(render_unsets=True)
            flavorprofile_dict['id'] = uuidutils.generate_uuid()
            db_flavor_profile = self.repositories.flavor_profile.create(
                lock_session, **flavorprofile_dict)
            lock_session.commit()
        except odb_exceptions.DBDuplicateEntry:
            lock_session.rollback()
            raise exceptions.IDAlreadyExists()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()
        result = self._convert_db_to_type(
            db_flavor_profile, profile_types.FlavorProfileResponse)
        return profile_types.FlavorProfileRootResponse(flavorprofile=result)

    def _validate_update_fp(self, context, id, flavorprofile):
        if flavorprofile.name is None:
            raise exceptions.InvalidOption(value=None, option=constants.NAME)
        if flavorprofile.provider_name is None:
            raise exceptions.InvalidOption(value=None,
                                           option=constants.PROVIDER_NAME)
        if flavorprofile.flavor_data is None:
            raise exceptions.InvalidOption(value=None,
                                           option=constants.FLAVOR_DATA)

        # Don't allow changes to the flavor_data or provider_name if it
        # is in use.
        if (not isinstance(flavorprofile.flavor_data, wtypes.UnsetType) or
                not isinstance(flavorprofile.provider_name, wtypes.UnsetType)):
            if self.repositories.flavor.count(context.session,
                                              flavor_profile_id=id) > 0:
                raise exceptions.ObjectInUse(object='Flavor profile', id=id)

    @wsme_pecan.wsexpose(profile_types.FlavorProfileRootResponse,
                         wtypes.text, status_code=200,
                         body=profile_types.FlavorProfileRootPUT)
    def put(self, id, flavor_profile_):
        """Updates a flavor Profile."""
        flavorprofile = flavor_profile_.flavorprofile
        context = pecan.request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_PUT)

        self._validate_update_fp(context, id, flavorprofile)

        if not isinstance(flavorprofile.flavor_data, wtypes.UnsetType):
            # Do a basic JSON validation on the metadata
            try:
                flavor_data_dict = jsonutils.loads(flavorprofile.flavor_data)
            except Exception:
                raise exceptions.InvalidOption(
                    value=flavorprofile.flavor_data,
                    option=constants.FLAVOR_DATA)

            if isinstance(flavorprofile.provider_name, wtypes.UnsetType):
                db_flavor_profile = self._get_db_flavor_profile(
                    context.session, id)
                provider_driver = db_flavor_profile.provider_name
            else:
                provider_driver = flavorprofile.provider_name

            # Validate that the provider driver supports the metadata
            driver = driver_factory.get_driver(provider_driver)
            driver_utils.call_provider(driver.name, driver.validate_flavor,
                                       flavor_data_dict)

        lock_session = db_api.get_session(autocommit=False)
        try:
            flavorprofile_dict = flavorprofile.to_dict(render_unsets=False)
            if flavorprofile_dict:
                db_flavor_profile = self.repositories.flavor_profile.update(
                    lock_session, id, **flavorprofile_dict)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_flavor_profile = self._get_db_flavor_profile(context.session, id)
        result = self._convert_db_to_type(
            db_flavor_profile, profile_types.FlavorProfileResponse)
        return profile_types.FlavorProfileRootResponse(flavorprofile=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, flavor_profile_id):
        """Deletes a Flavor Profile"""
        context = pecan.request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_DELETE)

        # Don't allow it to be deleted if it is in use by a flavor
        if self.repositories.flavor.count(
                context.session, flavor_profile_id=flavor_profile_id) > 0:
            raise exceptions.ObjectInUse(object='Flavor profile',
                                         id=flavor_profile_id)

        try:
            self.repositories.flavor_profile.delete(context.session,
                                                    id=flavor_profile_id)
        except sa_exception.NoResultFound:
            raise exceptions.NotFound(resource='Flavor profile',
                                      id=flavor_profile_id)
