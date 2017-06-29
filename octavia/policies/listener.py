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
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_GET_ALL),
        constants.RULE_API_READ,
        "List Listeners",
        [{'method': 'GET', 'path': '/v2.0/lbaas/listeners'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_GET_ALL_GLOBAL),
        constants.RULE_API_READ_GLOBAL,
        "List Listeners including resources owned by others",
        [{'method': 'GET', 'path': '/v2.0/lbaas/listeners'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_POST),
        constants.RULE_API_WRITE,
        "Create a Listener",
        [{'method': 'POST', 'path': '/v2.0/lbaas/listeners'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_GET_ONE),
        constants.RULE_API_READ,
        "Show Listener details",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/listeners/{listener_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_PUT),
        constants.RULE_API_WRITE,
        "Update a Listener",
        [{'method': 'PUT',
          'path': '/v2.0/lbaas/listeners/{listener_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_DELETE),
        constants.RULE_API_WRITE,
        "Remove a Listener",
        [{'method': 'DELETE',
          'path': '/v2.0/lbaas/listeners/{listener_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_LISTENER,
                                    action=constants.RBAC_GET_STATS),
        constants.RULE_API_READ,
        "Show Listener statistics",
        [{'method': 'GET',
          'path': '/v2.0/lbaas/listeners/{listener_id}/stats'}]
    ),
]


def list_rules():
    return rules
