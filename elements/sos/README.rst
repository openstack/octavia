Element to install sosreport.

sosreport is a tool that collects information about a system.

The sos plugin for Octavia can gather information of installed packages, log
and configuration files for Octavia controller components and amphora agent.
The result is a generated report that can be used for troubleshooting. The
plugin redacts confidential data such as passwords, certificates and secrets.

At present sos only installs in Red Hat family images as the plugin does not
support other distributions.
