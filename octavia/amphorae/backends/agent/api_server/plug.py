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
import socket
import subprocess

import flask
import jinja2
import netifaces
import pyroute2
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts

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

    # assume for now only a fixed subnet size
    sections = vip.split('.')[:3]
    sections.append('255')
    broadcast = '.'.join(sections)

    # write interface file
    with open(util.get_network_interface_file(interface), 'w') as text_file:
        text = template_vip.render(
            interface=interface,
            vip=vip,
            broadcast=broadcast,
            # assume for now only a fixed subnet size
            netmask='255.255.255.0')
        text_file.write(text)

    # bring interfaces up
    _bring_if_down("{interface}".format(interface=interface))
    _bring_if_down("{interface}:0".format(interface=interface))
    _bring_if_up("{interface}".format(interface=interface), 'VIP')
    _bring_if_up("{interface}:0".format(interface=interface), 'VIP')

    # Setup policy based routes for the amphora

    ip = pyroute2.IPRoute()

    cidr_split = subnet_cidr.split('/')

    num_interface = ip.link_lookup(ifname=interface)

    ip.route('add',
             dst=cidr_split[0],
             mask=int(cidr_split[1]),
             oif=num_interface,
             table=1,
             rtproto='RTPROT_BOOT',
             rtscope='RT_SCOPE_LINK')

    ip.route('add',
             dst='0.0.0.0',
             gateway=gateway,
             oif=num_interface,
             table=1,
             rtproto='RTPROT_BOOT')

    ip.rule('add',
            table=1,
            action='FR_ACT_TO_TBL',
            src=cidr_split[0],
            src_len=int(cidr_split[1]))

    ip.rule('add',
            table=1,
            action='FR_ACT_TO_TBL',
            dst=cidr_split[0],
            dst_len=int(cidr_split[1]))

    return flask.make_response(flask.jsonify(dict(
        message="OK",
        details="VIP {vip} plugged on interface {interface}".format(
            vip=vip, interface=interface))), 202)


def plug_network(mac_address):
    interface = _interface_by_mac(mac_address)

    # write interface file
    with open(util.get_network_interface_file(interface), 'w') as text_file:
        text = template_port.render(interface=interface)
        text_file.write(text)

    _bring_if_down(interface)
    _bring_if_up(interface, 'network')

    return flask.make_response(flask.jsonify(dict(
        message="OK",
        details="Plugged on interface {interface}".format(
            interface=interface))), 202)


def _interface_by_mac(mac):
    for interface in netifaces.interfaces():
        if netifaces.AF_LINK in netifaces.ifaddresses(interface):
            for link in netifaces.ifaddresses(interface)[netifaces.AF_LINK]:
                if link.get('addr') == mac:
                    return interface
    raise exceptions.HTTPException(
        response=flask.make_response(flask.jsonify(dict(
            details="No suitable network interface found")), 404))


def _bring_if_up(params, what):
    # bring interface up
    cmd = "ifup {params}".format(params=params)
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.debug("Failed to if up {0}".format(e))
        raise exceptions.HTTPException(
            response=flask.make_response(flask.jsonify(dict(
                message='Error plugging {0}'.format(what),
                details=e.output)), 500))


def _bring_if_down(params):
    cmd = "ifdown {params}".format(params=params)
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        pass
