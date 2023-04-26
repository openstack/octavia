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
import os
import stat

from oslo_config import cfg
import simplejson

from octavia.common import constants as consts

CONF = cfg.CONF


class InterfaceFile(object):
    def __init__(self, name, if_type,
                 mtu=None, addresses=None,
                 routes=None, rules=None, scripts=None):
        self.name = name
        self.if_type = if_type
        self.mtu = mtu
        self.addresses = addresses or []
        self.routes = routes or []
        self.rules = rules or []
        self.scripts = scripts or {
            consts.IFACE_UP: [],
            consts.IFACE_DOWN: []
        }

    @classmethod
    def get_extensions(cls):
        return [".json"]

    @classmethod
    def load(cls, fp):
        return simplejson.load(fp)

    @classmethod
    def dump(cls, obj):
        return simplejson.dumps(obj)

    @classmethod
    def from_file(cls, filename):
        with open(filename, encoding='utf-8') as fp:
            config = cls.load(fp)

        return InterfaceFile(**config)

    @classmethod
    def get_directory(cls):
        return (CONF.amphora_agent.agent_server_network_dir or
                consts.AMP_NET_DIR_TEMPLATE)

    @classmethod
    def get_host_routes(cls, routes, **kwargs):
        host_routes = []
        if routes:
            for hr in routes:
                route = {
                    consts.DST: hr['destination'],
                    consts.GATEWAY: hr['nexthop'],
                    consts.FLAGS: [consts.ONLINK]
                }
                route.update(kwargs)
                host_routes.append(route)
        return host_routes

    def write(self):
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        net_dir = self.get_directory()

        try:
            os.makedirs(net_dir)
        except OSError:
            pass

        interface_file = "{}.json".format(self.name)

        with os.fdopen(os.open(os.path.join(net_dir, interface_file),
                               flags, mode), 'w') as fp:
            interface = {
                consts.NAME: self.name,
                consts.IF_TYPE: self.if_type,
                consts.ADDRESSES: self.addresses,
                consts.ROUTES: self.routes,
                consts.RULES: self.rules,
                consts.SCRIPTS: self.scripts
            }
            if self.mtu:
                interface[consts.MTU] = self.mtu
            fp.write(self.dump(interface))


