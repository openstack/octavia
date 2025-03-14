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
import ipaddress

from octavia_lib.api.drivers import data_models as driver_dm
from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
from pecan import expose as pecan_expose
from pecan import request as pecan_request
from sqlalchemy.orm import exc as sa_exception
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.drivers import driver_factory
from octavia.api.drivers import utils as driver_utils
from octavia.api.v2.controllers import base
from octavia.api.v2.controllers import listener
from octavia.api.v2.controllers import pool
from octavia.api.v2.types import load_balancer as lb_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.common import stats
from octavia.common import utils
from octavia.common import validate
from octavia.db import prepare as db_prepare
from octavia.i18n import _
from octavia.network import base as network_base


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class LoadBalancersController(base.BaseController):
    RBAC_TYPE = constants.RBAC_LOADBALANCER

    def __init__(self):
        super().__init__()

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_one(self, id, fields=None):
        """Gets a single load balancer's details."""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            load_balancer = self._get_db_lb(context.session, id,
                                            show_deleted=False)

        if not load_balancer:
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(),
                id=id)

        self._auth_validate_action(context, load_balancer.project_id,
                                   constants.RBAC_GET_ONE)

        result = self._convert_db_to_type(
            load_balancer, lb_types.LoadBalancerResponse)
        if fields is not None:
            result = self._filter_fields([result], fields)[0]
        return lb_types.LoadBalancerRootResponse(loadbalancer=result)

    @wsme_pecan.wsexpose(lb_types.LoadBalancersRootResponse, wtypes.text,
                         [wtypes.text], ignore_extra_args=True)
    def get_all(self, project_id=None, fields=None):
        """Lists all load balancers."""
        pcontext = pecan_request.context
        context = pcontext.get('octavia_context')

        query_filter = self._auth_get_all(context, project_id)

        with context.session.begin():
            load_balancers, links = (
                self.repositories.load_balancer.get_all_API_list(
                    context.session, show_deleted=False,
                    pagination_helper=pcontext.get(
                        constants.PAGINATION_HELPER),
                    **query_filter))
        result = self._convert_db_to_type(
            load_balancers, [lb_types.LoadBalancerResponse])
        if fields is not None:
            result = self._filter_fields(result, fields)
        return lb_types.LoadBalancersRootResponse(
            loadbalancers=result, loadbalancers_links=links)

    def _test_lb_status(self, session, id, lb_status=constants.PENDING_UPDATE):
        """Verify load balancer is in a mutable state."""
        lb_repo = self.repositories.load_balancer
        if not lb_repo.test_and_set_provisioning_status(
                session, id, lb_status):
            prov_status = lb_repo.get(session, id=id).provisioning_status
            LOG.info("Invalid state %(state)s of loadbalancer resource %(id)s",
                     {"state": prov_status, "id": id})
            raise exceptions.LBPendingStateError(
                state=prov_status, id=id)

    def _test_and_set_failover_prov_status(self, session, id):
        lb_repo = self.repositories.load_balancer
        if not lb_repo.set_status_for_failover(session, id,
                                               constants.PENDING_UPDATE):
            prov_status = lb_repo.get(session, id=id).provisioning_status
            LOG.info("Invalid state %(state)s of loadbalancer resource %(id)s",
                     {"state": prov_status, "id": id})
            raise exceptions.LBPendingStateError(
                state=prov_status, id=id)

    @staticmethod
    def _validate_network_and_fill_or_validate_subnet(load_balancer,
                                                      context=None):
        network = validate.network_exists_optionally_contains_subnet(
            network_id=load_balancer.vip_network_id,
            subnet_id=load_balancer.vip_subnet_id,
            context=context)
        if not load_balancer.vip_subnet_id:
            network_driver = utils.get_network_driver()
            if load_balancer.vip_address:
                for subnet_id in network.subnets:
                    subnet = network_driver.get_subnet(subnet_id)
                    if validate.is_ip_member_of_cidr(load_balancer.vip_address,
                                                     subnet.cidr):
                        load_balancer.vip_subnet_id = subnet_id
                        break
                if not load_balancer.vip_subnet_id:
                    raise exceptions.ValidationException(detail=_(
                        "Supplied network does not contain a subnet for "
                        "VIP address specified."
                    ))
            else:
                # If subnet and IP are not provided, pick the first subnet with
                # enough available IPs, preferring ipv4
                if not network.subnets:
                    raise exceptions.ValidationException(detail=_(
                        "Supplied network does not contain a subnet."
                    ))
                ip_avail = network_driver.get_network_ip_availability(
                    network)
                if (CONF.controller_worker.loadbalancer_topology ==
                        constants.TOPOLOGY_SINGLE):
                    num_req_ips = 2
                if (CONF.controller_worker.loadbalancer_topology ==
                        constants.TOPOLOGY_ACTIVE_STANDBY):
                    num_req_ips = 3
                subnets = [subnet_id for subnet_id in network.subnets if
                           utils.subnet_ip_availability(ip_avail, subnet_id,
                                                        num_req_ips)]
                if not subnets:
                    raise exceptions.ValidationException(detail=_(
                        "Subnet(s) in the supplied network do not contain "
                        "enough available IPs."
                    ))
                for subnet_id in subnets:
                    # Use the first subnet, in case there are no ipv4 subnets
                    if not load_balancer.vip_subnet_id:
                        load_balancer.vip_subnet_id = subnet_id
                    subnet = network_driver.get_subnet(subnet_id)
                    if subnet.ip_version == 4:
                        load_balancer.vip_subnet_id = subnet_id
                        break

    @staticmethod
    def _validate_port_and_fill_or_validate_subnet(load_balancer,
                                                   context=None):
        port = validate.port_exists(port_id=load_balancer.vip_port_id,
                                    context=context)
        validate.check_port_in_use(port)
        load_balancer.vip_network_id = port.network_id

        # validate the request vip port whether applied the qos_policy and
        # store the port_qos_policy to loadbalancer obj if possible. The
        # default behavior is that if 'vip_qos_policy_id' is specified in the
        # request, it will override the qos_policy applied on vip_port.
        port_qos_policy_id = port.qos_policy_id
        if (port_qos_policy_id and
                isinstance(load_balancer.vip_qos_policy_id, wtypes.UnsetType)):
            load_balancer.vip_qos_policy_id = port_qos_policy_id

        if load_balancer.vip_subnet_id:
            # If we were provided a subnet_id, validate it exists and that
            # there is a fixed_ip on the port that matches the provided subnet
            validate.subnet_exists(subnet_id=load_balancer.vip_subnet_id,
                                   context=context)
            for port_fixed_ip in port.fixed_ips:
                if port_fixed_ip.subnet_id == load_balancer.vip_subnet_id:
                    load_balancer.vip_address = port_fixed_ip.ip_address
                    break  # Just pick the first address found in the subnet
            if not load_balancer.vip_address:
                raise exceptions.ValidationException(detail=_(
                    "No VIP address found on the specified VIP port within "
                    "the specified subnet."))
        elif load_balancer.vip_address:
            normalized_lb_ip = ipaddress.ip_address(
                load_balancer.vip_address).compressed
            for port_fixed_ip in port.fixed_ips:
                normalized_port_ip = ipaddress.ip_address(
                    port_fixed_ip.ip_address).compressed
                if normalized_port_ip == normalized_lb_ip:
                    load_balancer.vip_subnet_id = port_fixed_ip.subnet_id
                    break
            if not load_balancer.vip_subnet_id:
                raise exceptions.ValidationException(detail=_(
                    "Specified VIP address not found on the "
                    "specified VIP port."))
        elif len(port.fixed_ips) == 1:
            # User provided only a port, get the subnet and address from it
            load_balancer.vip_subnet_id = port.fixed_ips[0].subnet_id
            load_balancer.vip_address = port.fixed_ips[0].ip_address
        else:
            raise exceptions.ValidationException(detail=_(
                "VIP port's subnet could not be determined. Please "
                "specify either a VIP subnet or address."))

    @staticmethod
    def _validate_subnets_share_network_but_no_duplicates(load_balancer):
        # Validate that no subnet_id is used more than once
        subnet_use_counts = {load_balancer.vip_subnet_id: 1}
        for vip in load_balancer.additional_vips:
            if vip.subnet_id in subnet_use_counts:
                raise exceptions.ValidationException(detail=_(
                    'Duplicate VIP subnet(s) specified. Only one IP can be '
                    'bound per subnet.'))
            subnet_use_counts[vip.subnet_id] = 1

        # Validate that all subnets belong to the same network
        network_driver = utils.get_network_driver()
        used_subnets = {}
        for subnet_id in subnet_use_counts:
            used_subnets[subnet_id] = network_driver.get_subnet(subnet_id)
        all_networks = [subnet.network_id for subnet in used_subnets.values()]
        if len(set(all_networks)) > 1:
            raise exceptions.ValidationException(detail=_(
                'All VIP subnets must belong to the same network.'
            ))
        # Fill the network_id for each additional_vip
        for vip in load_balancer.additional_vips:
            vip.network_id = used_subnets[vip.subnet_id].network_id

    def _validate_vip_request_object(self, load_balancer, context=None):
        allowed_network_objects = []
        if CONF.networking.allow_vip_port_id:
            allowed_network_objects.append('vip_port_id')
        if CONF.networking.allow_vip_network_id:
            allowed_network_objects.append('vip_network_id')
        if CONF.networking.allow_vip_subnet_id:
            allowed_network_objects.append('vip_subnet_id')

        msg = _("use of %(object)s is disallowed by this deployment's "
                "configuration.")
        if (load_balancer.vip_port_id and
                not CONF.networking.allow_vip_port_id):
            raise exceptions.ValidationException(
                detail=msg % {'object': 'vip_port_id'})
        if (load_balancer.vip_network_id and
                not CONF.networking.allow_vip_network_id):
            raise exceptions.ValidationException(
                detail=msg % {'object': 'vip_network_id'})
        if (load_balancer.vip_subnet_id and
                not CONF.networking.allow_vip_subnet_id):
            raise exceptions.ValidationException(
                detail=msg % {'object': 'vip_subnet_id'})

        if not (load_balancer.vip_port_id or
                load_balancer.vip_network_id or
                load_balancer.vip_subnet_id):
            raise exceptions.VIPValidationException(
                objects=', '.join(allowed_network_objects))

        # Validate the port id
        if load_balancer.vip_port_id:
            self._validate_port_and_fill_or_validate_subnet(load_balancer,
                                                            context=context)
        # If no port id, validate the network id (and subnet if provided)
        elif load_balancer.vip_network_id:
            self._validate_network_and_fill_or_validate_subnet(load_balancer,
                                                               context=context)
        # Validate just the subnet id
        elif load_balancer.vip_subnet_id:
            subnet = validate.subnet_exists(
                subnet_id=load_balancer.vip_subnet_id, context=context)
            load_balancer.vip_network_id = subnet.network_id
        if load_balancer.vip_qos_policy_id:
            validate.qos_policy_exists(
                qos_policy_id=load_balancer.vip_qos_policy_id)

        # Even though we've just validated the subnet or else retrieved its ID
        # directly from the port, we might still be missing the network.
        if not load_balancer.vip_network_id:
            subnet = validate.subnet_exists(
                subnet_id=load_balancer.vip_subnet_id)
            load_balancer.vip_network_id = subnet.network_id

        # Multi-vip validation for ensuring subnets are "sane"
        self._validate_subnets_share_network_but_no_duplicates(load_balancer)

        # Validate optional security groups
        if load_balancer.vip_sg_ids:
            for sg_id in load_balancer.vip_sg_ids:
                validate.security_group_exists(sg_id, context=context)

    def _validate_vnic_type(self, vnic_type: str,
                            load_balancer: lb_types.LoadBalancerPOST):
        if (vnic_type == constants.VNIC_TYPE_DIRECT and
                load_balancer.vip_sg_ids):
            msg = _("VIP Security Groups are not allowed with VNIC direct "
                    "type")
            raise exceptions.ValidationException(detail=msg)

    @staticmethod
    def _create_vip_port_if_not_exist(load_balancer_db):
        """Create vip port."""
        network_driver = utils.get_network_driver()
        try:
            return network_driver.allocate_vip(load_balancer_db)
        except network_base.AllocateVIPException as e:
            # Convert neutron style exception to octavia style
            # if the error was API ready
            if getattr(e, 'orig_code', None) is not None:
                e.code = e.orig_code
            if getattr(e, 'orig_msg', None) is not None:
                e.message = e.orig_msg
                e.msg = e.orig_msg
            raise e

    def _get_provider(self, session, load_balancer):
        """Decide on the provider for this load balancer."""

        provider = None
        if not isinstance(load_balancer.flavor_id, wtypes.UnsetType):
            try:
                with session.begin():
                    provider = self.repositories.flavor.get_flavor_provider(
                        session, load_balancer.flavor_id)
            except sa_exception.NoResultFound as e:
                raise exceptions.ValidationException(
                    detail=_("Invalid flavor_id.")) from e

        # No provider specified and no flavor specified, use conf default
        if (isinstance(load_balancer.provider, wtypes.UnsetType) and
                not provider):
            provider = CONF.api_settings.default_provider_driver
        # Both provider and flavor specified, they must match
        elif (not isinstance(load_balancer.provider, wtypes.UnsetType) and
                provider):
            if provider != load_balancer.provider:
                raise exceptions.ProviderFlavorMismatchError(
                    flav=load_balancer.flavor_id, prov=load_balancer.provider)
        # No flavor, but provider, use the provider specified
        elif not provider:
            provider = load_balancer.provider
        # Otherwise, use the flavor provider we found above

        return provider

    def _apply_flavor_to_lb_dict(self, lock_session, driver, lb_dict):

        flavor_dict = {}
        if 'flavor_id' in lb_dict:
            try:
                flavor_dict = (
                    self.repositories.flavor.get_flavor_metadata_dict(
                        lock_session, lb_dict['flavor_id']))
            except sa_exception.NoResultFound as e:
                raise exceptions.ValidationException(
                    detail=_("Invalid flavor_id.")) from e

        # Make sure the driver will still accept the flavor metadata
        if flavor_dict:
            driver_utils.call_provider(driver.name, driver.validate_flavor,
                                       flavor_dict)

        # Apply the flavor settings to the load balanacer
        # Use the configuration file settings as defaults
        lb_dict[constants.TOPOLOGY] = flavor_dict.get(
            constants.LOADBALANCER_TOPOLOGY,
            CONF.controller_worker.loadbalancer_topology)

        return flavor_dict

    def _validate_flavor(self, session, load_balancer):
        if not isinstance(load_balancer.flavor_id, wtypes.UnsetType):
            with session.begin():
                flavor = self.repositories.flavor.get(
                    session, id=load_balancer.flavor_id)
            if not flavor:
                raise exceptions.ValidationException(
                    detail=_("Invalid flavor_id."))
            if not flavor.enabled:
                raise exceptions.DisabledOption(option='flavor',
                                                value=load_balancer.flavor_id)

    def _validate_and_return_az_dict(self, lock_session, driver, lb_dict):

        az_dict = {}
        if 'availability_zone' in lb_dict:
            try:
                az = self.repositories.availability_zone.get(
                    lock_session, name=lb_dict['availability_zone'])
                az_dict = (
                    self.repositories.availability_zone
                    .get_availability_zone_metadata_dict(lock_session, az.name)
                )
            except sa_exception.NoResultFound as e:
                raise exceptions.ValidationException(
                    detail=_("Invalid availability_zone.")) from e

        # Make sure the driver will still accept the availability zone metadata
        if az_dict:
            try:
                driver_utils.call_provider(driver.name,
                                           driver.validate_availability_zone,
                                           az_dict)
            except NotImplementedError as e:
                raise exceptions.ProviderNotImplementedError(
                    prov=driver.name, user_msg="This provider does not support"
                                               " availability zones.") from e

        return az_dict

    def _validate_availability_zone(self, session, load_balancer):
        if not isinstance(load_balancer.availability_zone, wtypes.UnsetType):
            with session.begin():
                az = self.repositories.availability_zone.get(
                    session, name=load_balancer.availability_zone)
            if not az:
                raise exceptions.ValidationException(
                    detail=_("Invalid availability zone."))
            if not az.enabled:
                raise exceptions.DisabledOption(
                    option='availability_zone',
                    value=load_balancer.availability_zone)

    @wsme_pecan.wsexpose(lb_types.LoadBalancerFullRootResponse,
                         body=lb_types.LoadBalancerRootPOST, status_code=201)
    def post(self, load_balancer: lb_types.LoadBalancerRootPOST):
        """Creates a load balancer."""
        load_balancer = load_balancer.loadbalancer
        context = pecan_request.context.get('octavia_context')

        if not load_balancer.project_id and context.project_id:
            load_balancer.project_id = context.project_id

        if not load_balancer.project_id:
            raise exceptions.ValidationException(detail=_(
                "Missing project ID in request where one is required. "
                "An administrator should check the keystone settings "
                "in the Octavia configuration."))

        self._auth_validate_action(context, load_balancer.project_id,
                                   constants.RBAC_POST)
        if not isinstance(load_balancer.vip_sg_ids, wtypes.UnsetType):
            self._auth_validate_action(
                context, load_balancer.project_id,
                f"{constants.RBAC_POST}:vip_sg_ids")

        self._validate_vip_request_object(load_balancer, context=context)

        self._validate_flavor(context.session, load_balancer)

        self._validate_availability_zone(context.session, load_balancer)

        provider = self._get_provider(context.session, load_balancer)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(provider)

        lock_session = context.session
        lock_session.begin()
        try:
            if self.repositories.check_quota_met(
                    lock_session,
                    data_models.LoadBalancer,
                    load_balancer.project_id):
                raise exceptions.QuotaException(
                    resource=data_models.LoadBalancer._name())

            db_lb, db_pools, db_lists = None, None, None

            lb_dict = db_prepare.create_load_balancer(load_balancer.to_dict(
                render_unsets=False
            ))
            vip_dict = lb_dict.pop('vip', {})
            additional_vip_dicts = lb_dict.pop('additional_vips', [])

            # Make sure we store the right provider in the DB
            lb_dict['provider'] = driver.name

            # NoneType can be weird here, have to force type a second time
            listeners = lb_dict.pop('listeners', []) or []
            pools = lb_dict.pop('pools', []) or []

            flavor_dict = self._apply_flavor_to_lb_dict(lock_session, driver,
                                                        lb_dict)

            az_dict = self._validate_and_return_az_dict(lock_session, driver,
                                                        lb_dict)
            # Validate the network as soon as we have the AZ data
            validate.network_allowed_by_config(
                load_balancer.vip_network_id,
                valid_networks=az_dict.get(constants.VALID_VIP_NETWORKS))

            # Apply the anticipated vNIC type so the create will return the
            # right vip_vnic_type
            if flavor_dict and flavor_dict.get(constants.SRIOV_VIP, False):
                vip_dict[constants.VNIC_TYPE] = constants.VNIC_TYPE_DIRECT
            else:
                vip_dict[constants.VNIC_TYPE] = constants.VNIC_TYPE_NORMAL

            self._validate_vnic_type(vip_dict[constants.VNIC_TYPE],
                                     load_balancer)

            db_lb = self.repositories.create_load_balancer_and_vip(
                lock_session, lb_dict, vip_dict, additional_vip_dicts)

            # Pass the flavor dictionary through for the provider drivers
            # This is a "virtual" lb_dict item that includes the expanded
            # flavor dict instead of just the flavor_id we store in the DB.
            lb_dict['flavor'] = flavor_dict

            # Do the same with the availability_zone dict
            lb_dict['availability_zone'] = az_dict

            # See if the provider driver wants to manage the VIP port
            # This will still be called if the user provided a port to
            # allow drivers to collect any required information about the
            # VIP port.
            octavia_owned = False
            try:
                provider_vip_dict = driver_utils.vip_dict_to_provider_dict(
                    vip_dict)
                provider_additional_vips = [
                    driver_utils.additional_vip_dict_to_provider_dict(add_vip)
                    for add_vip in additional_vip_dicts]
                vip_dict, additional_vip_dicts = driver_utils.call_provider(
                    driver.name, driver.create_vip_port, db_lb.id,
                    db_lb.project_id, provider_vip_dict,
                    provider_additional_vips)
                vip = driver_utils.provider_vip_dict_to_vip_obj(vip_dict)
                add_vips = [data_models.AdditionalVip(**add_vip)
                            for add_vip in additional_vip_dicts]
            except exceptions.ProviderNotImplementedError:
                # create vip port if not exist, driver didn't want to create
                # the VIP port
                vip, add_vips = self._create_vip_port_if_not_exist(db_lb)
                LOG.info('Created VIP port %s for provider %s.',
                         vip.port_id, driver.name)
                # If a port_id wasn't passed in and we made it this far
                # we created the VIP
                if 'port_id' not in vip_dict or not vip_dict['port_id']:
                    octavia_owned = True

            # Check if the driver claims octavia owns the VIP port.
            if vip.octavia_owned:
                octavia_owned = True

            self.repositories.vip.update(
                lock_session, db_lb.id, ip_address=vip.ip_address,
                port_id=vip.port_id, network_id=vip.network_id,
                subnet_id=vip.subnet_id, octavia_owned=octavia_owned)
            for add_vip in add_vips:
                self.repositories.additional_vip.update(
                    lock_session, db_lb.id, ip_address=add_vip.ip_address,
                    port_id=add_vip.port_id, network_id=add_vip.network_id,
                    subnet_id=add_vip.subnet_id)

            if listeners or pools:
                # expire_all is required here, it ensures that the loadbalancer
                # will be re-fetched with its associated vip in _graph_create.
                # without expire_all the vip attributes that have been updated
                # just before this call may not be set correctly in the
                # loadbalancer object.
                lock_session.expire_all()

                db_pools, db_lists = self._graph_create(
                    lock_session, db_lb, listeners, pools)

            # Prepare the data for the driver data model
            driver_lb_dict = driver_utils.lb_dict_to_provider_dict(
                lb_dict, vip, add_vips, db_pools, db_lists)

            lock_session.flush()

            # Dispatch to the driver
            LOG.info("Sending create Load Balancer %s to provider %s",
                     db_lb.id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.loadbalancer_create,
                driver_dm.LoadBalancer.from_dict(driver_lb_dict))

            lock_session.commit()
        except odb_exceptions.DBDuplicateEntry as e:
            lock_session.rollback()
            raise exceptions.IDAlreadyExists() from e
        except Exception:
            with excutils.save_and_reraise_exception():
                lock_session.rollback()

        with context.session.begin():
            db_lb = self._get_db_lb(context.session, db_lb.id)

        result = self._convert_db_to_type(
            db_lb, lb_types.LoadBalancerFullResponse)
        return lb_types.LoadBalancerFullRootResponse(loadbalancer=result)

    def _graph_create(self, session, db_lb, listeners, pools):
        # Track which pools must have a full specification
        pools_required = set()
        # Look through listeners and find any extra pools, and move them to the
        # top level so they are created first.
        for li in listeners:
            default_pool = li.get('default_pool')
            pool_name = (
                default_pool.get('name') if default_pool else None)
            # All pools need to have a name so they can be referenced
            if default_pool and not pool_name:
                raise exceptions.ValidationException(
                    detail='Pools must be named when creating a fully '
                           'populated loadbalancer.')
            # If a pool has more than a name, assume it's a full specification
            # (but use >3 because it will also have "enabled" and "tls_enabled"
            # as default)
            if default_pool and len(default_pool) > 3:
                pools.append(default_pool)
                li['default_pool'] = {'name': pool_name}
            # Otherwise, it's a reference and we record it and move on
            elif default_pool:
                pools_required.add(pool_name)
            # We also need to check policy redirects
            for policy in li.get('l7policies'):
                redirect_pool = policy.get('redirect_pool')
                pool_name = (
                    redirect_pool.get('name') if redirect_pool else None)
                # All pools need to have a name so they can be referenced
                if redirect_pool and not pool_name:
                    raise exceptions.ValidationException(
                        detail='Pools must be named when creating a fully '
                               'populated loadbalancer.')
                # If a pool has more than a name, assume it's a full spec
                # (but use >2 because it will also have "enabled" and
                # "tls_enabled" as default)
                if redirect_pool and len(redirect_pool) > 3:
                    pool_name = redirect_pool['name']
                    policy['redirect_pool'] = {'name': pool_name}
                    pools.append(redirect_pool)
                # Otherwise, it's a reference and we record it and move on
                elif redirect_pool:
                    pools_required.add(pool_name)

        # Make sure all pool names are unique.
        pool_names = [p.get('name') for p in pools]
        if len(set(pool_names)) != len(pool_names):
            raise exceptions.ValidationException(
                detail="Pool names must be unique when creating a fully "
                       "populated loadbalancer.")
        # Make sure every reference is present in our spec list
        for pool_ref in pools_required:
            if pool_ref not in pool_names:
                raise exceptions.ValidationException(
                    detail="Pool '{name}' was referenced but no full "
                           "definition was found.".format(name=pool_ref))

        # Check quotas for pools.
        if pools and self.repositories.check_quota_met(
                session, data_models.Pool, db_lb.project_id,
                count=len(pools)):
            raise exceptions.QuotaException(resource=data_models.Pool._name())

        # Now create all of the pools ahead of the listeners.
        new_pools = []
        pool_name_ids = {}
        for p in pools:
            # Check that pools have mandatory attributes, since we have to
            # bypass the normal validation layer to allow for name-only
            for attr in ('protocol', 'lb_algorithm'):
                if attr not in p:
                    raise exceptions.ValidationException(
                        detail="Pool definition for '{name}' missing required "
                               "attribute: {attr}".format(name=p['name'],
                                                          attr=attr))
            p['load_balancer_id'] = db_lb.id
            p['project_id'] = db_lb.project_id
            new_pool = (pool.PoolsController()._graph_create(
                session, p))
            new_pools.append(new_pool)
            pool_name_ids[new_pool.name] = new_pool.id

        # Now check quotas for listeners
        if listeners and self.repositories.check_quota_met(
                session, data_models.Listener, db_lb.project_id,
                count=len(listeners)):
            raise exceptions.QuotaException(
                resource=data_models.Listener._name())

        # Now create all of the listeners
        new_lists = []
        for li in listeners:
            default_pool = li.pop('default_pool', None)
            # If there's a default pool, replace it with the ID
            if default_pool:
                pool_name = default_pool['name']
                pool_id = pool_name_ids.get(pool_name)
                if not pool_id:
                    raise exceptions.SingleCreateDetailsMissing(
                        type='Pool', name=pool_name)
                li['default_pool_id'] = pool_id
            li['load_balancer_id'] = db_lb.id
            li['project_id'] = db_lb.project_id
            new_lists.append(listener.ListenersController()._graph_create(
                session, li, pool_name_ids=pool_name_ids))

        return new_pools, new_lists

    @wsme_pecan.wsexpose(lb_types.LoadBalancerRootResponse,
                         wtypes.text, status_code=200,
                         body=lb_types.LoadBalancerRootPUT)
    def put(self, id, load_balancer):
        """Updates a load balancer."""
        load_balancer = load_balancer.loadbalancer
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_lb = self._get_db_lb(context.session, id, show_deleted=False)

        self._auth_validate_action(context, db_lb.project_id,
                                   constants.RBAC_PUT)
        if not isinstance(load_balancer.vip_sg_ids, wtypes.UnsetType):
            self._auth_validate_action(context, db_lb.project_id,
                                       f"{constants.RBAC_PUT}:vip_sg_ids")

        if not isinstance(load_balancer.vip_qos_policy_id, wtypes.UnsetType):
            network_driver = utils.get_network_driver()
            validate.qos_extension_enabled(network_driver)
            if load_balancer.vip_qos_policy_id is not None:
                if db_lb.vip.qos_policy_id != load_balancer.vip_qos_policy_id:
                    validate.qos_policy_exists(load_balancer.vip_qos_policy_id)

        if not isinstance(load_balancer.vip_sg_ids, wtypes.UnsetType):
            if load_balancer.vip_sg_ids is None:
                load_balancer.vip_sg_ids = []
            else:
                for sg_id in load_balancer.vip_sg_ids:
                    validate.security_group_exists(sg_id, context=context)

        self._validate_vnic_type(db_lb.vip.vnic_type, load_balancer)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(db_lb.provider)

        with context.session.begin():
            self._test_lb_status(context.session, id)

            # Prepare the data for the driver data model
            lb_dict = load_balancer.to_dict(render_unsets=False)
            lb_dict['id'] = id
            vip_dict = lb_dict.pop('vip', {})
            lb_dict = driver_utils.lb_dict_to_provider_dict(lb_dict)
            if 'qos_policy_id' in vip_dict:
                lb_dict['vip_qos_policy_id'] = vip_dict['qos_policy_id']

            # Also prepare the baseline object data
            old_provider_lb = (
                driver_utils.db_loadbalancer_to_provider_loadbalancer(
                    db_lb, for_delete=True))

            # Dispatch to the driver
            LOG.info("Sending update Load Balancer %s to provider "
                     "%s", id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.loadbalancer_update,
                old_provider_lb,
                driver_dm.LoadBalancer.from_dict(lb_dict))

            db_lb_dict = load_balancer.to_dict(render_unsets=False)
            if 'vip' in db_lb_dict:
                db_vip_dict = db_lb_dict.pop('vip')
                self.repositories.vip.update(context.session, id,
                                             **db_vip_dict)
            if db_lb_dict:
                self.repositories.load_balancer.update(context.session, id,
                                                       **db_lb_dict)

        # Force SQL alchemy to query the DB, otherwise we get inconsistent
        # results
        context.session.expire_all()
        with context.session.begin():
            db_lb = self._get_db_lb(context.session, id)
        result = self._convert_db_to_type(db_lb, lb_types.LoadBalancerResponse)
        return lb_types.LoadBalancerRootResponse(loadbalancer=result)

    @wsme_pecan.wsexpose(None, wtypes.text, wtypes.text, status_code=204)
    def delete(self, id, cascade=False):
        """Deletes a load balancer."""
        context = pecan_request.context.get('octavia_context')
        cascade = strutils.bool_from_string(cascade)
        with context.session.begin():
            db_lb = self._get_db_lb(context.session, id, show_deleted=False)

        self._auth_validate_action(context, db_lb.project_id,
                                   constants.RBAC_DELETE)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(db_lb.provider)

        with context.session.begin():
            if (db_lb.listeners or db_lb.pools) and not cascade:
                msg = _("Cannot delete Load Balancer %s - "
                        "it has children") % id
                LOG.warning(msg)
                raise exceptions.ValidationException(detail=msg)
            self._test_lb_status(context.session, id,
                                 lb_status=constants.PENDING_DELETE)

            LOG.info("Sending delete Load Balancer %s to provider %s",
                     id, driver.name)
            provider_loadbalancer = (
                driver_utils.db_loadbalancer_to_provider_loadbalancer(
                    db_lb, for_delete=True))
            driver_utils.call_provider(driver.name, driver.loadbalancer_delete,
                                       provider_loadbalancer, cascade)

    @pecan_expose()
    def _lookup(self, id, *remainder):
        """Overridden pecan _lookup method for custom routing.

        Currently it checks if this was a status request and routes
        the request to the StatusController.

        'statuses' is aliased here for backward compatibility with
        neutron-lbaas LBaaS v2 API.
        """
        is_children = (
            id and remainder and (
                remainder[0] == 'status' or remainder[0] == 'statuses' or (
                    remainder[0] == 'stats' or remainder[0] == 'failover'
                )
            )
        )
        if is_children:
            controller = remainder[0]
            remainder = remainder[1:]
            if controller in ('status', 'statuses'):
                return StatusController(lb_id=id), remainder
            if controller == 'stats':
                return StatisticsController(lb_id=id), remainder
            if controller == 'failover':
                return FailoverController(lb_id=id), remainder
        return None


