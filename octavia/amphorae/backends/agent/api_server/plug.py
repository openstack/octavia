# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright 2016 Rackspace
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
import itertools
import os
import socket
import stat

from oslo_config import cfg
from oslo_log import log as logging
import pyroute2
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class Plug(object):
    def __init__(self, osutils):
        self._osutils = osutils

    def plug_lo(self):
        self._osutils.write_interface_file(
            interface="lo",
            ip_address="127.0.0.1",
            prefixlen=8)

    def render_vips(self, vips):
        rendered_vips = []
        for vip in vips:
            ip_address = ipaddress.ip_address(vip['ip_address'])
            subnet_cidr = ipaddress.ip_network(vip['subnet_cidr'])
            prefixlen = subnet_cidr.prefixlen
            host_routes = vip['host_routes']
            gateway = vip['gateway']
            rendered_vips.append({
                'ip_address': ip_address.exploded,
                'ip_version': ip_address.version,
                'gateway': gateway,
                'host_routes': host_routes,
                'prefixlen': prefixlen
            })
        return rendered_vips

    def build_vrrp_info(self, vrrp_ip, subnet_cidr, gateway, host_routes):
        vrrp_info = {}
        if vrrp_ip:
            ip_address = ipaddress.ip_address(vrrp_ip)
            subnet_cidr = ipaddress.ip_network(subnet_cidr)
            prefixlen = subnet_cidr.prefixlen
            vrrp_info.update({
                'ip': ip_address.exploded,
                'ip_version': ip_address.version,
                'gateway': gateway,
                'host_routes': host_routes,
                'prefixlen': prefixlen
            })
        return vrrp_info

    def plug_vip(self, vip, subnet_cidr, gateway,
                 mac_address, mtu=None, vrrp_ip=None, host_routes=(),
                 additional_vips=()):
        vips = [{
            'ip_address': vip,
            'subnet_cidr': subnet_cidr,
            'gateway': gateway,
            'host_routes': host_routes
        }] + list(additional_vips)

        try:
            rendered_vips = self.render_vips(vips)
        except ValueError as e:
            vip_error_message = "Invalid VIP: {}".format(e)
            return webob.Response(json={'message': vip_error_message},
                                  status=400)

        try:
            vrrp_info = self.build_vrrp_info(vrrp_ip, subnet_cidr,
                                             gateway, host_routes)
        except ValueError as e:
            return webob.Response(
                json={'message': "Invalid VRRP Address: {}".format(e)},
                status=400)

        # Check if the interface is already in the network namespace
        # Do not attempt to re-plug the VIP if it is already in the
        # network namespace
        if self._netns_interface_exists(mac_address):
            return webob.Response(
                json={'message': "Interface already exists"}, status=409)

        # Check that the interface has been fully plugged
        self._interface_by_mac(mac_address)

        # Always put the VIP interface as eth1
        primary_interface = consts.NETNS_PRIMARY_INTERFACE

        self._osutils.write_vip_interface_file(
            interface=primary_interface,
            vips=rendered_vips,
            mtu=mtu,
            vrrp_info=vrrp_info)

        # Update the list of interfaces to add to the namespace
        # This is used in the amphora reboot case to re-establish the namespace
        self._update_plugged_interfaces_file(primary_interface, mac_address)

        with pyroute2.IPRoute() as ipr:
            # Move the interfaces into the namespace
            idx = ipr.link_lookup(address=mac_address)[0]
            ipr.link('set', index=idx, net_ns_fd=consts.AMPHORA_NAMESPACE,
                     IFLA_IFNAME=primary_interface)

        # bring interfaces up
        self._osutils.bring_interface_up(primary_interface, 'VIP')

        vip_message = "VIPs plugged on interface {interface}: {vips}".format(
            interface=primary_interface,
            vips=", ".join(v['ip_address'] for v in rendered_vips)
        )

        return webob.Response(json={
            'message': "OK",
            'details': vip_message}, status=202)

    def _check_ip_addresses(self, fixed_ips):
        if fixed_ips:
            for ip in fixed_ips:
                try:
                    socket.inet_pton(socket.AF_INET, ip.get('ip_address'))
                except socket.error:
                    socket.inet_pton(socket.AF_INET6, ip.get('ip_address'))

    def plug_network(self, mac_address, fixed_ips, mtu=None,
                     vip_net_info=None):
        try:
            self._check_ip_addresses(fixed_ips=fixed_ips)
        except socket.error:
            return webob.Response(json={
                'message': "Invalid network port"}, status=400)

        # Check if the interface is already in the network namespace
        # Do not attempt to re-plug the network if it is already in the
        # network namespace, just ensure all fixed_ips are up
        if self._netns_interface_exists(mac_address):
            # Get the existing interface name and path
            existing_interface = self._netns_interface_by_mac(mac_address)

            # If we have net_info, this is the special case of plugging a new
            # subnet on the vrrp port, which is essentially a re-vip-plug
            if vip_net_info:
                vrrp_ip = vip_net_info.get('vrrp_ip')
                subnet_cidr = vip_net_info['subnet_cidr']
                gateway = vip_net_info['gateway']
                host_routes = vip_net_info.get('host_routes', [])

                vips = [{
                    'ip_address': vip_net_info['vip'],
                    'subnet_cidr': subnet_cidr,
                    'gateway': gateway,
                    'host_routes': host_routes
                }] + vip_net_info.get('additional_vips', [])
                rendered_vips = self.render_vips(vips)
                vrrp_info = self.build_vrrp_info(vrrp_ip, subnet_cidr,
                                                 gateway, host_routes)

                self._osutils.write_vip_interface_file(
                    interface=existing_interface,
                    vips=rendered_vips,
                    mtu=mtu,
                    vrrp_info=vrrp_info,
                    fixed_ips=fixed_ips)
                self._osutils.bring_interface_up(existing_interface, 'vip')
            # Otherwise, we are just plugging a run-of-the-mill network
            else:
                # Write an updated config
                self._osutils.write_port_interface_file(
                    interface=existing_interface,
                    fixed_ips=fixed_ips,
                    mtu=mtu)
                self._osutils.bring_interface_up(existing_interface, 'network')

            util.send_member_advertisements(fixed_ips)
            return webob.Response(json={
                'message': "OK",
                'details': "Updated existing interface {interface}".format(
                    # TODO(rm_work): Everything in this should probably use
                    # HTTP code 200, but continuing to use 202 for consistency.
                    interface=existing_interface)}, status=202)

        # This is the interface as it was initially plugged into the
        # default network namespace, this will likely always be eth1
        default_netns_interface = self._interface_by_mac(mac_address)

        # We need to determine the interface name when inside the namespace
        # to avoid name conflicts
        netns_interface = self._netns_get_next_interface()

        LOG.info('Plugged interface %s will become %s in the namespace %s',
                 default_netns_interface, netns_interface,
                 consts.AMPHORA_NAMESPACE)
        self._osutils.write_port_interface_file(
            interface=netns_interface,
            fixed_ips=fixed_ips,
            mtu=mtu)

        # Update the list of interfaces to add to the namespace
        self._update_plugged_interfaces_file(netns_interface, mac_address)

        with pyroute2.IPRoute() as ipr:
            # Move the interfaces into the namespace
            idx = ipr.link_lookup(address=mac_address)[0]
            ipr.link('set', index=idx,
                     net_ns_fd=consts.AMPHORA_NAMESPACE,
                     IFLA_IFNAME=netns_interface)

        self._osutils.bring_interface_up(netns_interface, 'network')
        util.send_member_advertisements(fixed_ips)

        return webob.Response(json={
            'message': "OK",
            'details': "Plugged on interface {interface}".format(
                interface=netns_interface)}, status=202)

    def _interface_by_mac(self, mac):
        try:
            with pyroute2.IPRoute() as ipr:
                idx = ipr.link_lookup(address=mac)[0]
                # Workaround for https://github.com/PyCQA/pylint/issues/8497
                # pylint: disable=E1136, E1121
                addr = ipr.get_links(idx)[0]
                for attr in addr['attrs']:
                    if attr[0] == consts.IFLA_IFNAME:
                        return attr[1]
        except Exception as e:
            LOG.info('Unable to find interface with MAC: %s, rescanning '
                     'and returning 404. Reported error: %s', mac, str(e))

        # Poke the kernel to re-enumerate the PCI bus.
        # We have had cases where nova hot plugs the interface but
        # the kernel doesn't get the memo.
        filename = '/sys/bus/pci/rescan'
        flags = os.O_WRONLY
        if os.path.isfile(filename):
            with os.fdopen(os.open(filename, flags), 'w') as rescan_file:
                rescan_file.write('1')
        raise exceptions.HTTPException(
            response=webob.Response(json={
                'details': "No suitable network interface found"}, status=404))

    def _update_plugged_interfaces_file(self, interface, mac_address):
        # write interfaces to plugged_interfaces file and prevent duplicates
        plug_inf_file = consts.PLUGGED_INTERFACES
        flags = os.O_RDWR | os.O_CREAT
        # mode 0644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        with os.fdopen(os.open(plug_inf_file, flags, mode), 'r+') as text_file:
            inf_list = [inf.split()[0].rstrip() for inf in text_file]
            if mac_address not in inf_list:
                text_file.write("{mac_address} {interface}\n".format(
                    mac_address=mac_address, interface=interface))

    def _netns_interface_by_mac(self, mac_address):
        with pyroute2.NetNS(consts.AMPHORA_NAMESPACE,
                            flags=os.O_CREAT) as netns:
            for link in netns.get_links():
                attr_dict = dict(link['attrs'])
                if attr_dict.get(consts.IFLA_ADDRESS) == mac_address:
                    return attr_dict.get(consts.IFLA_IFNAME)
        return None

    def _netns_interface_exists(self, mac_address):
        return self._netns_interface_by_mac(mac_address) is not None

    def _netns_get_next_interface(self):
        with pyroute2.NetNS(consts.AMPHORA_NAMESPACE,
                            flags=os.O_CREAT) as netns:
            existing_ifaces = [
                dict(link['attrs']).get(consts.IFLA_IFNAME)
                for link in netns.get_links()]
            # find the first unused ethXXX
            for idx in itertools.count(start=2):
                iface_name = f"eth{idx}"
                if iface_name not in existing_ifaces:
                    break
            return iface_name
