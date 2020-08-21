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

from oslo_db import api as oslo_db_api
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import availability_zones as availability_zone_types
from octavia.common import constants
from octavia.common import exceptions
from octavia.db import api as db_api

LOG = logging.getLogger(__name__)


class AvailabilityZonesController(base.BaseController):
    RBAC_TYPE = constants.RBAC_AVAILABILITY_ZONE

    def __init__(self):
        super().__init__()

    @wsme_pecan.wsexpose(availability_zone_types.AvailabilityZoneRootResponse,
                         wtypes.text, [wtypes.text], ignore_extra_args=True)
    def get_one(self, name, fields=None):
        """Gets an Availability Zone's detail."""
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ONE)
        if name == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone',
                                      id=constants.NIL_UUID)
        db_availability_zone = self._get_db_availability_zone(
            context.session, name)
        result = self._convert_db_to_type(
            db_availability_zone,
            availability_zone_types.AvailabilityZoneResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return availability_zone_types.AvailabilityZoneRootResponse(
            availability_zone=result)

    @wsme_pecan.wsexpose(availability_zone_types.AvailabilityZonesRootResponse,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all Availability Zones."""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)
        db_availability_zones, links = (
            self.repositories.availability_zone.get_all(
                context.session,
                pagination_helper=pcontext.get(constants.PAGINATION_HELPER)))
        result = self._convert_db_to_type(
            db_availability_zones,
            [availability_zone_types.AvailabilityZoneResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return availability_zone_types.AvailabilityZonesRootResponse(
            availability_zones=result, availability_zones_links=links)

    @wsme_pecan.wsexpose(availability_zone_types.AvailabilityZoneRootResponse,
                         body=availability_zone_types.AvailabilityZoneRootPOST,
                         status_code=201)
    def post(self, availability_zone_):
        """Creates an Availability Zone."""
        availability_zone = availability_zone_.availability_zone
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_POST)

        lock_session = db_api.get_session(autocommit=False)
        try:
            availability_zone_dict = availability_zone.to_dict(
                render_unsets=True)
            db_availability_zone = self.repositories.availability_zone.create(
                lock_session, **availability_zone_dict)
            lock_session.commit()
        except odb_exceptions.DBDuplicateEntry as e:
            lock_session.rollback()
            raise exceptions.RecordAlreadyExists(
                field='availability zone', name=availability_zone.name) from e
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()
        result = self._convert_db_to_type(
            db_availability_zone,
            availability_zone_types.AvailabilityZoneResponse)
        return availability_zone_types.AvailabilityZoneRootResponse(
            availability_zone=result)

    @wsme_pecan.wsexpose(availability_zone_types.AvailabilityZoneRootResponse,
                         wtypes.text, status_code=200,
                         body=availability_zone_types.AvailabilityZoneRootPUT)
    def put(self, name, availability_zone_):
        availability_zone = availability_zone_.availability_zone
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_PUT)
        if name == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone',
                                      id=constants.NIL_UUID)
        lock_session = db_api.get_session(autocommit=False)
        try:
            availability_zone_dict = availability_zone.to_dict(
                render_unsets=False)
            if availability_zone_dict:
                self.repositories.availability_zone.update(
                    lock_session, name, **availability_zone_dict)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_availability_zone = self._get_db_availability_zone(
            context.session, name)
        result = self._convert_db_to_type(
            db_availability_zone,
            availability_zone_types.AvailabilityZoneResponse)
        return availability_zone_types.AvailabilityZoneRootResponse(
            availability_zone=result)

    @oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, availability_zone_name):
        """Deletes an Availability Zone"""
        context = pecan_request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_DELETE)
        if availability_zone_name == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Availability Zone',
                                      id=constants.NIL_UUID)
        serial_session = db_api.get_session(autocommit=False)
        serial_session.connection(
            execution_options={'isolation_level': 'SERIALIZABLE'})
        try:
            self.repositories.availability_zone.delete(
                serial_session, name=availability_zone_name)
            serial_session.commit()
        # Handle when load balancers still reference this availability_zone
        except odb_exceptions.DBReferenceError as e:
            serial_session.rollback()
            raise exceptions.ObjectInUse(object='Availability Zone',
                                         id=availability_zone_name) from e
        except sa_exception.NoResultFound as e:
            serial_session.rollback()
            raise exceptions.NotFound(resource='Availability Zone',
                                      id=availability_zone_name) from e
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error(
                    'Unknown availability_zone delete exception: %s', str(e))
                serial_session.rollback()
        finally:
            serial_session.close()
