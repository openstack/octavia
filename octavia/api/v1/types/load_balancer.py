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

from octavia.api.common import types as base
from octavia.api.v1.types import listener


class VIP(base.BaseType):
    """Defines the response and acceptable POST request attributes."""
    ip_address = wtypes.wsattr(base.IPAddressType())
    port_id = wtypes.wsattr(wtypes.UuidType())
    subnet_id = wtypes.wsattr(wtypes.UuidType())
    network_id = wtypes.wsattr(wtypes.UuidType())


class LoadBalancerResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    vip = wtypes.wsattr(VIP)
    project_id = wtypes.wsattr(wtypes.StringType())
    listeners = wtypes.wsattr([listener.ListenerResponse])
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)

    @classmethod
    def from_data_model(cls, data_model, children=False):
        lb = super(LoadBalancerResponse, cls).from_data_model(
            data_model, children=children)
        # NOTE(blogan): VIP is technically a child but its the main piece of
        # a load balancer so it makes sense to show it no matter what.
        lb.vip = VIP.from_data_model(data_model.vip)
        if not children:
            # NOTE(blogan): don't show listeners if the request does not want
            # to see children
            del lb.listeners
            return lb
        lb.listeners = [
            listener.ListenerResponse.from_data_model(
                listener_dm, children=children)
            for listener_dm in data_model.listeners
        ]
        return lb


class LoadBalancerPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    vip = wtypes.wsattr(VIP, mandatory=True)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    listeners = wtypes.wsattr([listener.ListenerPOST], default=[])


class LoadBalancerPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)
