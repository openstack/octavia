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
#    under the License.

import logging
import os
import re
import socket
import subprocess

import flask
import ipaddress
import netifaces
import pyroute2
import six

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts

LOG = logging.getLogger(__name__)


def compile_amphora_info():
    return flask.jsonify(
        {'hostname': socket.gethostname(),
         'haproxy_version': _get_version_of_installed_package('haproxy'),
         'api_version': api_server.VERSION})


def compile_amphora_details():
    listener_list = util.get_listeners()
    meminfo = _get_meminfo()
    cpu = _cpu()
    st = os.statvfs('/')
    return flask.jsonify(
        {'hostname': socket.gethostname(),
         'haproxy_version': _get_version_of_installed_package('haproxy'),
         'api_version': api_server.VERSION,
         'networks': _get_networks(),
         'active': True,
         'haproxy_count': _count_haproxy_processes(listener_list),
         'cpu': {
             'total': cpu['total'],
             'user': cpu['user'],
             'system': cpu['system'],
             'soft_irq': cpu['softirq'], },
         'memory': {
             'total': meminfo['MemTotal'],
             'free': meminfo['MemFree'],
             'buffers': meminfo['Buffers'],
             'cached': meminfo['Cached'],
             'swap_used': meminfo['SwapCached'],
             'shared': meminfo['Shmem'],
             'slab': meminfo['Slab'], },
         'disk': {
             'used': (st.f_blocks - st.f_bfree) * st.f_frsize,
             'available': st.f_bavail * st.f_frsize},
         'load': [
             _load()],
         'topology': consts.TOPOLOGY_SINGLE,
         'topology_status': consts.TOPOLOGY_STATUS_OK,
         'listeners': listener_list,
         'packages': {}})


def _get_version_of_installed_package(name):
    cmd = "dpkg --status " + name
    out = subprocess.check_output(cmd.split())
    m = re.search('Version: .*', out)
    return m.group(0)[len('Version: '):]


def _count_haproxy_processes(listener_list):
    num = 0
    for listener_id in listener_list:
        if util.is_listener_running(listener_id):
            # optional check if it's still running
            num += 1
    return num


def _get_meminfo():
    re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
    result = dict()
    for line in open('/proc/meminfo'):
        match = re_parser.match(line)
        if not match:
            continue  # skip lines that don't parse
        key, value = match.groups(['key', 'value'])
        result[key] = int(value)
    return result


def _cpu():
    with open('/proc/stat') as f:
        cpu = f.readline()
        vals = cpu.split(' ')
        return {
            'user': vals[2],
            'nice': vals[3],
            'system': vals[4],
            'idle': vals[5],
            'iowait': vals[6],
            'irq': vals[7],
            'softirq': vals[8],
            'total': sum([int(i) for i in vals[2:]])
        }


def _load():
    with open('/proc/loadavg') as f:
        load = f.readline()
        vals = load.split(' ')
        return vals[:3]


def _get_networks():
    networks = dict()
    with pyroute2.NetNS(consts.AMPHORA_NAMESPACE) as netns:
        for interface in netns.get_links():
            interface_name = None
            for item in interface['attrs']:
                if item[0] == 'IFLA_IFNAME' and not item[1].startswith('eth'):
                    break
                elif item[0] == 'IFLA_IFNAME':
                    interface_name = item[1]
                if item[0] == 'IFLA_STATS64':
                    networks[interface_name] = dict(
                        network_tx=item[1]['tx_bytes'],
                        network_rx=item[1]['rx_bytes'])
    return networks


def get_interface(ip_addr):

    try:
        if six.PY2:
            ip_version = ipaddress.ip_address(unicode(ip_addr)).version
        else:
            ip_version = ipaddress.ip_address(ip_addr).version
    except Exception:
        return flask.make_response(
            flask.jsonify(dict(message="Invalid IP address")), 400)

    if ip_version == 4:
        address_format = netifaces.AF_INET
    elif ip_version == 6:
        address_format = netifaces.AF_INET6
    else:
        return flask.make_response(
            flask.jsonify(dict(message="Bad IP address version")), 400)

    # We need to normalize the address as IPv6 has multiple representations
    # fe80:0000:0000:0000:f816:3eff:fef2:2058 == fe80::f816:3eff:fef2:2058
    normalized_addr = socket.inet_ntop(address_format,
                                       socket.inet_pton(address_format,
                                                        ip_addr))

    with pyroute2.NetNS(consts.AMPHORA_NAMESPACE) as netns:
        for addr in netns.get_addr():
            # Save the interface index as IPv6 records don't list a
            # textual interface
            interface_idx = addr['index']
            # Save the address family (IPv4/IPv6) for use normalizing
            # the IP address for comparison
            interface_af = addr['family']
            # Search through the attributes of each address record
            for attr in addr['attrs']:
                # Look for the attribute name/value pair for the address
                if attr[0] == 'IFA_ADDRESS':
                    # Compare the normalized address with the address we
                    # we are looking for.  Since we have matched the name
                    # above, attr[1] is the address value
                    if normalized_addr == socket.inet_ntop(
                            interface_af,
                            socket.inet_pton(interface_af, attr[1])):

                        # Lookup the matching interface name by
                        # getting the interface with the index we found
                        # in the above address search
                        lookup_int = netns.get_links(interface_idx)
                        # Search through the attributes of the matching
                        # interface record
                        for int_attr in lookup_int[0]['attrs']:
                            # Look for the attribute name/value pair
                            # that includes the interface name
                            if int_attr[0] == 'IFLA_IFNAME':
                                # Return the response with the matching
                                # interface name that is in int_attr[1]
                                # for the matching interface attribute
                                # name
                                return flask.make_response(
                                    flask.jsonify(
                                        dict(message='OK',
                                             interface=int_attr[1])), 200)

    return flask.make_response(
        flask.jsonify(dict(message="Error interface not found "
                                   "for IP address")), 404)
