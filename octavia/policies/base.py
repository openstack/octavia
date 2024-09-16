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

    # API access methods
    #
    # These are the only rules that should be applied to API endpoints.

    policy.RuleDefault(
        name='load-balancer:read',
        check_str='rule:load-balancer:observer_and_owner or '
                  'rule:load-balancer:global_observer or '
                  'rule:load-balancer:member_and_owner or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:read-global',
        check_str='rule:load-balancer:global_observer or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:write',
        check_str='rule:load-balancer:member_and_owner or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:read-quota',
        check_str='rule:load-balancer:observer_and_owner or '
                  'rule:load-balancer:global_observer or '
                  'rule:load-balancer:member_and_owner or '
                  'rule:load-balancer:quota-admin or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:read-quota-global',
        check_str='rule:load-balancer:global_observer or '
                  'rule:load-balancer:quota-admin or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:write-quota',
        check_str='rule:load-balancer:quota-admin or '
                  'rule:load-balancer:admin',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),
]


def list_rules():
    return rules
