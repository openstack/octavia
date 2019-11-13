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

from wsme import types as wtypes

from octavia.api.common import types


class BaseAvailabilityZoneType(types.BaseType):
    _type_to_model_map = {}
    _child_map = {}


class AvailabilityZoneResponse(BaseAvailabilityZoneType):
    """Defines which attributes are to be shown on any response."""
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    availability_zone_profile_id = wtypes.wsattr(wtypes.StringType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        availability_zone = super(
            AvailabilityZoneResponse, cls).from_data_model(
            data_model, children=children)
        return availability_zone


class AvailabilityZoneRootResponse(types.BaseType):
    availability_zone = wtypes.wsattr(AvailabilityZoneResponse)


class AvailabilityZonesRootResponse(types.BaseType):
    availability_zones = wtypes.wsattr([AvailabilityZoneResponse])
    availability_zones_links = wtypes.wsattr([types.PageType])


class AvailabilityZonePOST(BaseAvailabilityZoneType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    availability_zone_profile_id = wtypes.wsattr(wtypes.UuidType(),
                                                 mandatory=True)


class AvailabilityZoneRootPOST(types.BaseType):
    availability_zone = wtypes.wsattr(AvailabilityZonePOST)


class AvailabilityZonePUT(BaseAvailabilityZoneType):
    """Defines the attributes of a PUT request."""
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)


class AvailabilityZoneRootPUT(types.BaseType):
    availability_zone = wtypes.wsattr(AvailabilityZonePUT)
