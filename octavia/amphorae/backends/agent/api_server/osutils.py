# Copyright 2017 Red Hat, Inc. All rights reserved.
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

import subprocess

import distro
from oslo_config import cfg
from oslo_log import log as logging
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.utils import interface_file
from octavia.common import constants as consts
from octavia.common import exceptions as octavia_exceptions

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class BaseOS(object):

    def __init__(self, os_name):
        self.os_name = os_name
        self.package_name_map = {}

    @classmethod
    def _get_subclasses(cls):
        for subclass in cls.__subclasses__():
            for sc in subclass._get_subclasses():
                yield sc
            yield subclass

    @classmethod
    def get_os_util(cls):
        os_name = distro.id()
        for subclass in cls._get_subclasses():
            if subclass.is_os_name(os_name):
                return subclass(os_name)
        raise octavia_exceptions.InvalidAmphoraOperatingSystem(os_name=os_name)

    def _map_package_name(self, package_name):
        return self.package_name_map.get(package_name, package_name)

    def write_interface_file(self, interface, ip_address, prefixlen):
        interface = interface_file.InterfaceFile(
            name=interface,
            if_type=consts.LO,
            addresses=[{
                "address": ip_address,
                "prefixlen": prefixlen
            }]
        )
        interface.write()

    def write_vip_interface_file(self, interface, vips, mtu, vrrp_info,
                                 fixed_ips=None):
        vip_interface = interface_file.VIPInterfaceFile(
            name=interface,
            mtu=mtu,
            vips=vips,
            vrrp_info=vrrp_info,
            fixed_ips=fixed_ips,
            topology=CONF.controller_worker.loadbalancer_topology)
        vip_interface.write()

    def write_port_interface_file(self, interface, fixed_ips, mtu):
        port_interface = interface_file.PortInterfaceFile(
            name=interface,
            mtu=mtu,
            fixed_ips=fixed_ips)
        port_interface.write()

    @classmethod
    def bring_interface_up(cls, interface, name):
        cmd = ("ip netns exec {ns} amphora-interface up {params}".format(
            ns=consts.AMPHORA_NAMESPACE, params=interface))
        LOG.debug("Executing: %s", cmd)
        try:
            out = subprocess.check_output(cmd.split(),
                                          stderr=subprocess.STDOUT)
            for line in out.decode('utf-8').split('\n'):
                LOG.debug(line)
        except subprocess.CalledProcessError as e:
            LOG.error('Failed to set up %s due to error: %s %s', interface,
                      e, e.output)
            raise exceptions.HTTPException(
                response=webob.Response(json={
                    'message': 'Error plugging {0}'.format(name),
                    'details': e.output}, status=500))


class Ubuntu(BaseOS):

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['ubuntu', 'debian']

    def cmd_get_version_of_installed_package(self, package_name):
        name = self._map_package_name(package_name)
        return "dpkg-query -W -f=${{Version}} {name}".format(name=name)


class RH(BaseOS):

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['fedora', 'rhel']

    def cmd_get_version_of_installed_package(self, package_name):
        name = self._map_package_name(package_name)
        return "rpm -q --queryformat %{{VERSION}} {name}".format(name=name)


class CentOS(RH):

    def __init__(self, os_name):
        super().__init__(os_name)
        if distro.version() == '7':
            self.package_name_map.update({'haproxy': 'haproxy18'})

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['centos']
