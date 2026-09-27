Octavia active-active distributor agent image element.

The image contains the distributor REST agent and a local Open vSwitch
instance. For development builds, point the source repository at the
active-active Octavia checkout:

.. sourcecode:: sh

    DIB_REPOLOCATION_distributor_agent=/root/osp_aio_helm/octavia-active-active
    DIB_REPOREF_distributor_agent=HEAD

The distributor agent receives its certificates and
``/etc/octavia/distributor-agent.conf`` through Nova config-drive. The image
must have a frontend interface attached by Nova; the agent resolves it by
MAC, creates one isolated bridge per load balancer, and persists OpenFlow
state under ``/var/lib/octavia/distributor``.
