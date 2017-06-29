================
Octavia Policies
================

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
        User is considered an admin for all load-balnacer APIs including
        resources owned by others.

    role:admin
        User is admin to all APIs.

.. note::

    'is_admin:True' is a policy rule that takes into account the
    auth_strategy == noauth configuration setting.
    It is equivalent to 'rule:context_is_admin or {auth_strategy == noauth}'
    if that would be valid syntax.

An alternate policy file has been provided in octavia/etc/policy called
admin_or_owner-policy.json that removes the load-balancer RBAC role
requirement. Please see the README.rst in that directory for more information.

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

Default Octavia Policies
------------------------

.. literalinclude:: _static/octavia.policy.yaml.sample
