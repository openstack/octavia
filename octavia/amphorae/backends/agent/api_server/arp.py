# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""ARP behavior controls used by active-active amphorae."""

import logging
import subprocess

import flask
import netifaces
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
    for interface in netifaces.interfaces():
        for link in netifaces.ifaddresses(interface).get(netifaces.AF_LINK,
                                                         []):
            if link.get('addr', '').lower() == wanted:
                return interface
    raise exceptions.HTTPException(
        response=flask.make_response(flask.jsonify({
            'message': 'No suitable network interface found'}), 404))
