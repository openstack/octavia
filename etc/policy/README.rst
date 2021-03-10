===========================
Octavia Sample Policy Files
===========================

The sample policy.yaml files described here can be copied into
/etc/octavia/policy.yaml to override the default RBAC policy for Octavia.

See the `Octavia Policy Guide <https://docs.openstack.org/octavia/latest/configuration/policy.html>`_ for more information about these policy override files.

admin_or_owner-policy.yaml
--------------------------
This policy file disables the requirement for load-balancer service users to
have one of the load-balancer:* roles.  It provides a similar policy to
legacy OpenStack policies where any user or admin has access to load-balancer
resources that they own.  Users with the admin role has access to all
load-balancer resources, whether they own them or not.

keystone_default_roles-policy.yaml
----------------------------------
This policy file disables the requirement for load-balancer service users to
have one of the load-balancer:* roles.

This policy will honor the following Keystone default roles in the Octavia API:

* System scoped - Admin
* System scoped - Reader
* Project scoped - Reader
* Project scoped - Member
