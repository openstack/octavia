# Copyright 2011, VMware, Inc., 2014 A10 Networks
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# Borrowed from nova code base, more utilities will be added/borrowed as and
# when needed.

"""Utilities and helper functions."""

import base64
import hashlib
import re
import socket

import netaddr
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from stevedore import driver as stevedore_driver

from octavia.common import constants

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def get_hostname():
    return socket.gethostname()


def base64_sha1_string(string_to_hash):
    """Get a b64-encoded sha1 hash of a string. Not intended to be secure!"""
    # TODO(rm_work): applying nosec here because this is not intended to be
    # secure, it's just a way to get a consistent ID. Changing this would
    # break backwards compatibility with existing loadbalancers.
    hash_str = hashlib.sha1(string_to_hash.encode('utf-8')).digest()  # nosec
    b64_str = base64.b64encode(hash_str, str.encode('_-', 'ascii'))
    b64_sha1 = b64_str.decode('UTF-8')
    # https://github.com/haproxy/haproxy/issues/644
    return re.sub(r"^-", "x", b64_sha1)


def get_amphora_driver():
    amphora_driver = stevedore_driver.DriverManager(
        namespace='octavia.amphora.drivers',
        name=CONF.controller_worker.amphora_driver,
        invoke_on_load=True
    ).driver
    return amphora_driver


def get_network_driver():
    CONF.import_group('controller_worker', 'octavia.common.config')
    network_driver = stevedore_driver.DriverManager(
        namespace='octavia.network.drivers',
        name=CONF.controller_worker.network_driver,
        invoke_on_load=True
    ).driver
    return network_driver


def is_ipv4(ip_address):
    """Check if ip address is IPv4 address."""
    ip = netaddr.IPAddress(ip_address)
    return ip.version == 4


def is_ipv6(ip_address):
    """Check if ip address is IPv6 address."""
    ip = netaddr.IPAddress(ip_address)
    return ip.version == 6


def is_cidr_ipv6(cidr):
    """Check if CIDR is IPv6 address with subnet prefix."""
    ip = netaddr.IPNetwork(cidr)
    return ip.version == 6


def is_ipv6_lla(ip_address):
    """Check if ip address is IPv6 link local address."""
    ip = netaddr.IPAddress(ip_address)
    return ip.version == 6 and ip.is_link_local()


def ip_port_str(ip_address, port):
    """Return IP port as string representation depending on address family."""
    ip = netaddr.IPAddress(ip_address)
    if ip.version == 4:
        return "{ip}:{port}".format(ip=ip, port=port)
    return "[{ip}]:{port}".format(ip=ip, port=port)


def netmask_to_prefix(netmask):
    return netaddr.IPAddress(netmask).netmask_bits()


def ip_netmask_to_cidr(ip, netmask):
    net = netaddr.IPNetwork("0.0.0.0/0")
    if ip and netmask:
        net = netaddr.IPNetwork(
            "{ip}/{netmask}".format(ip=ip, netmask=netmask)
        )
    return "{ip}/{netmask}".format(ip=net.network, netmask=net.prefixlen)


def get_vip_security_group_name(loadbalancer_id):
    if loadbalancer_id:
        return constants.VIP_SECURITY_GROUP_PREFIX + loadbalancer_id
    return None


def get_compatible_value(value):
    if isinstance(value, str):
        value = value.encode('utf-8')
    return value


def get_compatible_server_certs_key_passphrase():
    key = CONF.certificates.server_certs_key_passphrase
    if isinstance(key, str):
        key = key.encode('utf-8')
    return base64.urlsafe_b64encode(key)


def subnet_ip_availability(nw_ip_avail, subnet_id, req_num_ips):
    for subnet in nw_ip_avail.subnet_ip_availability:
        if subnet['subnet_id'] == subnet_id:
            return subnet['total_ips'] - subnet['used_ips'] >= req_num_ips
    return None


def b(s):
    return s.encode('utf-8')


def expand_expected_codes(codes):
    """Expand the expected code string in set of codes.

    200-204 -> 200, 201, 202, 204
    200, 203 -> 200, 203
    """
    retval = set()
    codes = re.split(', *', codes)
    for code in codes:
        if not code:
            continue
        if '-' in code:
            low, hi = code.split('-')[:2]
            retval.update(
                str(i) for i in range(int(low), int(hi) + 1))
        else:
            retval.add(code)
    return retval


class exception_logger(object):
    """Wrap a function and log raised exception

    :param logger: the logger to log the exception default is LOG.exception

    :returns: origin value if no exception raised; re-raise the exception if
              any occurred

    """
    def __init__(self, logger=None):
        self.logger = logger

    def __call__(self, func):
        if self.logger is None:
            _LOG = logging.getLogger(func.__module__)
            self.logger = _LOG.exception

        def call(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.logger(e)
        return call
