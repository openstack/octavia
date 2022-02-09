#!/bin/bash
#
# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

set -e

usage() {
    echo
    echo "Usage: $(basename "$0") [add|delete] [ipv4|ipv6] <interface>"
    echo
    exit 1
}

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    usage
fi

if [ "$1" == "add" ]; then

    if [ -x "$(sudo bash -c 'command -v nft')" ]; then
        # Note: inet for nat requires a 5.2 or newer kernel.
        if [ "$2" == "ipv4" ]; then
            nft add table ip octavia-ipv4
            nft add chain ip octavia-ipv4 ip-udp-masq { type nat hook postrouting priority 100\;}
            nft add rule ip octavia-ipv4 ip-udp-masq oifname "$3" meta l4proto udp masquerade
            nft add chain ip octavia-ipv4 ip-sctp-masq { type nat hook postrouting priority 100\;}
            nft add rule ip octavia-ipv4 ip-sctp-masq oifname "$3" meta l4proto sctp masquerade
            nft -- add chain ip octavia-ipv4 prerouting { type filter hook prerouting priority -300 \; }
            nft add rule ip octavia-ipv4 prerouting iifname "$3" meta l4proto tcp notrack
            nft -- add chain ip octavia-ipv4 output { type filter hook output priority -300 \; }
            nft add rule ip octavia-ipv4 output oifname "$3" meta l4proto tcp notrack

        elif [ "$2" == "ipv6" ]; then
            nft add table ip6 octavia-ipv6
            nft add chain ip6 octavia-ipv6 ip6-udp-masq { type nat hook postrouting priority 100\;}
            nft add rule ip6 octavia-ipv6 ip6-udp-masq oifname "$3" meta l4proto udp masquerade
            nft add chain ip6 octavia-ipv6 ip6-sctp-masq { type nat hook postrouting priority 100\;}
            nft add rule ip6 octavia-ipv6 ip6-sctp-masq oifname "$3" meta l4proto sctp masquerade
            nft -- add chain ip6 octavia-ipv6 prerouting { type filter hook prerouting priority -300 \; }
            nft add rule ip6 octavia-ipv6 prerouting iifname "$3" meta l4proto tcp notrack
            nft -- add chain ip6 octavia-ipv6 output { type filter hook output priority -300 \; }
            nft add rule ip6 octavia-ipv6 output oifname "$3" meta l4proto tcp notrack
        else
            usage
        fi

    else # nft not found, fall back to iptables
        if [ "$2" == "ipv4" ]; then
            /sbin/iptables -t nat -A POSTROUTING -p udp -o $3 -j MASQUERADE
            /sbin/iptables -t nat -A POSTROUTING -p sctp -o $3 -j MASQUERADE

            /sbin/iptables -t raw -A PREROUTING -p tcp -i $3 -j NOTRACK
            /sbin/iptables -t raw -A OUTPUT -p tcp -o $3 -j NOTRACK
        elif [ "$2" == "ipv6" ]; then
            /sbin/ip6tables -t nat -A POSTROUTING -p udp -o $3 -j MASQUERADE
            /sbin/ip6tables -t nat -A POSTROUTING -p sctp -o $3 -j MASQUERADE

            /sbin/ip6tables -t raw -A PREROUTING -p tcp -i $3 -j NOTRACK
            /sbin/ip6tables -t raw -A OUTPUT -p tcp -o $3 -j NOTRACK
        else
            usage
        fi
    fi

elif [ "$1" == "delete" ]; then

    if [ -x "$(sudo bash -c 'command -v nft')" ]; then
        if [ "$2" == "ipv4" ]; then
            nft flush chain ip octavia-ipv4 ip-udp-masq
            nft delete chain ip octavia-ipv4 ip-udp-masq
            nft flush chain ip octavia-ipv4 ip-sctp-masq
            nft delete chain ip octavia-ipv4 ip-sctp-masq
            nft flush chain ip octavia-ipv4 prerouting
            nft delete chain ip octavia-ipv4 prerouting
            nft flush chain ip octavia-ipv4 output
            nft delete chain ip octavia-ipv4 output
        elif [ "$2" == "ipv6" ]; then
            nft flush chain ip6 octavia-ipv6 ip-udp-masq
            nft delete chain ip6 octavia-ipv6 ip-udp-masq
            nft flush chain ip6 octavia-ipv6 ip-sctp-masq
            nft delete chain ip6 octavia-ipv6 ip-sctp-masq
            nft flush chain ip6 octavia-ipv6 prerouting
            nft delete chain ip6 octavia-ipv6 prerouting
            nft flush chain ip6 octavia-ipv6 output
            nft delete chain ip6 octavia-ipv6 output
        else
            usage
        fi

    else # nft not found, fall back to iptables
        if [ "$2" == "ipv4" ]; then
            /sbin/iptables -t nat -D POSTROUTING -p udp -o $3 -j MASQUERADE
            /sbin/iptables -t nat -D POSTROUTING -p sctp -o $3 -j MASQUERADE
            /sbin/iptables -t raw -D PREROUTING -p tcp -i $3 -j NOTRACK
            /sbin/iptables -t raw -D OUTPUT -p tcp -o $3 -j NOTRACK
        elif [ "$2" == "ipv6" ]; then
            /sbin/ip6tables -t nat -D POSTROUTING -p udp -o $3 -j MASQUERADE
            /sbin/ip6tables -t nat -D POSTROUTING -p sctp -o $3 -j MASQUERADE
            /sbin/ip6tables -t raw -D PREROUTING -p tcp -i $3 -j NOTRACK
            /sbin/ip6tables -t raw -D OUTPUT -p tcp -o $3 -j NOTRACK
        else
            usage
        fi
    fi
else
    usage
fi
