# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""ARP behavior controls used by active-active amphorae."""

import logging
import os
import subprocess

import flask
import pyroute2
from werkzeug import exceptions

from octavia.common import constants as consts

LOG = logging.getLogger(__name__)


def enable_or_disable(arp_ignore_value, mac_address):
    interface = _interface_by_mac(mac_address)
    command = [
        'ip', 'netns', 'exec', consts.AMPHORA_NAMESPACE,
        'sysctl', '-w',
        'net.ipv4.conf.{0}.arp_ignore={1}'.format(
            interface, arp_ignore_value)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        LOG.warning('Unable to set ARP behavior on %s: %s', interface, exc)
        raise exceptions.HTTPException(
            response=flask.make_response(flask.jsonify({
                'message': 'Error enabling/disabling ARP',
                'details': str(exc)}), 500))

    return flask.make_response(flask.jsonify({
        'message': 'OK', 'details': 'ARP behavior updated'}), 202)


def _interface_by_mac(mac_address):
    wanted = mac_address.lower()
    # Amphora data-plane interfaces live in the amphora network namespace;
    # the agent process itself runs in the root namespace.  Looking up the
    # MAC with netifaces in the root namespace therefore misses VRRP/VIP
    # interfaces and makes active-active ARP suppression fail with 404.
    with pyroute2.NetNS(consts.AMPHORA_NAMESPACE,
                        flags=os.O_CREAT) as netns:
        for link in netns.get_links():
            attrs = dict(link['attrs'])
            if attrs.get(consts.IFLA_ADDRESS, '').lower() == wanted:
                return attrs.get(consts.IFLA_IFNAME)
    raise exceptions.HTTPException(
        response=flask.make_response(flask.jsonify({
            'message': 'No suitable network interface found'}), 404))
