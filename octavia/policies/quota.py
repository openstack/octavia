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
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_GET_ALL),
        constants.RULE_API_READ_QUOTA,
        "List Quotas",
        [{'method': 'GET', 'path': '/v2/lbaas/quotas'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_GET_ALL_GLOBAL),
        constants.RULE_API_READ_QUOTA_GLOBAL,
        "List Quotas including resources owned by others",
        [{'method': 'GET', 'path': '/v2/lbaas/quotas'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_GET_ONE),
        constants.RULE_API_READ_QUOTA,
        "Show Quota details",
        [{'method': 'GET',
          'path': '/v2/lbaas/quotas/{project_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_PUT),
        constants.RULE_API_WRITE_QUOTA,
        "Update a Quota",
        [{'method': 'PUT',
          'path': '/v2/lbaas/quotas/{project_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_DELETE),
        constants.RULE_API_WRITE_QUOTA,
        "Reset a Quota",
        [{'method': 'DELETE',
          'path': '/v2/lbaas/quotas/{project_id}'}]
    ),
    policy.DocumentedRuleDefault(
        '{rbac_obj}{action}'.format(rbac_obj=constants.RBAC_QUOTA,
                                    action=constants.RBAC_GET_DEFAULTS),
        constants.RULE_API_READ_QUOTA,
        "Show Default Quota for a Project",
        [{'method': 'GET',
          'path': '/v2/lbaas/quotas/{project_id}/default'}]
    ),
]


def list_rules():
    return rules
