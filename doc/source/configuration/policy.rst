================
Octavia Policies
================

.. warning::

   JSON formatted policy file is deprecated since Octavia 8.0.0 (Wallaby).
   This `oslopolicy-convert-json-to-yaml`__ tool will migrate your existing
   JSON-formatted policy file to YAML in a backward-compatible way.

.. __: https://docs.openstack.org/oslo.policy/latest/cli/oslopolicy-convert-json-to-yaml.html

.. _Keystone Default Roles: https://docs.openstack.org/keystone/latest/admin/service-api-protection.html

Octavia Advanced Role Based Access Control (RBAC)
-------------------------------------------------

Octavia adopted the "Advanced Role Based Access Control (RBAC)" default
policies in the Pike release of OpenStack. This provides a fine-grained default
access control policy for the Octavia service.

The Octavia Advanced RBAC goes beyond the OpenStack legacy RBAC policies of
allowing "owners and admins" full access to all services. It also provides a
more fine-grained RBAC policy than the newer `Keystone Default Roles`_ .

The default policy is to not allow access unless the auth_strategy is 'noauth'.

Users must be a member of one of the following roles to have access to
the load-balancer API:

.. glossary::

    role:load-balancer_observer
        User has access to load-balancer read-only APIs.

    role:load-balancer_global_observer
        User has access to load-balancer read-only APIs including resources
        owned by others.

    role:load-balancer_member
        User has access to load-balancer read and write APIs.

    role:load-balancer_quota_admin
        User is considered an admin for quota APIs only.

    role:load-balancer_admin
        User is considered an admin for all load-balancer APIs including
        resources owned by others.

    role:admin and system_scope:all
        User is admin to all service APIs, including Octavia.

.. note::

    'is_admin:True' is a policy rule that takes into account the
    auth_strategy == noauth configuration setting.
    It is equivalent to 'rule:context_is_admin or {auth_strategy == noauth}'
    if that would be valid syntax.

These roles are in addition to the `Keystone Default Roles`_:

* role:reader
* role:member

In addition, the Octavia API supports Keystone scoped tokens. When enabled
in Oslo Policy, users will need to present a token scoped to either the
"system" or a specific "project". See the section `Upgrade Considerations`_
for more information.

See the section `Managing Octavia User Roles`_ for examples and advice on how
to apply these RBAC policies in production.

Legacy Admin or Owner Policy Override File
------------------------------------------

An alternate policy file has been provided in octavia/etc/policy called
admin_or_owner-policy.yaml that removes the load-balancer RBAC role
requirement. Please see the README.rst in that directory for more information.

This will drop the role requirements to allow access to all with the "admin"
role or if the user is a member of the project that created the resource. All
users have access to the Octavia API to create and manage load balancers
under their project.

OpenStack Default Roles Policy Override File
--------------------------------------------

An alternate policy file has been provided in octavia/etc/policy called
keystone_default_roles-policy.yaml that removes the load-balancer RBAC role
requirement. Please see the README.rst in that directory for more information.

This policy will honor the following `Keystone Default Roles`_ in the Octavia
API:

* Admin
* Project scoped - Reader
* Project scoped - Member

In addition, there is an alternate policy file that enables system scoped
tokens checking called keystone_default_roles_scoped-policy.yaml.

* System scoped - Admin
* System scoped - Reader
* Project scoped - Reader
* Project scoped - Member


Managing Octavia User Roles
---------------------------

User and group roles are managed through the Keystone (identity) project.

A role can be added to a user with the following command::

    openstack role add --project <project name or id> --user <user name or id> <role>

An example where user "jane", in the "engineering" project, gets a new role
"load-balancer_member"::

    openstack role add --project engineering --user jane load-balancer_member

Keystone Group Roles
~~~~~~~~~~~~~~~~~~~~

Roles can also be assigned to `Keystone groups
<https://docs.openstack.org/keystone/latest/admin/identity-concepts.html>`_.
This can simplify the management of user roles greatly.

For example, your cloud may have a "users" group defined in Keystone. This
group is set up to have all of the regular users of your cloud as a member.
If you want all of your users to have access to the load balancing service
Octavia, you could add the "load-balancer_member" role to the "users" group::

    openstack role add --domain default --group users load-balancer_member

Upgrade Considerations
----------------------

Starting with the Wallaby release of Octavia, Keystone token scopes and
default roles can be enforced. By default, in the Wallaby release, `Oslo Policy
<https://docs.openstack.org/oslo.policy/latest>`_
will not be enforcing these new roles and scopes. However, at some point in the
future they may become the default. You may want to enable them now to be ready
for the later transition. This section will describe those settings.

The Oslo Policy project defines two configuration settings, among others, that
can be set in the Octavia configuration file to influence how policies are
handled in the Octavia API. Those two settings are `enforce_scope
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_scope>`_ and `enforce_new_defaults
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_new_defaults>`_.

