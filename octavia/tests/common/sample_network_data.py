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
import collections


def create_iproute_ipv4_address(ip_address, broadcast_address, interface_name):
    """Returns a netlink/iproute (pyroute2) IPv4 address."""
    Stats = collections.namedtuple('Stats', ('qsize', 'delta', 'delay'))
    return (
        {'family': 2, 'prefixlen': 24, 'flags': 0, 'scope': 0, 'index': 2,
         'attrs': [('IFA_ADDRESS', ip_address), ('IFA_LOCAL', ip_address),
                   ('IFA_BROADCAST', broadcast_address),
                   ('IFA_LABEL', interface_name), ('IFA_FLAGS', 0),
                   ('IFA_CACHEINFO', {'ifa_preferred': 49256,
                                      'ifa_valid': 49256, 'cstamp': 1961,
                                      'tstamp': 73441020})],
         'header': {'length': 88, 'type': 20, 'flags': 2,
                    'sequence_number': 258, 'pid': 7590, 'error': None,
                    'stats': Stats(qsize=0, delta=0, delay=0)},
         'event': 'RTM_NEWADDR'},)


def create_iproute_ipv6_address(ip_address, interface_name):
    """Returns a netlink/iproute (pyroute2) IPv6 address."""
    Stats = collections.namedtuple('Stats', ('qsize', 'delta', 'delay'))
    return (
        {'family': 10, 'prefixlen': 64, 'flags': 0, 'scope': 0, 'index': 2,
         'attrs': [('IFA_CACHEINFO', {'ifa_preferred': 604503,
                                      'ifa_valid': 2591703, 'cstamp': 2038,
                                      'tstamp': 77073215}),
                   ('IFA_ADDRESS', '2001:db8:ffff:ffff:ffff:ffff:ffff:ffff'),
                   ('IFA_FLAGS', 768)],
         'header': {'length': 72, 'type': 20, 'flags': 2,
                    'sequence_number': 257, 'pid': 7590, 'error': None,
                    'stats': Stats(qsize=0, delta=0, delay=0)},
         'event': 'RTM_NEWADDR'},
        {'family': 10, 'prefixlen': 64, 'flags': 0, 'scope': 0, 'index': 2,
         'attrs': [('IFA_CACHEINFO', {'ifa_preferred': 604503,
                                      'ifa_valid': 2591703, 'cstamp': 2038,
                                      'tstamp': 77073215}),
                   ('IFA_ADDRESS', ip_address), ('IFA_FLAGS', 768)],
         'header': {'length': 72, 'type': 20, 'flags': 2,
                    'sequence_number': 257, 'pid': 7590, 'error': None,
                    'stats': Stats(qsize=0, delta=0, delay=0)},
         'event': 'RTM_NEWADDR'},)


