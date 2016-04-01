# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
import jinja2
import netifaces
import pyroute2
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.i18n import _LE, _LI


ETH_PORT_CONF = 'plug_vip_ethX.conf.j2'

ETH_X_VIP_CONF = 'plug_port_ethX.conf.j2'

LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
template_port = j2_env.get_template(ETH_X_VIP_CONF)
template_vip = j2_env.get_template(ETH_PORT_CONF)


def plug_vip(vip, subnet_cidr, gateway, mac_address):
    # validate vip
    try:
        socket.inet_aton(vip)
    except socket.error:
        return flask.make_response(flask.jsonify(dict(
            message="Invalid VIP")), 400)

    interface = _interface_by_mac(mac_address)
    primary_interface = "{interface}".format(interface=interface)
    secondary_interface = "{interface}:0".format(interface=interface)

    # assume for now only a fixed subnet size
    sections = vip.split('.')[:3]
    sections.append('255')
    broadcast = '.'.join(sections)

    # We need to setup the netns network directory so that the ifup
    # commands used here and in the startup scripts "sees" the right
    # interfaces and scripts.
    interface_file_path = util.get_network_interface_file(interface)
    os.makedirs('/etc/netns/' + consts.AMPHORA_NAMESPACE)
    shutil.copytree('/etc/network',
                    '/etc/netns/{}/network'.format(consts.AMPHORA_NAMESPACE),
                    symlinks=True,
                    ignore=shutil.ignore_patterns('eth0*', 'openssh*'))
    name = '/etc/netns/{}/network/interfaces'.format(consts.AMPHORA_NAMESPACE)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00644
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    with os.fdopen(os.open(name, flags, mode), 'w') as file:
        file.write('auto lo\n')
        file.write('iface lo inet loopback\n')
        file.write('source /etc/netns/{}/network/interfaces.d/*.cfg\n'.format(
            consts.AMPHORA_NAMESPACE))

    # write interface file
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

    with os.fdopen(os.open(interface_file_path, flags, mode),
                   'w') as text_file:
        text = template_vip.render(
            interface=interface,
            vip=vip,
            broadcast=broadcast,
            # assume for now only a fixed subnet size
            netmask='255.255.255.0')
        text_file.write(text)

    # Update the list of interfaces to add to the namespace
    # This is used in the amphora reboot case to re-establish the namespace
    _update_plugged_interfaces_file(interface, mac_address)

    # Create the namespace
    netns = pyroute2.NetNS(consts.AMPHORA_NAMESPACE, flags=os.O_CREAT)
    netns.close()

    with pyroute2.IPRoute() as ipr:
        # Move the interfaces into the namespace
        idx = ipr.link_lookup(ifname=primary_interface)[0]
        ipr.link('set', index=idx, net_ns_fd=consts.AMPHORA_NAMESPACE)

    # bring interfaces up
    _bring_if_down(primary_interface)
    _bring_if_down(secondary_interface)
    _bring_if_up(primary_interface, 'VIP')
    _bring_if_up(secondary_interface, 'VIP')

    return flask.make_response(flask.jsonify(dict(
        message="OK",
        details="VIP {vip} plugged on interface {interface}".format(
            vip=vip, interface=interface))), 202)


def plug_network(mac_address):
    # This is the interface as it was initially plugged into the
    # default network namespace, this will likely always be eth1
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
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00644
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

    with os.fdopen(os.open(interface_file_path, flags, mode),
                   'w') as text_file:
        text = template_port.render(interface=netns_interface)
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
