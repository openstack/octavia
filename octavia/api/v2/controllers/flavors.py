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

from oslo_db import api as oslo_db_api
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import uuidutils
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import flavors as flavor_types
from octavia.common import constants
from octavia.common import exceptions
from octavia.db import api as db_api

LOG = logging.getLogger(__name__)


class FlavorsController(base.BaseController):
    RBAC_TYPE = constants.RBAC_FLAVOR

    def __init__(self):
        super(FlavorsController, self).__init__()

    @wsme_pecan.wsexpose(flavor_types.FlavorRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a flavor's detail."""
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ONE)
        if id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Flavor', id=constants.NIL_UUID)
        db_flavor = self._get_db_flavor(context.session, id)
        result = self._convert_db_to_type(db_flavor,
                                          flavor_types.FlavorResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return flavor_types.FlavorRootResponse(flavor=result)

    @wsme_pecan.wsexpose(flavor_types.FlavorsRootResponse,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, fields=None):
        """Lists all flavors."""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_GET_ALL)
        db_flavors, links = self.repositories.flavor.get_all(
            context.session,
            pagination_helper=pcontext.get(constants.PAGINATION_HELPER))
        result = self._convert_db_to_type(
            db_flavors, [flavor_types.FlavorResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return flavor_types.FlavorsRootResponse(
            flavors=result, flavors_links=links)

    @wsme_pecan.wsexpose(flavor_types.FlavorRootResponse,
                         body=flavor_types.FlavorRootPOST, status_code=201)
    def post(self, flavor_):
        """Creates a flavor."""
        flavor = flavor_.flavor
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_POST)

        # TODO(johnsom) Validate the flavor profile ID

        lock_session = db_api.get_session(autocommit=False)
        try:
            flavor_dict = flavor.to_dict(render_unsets=True)
            flavor_dict['id'] = uuidutils.generate_uuid()
            db_flavor = self.repositories.flavor.create(lock_session,
                                                        **flavor_dict)
            lock_session.commit()
        except odb_exceptions.DBDuplicateEntry:
            lock_session.rollback()
            raise exceptions.RecordAlreadyExists(field='flavor',
                                                 name=flavor.name)
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()
        result = self._convert_db_to_type(db_flavor,
                                          flavor_types.FlavorResponse)
        return flavor_types.FlavorRootResponse(flavor=result)

    @wsme_pecan.wsexpose(flavor_types.FlavorRootResponse,
                         wtypes.text, status_code=200,
                         body=flavor_types.FlavorRootPUT)
    def put(self, id, flavor_):
        flavor = flavor_.flavor
        context = pecan_request.context.get('octavia_context')
        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_PUT)
        if id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Flavor', id=constants.NIL_UUID)
        lock_session = db_api.get_session(autocommit=False)
        try:
            flavor_dict = flavor.to_dict(render_unsets=False)
            if flavor_dict:
                self.repositories.flavor.update(lock_session, id,
                                                **flavor_dict)
            lock_session.commit()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        db_flavor = self._get_db_flavor(context.session, id)
        result = self._convert_db_to_type(db_flavor,
                                          flavor_types.FlavorResponse)
        return flavor_types.FlavorRootResponse(flavor=result)

    @oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, flavor_id):
        """Deletes a Flavor"""
        context = pecan_request.context.get('octavia_context')

        self._auth_validate_action(context, context.project_id,
                                   constants.RBAC_DELETE)
        if flavor_id == constants.NIL_UUID:
            raise exceptions.NotFound(resource='Flavor', id=constants.NIL_UUID)
        serial_session = db_api.get_session(autocommit=False)
        serial_session.connection(
            execution_options={'isolation_level': 'SERIALIZABLE'})
        try:
            self.repositories.flavor.delete(serial_session, id=flavor_id)
            serial_session.commit()
        # Handle when load balancers still reference this flavor
        except odb_exceptions.DBReferenceError:
            serial_session.rollback()
            raise exceptions.ObjectInUse(object='Flavor', id=flavor_id)
        except sa_exception.NoResultFound:
            serial_session.rollback()
            raise exceptions.NotFound(resource='Flavor', id=flavor_id)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error('Unknown flavor delete exception: %s', str(e))
                serial_session.rollback()
        finally:
            serial_session.close()
