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

from octavia.api.v1.controllers import base
from octavia.api.v1.controllers import listener
from octavia.api.v1.controllers import pool
from octavia.api.v1.types import load_balancer as lb_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
import octavia.common.validate as validate
from octavia.db import prepare as db_prepare
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class LoadBalancersController(base.BaseController):

    def __init__(self):
        super(LoadBalancersController, self).__init__()
        self.handler = self.handler.load_balancer

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse, wtypes.text)
    def get_one(self, id):
        """Gets a single load balancer's details."""
        context = pecan.request.context.get('octavia_context')
        load_balancer = self._get_db_lb(context.session, id)
        return self._convert_db_to_type(load_balancer,
                                        lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose([lb_types.LoadBalancerResponse], wtypes.text,
                         wtypes.text)
    def get_all(self, tenant_id=None, project_id=None):
        """Lists all load balancers."""
        # NOTE(blogan): tenant_id and project_id are optional query parameters
        # tenant_id and project_id are the same thing.  tenant_id will be kept
        # around for a short amount of time.
        context = pecan.request.context.get('octavia_context')
        project_id = context.project_id or project_id or tenant_id
        load_balancers = self.repositories.load_balancer.get_all(
            context.session, project_id=project_id)
        return self._convert_db_to_type(load_balancers,
                                        [lb_types.LoadBalancerResponse])

    def _test_lb_status(self, session, id, lb_status=constants.PENDING_UPDATE):
        """Verify load balancer is in a mutable state."""
        lb_repo = self.repositories.load_balancer
        if not lb_repo.test_and_set_provisioning_status(
                session, id, lb_status):
            LOG.info(_LI("Load Balancer %s is immutable."), id)
            db_lb = lb_repo.get(session, id=id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=id)

    def _create_load_balancer_graph(self, context, load_balancer):
        prepped_lb = db_prepare.create_load_balancer_tree(
            load_balancer.to_dict(render_unsets=True))
        try:
            db_lb = self.repositories.create_load_balancer_tree(
                context.session, prepped_lb)
        except Exception:
            raise
        try:
            LOG.info(_LI("Sending full load balancer configuration %s to "
                         "the handler"), db_lb.id)
            self.handler.create(db_lb)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    context.session, db_lb.id,
                    provisioning_status=constants.ERROR)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse,
                                        children=True)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse,
                         body=lb_types.LoadBalancerPOST, status_code=202)
    def post(self, load_balancer):
        """Creates a load balancer."""
        # Validate the subnet id
        if load_balancer.vip.subnet_id:
            if not validate.subnet_exists(load_balancer.vip.subnet_id):
                raise exceptions.NotFound(resource='Subnet',
                                          id=load_balancer.vip.subnet_id)

        context = pecan.request.context.get('octavia_context')
        if load_balancer.listeners:
            return self._create_load_balancer_graph(context, load_balancer)
        lb_dict = db_prepare.create_load_balancer(load_balancer.to_dict(
            render_unsets=True
        ))
        vip_dict = lb_dict.pop('vip', {})
        try:
            db_lb = self.repositories.create_load_balancer_and_vip(
                context.session, lb_dict, vip_dict)
        except odb_exceptions.DBDuplicateEntry:
            raise exceptions.IDAlreadyExists()
        # Handler will be responsible for sending to controller
        try:
            LOG.info(_LI("Sending created Load Balancer %s to the handler"),
                     db_lb.id)
            self.handler.create(db_lb)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    context.session, db_lb.id,
                    provisioning_status=constants.ERROR)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerResponse,
                         wtypes.text, status_code=202,
                         body=lb_types.LoadBalancerPUT)
    def put(self, id, load_balancer):
        """Updates a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_lb = self._get_db_lb(context.session, id)
        self._test_lb_status(context.session, id)

        try:
            LOG.info(_LI("Sending updated Load Balancer %s to the handler"),
                     id)
            self.handler.update(db_lb, load_balancer)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    context.session, id, provisioning_status=constants.ERROR)
        db_lb = self._get_db_lb(context.session, id)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)

    def _delete(self, id, cascade=False):
        """Deletes a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_lb = self._get_db_lb(context.session, id)
        self._test_lb_status(context.session, id,
                             lb_status=constants.PENDING_DELETE)

        try:
            LOG.info(_LI("Sending deleted Load Balancer %s to the handler"),
                     db_lb.id)
            self.handler.delete(db_lb, cascade)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.load_balancer.update(
                    context.session, db_lb.id,
                    provisioning_status=constants.ERROR)
        return self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a load balancer."""
        return self._delete(id, cascade=False)

    @pecan.expose()
    def _lookup(self, lb_id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Verifies that the load balancer passed in the url exists, and if so
        decides which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if lb_id and len(remainder) and (remainder[0] == 'listeners' or
                                         remainder[0] == 'pools' or
                                         remainder[0] == 'delete_cascade'):
            controller = remainder[0]
            remainder = remainder[1:]
            db_lb = self.repositories.load_balancer.get(context.session,
                                                        id=lb_id)
            if not db_lb:
                LOG.info(_LI("Load Balancer %s was not found."), lb_id)
                raise exceptions.NotFound(
                    resource=data_models.LoadBalancer._name(), id=lb_id)
            if controller == 'listeners':
                return listener.ListenersController(
                    load_balancer_id=db_lb.id), remainder
            elif controller == 'pools':
                return pool.PoolsController(
                    load_balancer_id=db_lb.id), remainder
            elif (controller == 'delete_cascade'):
                return LBCascadeDeleteController(db_lb.id), ''


class LBCascadeDeleteController(LoadBalancersController):
        def __init__(self, lb_id):
            super(LBCascadeDeleteController, self).__init__()
            self.lb_id = lb_id

        @wsme_pecan.wsexpose(None, status_code=202)
        def delete(self):
            """Deletes a load balancer."""
            return self._delete(self.lb_id, cascade=True)
