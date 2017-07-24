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


class BaseFlavorProfileType(types.BaseType):
    _type_to_model_map = {}
    _child_map = {}


class FlavorProfileResponse(BaseFlavorProfileType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    provider_name = wtypes.wsattr(wtypes.StringType())
    flavor_data = wtypes.wsattr(wtypes.StringType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        flavorprofile = super(FlavorProfileResponse, cls).from_data_model(
            data_model, children=children)
        return flavorprofile


class FlavorProfileRootResponse(types.BaseType):
    flavorprofile = wtypes.wsattr(FlavorProfileResponse)


class FlavorProfilesRootResponse(types.BaseType):
    flavorprofiles = wtypes.wsattr([FlavorProfileResponse])
    flavorprofile_links = wtypes.wsattr([types.PageType])


class FlavorProfilePOST(BaseFlavorProfileType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)
    provider_name = wtypes.wsattr(wtypes.StringType(max_length=255),
                                  mandatory=True)
    flavor_data = wtypes.wsattr(wtypes.StringType(max_length=4096),
                                mandatory=True)


class FlavorProfileRootPOST(types.BaseType):
    flavorprofile = wtypes.wsattr(FlavorProfilePOST)


class FlavorProfilePUT(BaseFlavorProfileType):
    """Defines the attributes of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    provider_name = wtypes.wsattr(wtypes.StringType(max_length=255))
    flavor_data = wtypes.wsattr(wtypes.StringType(max_length=4096))


class FlavorProfileRootPUT(types.BaseType):
    flavorprofile = wtypes.wsattr(FlavorProfilePUT)
