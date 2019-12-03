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


class BaseAvailabilityZoneProfileType(types.BaseType):
    _type_to_model_map = {}
    _child_map = {}


class AvailabilityZoneProfileResponse(BaseAvailabilityZoneProfileType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    provider_name = wtypes.wsattr(wtypes.StringType())
    availability_zone_data = wtypes.wsattr(wtypes.StringType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        availability_zone_profile = super(
            AvailabilityZoneProfileResponse, cls).from_data_model(
            data_model, children=children)
        return availability_zone_profile


class AvailabilityZoneProfileRootResponse(types.BaseType):
    availability_zone_profile = wtypes.wsattr(AvailabilityZoneProfileResponse)


class AvailabilityZoneProfilesRootResponse(types.BaseType):
    availability_zone_profiles = wtypes.wsattr(
        [AvailabilityZoneProfileResponse])
    availability_zone_profile_links = wtypes.wsattr([types.PageType])


class AvailabilityZoneProfilePOST(BaseAvailabilityZoneProfileType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)
    provider_name = wtypes.wsattr(wtypes.StringType(max_length=255),
                                  mandatory=True)
    availability_zone_data = wtypes.wsattr(wtypes.StringType(max_length=4096),
                                           mandatory=True)


class AvailabilityZoneProfileRootPOST(types.BaseType):
    availability_zone_profile = wtypes.wsattr(AvailabilityZoneProfilePOST)


class AvailabilityZoneProfilePUT(BaseAvailabilityZoneProfileType):
    """Defines the attributes of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    provider_name = wtypes.wsattr(wtypes.StringType(max_length=255))
    availability_zone_data = wtypes.wsattr(wtypes.StringType(max_length=4096))


class AvailabilityZoneProfileRootPUT(types.BaseType):
    availability_zone_profile = wtypes.wsattr(AvailabilityZoneProfilePUT)
