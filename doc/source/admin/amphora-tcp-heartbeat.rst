====================================================
Optional TCP transport of amphora heartbeat messages
====================================================

Amphorae normally send heartbeat messages in UDP packets to the health
manager. If the underlying network does not support fragmented UDP packets
large heartbeats may not arrive at the health manager. The message may
become large if the load balancer has many listeners and pool members.

To ensure that large heartbeat messages are not lost in such an environment
you may configure Octavia to let the amphorae switch to TCP transport
on a per-message basis.

Enable this feature by setting the threshold to a positive value:

.. code-block:: ini

   [health_manager]
   ...
   heartbeat_use_tcp_threshold = 8000

Heartbeat messages with 8000 bytes or more will then be sent via TCP, smaller
messages will be sent in a UDP packet. The TCP port number is the same as the
UDP port (default is port 5555).
The default value for ``heartbeat_use_tcp_threshold`` is -1, which disables
TCP transport for the heartbeat completely.

If you enable this option after an Octavia upgrade, you may need to rebuild
the amphora image so that the amphorae run a software version that supports
this feature.

To allow TCP heartbeat traffic from the amphora to the health manager some
additional rules to security groups and firewalls may be required:

* Security groups of amphorae must allow egress traffic to TCP port 5555.
* Any firewall protecting the interface on which the health manager listens
  must allow incoming TCP connections to port 5555.
