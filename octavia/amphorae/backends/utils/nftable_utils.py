# Copyright 2024 Red Hat, Inc. All rights reserved.
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
import os
import stat
import subprocess

from octavia_lib.common import constants as lib_consts
from oslo_log import log as logging
from webob import exc

from octavia.amphorae.backends.utils import network_namespace
from octavia.common import constants as consts
from octavia.common import utils

LOG = logging.getLogger(__name__)


def write_nftable_vip_rules_file(interface_name, rules):
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00600
    mode = stat.S_IRUSR | stat.S_IWUSR

    # Create some strings shared on both code paths
    table_string = f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} {{\n'
    chain_string = f'  chain {consts.NFT_VIP_CHAIN} {{\n'
    hook_string = (f'    type filter hook ingress device {interface_name} '
                   f'priority {consts.NFT_SRIOV_PRIORITY}; policy drop;\n')

    # Allow ICMP destination unreachable for PMTUD
    icmp_string = '      icmp type destination-unreachable accept\n'
    # Allow the required neighbor solicitation/discovery PMTUD ICMPV6
    icmpv6_string = ('      icmpv6 type { nd-neighbor-solicit, '
                     'nd-router-advert, nd-neighbor-advert, packet-too-big, '
                     'destination-unreachable } accept\n')
    # Allow DHCP responses
    dhcp_string = '      udp sport 67 udp dport 68 accept\n'
    dhcpv6_string = '      udp sport 547 udp dport 546 accept\n'

    # Check if an existing rules file exists or we be need to create an
    # "drop all" file with no rules except for VRRP. If it exists, we should
    # not overwrite it here as it could be a reboot unless we were passed new
    # rules.
    if os.path.isfile(consts.NFT_VIP_RULES_FILE):
        if not rules:
            return
        with os.fdopen(
                os.open(consts.NFT_VIP_RULES_FILE, flags, mode), 'w') as file:
            # Clear the existing rules in the kernel
            # Note: The "nft -f" method is atomic, so clearing the rules will
            #       not leave the amphora exposed.
            # Create and delete the table to not get errors if the table does
            # not exist yet.
            file.write(f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} '
                       '{}\n')
            file.write(f'delete table {consts.NFT_FAMILY} '
                       f'{consts.NFT_VIP_TABLE}\n')
            file.write(table_string)
            file.write(chain_string)
            file.write(hook_string)
            file.write(icmp_string)
            file.write(icmpv6_string)
            file.write(dhcp_string)
            file.write(dhcpv6_string)
            for rule in rules:
                file.write(f'      {_build_rule_cmd(rule)}\n')
            file.write('  }\n')  # close the chain
            file.write('}\n')  # close the table
    else:  # No existing rules, create the "drop all" base rules
        with os.fdopen(
                os.open(consts.NFT_VIP_RULES_FILE, flags, mode), 'w') as file:
            file.write(table_string)
            file.write(chain_string)
            file.write(hook_string)
            file.write(icmp_string)
            file.write(icmpv6_string)
            file.write(dhcp_string)
            file.write(dhcpv6_string)
            file.write('  }\n')  # close the chain
            file.write('}\n')  # close the table


def _build_rule_cmd(rule):
    prefix_saddr = ''
    if rule[consts.CIDR] and rule[consts.CIDR] != '0.0.0.0/0':
        cidr_ip_version = utils.ip_version(rule[consts.CIDR].split('/')[0])
        if cidr_ip_version == 4:
            prefix_saddr = f'ip saddr {rule[consts.CIDR]} '
        elif cidr_ip_version == 6:
            prefix_saddr = f'ip6 saddr {rule[consts.CIDR]} '
        else:
            raise exc.HTTPBadRequest(explanation='Unknown ip version')

    if rule[consts.PROTOCOL] == lib_consts.PROTOCOL_SCTP:
        return f'{prefix_saddr}sctp dport {rule[consts.PORT]} accept'
    if rule[consts.PROTOCOL] == lib_consts.PROTOCOL_TCP:
        return f'{prefix_saddr}tcp dport {rule[consts.PORT]} accept'
    if rule[consts.PROTOCOL] == lib_consts.PROTOCOL_UDP:
        return f'{prefix_saddr}udp dport {rule[consts.PORT]} accept'
    if rule[consts.PROTOCOL] == consts.VRRP:
        return f'{prefix_saddr}ip protocol 112 accept'
    raise exc.HTTPBadRequest(explanation='Unknown protocol used in rules')


def load_nftables_file():
    cmd = [consts.NFT_CMD, '-o', '-f', consts.NFT_VIP_RULES_FILE]
    try:
        with network_namespace.NetworkNamespace(consts.AMPHORA_NAMESPACE):
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except Exception as e:
        if hasattr(e, 'output'):
            LOG.error(e.output)
        else:
            LOG.error(e)
        raise
