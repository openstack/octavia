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

import logging
import os
import shutil
import socket
import stat
import subprocess

import flask
import ipaddress
import jinja2
import netifaces
from oslo_config import cfg
import pyroute2
import six
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.i18n import _LE, _LI


CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')

ETH_X_VIP_CONF = 'plug_vip_ethX.conf.j2'
ETH_X_PORT_CONF = 'plug_port_ethX.conf.j2'

LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
template_port = j2_env.get_template(ETH_X_PORT_CONF)
template_vip = j2_env.get_template(ETH_X_VIP_CONF)


def plug_vip(vip, subnet_cidr, gateway,
             mac_address, vrrp_ip=None, host_routes=None):
    # Validate vip and subnet_cidr, calculate broadcast address and netmask
    try:
        render_host_routes = []
        ip = ipaddress.ip_address(
            vip if six.text_type == type(vip) else six.u(vip))
        network = ipaddress.ip_network(
            subnet_cidr if six.text_type == type(subnet_cidr)
            else six.u(subnet_cidr))
        vip = ip.exploded
        broadcast = network.broadcast_address.exploded
        netmask = (network.prefixlen if ip.version is 6
                   else network.netmask.exploded)
        vrrp_version = None
        if vrrp_ip:
            vrrp_ip_obj = ipaddress.ip_address(
                vrrp_ip if six.text_type == type(vrrp_ip) else six.u(vrrp_ip)
            )
            vrrp_version = vrrp_ip_obj.version
        if host_routes:
            for hr in host_routes:
                network = ipaddress.ip_network(
                    hr['destination'] if isinstance(
                        hr['destination'], six.text_type) else
                    six.u(hr['destination']))
                render_host_routes.append({'network': network,
                                           'gw': hr['nexthop']})
    except ValueError:
        return flask.make_response(flask.jsonify(dict(
            message="Invalid VIP")), 400)

    # Check if the interface is already in the network namespace
    # Do not attempt to re-plug the VIP if it is already in the
    # network namespace
    if _netns_interface_exists(mac_address):
        return flask.make_response(flask.jsonify(dict(
            message="Interface already exists")), 409)

    # This is the interface prior to moving into the netns
    default_netns_interface = _interface_by_mac(mac_address)

    # Always put the VIP interface as eth1
    primary_interface = consts.NETNS_PRIMARY_INTERFACE
    secondary_interface = "{interface}:0".format(interface=primary_interface)

    # We need to setup the netns network directory so that the ifup
    # commands used here and in the startup scripts "sees" the right
    # interfaces and scripts.
    interface_file_path = util.get_network_interface_file(primary_interface)
    os.makedirs('/etc/netns/' + consts.AMPHORA_NAMESPACE)
    shutil.copytree('/etc/network',
                    '/etc/netns/{}/network'.format(consts.AMPHORA_NAMESPACE),
                    symlinks=True,
                    ignore=shutil.ignore_patterns('eth0*', 'openssh*'))
    name = '/etc/netns/{}/network/interfaces'.format(consts.AMPHORA_NAMESPACE)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00644
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    with os.fdopen(os.open(name, flags, mode), 'w') as int_file:
        int_file.write('auto lo\n')
        int_file.write('iface lo inet loopback\n')
        if not CONF.amphora_agent.agent_server_network_file:
            int_file.write('source /etc/netns/{}/network/'
                           'interfaces.d/*.cfg\n'.format(
                               consts.AMPHORA_NAMESPACE))

    # write interface file

    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    # If we are using a consolidated interfaces file, just append
    # otherwise clear the per interface file as we are rewriting it
    # TODO(johnsom): We need a way to clean out old interfaces records
    if CONF.amphora_agent.agent_server_network_file:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

    with os.fdopen(os.open(interface_file_path, flags, mode),
                   'w') as text_file:
        text = template_vip.render(
            interface=primary_interface,
            vip=vip,
            vip_ipv6=ip.version is 6,
            broadcast=broadcast,
            netmask=netmask,
            gateway=gateway,
            vrrp_ip=vrrp_ip,
            vrrp_ipv6=vrrp_version is 6,
            host_routes=render_host_routes,
        )
        text_file.write(text)

    # Update the list of interfaces to add to the namespace
    # This is used in the amphora reboot case to re-establish the namespace
    _update_plugged_interfaces_file(primary_interface, mac_address)

    # Create the namespace
    netns = pyroute2.NetNS(consts.AMPHORA_NAMESPACE, flags=os.O_CREAT)
    netns.close()

    with pyroute2.IPRoute() as ipr:
        # Move the interfaces into the namespace
        idx = ipr.link_lookup(ifname=default_netns_interface)[0]
        ipr.link('set', index=idx, net_ns_fd=consts.AMPHORA_NAMESPACE,
                 IFLA_IFNAME=primary_interface)

    # bring interfaces up
    _bring_if_down(primary_interface)
    _bring_if_down(secondary_interface)
    _bring_if_up(primary_interface, 'VIP')
    _bring_if_up(secondary_interface, 'VIP')

    return flask.make_response(flask.jsonify(dict(
        message="OK",
        details="VIP {vip} plugged on interface {interface}".format(
            vip=vip, interface=primary_interface))), 202)