[oslo_policy] enforce_scope
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keystone has introduced the concept of `token scopes
<https://docs.openstack.org/keystone/latest/admin/tokens-overview.html#authorization-scopes>`_.
Currently, Oslo Policy defaults to not enforce the scope validation of a
token for backward compatibility reasons.

The Octavia API supports enforcing the Keystone token scopes as of the Wallaby
release. If you are ready to start enforcing the Keystone token scope in the
Octavia API you can add the following setting to your Octavia API configuration
file::

    [oslo_policy]
    enforce_scope = True

Currently the primary effect of this setting is to allow a system scoped
admin token when performing administrative API calls to the Octavia API.
It will also allow system scoped reader tokens to have the equivalent of the
load-balancer_global_observer role.

The Octavia API already enforces the project scoping in Keystone tokens.

[oslo_policy] enforce_new_defaults
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Octavia Wallaby release added support for `Keystone Default Roles`_ in
the default policies. The previous Octavia Advanced RBAC policies have now
been deprecated in favor of the new policies requiring one of the new
`Keystone Default Roles`_.
Currently, Oslo Policy defaults to using the deprecated policies that do not
require the new `Keystone Default Roles`_ for backward compatibility.

The Octavia API supports requiring these new `Keystone Default Roles`_ as of
the Wallaby release. If you are ready to start requiring these roles you can
enable the new policies by adding the following setting to your Octavia API
configuration file::

    [oslo_policy]
    enforce_new_defaults = True

When the new default policies are enabled in the Octavia API, users with the
load-balancer:observer role will also require the Keystone default role of
"role:reader". Users with the load-balancer:member role will also require
the Keystone default role of "role:member".

Sample File Generation
----------------------

To generate a sample policy.yaml file from the Octavia defaults, run the
oslo policy generation script::

    oslopolicy-sample-generator
    --config-file etc/policy/octavia-policy-generator.conf
    --output-file policy.yaml.sample

Merged File Generation
----------------------

This will output a policy file which includes all registered policy defaults
and all policies configured with a policy file. This file shows the effective
policy in use by the project::

    oslopolicy-policy-generator
    --config-file etc/policy/octavia-policy-generator.conf

This tool uses the output_file path from the config-file.

List Redundant Configurations
-----------------------------

This will output a list of matches for policy rules that are defined in a
configuration file where the rule does not differ from a registered default
rule. These are rules that can be removed from the policy file with no change
in effective policy::

    oslopolicy-list-redundant
    --config-file etc/policy/octavia-policy-generator.conf

Default Octavia Policies - API Effective Rules
----------------------------------------------

This section will list the RBAC rules the Octavia API will use followed by a
list of the roles that will be allowed access.

Without `enforce_scope
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_scope>`_ and `enforce_new_defaults
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_new_defaults>`_:

* load-balancer:read

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_member and <project member>
  * load-balancer_observer and <project member>
  * role:admin

* load-balancer:read-global

  * load-balancer_admin
  * load-balancer_global_observer
  * role:admin

* load-balancer:write

  * load-balancer_admin
  * load-balancer_member and <project member>
  * role:admin

* load-balancer:read-quota

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_member and <project member>
  * load-balancer_observer and <project member>
  * load-balancer_quota_admin
  * role:admin

* load-balancer:read-quota-global

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_quota_admin
  * role:admin

* load-balancer:write-quota

  * load-balancer_admin
  * load-balancer_quota_admin
  * role:admin

With `enforce_scope
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_scope>`_ and `enforce_new_defaults
<https://docs.openstack.org/oslo.policy/latest/configuration/index.html#oslo_policy.enforce_new_defaults>`_:

* load-balancer:read

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_member and <project member> and role:member
  * load-balancer_observer and <project member> and role:reader
  * role:admin and system_scope:all
  * role:reader and system_scope:all

* load-balancer:read-global

  * load-balancer_admin
  * load-balancer_global_observer
  * role:admin and system_scope:all
  * role:reader and system_scope:all

* load-balancer:write

  * load-balancer_admin
  * load-balancer_member and <project member> and role:member
  * role:admin and system_scope:all

* load-balancer:read-quota

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_member and <project member> and role:member
  * load-balancer_observer and <project member> and role:reader
  * load-balancer_quota_admin
  * role:admin and system_scope:all
  * role:reader and system_scope:all

* load-balancer:read-quota-global

  * load-balancer_admin
  * load-balancer_global_observer
  * load-balancer_quota_admin
  * role:admin and system_scope:all
  * role:reader and system_scope:all

* load-balancer:write-quota

  * load-balancer_admin
  * load-balancer_quota_admin
  * role:admin and system_scope:all

Default Octavia Policies - Generated From The Octavia Code
----------------------------------------------------------

.. literalinclude:: _static/octavia.policy.yaml.sample
