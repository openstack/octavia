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

from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v2.controllers import base
from octavia.api.v2.types import load_balancer as lb_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
import octavia.common.validate as validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare
from octavia.i18n import _LI


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class LoadBalancersController(base.BaseController):

    def __init__(self):
        super(LoadBalancersController, self).__init__()
        self.handler = self.handler.load_balancer

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse, wtypes.text)
    def get_one(self, id):
        """Gets a single load balancer's details."""
        context = pecan.request.context.get('octavia_context')
        load_balancer = self._get_db_lb(context.session, id)
        result = self._convert_db_to_type(load_balancer,
                                          lb_types.LoadBalancerResponse)
        return lb_types.LoadBalancerRootResponse(loadbalancer=result)

    @wsme_pecan.wsexpose(lb_types.LoadBalancersRootResponse, wtypes.text,
                         wtypes.text)
    def get_all(self, tenant_id=None, project_id=None):
        """Lists all load balancers."""
        # NOTE(blogan): tenant_id and project_id are optional query parameters
        # tenant_id and project_id are the same thing.  tenant_id will be kept
        # around for a long amount of time.
        context = pecan.request.context.get('octavia_context')
        project_id = context.project_id or project_id or tenant_id
        load_balancers = self.repositories.load_balancer.get_all(
            context.session, project_id=project_id)
        result = self._convert_db_to_type(load_balancers,
                                          [lb_types.LoadBalancerResponse])
        return lb_types.LoadBalancersRootResponse(loadbalancers=result)

    def _test_lb_status(self, session, id, lb_status=constants.PENDING_UPDATE):
        """Verify load balancer is in a mutable state."""
        lb_repo = self.repositories.load_balancer
        if not lb_repo.test_and_set_provisioning_status(
                session, id, lb_status):
            prov_status = lb_repo.get(session, id=id).provisioning_status
            LOG.info(_LI(
                "Invalid state %(state)s of loadbalancer resource %(id)s"),
                {"state": prov_status, "id": id})
            raise exceptions.LBPendingStateError(
                state=prov_status, id=id)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse,
                         body=lb_types.LoadBalancerRootPOST, status_code=202)
    def post(self, load_balancer):
        """Creates a load balancer."""
        load_balancer = load_balancer.loadbalancer
        context = pecan.request.context.get('octavia_context')

        project_id = context.project_id
        if context.is_admin or CONF.auth_strategy == constants.NOAUTH:
            if load_balancer.project_id:
                project_id = load_balancer.project_id

        if not project_id:
            raise exceptions.MissingAPIProjectID()

        load_balancer.project_id = project_id

        # Validate the subnet id
        if load_balancer.vip_subnet_id:
            if not validate.subnet_exists(load_balancer.vip_subnet_id):
                raise exceptions.NotFound(resource='Subnet',
                                          id=load_balancer.vip_subnet_id)

        lock_session = db_api.get_session(autocommit=False)
        if self.repositories.check_quota_met(
                context.session,
                lock_session,
                data_models.LoadBalancer,
                load_balancer.project_id):
            lock_session.rollback()
            raise exceptions.QuotaException

        # TODO(blogan): lb graph, look at v1 code

        try:
            lb_dict = db_prepare.create_load_balancer(load_balancer.to_dict(
                render_unsets=True
            ))
            vip_dict = lb_dict.pop('vip', {})
            db_lb = self.repositories.create_load_balancer_and_vip(
                lock_session, lb_dict, vip_dict)
            lock_session.commit()
        except odb_exceptions.DBDuplicateEntry:
            lock_session.rollback()
            raise exceptions.IDAlreadyExists()
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

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
        result = self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)
        return lb_types.LoadBalancerRootResponse(loadbalancer=result)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse,
                         wtypes.text, status_code=200,
                         body=lb_types.LoadBalancerRootPUT)
    def put(self, id, load_balancer):
        """Updates a load balancer."""
        load_balancer = load_balancer.loadbalancer
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
        result = self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)
        return lb_types.LoadBalancerRootResponse(loadbalancer=result)

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
        result = self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)
        return lb_types.LoadBalancersRootResponse(loadbalancer=result)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, id):
        """Deletes a load balancer."""
        return self._delete(id)