def _generate_network_file_text(netns_interface, fixed_ips):
    text = ''
    if fixed_ips is None:
        text = template_port.render(interface=netns_interface)
    else:
        for index, fixed_ip in enumerate(fixed_ips, -1):
            if index == -1:
                netns_ip_interface = netns_interface
            else:
                netns_ip_interface = "{int}:{ip}".format(
                    int=netns_interface, ip=index)
            try:
                ip_addr = fixed_ip['ip_address']
                cidr = fixed_ip['subnet_cidr']
                ip = ipaddress.ip_address(
                    ip_addr if six.text_type == type(
                        ip_addr) else six.u(ip_addr))
                network = ipaddress.ip_network(
                    cidr if six.text_type == type(
                        cidr) else six.u(cidr))
                broadcast = network.broadcast_address.exploded
                netmask = (network.prefixlen if ip.version is 6
                           else network.netmask.exploded)
                host_routes = []
                for hr in fixed_ip.get('host_routes', []):
                    network = ipaddress.ip_network(
                        hr['destination'] if isinstance(
                            hr['destination'], six.text_type) else
                        six.u(hr['destination']))
                    host_routes.append({'network': network,
                                        'gw': hr['nexthop']})
            except ValueError:
                return flask.make_response(flask.jsonify(dict(
                    message="Invalid network IP")), 400)
            new_text = template_port.render(interface=netns_ip_interface,
                                            ipv6=ip.version is 6,
                                            ip_address=ip.exploded,
                                            broadcast=broadcast,
                                            netmask=netmask,
                                            host_routes=host_routes)
            text = '\n'.join([text, new_text])
    return text


def _check_ip_addresses(fixed_ips):
    if fixed_ips:
        for ip in fixed_ips:
            try:
                socket.inet_pton(socket.AF_INET, ip.get('ip_address'))
            except socket.error:
                socket.inet_pton(socket.AF_INET6, ip.get('ip_address'))


def plug_network(mac_address, fixed_ips):

    # Check if the interface is already in the network namespace
    # Do not attempt to re-plug the network if it is already in the
    # network namespace
    if _netns_interface_exists(mac_address):
        return flask.make_response(flask.jsonify(dict(
            message="Interface already exists")), 409)

    # This is the interface as it was initially plugged into the
    # default network namespace, this will likely always be eth1

    try:
        _check_ip_addresses(fixed_ips=fixed_ips)
    except socket.error:
        return flask.make_response(flask.jsonify(dict(
            message="Invalid network port")), 400)

    default_netns_interface = _interface_by_mac(mac_address)

    # We need to determine the interface name when inside the namespace
    # to avoid name conflicts
    with pyroute2.NetNS(consts.AMPHORA_NAMESPACE, flags=os.O_CREAT) as netns:

        # 1 means just loopback, but we should already have a VIP
        # This works for the add/delete/add case as we don't delete interfaces
        # Note, eth0 is skipped because that is the VIP interface
        netns_interface = 'eth{0}'.format(len(netns.get_links()))

    LOG.info(_LI('Plugged interface {0} will become {1} in the '
                 'namespace {2}').format(default_netns_interface,
                                         netns_interface,
                                         consts.AMPHORA_NAMESPACE))
    interface_file_path = util.get_network_interface_file(netns_interface)

    # write interface file

    # If we are using a consolidated interfaces file, just append
    # otherwise clear the per interface file as we are rewriting it
    # TODO(johnsom): We need a way to clean out old interfaces records
    if CONF.amphora_agent.agent_server_network_file:
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

    # mode 00644
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    with os.fdopen(os.open(interface_file_path, flags, mode),
                   'w') as text_file:
        text = _generate_network_file_text(netns_interface, fixed_ips)
        text_file.write(text)

    # Update the list of interfaces to add to the namespace
    _update_plugged_interfaces_file(netns_interface, mac_address)

    with pyroute2.IPRoute() as ipr:
        # Move the interfaces into the namespace
        idx = ipr.link_lookup(ifname=default_netns_interface)[0]
        ipr.link('set', index=idx,
                 net_ns_fd=consts.AMPHORA_NAMESPACE,
                 IFLA_IFNAME=netns_interface)

    _bring_if_down(netns_interface)
    _bring_if_up(netns_interface, 'network')

    return flask.make_response(flask.jsonify(dict(
        message="OK",
        details="Plugged on interface {interface}".format(
            interface=netns_interface))), 202)


def _interface_by_mac(mac):
    for interface in netifaces.interfaces():
        if netifaces.AF_LINK in netifaces.ifaddresses(interface):
            for link in netifaces.ifaddresses(interface)[netifaces.AF_LINK]:
                if link.get('addr', '').lower() == mac.lower():
                    return interface
    raise exceptions.HTTPException(
        response=flask.make_response(flask.jsonify(dict(
            details="No suitable network interface found")), 404))


def _bring_if_up(interface, what):
    # Note, we are not using pyroute2 for this as it is not /etc/netns
    # aware.
    cmd = ("ip netns exec {ns} ifup {params}".format(
        ns=consts.AMPHORA_NAMESPACE, params=interface))
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.error(_LE('Failed to if up {0} due to '
                      'error: {1}').format(interface, str(e)))
        raise exceptions.HTTPException(
            response=flask.make_response(flask.jsonify(dict(
                message='Error plugging {0}'.format(what),
                details=e.output)), 500))


def _bring_if_down(interface):
    # Note, we are not using pyroute2 for this as it is not /etc/netns
    # aware.
    cmd = ("ip netns exec {ns} ifdown {params}".format(
        ns=consts.AMPHORA_NAMESPACE, params=interface))
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        pass


def _update_plugged_interfaces_file(interface, mac_address):
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


def _netns_interface_exists(mac_address):
    with pyroute2.NetNS(consts.AMPHORA_NAMESPACE, flags=os.O_CREAT) as netns:
        for link in netns.get_links():
            for attr in link['attrs']:
                if attr[0] == 'IFLA_ADDRESS' and attr[1] == mac_address:
                    return True
    return False
