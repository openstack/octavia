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

from octavia.common import constants as consts


def write_nftable_vip_rules_file(interface_name, rules):
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00600
    mode = stat.S_IRUSR | stat.S_IWUSR

    # Create some strings shared on both code paths
    table_string = f'table {consts.NFT_FAMILY} {consts.NFT_VIP_TABLE} {{\n'
    chain_string = f'  chain {consts.NFT_VIP_CHAIN} {{\n'
    hook_string = (f'    type filter hook ingress device {interface_name} '
                   f'priority {consts.NFT_SRIOV_PRIORITY}; policy drop;\n')

    # Check if an existing rules file exists or we if need to create an
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
            file.write(f'flush chain {consts.NFT_FAMILY} '
                       f'{consts.NFT_VIP_TABLE} {consts.NFT_VIP_CHAIN}\n')
            file.write(table_string)
            file.write(chain_string)
            file.write(hook_string)
            # TODO(johnsom) Add peer ports here consts.HAPROXY_BASE_PEER_PORT
            #               and ip protocol 112 for VRRP. Need the peer address
            for rule in rules:
                file.write(f'    {rule}\n')
            file.write('  }\n')  # close the chain
            file.write('}\n')  # close the table
    else:  # No existing rules, create the "drop all" base rules
        with os.fdopen(
                os.open(consts.NFT_VIP_RULES_FILE, flags, mode), 'w') as file:
            file.write(table_string)
            file.write(chain_string)
            file.write(hook_string)
            # TODO(johnsom) Add peer ports here consts.HAPROXY_BASE_PEER_PORT
            #               and ip protocol 112 for VRRP. Need the peer address
            file.write('  }\n')  # close the chain
            file.write('}\n')  # close the table
