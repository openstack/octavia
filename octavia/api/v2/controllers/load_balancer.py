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
from octavia.common import utils
import octavia.common.validate as validate
from octavia.db import api as db_api
from octavia.db import prepare as db_prepare
from octavia.i18n import _, _LI


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
        if context.is_admin or CONF.auth_strategy == constants.NOAUTH:
            if project_id or tenant_id:
                project_id = {'project_id': project_id or tenant_id}
            else:
                project_id = {}
        else:
            project_id = {'project_id': context.project_id}
        load_balancers = self.repositories.load_balancer.get_all(
            context.session, **project_id)
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

    @staticmethod
    def _validate_network_and_fill_or_validate_subnet(load_balancer):
        network = validate.network_exists_optionally_contains_subnet(
            network_id=load_balancer.vip_network_id,
            subnet_id=load_balancer.vip_subnet_id)
        # If subnet is not provided, pick the first subnet, preferring ipv4
        if not load_balancer.vip_subnet_id:
            network_driver = utils.get_network_driver()
            for subnet_id in network.subnets:
                # Use the first subnet, in case there are no ipv4 subnets
                if not load_balancer.vip_subnet_id:
                    load_balancer.vip_subnet_id = subnet_id
                subnet = network_driver.get_subnet(subnet_id)
                if subnet.ip_version == 4:
                    load_balancer.vip_subnet_id = subnet_id
                    break
            if not load_balancer.vip_subnet_id:
                raise exceptions.ValidationException(detail=_(
                    "Supplied network does not contain a subnet."
                ))

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse,
                         body=lb_types.LoadBalancerRootPOST, status_code=201)
    def post(self, load_balancer):
        """Creates a load balancer."""
        load_balancer = load_balancer.loadbalancer
        context = pecan.request.context.get('octavia_context')

        project_id = context.project_id
        if context.is_admin or CONF.auth_strategy == constants.NOAUTH:
            if load_balancer.project_id:
                project_id = load_balancer.project_id
            elif load_balancer.tenant_id:
                project_id = load_balancer.tenant_id

        if not project_id:
            raise exceptions.ValidationException(detail=_(
                "Missing project ID in request where one is required."))

        load_balancer.project_id = project_id

        if not (load_balancer.vip_port_id or
                load_balancer.vip_network_id or
                load_balancer.vip_subnet_id):
            raise exceptions.ValidationException(detail=_(
                "VIP must contain one of: port_id, network_id, subnet_id."))

        # Validate the port id
        if load_balancer.vip_port_id:
            port = validate.port_exists(port_id=load_balancer.vip_port_id)
            load_balancer.vip_network_id = port.network_id
        # If no port id, validate the network id (and subnet if provided)
        elif load_balancer.vip_network_id:
            self._validate_network_and_fill_or_validate_subnet(load_balancer)
        # Validate just the subnet id
        elif load_balancer.vip_subnet_id:
            subnet = validate.subnet_exists(
                subnet_id=load_balancer.vip_subnet_id)
            load_balancer.vip_network_id = subnet.network_id

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
