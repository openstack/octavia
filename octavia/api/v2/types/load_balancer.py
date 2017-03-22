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

from wsme import types as wtypes

from octavia.api.common import types


class BaseLoadBalancerType(types.BaseType):
    _type_to_model_map = {'vip_address': 'vip.ip_address',
                          'vip_subnet_id': 'vip.subnet_id',
                          'vip_port_id': 'vip.port_id',
                          'vip_network_id': 'vip.network_id',
                          'admin_state_up': 'enabled'}


class LoadBalancerResponse(BaseLoadBalancerType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)
    project_id = wtypes.wsattr(wtypes.StringType())
    tenant_id = wtypes.wsattr(wtypes.StringType())
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    vip_address = wtypes.wsattr(types.IPAddressType())
    vip_port_id = wtypes.wsattr(wtypes.UuidType())
    vip_subnet_id = wtypes.wsattr(wtypes.UuidType())
    vip_network_id = wtypes.wsattr(wtypes.UuidType())
    # TODO(blogan): add listeners once that has been merged
    # TODO(ankur-gupta-f): add pools once that has been merged

    @classmethod
    def from_data_model(cls, data_model, children=False):
        result = super(BaseLoadBalancerType, cls).from_data_model(
            data_model, children=children)
        if data_model.vip:
            result.vip_subnet_id = data_model.vip.subnet_id
            result.vip_port_id = data_model.vip.port_id
            result.vip_address = data_model.vip.ip_address
            result.vip_network_id = data_model.vip.network_id
        result.tenant_id = data_model.project_id
        if not result.description:
            result.description = ""
        if not result.name:
            result.name = ""

        return result


class LoadBalancerRootResponse(types.BaseType):
    loadbalancer = wtypes.wsattr(LoadBalancerResponse)


class LoadBalancersRootResponse(types.BaseType):
    loadbalancers = wtypes.wsattr([LoadBalancerResponse])


class LoadBalancerPOST(BaseLoadBalancerType):
    """Defines mandatory and optional attributes of a POST request."""

    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    vip_address = wtypes.wsattr(types.IPAddressType())
    vip_port_id = wtypes.wsattr(wtypes.UuidType())
    vip_subnet_id = wtypes.wsattr(wtypes.UuidType())
    vip_network_id = wtypes.wsattr(wtypes.UuidType())
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    tenant_id = wtypes.wsattr(wtypes.StringType(max_length=36))


class LoadBalancerRootPOST(types.BaseType):
    loadbalancer = wtypes.wsattr(LoadBalancerPOST)


class LoadBalancerPUT(BaseLoadBalancerType):
    """Defines attributes that are acceptable of a PUT request."""

    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool)


class LoadBalancerRootPUT(types.BaseType):
    loadbalancer = wtypes.wsattr(LoadBalancerPUT)
