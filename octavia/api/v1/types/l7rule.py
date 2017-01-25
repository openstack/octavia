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

from wsme import types as wtypes

from octavia.api.common import types as base
from octavia.common import constants


class L7RuleResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    type = wtypes.wsattr(wtypes.StringType())
    compare_type = wtypes.wsattr(wtypes.StringType())
    key = wtypes.wsattr(wtypes.StringType())
    value = wtypes.wsattr(wtypes.StringType())
    invert = wtypes.wsattr(bool)


class L7RulePOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    type = wtypes.wsattr(
        wtypes.Enum(str,
                    *constants.SUPPORTED_L7RULE_TYPES),
        mandatory=True)
    compare_type = wtypes.wsattr(
        wtypes.Enum(str,
                    *constants.SUPPORTED_L7RULE_COMPARE_TYPES),
        mandatory=True)
    key = wtypes.wsattr(wtypes.StringType(max_length=255))
    value = wtypes.wsattr(wtypes.StringType(max_length=255), mandatory=True)
    invert = wtypes.wsattr(bool, default=False)


class L7RulePUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    type = wtypes.wsattr(
        wtypes.Enum(str,
                    *constants.SUPPORTED_L7RULE_TYPES))
    compare_type = wtypes.wsattr(
        wtypes.Enum(str,
                    *constants.SUPPORTED_L7RULE_COMPARE_TYPES))
    key = wtypes.wsattr(wtypes.StringType(max_length=255))
    value = wtypes.wsattr(wtypes.StringType(max_length=255))
    invert = wtypes.wsattr(bool)
