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

rules = [
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
    #     User is considered an admin for all load-balnacer APIs including
    #     resources owned by others.
    # role:admin
    #     User is admin to all APIs

    policy.RuleDefault('context_is_admin',
                       'role:admin or role:load-balancer_admin'),

    # Note: 'is_admin:True' is a policy rule that takes into account the
    # auth_strategy == noauth configuration setting.
    # It is equivalent to 'rule:context_is_admin or {auth_strategy == noauth}'

    policy.RuleDefault('load-balancer:owner', 'project_id:%(project_id)s'),

    # API access roles
    policy.RuleDefault('load-balancer:observer_and_owner',
                       'role:load-balancer_observer and '
                       'rule:load-balancer:owner'),

    policy.RuleDefault('load-balancer:global_observer',
                       'role:load-balancer_global_observer'),

    policy.RuleDefault('load-balancer:member_and_owner',
                       'role:load-balancer_member and '
                       'rule:load-balancer:owner'),

    # API access methods
    policy.RuleDefault('load-balancer:read',
                       'rule:load-balancer:observer_and_owner or '
                       'rule:load-balancer:global_observer or '
                       'rule:load-balancer:member_and_owner or is_admin:True'),

    policy.RuleDefault('load-balancer:read-global',
                       'rule:load-balancer:global_observer or '
                       'is_admin:True'),

    policy.RuleDefault('load-balancer:write',
                       'rule:load-balancer:member_and_owner or is_admin:True'),

    policy.RuleDefault('load-balancer:read-quota',
                       'rule:load-balancer:observer_and_owner or '
                       'rule:load-balancer:global_observer or '
                       'rule:load-balancer:member_and_owner or '
                       'role:load-balancer_quota_admin or '
                       'is_admin:True'),

    policy.RuleDefault('load-balancer:read-quota-global',
                       'rule:load-balancer:global_observer or '
                       'role:load-balancer_quota_admin or '
                       'is_admin:True'),

    policy.RuleDefault('load-balancer:write-quota',
                       'role:load-balancer_quota_admin or is_admin:True'),
]


def list_rules():
    return rules
