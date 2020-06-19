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
import fcntl
import socket
from struct import pack
from struct import unpack

from oslo_log import log as logging

from octavia.amphorae.backends.utils import network_namespace
from octavia.common import constants
from octavia.common import utils as common_utils

LOG = logging.getLogger(__name__)


def garp(interface, ip_address, net_ns=None):
    """Sends a gratuitous ARP for ip_address on the interface.

    :param interface: The interface name to send the GARP on.
    :param ip_address: The IP address to advertise in the GARP.
    :param net_ns: The network namespace to send the GARP from.
    :returns: None
    """
    ARP_ETHERTYPE = 0x0806
    BROADCAST_MAC = b'\xff\xff\xff\xff\xff\xff'

    # Get a socket, optionally inside a network namespace
    garp_socket = None
    if net_ns:
        with network_namespace.NetworkNamespace(net_ns):
            garp_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    else:
        garp_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)

    # Bind the socket with the ARP ethertype protocol
    garp_socket.bind((interface, ARP_ETHERTYPE))

    # Get the MAC address of the interface
    source_mac = garp_socket.getsockname()[4]

    garp_msg = [
        pack('!h', 1),                 # Hardware type ethernet
        pack('!h', 0x0800),            # Protocol type IPv4
        pack('!B', 6),                 # Hardware size
        pack('!B', 4),                 # Protocol size
        pack('!h', 1),                 # Opcode request
        source_mac,                    # Sender MAC address
        socket.inet_aton(ip_address),  # Sender IP address
        BROADCAST_MAC,                 # Target MAC address
        socket.inet_aton(ip_address)]  # Target IP address

    garp_ethernet = [
        BROADCAST_MAC,              # Ethernet destination
        source_mac,                 # Ethernet source
        pack('!h', ARP_ETHERTYPE),  # Ethernet type
        b''.join(garp_msg)]         # The GARP message

    garp_socket.send(b''.join(garp_ethernet))
    garp_socket.close()


def calculate_icmpv6_checksum(packet):
    """Calculate the ICMPv6 checksum for a packet.

    :param packet: The packet bytes to checksum.
    :returns: The checksum integer.
    """
    total = 0

    # Add up 16-bit words
    num_words = len(packet) // 2
    for chunk in unpack("!%sH" % num_words, packet[0:num_words * 2]):
        total += chunk

    # Add any left over byte
    if len(packet) % 2:
        total += packet[-1] << 8

    # Fold 32-bits into 16-bits
    total = (total >> 16) + (total & 0xffff)
    total += total >> 16
    return ~total + 0x10000 & 0xffff


def neighbor_advertisement(interface, ip_address, net_ns=None):
    """Sends a unsolicited neighbor advertisement for an ip on the interface.

    :param interface: The interface name to send the GARP on.
    :param ip_address: The IP address to advertise in the GARP.
    :param net_ns: The network namespace to send the GARP from.
    :returns: None
    """
    ALL_NODES_ADDR = 'ff02::1'
    SIOCGIFHWADDR = 0x8927

    # Get a socket, optionally inside a network namespace
    na_socket = None
    if net_ns:
        with network_namespace.NetworkNamespace(net_ns):
            na_socket = socket.socket(
                socket.AF_INET6, socket.SOCK_RAW,
                socket.getprotobyname(constants.IPV6_ICMP))
    else:
        na_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW,
                                  socket.getprotobyname(constants.IPV6_ICMP))

    # Per RFC 4861 section 4.4, the hop limit should be 255
    na_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 255)

    # Bind the socket with the source address
    na_socket.bind((ip_address, 0))

    # Get the byte representation of the MAC address of the interface
    # Note: You can't use getsockname() to get the MAC on this type of socket
    source_mac = fcntl.ioctl(na_socket.fileno(), SIOCGIFHWADDR, pack('256s',
                             bytes(interface, 'utf-8')))[18:24]

    # Get the byte representation of the source IP address
    source_ip_bytes = socket.inet_pton(socket.AF_INET6, ip_address)

    icmpv6_na_msg_prefix = [
        pack('!B', 136),         # ICMP Type Neighbor Advertisement
        pack('!B', 0)]           # ICMP Code
    icmpv6_na_msg_postfix = [
        pack('!I', 0xa0000000),  # Flags (Router, Override)
        source_ip_bytes,         # Target address
        pack('!B', 2),           # ICMPv6 option type target link-layer address
        pack('!B', 1),           # ICMPv6 option length
        source_mac]              # ICMPv6 option link-layer address

    # Calculate the ICMPv6 checksum
    icmpv6_pseudo_header = [
        source_ip_bytes,  # Source IP address
        socket.inet_pton(socket.AF_INET6, ALL_NODES_ADDR),  # Destination IP
        pack('!I', 58),   # IPv6 next header (ICMPv6)
        pack('!h', 32)]   # IPv6 payload length
    icmpv6_tmp_chksum = pack('!H', 0)  # Checksum are zeros for calculation
    tmp_chksum_msg = b''.join(icmpv6_pseudo_header + icmpv6_na_msg_prefix +
                              [icmpv6_tmp_chksum] + icmpv6_pseudo_header)
    checksum = pack('!H', calculate_icmpv6_checksum(tmp_chksum_msg))

    # Build the ICMPv6 unsolicitated neighbor advertisement
    icmpv6_msg = b''.join(icmpv6_na_msg_prefix + [checksum] +
                          icmpv6_na_msg_postfix)

    na_socket.sendto(icmpv6_msg, (ALL_NODES_ADDR, 0, 0, 0))
    na_socket.close()


def send_ip_advertisement(interface, ip_address, net_ns=None):
    """Send an address advertisement.

    This method will send either GARP (IPv4) or neighbor advertisements (IPv6)
    for the ip address specified.

    :param interface: The interface name to send the advertisement on.
    :param ip_address: The IP address to advertise.
    :param net_ns: The network namespace to send the advertisement from.
    :returns: None
    """
    try:
        if common_utils.is_ipv4(ip_address):
            garp(interface, ip_address, net_ns)
        elif common_utils.is_ipv6(ip_address):
            neighbor_advertisement(interface, ip_address, net_ns)
        else:
            LOG.error('Unknown IP version for address: "%s". Skipping',
                      ip_address)
    except Exception as e:
        LOG.warning('Unable to send address advertisement for address: "%s", '
                    'error: %s. Skipping', ip_address, str(e))
