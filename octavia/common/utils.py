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
import socket

import netaddr
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from stevedore import driver as stevedore_driver

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def get_hostname():
    return socket.gethostname()


def base64_sha1_string(string_to_hash):
    hash_str = hashlib.sha1(string_to_hash.encode('utf-8')).digest()
    b64_str = base64.b64encode(hash_str, str.encode('_-', 'ascii'))
    return b64_str.decode('UTF-8')


def get_network_driver():
    CONF.import_group('controller_worker', 'octavia.common.config')
    network_driver = stevedore_driver.DriverManager(
        namespace='octavia.network.drivers',
        name=CONF.controller_worker.network_driver,
        invoke_on_load=True
    ).driver
    return network_driver


def is_ipv6(ip_address):
    """Check if ip address is IPv6 address."""
    ip = netaddr.IPAddress(ip_address)
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
    elif ip.version == 6:
        return "[{ip}]:{port}".format(ip=ip, port=port)


def netmask_to_prefix(netmask):
    return netaddr.IPAddress(netmask).netmask_bits()


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
            LOG = logging.getLogger(func.__module__)
            self.logger = LOG.exception

        def call(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.logger(e)
        return call
