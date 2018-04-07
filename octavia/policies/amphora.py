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
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_AMPHORA,
                                    action=constants.RBAC_GET_ALL),
        constants.RULE_API_ADMIN,
        "List Amphorae",
        [{'method': 'GET', 'path': '/v2/octavia/amphorae'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_AMPHORA,
                                    action=constants.RBAC_GET_ONE),
        constants.RULE_API_ADMIN,
        "Show Amphora details",
        [{'method': 'GET', 'path': '/v2/octavia/amphorae/{amphora_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_AMPHORA,
                                    action=constants.RBAC_PUT_FAILOVER),
        constants.RULE_API_ADMIN,
        "Failover Amphora",
        [{'method': 'PUT',
          'path': '/v2/octavia/amphorae/{amphora_id}/failover'}]
    ),
]


def list_rules():
    return rules
