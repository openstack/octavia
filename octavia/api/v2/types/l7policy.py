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

from octavia.api.common import types
from octavia.api.v2.types import l7rule
from octavia.api.v2.types import pool
from octavia.common import constants


class BaseL7PolicyType(types.BaseType):
    _type_to_model_map = {'admin_state_up': 'enabled'}
    _child_map = {}


class L7PolicyResponse(BaseL7PolicyType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    provisioning_status = wtypes.wsattr(wtypes.StringType())
    operating_status = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)
    project_id = wtypes.wsattr(wtypes.StringType())
    action = wtypes.wsattr(wtypes.StringType())
    listener_id = wtypes.wsattr(wtypes.UuidType())
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(wtypes.StringType())
    redirect_prefix = wtypes.wsattr(wtypes.StringType())
    position = wtypes.wsattr(wtypes.IntegerType())
    rules = wtypes.wsattr([types.IdOnlyType])
    created_at = wtypes.wsattr(wtypes.datetime.datetime)
    updated_at = wtypes.wsattr(wtypes.datetime.datetime)
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType()))
    redirect_http_code = wtypes.wsattr(wtypes.IntegerType())

    @classmethod
    def from_data_model(cls, data_model, children=False):
        policy = super(L7PolicyResponse, cls).from_data_model(
            data_model, children=children)

        if cls._full_response():
            rule_model = l7rule.L7RuleFullResponse
        else:
            rule_model = types.IdOnlyType
        policy.rules = [
            rule_model.from_data_model(i) for i in data_model.l7rules]
        return policy


class L7PolicyFullResponse(L7PolicyResponse):
    @classmethod
    def _full_response(cls):
        return True

    rules = wtypes.wsattr([l7rule.L7RuleFullResponse])


class L7PolicyRootResponse(types.BaseType):
    l7policy = wtypes.wsattr(L7PolicyResponse)


class L7PoliciesRootResponse(types.BaseType):
    l7policies = wtypes.wsattr([L7PolicyResponse])
    l7policies_links = wtypes.wsattr([types.PageType])


class L7PolicyPOST(BaseL7PolicyType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    # TODO(johnsom) Remove after deprecation (R series)
    project_id = wtypes.wsattr(wtypes.StringType(max_length=36))
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS),
        mandatory=True)
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(types.URLType())
    redirect_prefix = wtypes.wsattr(types.URLType())
    position = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_POLICY_POSITION,
        maximum=constants.MAX_POLICY_POSITION),
        default=constants.MAX_POLICY_POSITION)
    listener_id = wtypes.wsattr(wtypes.UuidType(), mandatory=True)
    rules = wtypes.wsattr([l7rule.L7RuleSingleCreate])
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    redirect_http_code = wtypes.wsattr(
        wtypes.Enum(int, *constants.SUPPORTED_L7POLICY_REDIRECT_HTTP_CODES))


class L7PolicyRootPOST(types.BaseType):
    l7policy = wtypes.wsattr(L7PolicyPOST)


class L7PolicyPUT(BaseL7PolicyType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS))
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(types.URLType())
    redirect_prefix = wtypes.wsattr(types.URLType())
    position = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_POLICY_POSITION,
        maximum=constants.MAX_POLICY_POSITION))
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    redirect_http_code = wtypes.wsattr(
        wtypes.Enum(int, *constants.SUPPORTED_L7POLICY_REDIRECT_HTTP_CODES))


class L7PolicyRootPUT(types.BaseType):
    l7policy = wtypes.wsattr(L7PolicyPUT)


class L7PolicySingleCreate(BaseL7PolicyType):
    """Defines mandatory and optional attributes of a POST request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    admin_state_up = wtypes.wsattr(bool, default=True)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS),
        mandatory=True)
    redirect_pool = wtypes.wsattr(pool.PoolSingleCreate)
    redirect_url = wtypes.wsattr(types.URLType())
    redirect_prefix = wtypes.wsattr(types.URLType())
    position = wtypes.wsattr(wtypes.IntegerType(
        minimum=constants.MIN_POLICY_POSITION,
        maximum=constants.MAX_POLICY_POSITION),
        default=constants.MAX_POLICY_POSITION)
    rules = wtypes.wsattr([l7rule.L7RuleSingleCreate])
    tags = wtypes.wsattr(wtypes.ArrayType(wtypes.StringType(max_length=255)))
    redirect_http_code = wtypes.wsattr(
        wtypes.Enum(int, *constants.SUPPORTED_L7POLICY_REDIRECT_HTTP_CODES))
