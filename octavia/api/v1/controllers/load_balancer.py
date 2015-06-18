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

from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.controllers import listener
from octavia.api.v1.types import load_balancer as lb_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class LoadBalancersController(base.BaseController):

    def __init__(self):
        super(LoadBalancersController, self).__init__()
        self.handler = self.handler.load_balancer

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse, wtypes.text)
    def get_one(self, id):
        """Gets a single load balancer's details."""
        session = db_api.get_session()
        load_balancer = self.repositories.load_balancer.get(
            session, id=id)
        if not load_balancer:
            LOG.info(_LI("Load Balancer %s was not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(), id=id)
        return self._convert_db_to_type(load_balancer,
                                        lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose([lb_types.LoadBalancerResponse], wtypes.text)
    def get_all(self, tenant_id=None):
        """Lists all listeners on a load balancer."""
        # tenant_id is an optional query parameter
        session = db_api.get_session()
        load_balancers = self.repositories.load_balancer.get_all(
            session, tenant_id=tenant_id)
        return self._convert_db_to_type(load_balancers,
                                        [lb_types.LoadBalancerResponse])

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse,
                         body=lb_types.LoadBalancerPOST, status_code=202)
    def post(self, load_balancer):
        """Creates a load balancer."""
        session = db_api.get_session()
        lb_dict = load_balancer.to_dict()
        vip_dict = lb_dict.pop('vip')
        lb_dict['provisioning_status'] = constants.PENDING_CREATE
        lb_dict['operating_status'] = constants.OFFLINE
        try:
            db_lb = self.repositories.create_load_balancer_and_vip(
                session, lb_dict, vip_dict)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.IDAlreadyExists()
        # Handler will be responsible for sending to controller
        try:
            LOG.info(_LI("Sending created Load Balancer %s to the handler") %
                     db_lb.id)
            self.handler.create(db_lb)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    session, db_lb.id, provisioning_status=constants.ERROR)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse,
                         wtypes.text, status_code=202,
                         body=lb_types.LoadBalancerPUT)
    def put(self, id, load_balancer):
        """Updates a load balancer."""
        session = db_api.get_session()
        # Purely to make lines smaller length
        lb_repo = self.repositories.load_balancer
        db_lb = self.repositories.load_balancer.get(session, id=id)
        if not db_lb:
            LOG.info(_LI("Load Balancer %s was not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(), id=id)
        # Check load balancer is in a mutable status
        if not lb_repo.test_and_set_provisioning_status(
                session, id, constants.PENDING_UPDATE):
            LOG.info(_LI("Load Balancer %s is immutable.") % id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=id)
        try:
            LOG.info(_LI("Sending updated Load Balancer %s to the handler") %
                     id)
            self.handler.update(db_lb, load_balancer)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    session, id, provisioning_status=constants.ERROR)
        lb = self.repositories.load_balancer.get(session, id=id)
        return self._convert_db_to_type(lb, lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a load balancer."""
        session = db_api.get_session()
        # Purely to make lines smaller length
        lb_repo = self.repositories.load_balancer
        db_lb = self.repositories.load_balancer.get(session, id=id)
        if not db_lb:
            LOG.info(_LI("Load Balancer %s was not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(), id=id)
        # Check load balancer is in a mutable status
        if not lb_repo.test_and_set_provisioning_status(
                session, id, constants.PENDING_DELETE):
            LOG.info(_LI("Load Balancer %s is immutable.") % id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=id)
        db_lb = self.repositories.load_balancer.get(session, id=id)
        try:
            LOG.info(_LI("Sending deleted Load Balancer %s to the handler") %
                     db_lb.id)
            self.handler.delete(db_lb)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    session, db_lb.id, provisioning_status=constants.ERROR)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)

    @pecan.expose()
    def _lookup(self, lb_id, *remainder):
        """Overriden pecan _lookup method for custom routing.

        Verifies that the load balancer passed in the url exists, and if so
        decides which controller, if any, should control be passed.
        """
        session = db_api.get_session()
        if lb_id and len(remainder) and remainder[0] == 'listeners':
            remainder = remainder[1:]
            db_lb = self.repositories.load_balancer.get(session, id=lb_id)
            if not db_lb:
                LOG.info(_LI("Load Balancer %s was not found.") % lb_id)
                raise exceptions.NotFound(
                    resource=data_models.LoadBalancer._name(), id=lb_id)
            return listener.ListenersController(
                load_balancer_id=db_lb.id), remainder
