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

from oslo_log import versionutils
from oslo_policy import policy

from octavia.common import constants

# Octavia specific Advanced RBAC rules

# The default is to not allow access unless the auth_strategy is 'noauth'.
# Users must be a member of one of the following roles to have access to
# the load-balancer API:
#
# role:load-balancer_observer
#     User has access to load-balancer read-only APIs
# role:load-balancer_global_observer
#     User has access to load-balancer read-only APIs including resources
#     owned by others.
# role:load-balancer_member
#     User has access to load-balancer read and write APIs
# role:load-balancer_admin
#     User is considered an admin for all load-balancer APIs including
#     resources owned by others.

deprecated_context_is_admin = policy.DeprecatedRule(
    name='context_is_admin',
    check_str='role:admin or '
              'role:load-balancer_admin',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

# Note: 'is_admin:True' is a policy rule that takes into account the
# auth_strategy == noauth configuration setting.
# It is equivalent to 'rule:context_is_admin or {auth_strategy == noauth}'

deprecated_admin = policy.DeprecatedRule(
    name='load-balancer:admin',
    check_str='is_admin:True or '
              'role:admin or '
              'role:load-balancer_admin',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

deprecated_global_observer = policy.DeprecatedRule(
    name='load-balancer:global_observer',
    check_str='role:load-balancer_global_observer',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

deprecated_member_and_owner = policy.DeprecatedRule(
    name='load-balancer:member_and_owner',
    check_str='role:load-balancer_member and '
              'rule:load-balancer:owner',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

deprecated_observer_and_owner = policy.DeprecatedRule(
    name='load-balancer:observer_and_owner',
    check_str='role:load-balancer_observer and '
              'rule:load-balancer:owner',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

deprecated_quota_admin = policy.DeprecatedRule(
    name='load-balancer:quota-admin',
    check_str='role:load-balancer_quota_admin',
    deprecated_reason=constants.RBAC_ROLES_DEPRECATED_REASON,
    deprecated_since=versionutils.deprecated.WALLABY,
)

rules = [
    policy.RuleDefault(
        name='load-balancer:owner',
        check_str='project_id:%(project_id)s',
        scope_types=[constants.RBAC_SCOPE_PROJECT]),
]


def list_rules():
    return rules
