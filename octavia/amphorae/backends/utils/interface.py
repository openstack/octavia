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

import errno
import ipaddress
import os
import socket
import subprocess
import time

from oslo_config import cfg
from oslo_log import log as logging
import pyroute2
# pylint: disable=no-name-in-module
from pyroute2.netlink.rtnl import ifaddrmsg
# pylint: disable=no-name-in-module
from pyroute2.netlink.rtnl import rt_proto

from octavia.amphorae.backends.utils import interface_file
from octavia.common import constants as consts
from octavia.common import exceptions

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class InterfaceController(object):
    ADD = 'add'
    DELETE = 'delete'
    SET = 'set'
    FLUSH = 'flush'

    TENTATIVE_WAIT_INTERVAL = .2
    TENTATIVE_WAIT_TIMEOUT = 30

    def interface_file_list(self):
        net_dir = interface_file.InterfaceFile.get_directory()

        for f in os.listdir(net_dir):
            for ext in interface_file.InterfaceFile.get_extensions():
                if f.endswith(ext):
                    yield os.path.join(net_dir, f)

    def list(self):
        interfaces = {}
        for f in self.interface_file_list():
            iface = interface_file.InterfaceFile.from_file(f)
            interfaces[iface.name] = iface
        return interfaces

    def _family(self, address):
        return (socket.AF_INET6
                if ipaddress.ip_network(address, strict=False).version == 6
                else socket.AF_INET)

    def _ipr_command(self, method, *args,
                     retry_on_invalid_argument=False,
                     retry_interval=.2,
                     raise_on_error=True,
                     max_retries=20,
                     **kwargs):

        for dummy in range(max_retries + 1):
            try:
                method(*args, **kwargs)
                break
            except pyroute2.NetlinkError as e:
                if e.code == errno.EINVAL and retry_on_invalid_argument:
                    LOG.debug("Retrying after %f sec.", retry_interval)
                    time.sleep(retry_interval)
                    continue

                if args:
                    command = args[0]
                    if command == self.ADD and e.code != errno.EEXIST:
                        args_str = ', '.join(str(a) for a in args)
                        kwargs_str = ', '.join(
                            f'{k}={v}' for k, v in kwargs.items()
                        )
                        msg = (f"Cannot call {method.__name__} {command} "
                               f"with ({args_str}, {kwargs_str}): {e}")
                        if raise_on_error:
                            raise exceptions.AmphoraNetworkConfigException(msg)
                        LOG.error(msg)
                return
        else:
            msg = "Cannot call {} {} (with {}) after {} retries.".format(
                method.__name__, args, kwargs, max_retries)
            if raise_on_error:
                raise exceptions.AmphoraNetworkConfigException(msg)
            LOG.error(msg)

    def _dhclient_up(self, interface_name):
        cmd = ["/sbin/dhclient",
               "-lf",
               "/var/lib/dhclient/dhclient-{}.leases".format(
                   interface_name),
               "-pf",
               "/run/dhclient-{}.pid".format(interface_name),
               interface_name]
        LOG.debug("Running '%s'", cmd)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def _dhclient_down(self, interface_name):
        cmd = ["/sbin/dhclient",
               "-r",
               "-lf",
               "/var/lib/dhclient/dhclient-{}.leases".format(
                   interface_name),
               "-pf",
               "/run/dhclient-{}.pid".format(interface_name),
               interface_name]
        LOG.debug("Running '%s'", cmd)
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def _ipv6auto_up(self, interface_name):
        # Set values to enable SLAAC on interface_name
        # accept_ra is set to 2 to accept router advertisements if forwarding
        # is enabled on the interface
        for key, value in (('accept_ra', 2),
                           ('autoconf', 1)):
            cmd = ["/sbin/sysctl",
                   "-w",
                   "net.ipv6.conf.{}.{}={}".format(interface_name,
                                                   key, value)]
            LOG.debug("Running '%s'", cmd)
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def _ipv6auto_down(self, interface_name):
        for key, value in (('accept_ra', 0),
                           ('autoconf', 0)):
            cmd = ["/sbin/sysctl",
                   "-w",
                   "net.ipv6.conf.{}.{}={}".format(interface_name,
                                                   key, value)]
            LOG.debug("Running '%s'", cmd)
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)

    def _wait_tentative(self, ipr, idx):
        start = time.time()
        while time.time() - start < self.TENTATIVE_WAIT_TIMEOUT:
            addrs = ipr.get_addr(idx)
            has_tentative = [
                True
                for addr in addrs
                if (addr[consts.FAMILY] == socket.AF_INET6 and
                    addr['flags'] & ifaddrmsg.IFA_F_TENTATIVE)]
            if not has_tentative:
                return
            time.sleep(self.TENTATIVE_WAIT_INTERVAL)
        LOG.warning("Some IPV6 addresses remain still in 'tentative' state "
                    "after %d seconds.", self.TENTATIVE_WAIT_TIMEOUT)

    def _normalize_ip_address(self, address):
        if not address:
            return None
        ip_address = ipaddress.ip_address(address)
        return ip_address.compressed

    def _normalize_ip_network(self, address):
        if not address:
            return None
        ip_network = ipaddress.ip_network(address, strict=False)
        return ip_network.compressed

    def up(self, interface):
        LOG.info("Setting interface %s up", interface.name)

        with pyroute2.IPRoute() as ipr:
            idx = ipr.link_lookup(ifname=interface.name)[0]

            # Workaround for https://github.com/PyCQA/pylint/issues/8497
            # pylint: disable=E1136, E1121
            link = ipr.get_links(idx)[0]
            current_state = link.get(consts.STATE)

            if current_state == consts.IFACE_DOWN:
                self._ipr_command(ipr.link, self.SET, index=idx,
                                  state=consts.IFACE_UP, mtu=interface.mtu)
                for address in interface.addresses:
                    if address.get(consts.DHCP):
                        self._dhclient_up(interface.name)
                    if address.get(consts.IPV6AUTO):
                        self._ipv6auto_up(interface.name)

            self._addresses_up(interface, ipr, idx)
            self._routes_up(interface, ipr, idx)
            # only the vip port updates the rules
            if interface.if_type == consts.VIP:
                self._rules_up(interface, ipr, idx)

            self._scripts_up(interface, current_state)

    def _addresses_up(self, interface, ipr, idx):
        # Get existing addresses, this list is used to delete removed addresses
        current_addresses = []
        for addr in ipr.get_addr(index=idx):
            attrs = dict(addr['attrs'])
            # Skip non-static (ex: dynamic) addresses
            if not attrs['IFA_FLAGS'] & ifaddrmsg.IFA_F_PERMANENT:
                continue

            key = (self._normalize_ip_address(attrs['IFA_ADDRESS']),
                   addr[consts.PREFIXLEN])
            current_addresses.append(key)

        # Add new addresses
        for address in interface.addresses:
            if (consts.ADDRESS not in address or
                    address.get(consts.DHCP) or
                    address.get(consts.IPV6AUTO)):
                continue
            key = (self._normalize_ip_address(address.get(consts.ADDRESS)),
                   address.get(consts.PREFIXLEN))
            if key in current_addresses:
                current_addresses.remove(key)
            elif address.get(consts.OCTAVIA_OWNED, True):
                # By default all adresses are managed/owned by Octavia
                address[consts.FAMILY] = self._family(
                    address[consts.ADDRESS])
                LOG.debug("%s: Adding address %s", interface.name,
                          address)
                self._ipr_command(ipr.addr, self.ADD, index=idx, **address)

        self._wait_tentative(ipr, idx)

        # Remove unused addresses
        for addr, prefixlen in current_addresses:
            address = {
                consts.ADDRESS: addr,
                consts.PREFIXLEN: prefixlen,
                consts.FAMILY: self._family(addr)
            }
            LOG.debug("%s: Deleting address %s", interface.name,
                      address)
            self._ipr_command(ipr.addr, self.DELETE, index=idx,
                              **address)

    def _routes_up(self, interface, ipr, idx):
        # Get existing routes, this list will be used to remove old/unused
        # routes
        current_routes = []
        for route in ipr.get_routes(oif=idx):
            # We only consider 'static' routes (routes that are added by
            # octavia-interface), we don't update kernel or ra routes.
            if route['proto'] != rt_proto['static']:
                continue

            attrs = dict(route['attrs'])
            family = route[consts.FAMILY]
            # Disabling B104: hardcoded_bind_all_interfaces
            dst = attrs.get(
                'RTA_DST',
                '0.0.0.0' if family == socket.AF_INET else '::')  # nosec

            key = ("{}/{}".format(self._normalize_ip_address(dst),
                                  route.get('dst_len', 0)),
                   self._normalize_ip_address(attrs.get('RTA_GATEWAY')),
                   self._normalize_ip_address(attrs.get('RTA_PREFSRC')),
                   attrs.get('RTA_TABLE'))
            current_routes.append(key)

        # Add new routes
        for route in interface.routes:
            key = (self._normalize_ip_network(route.get(consts.DST)),
                   self._normalize_ip_address(route.get(consts.GATEWAY)),
                   self._normalize_ip_address(route.get(consts.PREFSRC)),
                   route.get(consts.TABLE, 254))
            if key in current_routes:
                # Route is already there, we want to keep it, remove it from
                # the list of routes to delete
                current_routes.remove(key)
            else:
                route[consts.FAMILY] = self._family(route[consts.DST])
                LOG.debug("%s: Adding route %s", interface.name, route)
                # Set retry_on_invalid_argument=True because the interface
                # might not be ready after setting its addresses
                # Set raise_on_error to False, possible invalid
                # (user-defined) routes from the subnet's host_routes will
                # not break the script.
                self._ipr_command(ipr.route, self.ADD,
                                  retry_on_invalid_argument=True,
                                  raise_on_error=False,
                                  oif=idx, **route)

        # Delete unused routes (only 'static' routes are considered, we only
        # delete routes we have previously added)
        for r in current_routes:
            route = {consts.DST: r[0],
                     consts.GATEWAY: r[1],
                     consts.PREFSRC: r[2],
                     consts.TABLE: r[3],
                     consts.FAMILY: self._family(r[0])}

            LOG.debug("%s: Deleting route %s", interface.name, route)
            self._ipr_command(ipr.route, self.DELETE,
                              retry_on_invalid_argument=True,
                              raise_on_error=False,
                              oif=idx, **route)

    def _rules_up(self, interface, ipr, idx):
        # Get existing rules
        current_rules = []
        for rule in ipr.get_rules():
            attrs = dict(rule['attrs'])
            if not attrs.get('FRA_SRC'):
                continue

            # skip the rules defined by the kernel (FRA_PROTOCOL == 2) or by
            # keepalived (FRA_PROTOCOL == 18)
            # we only consider removing the rules that we have previously added
            if attrs.get('FRA_PROTOCOL') in (2, 18):
                continue

            key = (attrs.get('FRA_TABLE'),
                   self._normalize_ip_address(attrs.get('FRA_SRC')),
                   rule[consts.SRC_LEN])
            current_rules.append(key)

        # Add new rules
        for rule in interface.rules:
            key = (rule.get(consts.TABLE, 254),
                   self._normalize_ip_address(rule.get(consts.SRC)),
                   rule.get(consts.SRC_LEN))
            if key in current_rules:
                current_rules.remove(key)
            else:
                rule[consts.FAMILY] = self._family(rule[consts.SRC])
                LOG.debug("%s: Adding rule %s", interface.name, rule)
                self._ipr_command(ipr.rule, self.ADD,
                                  retry_on_invalid_argument=True,
                                  **rule)

        # Remove old rules
        for r in current_rules:
            rule = {consts.TABLE: r[0],
                    consts.SRC: r[1],
                    consts.SRC_LEN: r[2]}
            if rule[consts.SRC]:
                rule[consts.FAMILY] = self._family(rule[consts.SRC])
            LOG.debug("%s: Deleting rule %s", interface.name, rule)
            self._ipr_command(ipr.rule, self.DELETE,
                              retry_on_invalid_argument=True,
                              **rule)

    def _scripts_up(self, interface, current_state):
        if current_state == consts.IFACE_DOWN:
            for script in interface.scripts[consts.IFACE_UP]:
                LOG.debug("%s: Running command '%s'",
                          interface.name, script[consts.COMMAND])
                subprocess.check_output(script[consts.COMMAND].split())

    def down(self, interface):
        LOG.info("Setting interface %s down", interface.name)

        for address in interface.addresses:
            if address.get(consts.DHCP):
                self._dhclient_down(interface.name)
            if address.get(consts.IPV6AUTO):
                self._ipv6auto_down(interface.name)

        with pyroute2.IPRoute() as ipr:
            idx = ipr.link_lookup(ifname=interface.name)[0]

            # Workaround for https://github.com/PyCQA/pylint/issues/8497
            # pylint: disable=E1136, E1121
            link = ipr.get_links(idx)[0]
            current_state = link.get(consts.STATE)

            if current_state == consts.IFACE_UP:
                # only the vip port updates the rules
                if interface.if_type == consts.VIP:
                    for rule in interface.rules:
                        rule[consts.FAMILY] = self._family(rule[consts.SRC])
                        LOG.debug("%s: Deleting rule %s", interface.name, rule)
                        self._ipr_command(ipr.rule, self.DELETE,
                                          raise_on_error=False, **rule)

                for route in interface.routes:
                    route[consts.FAMILY] = self._family(route[consts.DST])
                    LOG.debug("%s: Deleting route %s", interface.name, route)
                    self._ipr_command(ipr.route, self.DELETE,
                                      raise_on_error=False, oif=idx, **route)

                for address in interface.addresses:
                    if consts.ADDRESS not in address:
                        continue
                    address[consts.FAMILY] = self._family(
                        address[consts.ADDRESS])
                    LOG.debug("%s: Deleting address %s",
                              interface.name, address)
                    self._ipr_command(ipr.addr, self.DELETE,
                                      raise_on_error=False,
                                      index=idx, **address)

                self._ipr_command(ipr.flush_addr, raise_on_error=False,
                                  index=idx)

                self._ipr_command(ipr.link, self.SET, raise_on_error=False,
                                  index=idx, state=consts.IFACE_DOWN)

        if current_state == consts.IFACE_UP:
            for script in interface.scripts[consts.IFACE_DOWN]:
                LOG.debug("%s: Running command '%s'",
                          interface.name, script[consts.COMMAND])
                try:
                    subprocess.check_output(script[consts.COMMAND].split())
                except Exception as e:
                    LOG.error("Error while running command '%s' on %s: %s",
                              script[consts.COMMAND], interface.name, e)
