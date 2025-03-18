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
from octavia.policies import advanced_rbac

rules = [

    # OpenStack keystone default roles

    # Project scoped Member
    policy.RuleDefault(
        name='project-member',
        check_str='role:member and '
                  'project_id:%(project_id)s',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    # Project scoped Reader
    policy.RuleDefault(
        name='project-reader',
        check_str='role:reader and '
                  'project_id:%(project_id)s',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='context_is_admin',
        check_str='role:admin',
        deprecated_rule=advanced_rbac.deprecated_context_is_admin,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    # API access roles
    policy.RuleDefault(
        name='load-balancer:admin',
        check_str='is_admin:True or '
                  'role:admin',
        deprecated_rule=advanced_rbac.deprecated_admin,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    # Note: 'is_admin:True' is a policy rule that takes into account the
    # auth_strategy == noauth configuration setting.
    # It is equivalent to 'rule:context_is_admin or {auth_strategy == noauth}'

    policy.RuleDefault(
        name='service',
        check_str='role:service',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:global_observer',
        check_str='role:admin',
        deprecated_rule=advanced_rbac.deprecated_global_observer,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:member_and_owner',
        check_str='rule:project-member',
        deprecated_rule=advanced_rbac.deprecated_member_and_owner,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:observer_and_owner',
        check_str='rule:project-reader',
        deprecated_rule=advanced_rbac.deprecated_observer_and_owner,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),

    policy.RuleDefault(
        name='load-balancer:quota-admin',
        check_str='role:admin',
        deprecated_rule=advanced_rbac.deprecated_quota_admin,
        scope_types=[constants.RBAC_SCOPE_PROJECT]),
]


def list_rules():
    return rules
