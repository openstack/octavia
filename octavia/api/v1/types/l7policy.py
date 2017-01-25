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
from octavia.api.v1.types import l7rule
from octavia.api.v1.types import pool
from octavia.common import constants


class L7PolicyResponse(base.BaseType):
    """Defines which attributes are to be shown on any response."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType())
    description = wtypes.wsattr(wtypes.StringType())
    enabled = wtypes.wsattr(bool)
    action = wtypes.wsattr(wtypes.StringType())
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(wtypes.StringType())
    position = wtypes.wsattr(wtypes.IntegerType())
    l7rules = wtypes.wsattr([l7rule.L7RuleResponse])
    redirect_pool = wtypes.wsattr(pool.PoolResponse)

    @classmethod
    def from_data_model(cls, data_model, children=False):
        policy = super(L7PolicyResponse, cls).from_data_model(
            data_model, children=children)
        if not children:
            del policy.l7rules
            del policy.redirect_pool
            return policy
        policy.l7rules = [
            l7rule.L7RuleResponse.from_data_model(
                l7rule_dm, children=children)
            for l7rule_dm in data_model.l7rules
        ]
        if policy.redirect_pool_id:
            policy.redirect_pool = pool.PoolResponse.from_data_model(
                data_model.redirect_pool, children=children)
        else:
            del policy.redirect_pool
            del policy.redirect_pool_id
        return policy


class L7PolicyPOST(base.BaseType):
    """Defines mandatory and optional attributes of a POST request."""
    id = wtypes.wsattr(wtypes.UuidType())
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool, default=True)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS),
        mandatory=True)
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(base.URLType())
    position = wtypes.wsattr(wtypes.IntegerType(),
                             default=constants.MAX_POLICY_POSITION)
    redirect_pool = wtypes.wsattr(pool.PoolPOST)
    l7rules = wtypes.wsattr([l7rule.L7RulePOST], default=[])


class L7PolicyPUT(base.BaseType):
    """Defines attributes that are acceptable of a PUT request."""
    name = wtypes.wsattr(wtypes.StringType(max_length=255))
    description = wtypes.wsattr(wtypes.StringType(max_length=255))
    enabled = wtypes.wsattr(bool)
    action = wtypes.wsattr(
        wtypes.Enum(str, *constants.SUPPORTED_L7POLICY_ACTIONS))
    redirect_pool_id = wtypes.wsattr(wtypes.UuidType())
    redirect_url = wtypes.wsattr(base.URLType())
    position = wtypes.wsattr(wtypes.IntegerType())
