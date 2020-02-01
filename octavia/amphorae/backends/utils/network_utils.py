# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import ipaddress

import pyroute2

from octavia.common import exceptions


def _find_interface(ip_address, rtnl_api, normalized_addr):
    """Find the interface using a routing netlink API.

    :param ip_address: The IP address to search with.
    :param rtnl_api: A pyroute2 rtnl_api instance. (IPRoute, NetNS, etc.)
    :returns: The interface name if found, None if not found.
    :raises exceptions.InvalidIPAddress: Invalid IP address provided.
    """
    for addr in rtnl_api.get_addr(address=ip_address):
        # Save the interface index as IPv6 records don't list a textual
        # interface
        interface_idx = addr['index']
        # Search through the attributes of each address record
        for attr in addr['attrs']:
            # Look for the attribute name/value pair for the address
            if attr[0] == 'IFA_ADDRESS':
                # Compare the normalized address with the address we are
                # looking for.  Since we have matched the name above, attr[1]
                # is the address value
                if normalized_addr == ipaddress.ip_address(attr[1]).compressed:
                    # Lookup the matching interface name by getting the
                    # interface with the index we found in the above address
                    # search
                    lookup_int = rtnl_api.get_links(interface_idx)
                    # Search through the attributes of the matching interface
                    # record
                    for int_attr in lookup_int[0]['attrs']:
                        # Look for the attribute name/value pair that includes
                        # the interface name
                        if int_attr[0] == 'IFLA_IFNAME':
                            # Return the matching interface name that is in
                            # int_attr[1] for the matching interface attribute
                            # name
                            return int_attr[1]
    # We didn't find an interface with that IP address.
    return None


def get_interface_name(ip_address, net_ns=None):
    """Gets the interface name from an IP address.

    :param ip_address: The IP address to lookup.
    :param net_ns: The network namespace to find the interface in.
    :returns: The interface name.
    :raises exceptions.InvalidIPAddress: Invalid IP address provided.
    :raises octavia.common.exceptions.NotFound: No interface was found.
    """
    # We need to normalize the address as IPv6 has multiple representations
    # fe80:0000:0000:0000:f816:3eff:fef2:2058 == fe80::f816:3eff:fef2:2058
    try:
        normalized_addr = ipaddress.ip_address(ip_address).compressed
    except ValueError:
        raise exceptions.InvalidIPAddress(ip_addr=ip_address)

    if net_ns:
        with pyroute2.NetNS(net_ns) as rtnl_api:
            interface = _find_interface(ip_address, rtnl_api, normalized_addr)
    else:
        with pyroute2.IPRoute() as rtnl_api:
            interface = _find_interface(ip_address, rtnl_api, normalized_addr)
    if interface is not None:
        return interface
    raise exceptions.NotFound(resource='IP address', id=ip_address)
