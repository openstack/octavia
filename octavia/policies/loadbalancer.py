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
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='get_all'),
        constants.RULE_API_READ,
        "List Load Balancers",
        [{'method': 'GET', 'path': '/v2.0/lbaas/loadbalancers'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='get_all-global'),
        constants.RULE_API_READ_GLOBAL,
        "List Load Balancers including resources owned by others",
        [{'method': 'GET', 'path': '/v2.0/lbaas/loadbalancers'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='post'),
        constants.RULE_API_WRITE,
        "Create a Load Balancer",
        [{'method': 'POST', 'path': '/v2.0/lbaas/loadbalancers'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='get_one'),
        constants.RULE_API_READ,
        "Show Load Balancer details",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/loadbalancers/{loadbalancer_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='put'),
        constants.RULE_API_WRITE,
        "Update a Load Balancer",
        [{'method': 'PUT',
          'path': '/v2.0/lbaas/loadbalancers/{loadbalancer_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='delete'),
        constants.RULE_API_WRITE,
        "Remove a Load Balancer",
        [{'method': 'DELETE',
          'path': '/v2.0/lbaas/loadbalancers/{loadbalancer_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='get_stats'),
        constants.RULE_API_READ,
        "Show Load Balancer statistics",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/loadbalancers/{loadbalancer_id}/stats'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LOADBALANCER,
                                    action='get_status'),
        constants.RULE_API_READ,
        "Show Load Balancer status",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/loadbalancers/{loadbalancer_id}/status'}]
    ),
]


def list_rules():
    return rules
