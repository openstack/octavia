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


class BaseFlavorType(types.BaseType):
    _type_to_model_map = {}
    _child_map = {}


class FlavorResponse(BaseFlavorType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    flavor_profile_id = wtypes.wsattr(wtypes.StringType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        flavor = super(FlavorResponse, cls).from_data_model(
            data_model, children=children)
        return flavor


class FlavorRootResponse(types.BaseType):
    flavor = wtypes.wsattr(FlavorResponse)


class FlavorsRootResponse(types.BaseType):
    flavors = wtypes.wsattr([FlavorResponse])
    flavors_links = wtypes.wsattr([types.PageType])


class FlavorPOST(BaseFlavorType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    flavor_profile_id = wtypes.wsattr(wtypes.UuidType(), mandatory=True)


class FlavorRootPOST(types.BaseType):
    flavor = wtypes.wsattr(FlavorPOST)


class FlavorPUT(BaseFlavorType):
    """Defines the attributes of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)


class FlavorRootPUT(types.BaseType):
    flavor = wtypes.wsattr(FlavorPUT)
