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

import sys

from wsme import types as wtypes

from octavia.api.v1.types import base
from octavia.common import constants


class L7PolicyResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)
    action = wtypes.wsattr(wtypes.StringType(max_length=255))
    redirect_pool_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    redirect_url = wtypes.wsattr(wtypes.StringType(max_length=255))
    position = wtypes.wsattr(wtypes.IntegerType())


class L7PolicyPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS),
        mandatory=True)
    redirect_pool_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    redirect_url = wtypes.wsattr(base.URLType())
    position = wtypes.wsattr(wtypes.IntegerType(), default=sys.maxsize)


class L7PolicyPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS))
    redirect_pool_id = wtypes.wsattr(wtypes.StringType(max_length=255))
    redirect_url = wtypes.wsattr(base.URLType())
    position = wtypes.wsattr(wtypes.IntegerType())
