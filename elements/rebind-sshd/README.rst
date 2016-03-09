This element adds a post-BOUND script to the dhclient configuration to rebind
the ssh daemon to listen only on the management network interface.  The reason
for doing this is that some use cases require load balancing services on TCP
port 22 to work, and if SSH binds to the wildcard address on port 22, then
haproxy can't.

This also has the secondary benefit of making the amphora slightly more secure
as its SSH daemon will only respond to requests on the management network.
