This directory contains the octavia devstack plugin.  To
configure the neutron load balancer with octavia, in the [[local|localrc]] section
you will need to enable the neutron-lbaas and octavia devstack plugins and enable
the LBaaS and octavia services by editing the [[local|localrc]] section of your
local.conf file.

1) Enable the plugin

To enable the octavia plugin, add a line of the form:

    enable_plugin octavia <GITURL> [GITREF]

where

    <GITURL> is the URL of an octavia repository
    [GITREF] is an optional git ref (branch/ref/tag).  The default is
             master.

For example

    enable_plugin octavia https://git.openstack.org/openstack/octavia master

2) Enable the LBaaS Version 2 and Octavia services

For example

    ENABLED_SERVICES+=q-lbaasv2,octavia,o-api,o-cw,o-hk,o-hm

For more information, see the "Externally Hosted Plugins" section of
http://docs.openstack.org/developer/devstack/plugins.html.
