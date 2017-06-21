===========================
Octavia Sample Policy Files
===========================

The sample policy.json files described here can be copied into
/etc/octavia/policy.json to override the default RBAC policy for Octavia.

admin_or_owner-policy.json
--------------------------
This policy file disables the requirement for load-balancer service users to
have one of the load-balancer:* roles.  It provides a similar policy to
legacy OpenStack policies where any user or admin has access to load-balancer
resources that they own.  Users with the admin role has access to all
load-balancer resources, whether they own them or not.