class StatusController(base.BaseController):
    RBAC_TYPE = constants.RBAC_LOADBALANCER

    def __init__(self, lb_id):
        super().__init__()
        self.id = lb_id

    @wsme_pecan.wsexpose(lb_types.StatusRootResponse, wtypes.text,
                         status_code=200)
    def get(self):
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            load_balancer = self._get_db_lb(context.session, self.id,
                                            show_deleted=False)
        if not load_balancer:
            LOG.info("Load balancer %s not found.", id)
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(),
                id=id)

        self._auth_validate_action(context, load_balancer.project_id,
                                   constants.RBAC_GET_STATUS)

        result = self._convert_db_to_type(
            load_balancer, lb_types.LoadBalancerStatusResponse)
        result = lb_types.StatusResponse(loadbalancer=result)
        return lb_types.StatusRootResponse(statuses=result)


class StatisticsController(base.BaseController, stats.StatsMixin):
    RBAC_TYPE = constants.RBAC_LOADBALANCER

    def __init__(self, lb_id):
        super().__init__()
        self.id = lb_id

    @wsme_pecan.wsexpose(lb_types.StatisticsRootResponse, wtypes.text,
                         status_code=200)
    def get(self):
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            load_balancer = self._get_db_lb(context.session, self.id,
                                            show_deleted=False)
        if not load_balancer:
            LOG.info("Load balancer %s not found.", id)
            raise exceptions.NotFound(
                resource=data_models.LoadBalancer._name(),
                id=id)

        self._auth_validate_action(context, load_balancer.project_id,
                                   constants.RBAC_GET_STATS)

        with context.session.begin():
            lb_stats = self.get_loadbalancer_stats(context.session, self.id)

        result = self._convert_db_to_type(
            lb_stats, lb_types.LoadBalancerStatisticsResponse)
        return lb_types.StatisticsRootResponse(stats=result)


class FailoverController(LoadBalancersController):

    def __init__(self, lb_id):
        super().__init__()
        self.lb_id = lb_id

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def put(self, **kwargs):
        """Fails over a loadbalancer"""
        context = pecan_request.context.get('octavia_context')
        with context.session.begin():
            db_lb = self._get_db_lb(context.session, self.lb_id,
                                    show_deleted=False)

        self._auth_validate_action(context, db_lb.project_id,
                                   constants.RBAC_PUT_FAILOVER)

        # Load the driver early as it also provides validation
        driver = driver_factory.get_driver(db_lb.provider)

        with context.session.begin():
            self._test_and_set_failover_prov_status(context.session,
                                                    self.lb_id)
            LOG.info("Sending failover request for load balancer %s to the "
                     "provider %s", self.lb_id, driver.name)
            driver_utils.call_provider(
                driver.name, driver.loadbalancer_failover, self.lb_id)