def create_iproute_interface(interface_name):
    """Returns a netlink/iproute (pyroute2) interface."""
    Stats = collections.namedtuple('Stats', ('qsize', 'delta', 'delay'))
    return [{
        'family': 0, '__align': (), 'ifi_type': 1, 'index': 2, 'flags': 69699,
        'change': 0,
        'attrs': [('IFLA_TXQLEN', 1000), ('IFLA_IFNAME', interface_name),
                  ('IFLA_OPERSTATE', 'UP'), ('IFLA_LINKMODE', 0),
                  ('IFLA_MTU', 1500), ('IFLA_GROUP', 0),
                  ('IFLA_PROMISCUITY', 0), ('IFLA_NUM_TX_QUEUES', 1),
                  ('IFLA_GSO_MAX_SEGS', 65535),
                  ('IFLA_GSO_MAX_SIZE', 65536), ('IFLA_NUM_RX_QUEUES', 1),
                  ('IFLA_CARRIER', 1), ('IFLA_QDISC', 'fq_codel'),
                  ('IFLA_CARRIER_CHANGES', 2), ('IFLA_PROTO_DOWN', 0),
                  ('IFLA_CARRIER_UP_COUNT', 1),
                  ('IFLA_CARRIER_DOWN_COUNT', 1),
                  ('IFLA_MAP', {'mem_start': 0, 'mem_end': 0, 'base_addr': 0,
                                'irq': 0, 'dma': 0, 'port': 0}),
                  ('IFLA_ADDRESS', '52:54:00:cf:37:9e'),
                  ('IFLA_BROADCAST', 'ff:ff:ff:ff:ff:ff'),
                  ('IFLA_STATS64', {
                      'rx_packets': 756091, 'tx_packets': 780292,
                      'rx_bytes': 234846748, 'tx_bytes': 208583687,
                      'rx_errors': 0, 'tx_errors': 0, 'rx_dropped': 0,
                      'tx_dropped': 0, 'multicast': 0, 'collisions': 0,
                      'rx_length_errors': 0, 'rx_over_errors': 0,
                      'rx_crc_errors': 0, 'rx_frame_errors': 0,
                      'rx_fifo_errors': 0, 'rx_missed_errors': 0,
                      'tx_aborted_errors': 0, 'tx_carrier_errors': 0,
                      'tx_fifo_errors': 0, 'tx_heartbeat_errors': 0,
                      'tx_window_errors': 0, 'rx_compressed': 0,
                      'tx_compressed': 0}),
                  ('IFLA_STATS', {
                      'rx_packets': 756091, 'tx_packets': 780292,
                      'rx_bytes': 234846748, 'tx_bytes': 208583687,
                      'rx_errors': 0, 'tx_errors': 0, 'rx_dropped': 0,
                      'tx_dropped': 0, 'multicast': 0, 'collisions': 0,
                      'rx_length_errors': 0, 'rx_over_errors': 0,
                      'rx_crc_errors': 0, 'rx_frame_errors': 0,
                      'rx_fifo_errors': 0, 'rx_missed_errors': 0,
                      'tx_aborted_errors': 0, 'tx_carrier_errors': 0,
                      'tx_fifo_errors': 0, 'tx_heartbeat_errors': 0,
                      'tx_window_errors': 0, 'rx_compressed': 0,
                      'tx_compressed': 0}),
                  ('IFLA_XDP', '05:00:02:00:00:00:00:00'),
                  ('IFLA_AF_SPEC', {
                      'attrs': [
                          ('AF_INET', {
                              'dummy': 65664, 'forwarding': 1,
                              'mc_forwarding': 0, 'proxy_arp': 0,
                              'accept_redirects': 1,
                              'secure_redirects': 1,
                              'send_redirects': 1, 'shared_media': 1,
                              'rp_filter': 1, 'accept_source_route': 1,
                              'bootp_relay': 0, 'log_martians': 0,
                              'tag': 0, 'arpfilter': 0, 'medium_id': 0,
                              'noxfrm': 0, 'nopolicy': 0,
                              'force_igmp_version': 0, 'arp_announce': 0,
                              'arp_ignore': 0, 'promote_secondaries': 0,
                              'arp_accept': 0, 'arp_notify': 0,
                              'accept_local': 0, 'src_vmark': 0,
                              'proxy_arp_pvlan': 0, 'route_localnet': 0,
                              'igmpv2_unsolicited_report_interval': 10000,
                              'igmpv3_unsolicited_report_interval': 1000}),
                          ('AF_INET6', {
                              'attrs': [('IFLA_INET6_FLAGS', 2147483648),
                                        ('IFLA_INET6_CACHEINFO', {
                                            'max_reasm_len': 65535,
                                            'tstamp': 1859,
                                            'reachable_time': 30708,
                                            'retrans_time': 1000}),
                                        ('IFLA_INET6_CONF', {
                                            'forwarding': 1, 'hop_limit': 64,
                                            'mtu': 1500, 'accept_ra': 2,
                                            'accept_redirects': 1,
                                            'autoconf': 1,
                                            'dad_transmits': 1,
                                            'router_solicitations': 4294967295,
                                            'router_solicitation_interval':
                                                4000,
                                            'router_solicitation_delay': 1000,
                                            'use_tempaddr': 0,
                                            'temp_valid_lft': 604800,
                                            'temp_preferred_lft': 86400,
                                            'regen_max_retry': 3,
                                            'max_desync_factor': 600,
                                            'max_addresses': 16,
                                            'force_mld_version': 0,
                                            'accept_ra_defrtr': 1,
                                            'accept_ra_pinfo': 1,
                                            'accept_ra_rtr_pref': 1,
                                            'router_probe_interval': 60000,
                                            'accept_ra_rt_info_max_plen': 0,
                                            'proxy_ndp': 0,
                                            'optimistic_dad': 0,
                                            'accept_source_route': 0,
                                            'mc_forwarding': 0,
                                            'disable_ipv6': 0,
                                            'accept_dad': 1, 'force_tllao': 0,
                                            'ndisc_notify': 0}),
                                        ('IFLA_INET6_STATS', {
                                            'num': 37, 'inpkts': 57817,
                                            'inoctets': 144065857,
                                            'indelivers': 36758,
                                            'outforwdatagrams': 0,
                                            'outpkts': 35062,
                                            'outoctets': 4796485,
                                            'inhdrerrors': 0,
                                            'intoobigerrors': 0,
                                            'innoroutes': 0, 'inaddrerrors': 0,
                                            'inunknownprotos': 0,
                                            'intruncatedpkts': 0,
                                            'indiscards': 0,
                                            'outdiscards': 0, 'outnoroutes': 0,
                                            'reasmtimeout': 0, 'reasmreqds': 0,
                                            'reasmoks': 0, 'reasmfails': 0,
                                            'fragoks': 0, 'fragfails': 0,
                                            'fragcreates': 0,
                                            'inmcastpkts': 23214,
                                            'outmcastpkts': 6546,
                                            'inbcastpkts': 0,
                                            'outbcastpkts': 0,
                                            'inmcastoctets': 2255059,
                                            'outmcastoctets': 589090,
                                            'inbcastoctets': 0,
                                            'outbcastoctets': 0,
                                            'csumerrors': 0,
                                            'noectpkts': 57860,
                                            'ect1pkts': 0, 'ect0pkts': 0,
                                            'cepkts': 0}),
                                        ('IFLA_INET6_ICMP6STATS', {
                                            'num': 6, 'inmsgs': 2337,
                                            'inerrors': 0, 'outmsgs': 176,
                                            'outerrors': 0, 'csumerrors': 0}),
                                        ('IFLA_INET6_TOKEN', '::'),
                                        ('IFLA_INET6_ADDR_GEN_MODE', 0)]})]})],
        'header': {'length': 1304, 'type': 16, 'flags': 0,
                   'sequence_number': 261, 'pid': 7590, 'error': None,
                   'stats': Stats(qsize=0, delta=0, delay=0)},
        'state': 'up', 'event': 'RTM_NEWLINK'}]
