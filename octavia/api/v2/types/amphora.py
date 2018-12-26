#    Copyright 2016 Rackspace
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


class BaseAmphoraType(types.BaseType):
    _type_to_model_map = {'loadbalancer_id': 'load_balancer_id'}
    _child_map = {}


class AmphoraResponse(BaseAmphoraType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    loadbalancer_id = wtypes.wsattr(wtypes.UuidType())
    compute_id = wtypes.wsattr(wtypes.UuidType())
    lb_network_ip = wtypes.wsattr(types.IPAddressType())
    vrrp_ip = wtypes.wsattr(types.IPAddressType())
    ha_ip = wtypes.wsattr(types.IPAddressType())
    vrrp_port_id = wtypes.wsattr(wtypes.UuidType())
    ha_port_id = wtypes.wsattr(wtypes.UuidType())
    cert_expiration = wtypes.wsattr(wtypes.datetime.datetime)
    cert_busy = wtypes.wsattr(bool)
    role = wtypes.wsattr(wtypes.StringType())
    status = wtypes.wsattr(wtypes.StringType())
    vrrp_interface = wtypes.wsattr(wtypes.StringType())
    vrrp_id = wtypes.wsattr(wtypes.IntegerType())
    vrrp_priority = wtypes.wsattr(wtypes.IntegerType())
    cached_zone = wtypes.wsattr(wtypes.StringType())
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    image_id = wtypes.wsattr(wtypes.UuidType())
    compute_flavor = wtypes.wsattr(wtypes.StringType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        amphorae = super(AmphoraResponse, cls).from_data_model(
            data_model, children=children)

        return amphorae


class AmphoraRootResponse(types.BaseType):
    amphora = wtypes.wsattr(AmphoraResponse)


class AmphoraeRootResponse(types.BaseType):
    amphorae = wtypes.wsattr([AmphoraResponse])
    amphorae_links = wtypes.wsattr([types.PageType])


class AmphoraStatisticsResponse(BaseAmphoraType):
    """Defines which attributes are to show on stats response."""
    active_connections = wtypes.wsattr(wtypes.IntegerType())
    bytes_in = wtypes.wsattr(wtypes.IntegerType())
    bytes_out = wtypes.wsattr(wtypes.IntegerType())
    id = wtypes.wsattr(wtypes.UuidType())
    listener_id = wtypes.wsattr(wtypes.UuidType())
    loadbalancer_id = wtypes.wsattr(wtypes.UuidType())
    request_errors = wtypes.wsattr(wtypes.IntegerType())
    total_connections = wtypes.wsattr(wtypes.IntegerType())


class StatisticsRootResponse(types.BaseType):
    amphora_stats = wtypes.wsattr([AmphoraStatisticsResponse])
