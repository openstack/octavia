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

from octavia.amphorae.backends.utils import interface_file
from octavia.common import constants as consts
from octavia.common import exceptions

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class InterfaceController(object):
    ADD = 'add'
    DELETE = 'delete'
    SET = 'set'

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

    def _ipr_command(self, method, command,
                     retry_on_invalid_argument=False,
                     retry_interval=.2,
                     raise_on_error=True,
                     max_retries=20,
                     **kwargs):

        for dummy in range(max_retries + 1):
            try:
                method(command, **kwargs)
                break
            except pyroute2.NetlinkError as e:
                if e.code == errno.EINVAL and retry_on_invalid_argument:
                    LOG.debug("Retrying after %d sec.", retry_interval)
                    time.sleep(retry_interval)
                    continue

                if command == self.ADD and e.code != errno.EEXIST:
                    msg = "Cannot call {} {} (with {}): {}".format(
                        method.__name__, command, kwargs, e)
                    if raise_on_error:
                        raise exceptions.AmphoraNetworkConfigException(msg)
                    LOG.error(msg)
                return
        else:
            msg = "Cannot call {} {} (with {}) after {} retries.".format(
                method.__name__, command, kwargs, max_retries)
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
                if (addr['family'] == socket.AF_INET6 and
                    addr['flags'] & ifaddrmsg.IFA_F_TENTATIVE)]
            if not has_tentative:
                return
            time.sleep(self.TENTATIVE_WAIT_INTERVAL)
        LOG.warning("Some IPV6 addresses remain still in 'tentative' state "
                    "after %d seconds.", self.TENTATIVE_WAIT_TIMEOUT)

    def up(self, interface):
        LOG.info("Setting interface %s up", interface.name)

        for address in interface.addresses:
            if address.get(consts.DHCP):
                self._dhclient_up(interface.name)
            if address.get(consts.IPV6AUTO):
                self._ipv6auto_up(interface.name)

        with pyroute2.IPRoute() as ipr:
            idx = ipr.link_lookup(ifname=interface.name)[0]

            self._ipr_command(ipr.link, self.SET, index=idx,
                              state=consts.IFACE_UP, mtu=interface.mtu)

            for address in interface.addresses:
                if (consts.ADDRESS not in address or
                        address.get(consts.DHCP) or
                        address.get(consts.IPV6AUTO)):
                    continue
                address[consts.FAMILY] = self._family(address[consts.ADDRESS])
                LOG.debug("%s: Adding address %s", interface.name, address)
                self._ipr_command(ipr.addr, self.ADD, index=idx, **address)

            self._wait_tentative(ipr, idx)

            for route in interface.routes:
                route[consts.FAMILY] = self._family(route[consts.DST])
                LOG.debug("%s: Adding route %s", interface.name, route)
                # Set retry_on_invalid_argument=True because the interface
                # might not be ready after setting its addresses
                # Note: can we use 'replace' instead of 'add' here?
                # Set raise_on_error to False, possible invalid (user-defined)
                # routes from the subnet's host_routes will not break the
                # script.
                self._ipr_command(ipr.route, self.ADD,
                                  retry_on_invalid_argument=True,
                                  raise_on_error=False,
                                  oif=idx, **route)

            for rule in interface.rules:
                rule[consts.FAMILY] = self._family(rule[consts.SRC])
                LOG.debug("%s: Adding rule %s", interface.name, rule)
                self._ipr_command(ipr.rule, self.ADD,
                                  retry_on_invalid_argument=True,
                                  **rule)

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

            link = ipr.get_links(idx)[0]
            current_state = link.get(consts.STATE)

            if current_state == consts.IFACE_UP:
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
