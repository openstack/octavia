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

from octavia.common import constants
from oslo_policy import policy

rules = [
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_GET_ALL),
        constants.RULE_API_READ,
        "List Pools",
        [{'method': 'GET', 'path': '/v2.0/lbaas/pools'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_GET_ALL_GLOBAL),
        constants.RULE_API_READ_GLOBAL,
        "List Pools including resources owned by others",
        [{'method': 'GET', 'path': '/v2.0/lbaas/pools'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_POST),
        constants.RULE_API_WRITE,
        "Create a Pool",
        [{'method': 'POST', 'path': '/v2.0/lbaas/pools'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_GET_ONE),
        constants.RULE_API_READ,
        "Show Pool details",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/pools/{pool_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_PUT),
        constants.RULE_API_WRITE,
        "Update a Pool",
        [{'method': 'PUT',
          'path': '/v2.0/lbaas/pools/{pool_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_POOL,
                                    action=constants.RBAC_DELETE),
        constants.RULE_API_WRITE,
        "Remove a Pool",
        [{'method': 'DELETE',
          'path': '/v2.0/lbaas/pools/{pool_id}'}]
    ),
]


def list_rules():
    return rules