class VIPInterfaceFile(InterfaceFile):
    def __init__(self, name, mtu, vips, vrrp_info, fixed_ips, topology):

        super().__init__(name, if_type=consts.VIP, mtu=mtu)

        has_ipv4 = any(vip['ip_version'] == 4 for vip in vips)
        has_ipv6 = any(vip['ip_version'] == 6 for vip in vips)
        if vrrp_info:
            self.addresses.append({
                consts.ADDRESS: vrrp_info['ip'],
                consts.PREFIXLEN: vrrp_info['prefixlen']
            })
        else:
            if has_ipv4:
                self.addresses.append({
                    consts.DHCP: True
                })
            if has_ipv6:
                self.addresses.append({
                    consts.IPV6AUTO: True
                })

        ip_versions = set()

        for vip in vips:
            gateway = vip.get('gateway')
            ip_version = vip['ip_version']
            ip_versions.add(ip_version)

            if gateway:
                # Add default routes if there's a gateway
                self.routes.append({
                    consts.DST: (
                        "::/0" if ip_version == 6 else "0.0.0.0/0"),
                    consts.GATEWAY: gateway,
                    consts.FLAGS: [consts.ONLINK]
                })
                if topology != consts.TOPOLOGY_ACTIVE_STANDBY:
                    self.routes.append({
                        consts.DST: (
                            "::/0" if ip_version == 6 else "0.0.0.0/0"),
                        consts.GATEWAY: gateway,
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1,
                    })

            # In ACTIVE_STANDBY topology, keepalived configures the VIP
            # address. Keep track of it in the interface file but mark it with
            # a special flag so the amphora-interface would not add/delete
            # keepalived-maintained things.
            self.addresses.append({
                consts.ADDRESS: vip['ip_address'],
                consts.PREFIXLEN: 128 if ip_version == 6 else 32,
                # OCTAVIA_OWNED = False when this address is managed by another
                # tool (keepalived)
                consts.OCTAVIA_OWNED: (
                    topology != consts.TOPOLOGY_ACTIVE_STANDBY)
            })

            vip_cidr = ipaddress.ip_network(
                "{}/{}".format(vip['ip_address'], vip['prefixlen']),
                strict=False)
            self.routes.append({
                consts.DST: vip_cidr.exploded,
                consts.SCOPE: 'link'
            })

            if topology != consts.TOPOLOGY_ACTIVE_STANDBY:
                self.routes.append({
                    consts.DST: vip_cidr.exploded,
                    consts.PREFSRC: vip['ip_address'],
                    consts.SCOPE: 'link',
                    consts.TABLE: 1
                })
                self.rules.append({
                    consts.SRC: vip['ip_address'],
                    consts.SRC_LEN: 128 if ip_version == 6 else 32,
                    consts.TABLE: 1
                })

            self.routes.extend(self.get_host_routes(vip['host_routes']))
            self.routes.extend(self.get_host_routes(vip['host_routes'],
                                                    table=1))

        for fixed_ip in fixed_ips or ():
            ip_addr = fixed_ip['ip_address']
            cidr = fixed_ip['subnet_cidr']
            ip = ipaddress.ip_address(ip_addr)
            network = ipaddress.ip_network(cidr)
            prefixlen = network.prefixlen
            self.addresses.append({
                consts.ADDRESS: fixed_ip['ip_address'],
                consts.PREFIXLEN: prefixlen,
            })

            ip_versions.add(ip.version)

            gateway = fixed_ip.get('gateway')
            if gateway:
                # Add default routes if there's a gateway
                self.routes.append({
                    consts.DST: (
                        "::/0" if ip.version == 6 else "0.0.0.0/0"),
                    consts.GATEWAY: gateway,
                    consts.FLAGS: [consts.ONLINK]
                })
                if topology != consts.TOPOLOGY_ACTIVE_STANDBY:
                    self.routes.append({
                        consts.DST: (
                            "::/0" if ip.version == 6 else "0.0.0.0/0"),
                        consts.GATEWAY: gateway,
                        consts.FLAGS: [consts.ONLINK],
                        consts.TABLE: 1,
                    })

            host_routes = self.get_host_routes(
                fixed_ip.get('host_routes', []))
            self.routes.extend(host_routes)

        for ip_v in ip_versions:
            self.scripts[consts.IFACE_UP].append({
                consts.COMMAND: (
                    "/usr/local/bin/lvs-masquerade.sh add {} {}".format(
                        'ipv6' if ip_v == 6 else 'ipv4', name))
            })
            self.scripts[consts.IFACE_DOWN].append({
                consts.COMMAND: (
                    "/usr/local/bin/lvs-masquerade.sh delete {} {}".format(
                        'ipv6' if ip_v == 6 else 'ipv4', name))
            })


class PortInterfaceFile(InterfaceFile):
    def __init__(self, name, mtu, fixed_ips):
        super().__init__(name, if_type=consts.BACKEND, mtu=mtu)

        if fixed_ips:
            ip_versions = set()

            for fixed_ip in fixed_ips:
                ip_addr = fixed_ip['ip_address']
                cidr = fixed_ip['subnet_cidr']
                ip = ipaddress.ip_address(ip_addr)
                network = ipaddress.ip_network(cidr)
                prefixlen = network.prefixlen
                self.addresses.append({
                    consts.ADDRESS: fixed_ip['ip_address'],
                    consts.PREFIXLEN: prefixlen,
                })

                ip_versions.add(ip.version)

                host_routes = self.get_host_routes(
                    fixed_ip.get('host_routes', []))
                self.routes.extend(host_routes)
        else:
            ip_versions = {4, 6}

            self.addresses.append({
                consts.DHCP: True,
                consts.IPV6AUTO: True
            })

        for ip_version in ip_versions:
            self.scripts[consts.IFACE_UP].append({
                consts.COMMAND: (
                    "/usr/local/bin/lvs-masquerade.sh add {} {}".format(
                        'ipv6' if ip_version == 6 else 'ipv4', name))
            })
            self.scripts[consts.IFACE_DOWN].append({
                consts.COMMAND: (
                    "/usr/local/bin/lvs-masquerade.sh delete {} {}".format(
                        'ipv6' if ip_version == 6 else 'ipv4', name))
            })
