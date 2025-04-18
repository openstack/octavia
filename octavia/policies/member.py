# Copyright 2017 Rackspace, US Inc.
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

from oslo_policy import policy

from octavia.common import constants

rules = [
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_MEMBER}{constants.RBAC_GET_ALL}',
        constants.RULE_MEMBER_API_READ,
        "List Members of a Pool",
        [{'method': 'GET', 'path': '/v2/lbaas/pools/{pool_id}/members'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_MEMBER}{constants.RBAC_POST}',
        constants.RULE_API_WRITE,
        "Create a Member",
        [{'method': 'POST', 'path': '/v2/lbaas/pools/{pool_id}/members'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_MEMBER}{constants.RBAC_GET_ONE}',
        constants.RULE_API_READ,
        "Show Member details",
        [{'method': 'GET',
          'path': '/v2/lbaas/pools/{pool_id}/members/{member_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_MEMBER}{constants.RBAC_PUT}',
        constants.RULE_API_WRITE,
        "Update a Member",
        [{'method': 'PUT',
          'path': '/v2/lbaas/pools/{pool_id}/members/{member_id}'}]
    ),
    policy.DocumentedRuleDefault(
        f'{constants.RBAC_MEMBER}{constants.RBAC_DELETE}',
        constants.RULE_API_WRITE,
        "Remove a Member",
        [{'method': 'DELETE',
          'path': '/v2/lbaas/pools/{pool_id}/members/{member_id}'}]
    ),
]


def list_rules():
    return rules
