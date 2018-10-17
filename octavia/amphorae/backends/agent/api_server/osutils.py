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

import errno
import ipaddress
import os
import shutil
import stat
import subprocess

import distro
import jinja2
from oslo_config import cfg
from oslo_log import log as logging
import six
import webob
from werkzeug import exceptions

from octavia.common import constants as consts
from octavia.common import exceptions as octavia_exceptions
from octavia.common import utils

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))


class BaseOS(object):

    PACKAGE_NAME_MAP = {}

    def __init__(self, os_name):
        self.os_name = os_name

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

    @classmethod
    def _map_package_name(cls, package_name):
        return cls.PACKAGE_NAME_MAP.get(package_name, package_name)

    def get_network_interface_file(self, interface):
        if CONF.amphora_agent.agent_server_network_file:
            return CONF.amphora_agent.agent_server_network_file
        if CONF.amphora_agent.agent_server_network_dir:
            return os.path.join(CONF.amphora_agent.agent_server_network_dir,
                                interface)
        network_dir = consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
            netns=consts.AMPHORA_NAMESPACE)
        return os.path.join(network_dir, interface)

    def create_netns_dir(self, network_dir, netns_network_dir, ignore=None):
        # We need to setup the netns network directory so that the ifup
        # commands used here and in the startup scripts "sees" the right
        # interfaces and scripts.
        try:
            os.makedirs('/etc/netns/' + consts.AMPHORA_NAMESPACE)
        except OSError as e:
            # Raise the error if it's not "File exists" otherwise pass
            if e.errno != errno.EEXIST:
                raise

        shutil.copytree(
            network_dir,
            '/etc/netns/{netns}/{net_dir}'.format(
                netns=consts.AMPHORA_NAMESPACE,
                net_dir=netns_network_dir),
            symlinks=True,
            ignore=ignore)

    def write_vip_interface_file(self, interface_file_path,
                                 primary_interface, vip, ip, broadcast,
                                 netmask, gateway, mtu, vrrp_ip, vrrp_version,
                                 render_host_routes, template_vip):
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
                consts=consts,
                interface=primary_interface,
                vip=vip,
                vip_ipv6=ip.version == 6,
                prefix=utils.netmask_to_prefix(netmask),
                broadcast=broadcast,
                netmask=netmask,
                gateway=gateway,
                network=utils.ip_netmask_to_cidr(vip, netmask),
                mtu=mtu,
                vrrp_ip=vrrp_ip,
                vrrp_ipv6=vrrp_version == 6,
                host_routes=render_host_routes,
                topology=CONF.controller_worker.loadbalancer_topology,
            )
            text_file.write(text)

    def write_port_interface_file(self, netns_interface, fixed_ips, mtu,
                                  interface_file_path, template_port):
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
            text = self._generate_network_file_text(netns_interface, fixed_ips,
                                                    mtu, template_port)
            text_file.write(text)

    def _generate_network_file_text(self, netns_interface, fixed_ips, mtu,
                                    template_port):
        text = ''
        if fixed_ips is None:
            text = template_port.render(interface=netns_interface)
        else:
            for index, fixed_ip in enumerate(fixed_ips, -1):
                try:
                    ip_addr = fixed_ip['ip_address']
                    cidr = fixed_ip['subnet_cidr']
                    ip = ipaddress.ip_address(ip_addr if isinstance(
                        ip_addr, six.text_type) else six.u(ip_addr))
                    network = ipaddress.ip_network(
                        cidr if isinstance(
                            cidr, six.text_type) else six.u(cidr))
                    broadcast = network.broadcast_address.exploded
                    netmask = (network.prefixlen if ip.version == 6
                               else network.netmask.exploded)
                    host_routes = self.get_host_routes(fixed_ip)

                except ValueError:
                    return webob.Response(
                        json=dict(message="Invalid network IP"), status=400)
                new_text = template_port.render(interface=netns_interface,
                                                ipv6=ip.version == 6,
                                                ip_address=ip.exploded,
                                                broadcast=broadcast,
                                                netmask=netmask,
                                                mtu=mtu,
                                                host_routes=host_routes)
                text = '\n'.join([text, new_text])
        return text

    def get_host_routes(self, fixed_ip):
        host_routes = []
        for hr in fixed_ip.get('host_routes', []):
            network = ipaddress.ip_network(
                hr['destination'] if isinstance(
                    hr['destination'], six.text_type) else
                six.u(hr['destination']))
            host_routes.append({'network': network, 'gw': hr['nexthop']})
        return host_routes

    def _bring_if_up(self, interface, what):
        # Note, we are not using pyroute2 for this as it is not /etc/netns
        # aware.
        cmd = ("ip netns exec {ns} ifup {params}".format(
            ns=consts.AMPHORA_NAMESPACE, params=interface))
        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.error('Failed to ifup %s due to error: %s %s', interface, e,
                      e.output)
            raise exceptions.HTTPException(
                response=webob.Response(json=dict(
                    message='Error plugging {0}'.format(what),
                    details=e.output), status=500))

    def _bring_if_down(self, interface):
        # Note, we are not using pyroute2 for this as it is not /etc/netns
        # aware.
        cmd = ("ip netns exec {ns} ifdown {params}".format(
            ns=consts.AMPHORA_NAMESPACE, params=interface))
        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.info('Ignoring failure to ifdown %s due to error: %s %s',
                     interface, e, e.output)

    def bring_interfaces_up(self, ip, primary_interface, secondary_interface):
        self._bring_if_down(primary_interface)
        if secondary_interface:
            self._bring_if_down(secondary_interface)
        self._bring_if_up(primary_interface, 'VIP')
        if secondary_interface:
            self._bring_if_up(secondary_interface, 'VIP')

    def has_ifup_all(self):
        return True


class Ubuntu(BaseOS):

    ETH_X_PORT_CONF = 'plug_port_ethX.conf.j2'
    ETH_X_VIP_CONF = 'plug_vip_ethX.conf.j2'

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['ubuntu']

    def cmd_get_version_of_installed_package(self, package_name):
        name = self._map_package_name(package_name)
        return "dpkg-query -W -f=${{Version}} {name}".format(name=name)

    def get_network_interface_file(self, interface):
        if CONF.amphora_agent.agent_server_network_file:
            return CONF.amphora_agent.agent_server_network_file
        if CONF.amphora_agent.agent_server_network_dir:
            return os.path.join(CONF.amphora_agent.agent_server_network_dir,
                                interface + '.cfg')
        network_dir = consts.UBUNTU_AMP_NET_DIR_TEMPLATE.format(
            netns=consts.AMPHORA_NAMESPACE)
        return os.path.join(network_dir, interface + '.cfg')

    def get_network_path(self):
        return '/etc/network'

    def get_netns_network_dir(self):
        network_dir = self.get_network_path()
        return os.path.basename(network_dir)

    def create_netns_dir(
            self, network_dir=None, netns_network_dir=None, ignore=None):
        if not netns_network_dir:
            netns_network_dir = self.get_netns_network_dir()
        if not network_dir:
            network_dir = self.get_network_path()
        if not ignore:
            ignore = shutil.ignore_patterns('eth0*', 'openssh*')
        super(Ubuntu, self).create_netns_dir(
            network_dir, netns_network_dir, ignore)

    def write_interfaces_file(self):
        name = '/etc/netns/{}/network/interfaces'.format(
            consts.AMPHORA_NAMESPACE)
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

    def write_vip_interface_file(self, interface_file_path,
                                 primary_interface, vip, ip, broadcast,
                                 netmask, gateway, mtu, vrrp_ip, vrrp_version,
                                 render_host_routes, template_vip=None):
        if not template_vip:
            template_vip = j2_env.get_template(self.ETH_X_VIP_CONF)
        super(Ubuntu, self).write_vip_interface_file(
            interface_file_path, primary_interface, vip, ip, broadcast,
            netmask, gateway, mtu, vrrp_ip, vrrp_version, render_host_routes,
            template_vip)

    def write_port_interface_file(self, netns_interface, fixed_ips, mtu,
                                  interface_file_path=None,
                                  template_port=None):
        if not interface_file_path:
            interface_file_path = self.get_network_interface_file(
                netns_interface)
        if not template_port:
            template_port = j2_env.get_template(self.ETH_X_PORT_CONF)
        super(Ubuntu, self).write_port_interface_file(
            netns_interface, fixed_ips, mtu, interface_file_path,
            template_port)

    def has_ifup_all(self):
        return True


class RH(BaseOS):

    ETH_X_PORT_CONF = 'rh_plug_port_ethX.conf.j2'
    ETH_X_VIP_CONF = 'rh_plug_vip_ethX.conf.j2'
    ETH_X_ALIAS_VIP_CONF = 'rh_plug_vip_ethX_alias.conf.j2'
    ROUTE_ETH_X_CONF = 'rh_route_ethX.conf.j2'
    RULE_ETH_X_CONF = 'rh_rule_ethX.conf.j2'
    # The reason of make them as jinja templates is the current scripts force
    # to add the iptables, so leave it now for future extending if possible.
    ETH_IFUP_LOCAL_SCRIPT = 'rh_plug_port_eth_ifup_local.conf.j2'
    ETH_IFDOWN_LOCAL_SCRIPT = 'rh_plug_port_eth_ifdown_local.conf.j2'

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['fedora', 'rhel']

    def cmd_get_version_of_installed_package(self, package_name):
        name = self._map_package_name(package_name)
        return "rpm -q --queryformat %{{VERSION}} {name}".format(name=name)

    def get_network_interface_file(self, interface):
        if CONF.amphora_agent.agent_server_network_file:
            return CONF.amphora_agent.agent_server_network_file
        if CONF.amphora_agent.agent_server_network_dir:
            return os.path.join(CONF.amphora_agent.agent_server_network_dir,
                                'ifcfg-' + interface)
        network_dir = consts.RH_AMP_NET_DIR_TEMPLATE.format(
            netns=consts.AMPHORA_NAMESPACE)
        return os.path.join(network_dir, 'ifcfg-' + interface)

    def get_alias_network_interface_file(self, interface):
        return self.get_network_interface_file(interface + ':0')

    def get_static_routes_interface_file(self, interface):
        return self.get_network_interface_file('route-' + interface)

    def get_route_rules_interface_file(self, interface):
        return self.get_network_interface_file('rule-' + interface)

    def get_network_path(self):
        return '/etc/sysconfig/network-scripts'

    def get_netns_network_dir(self):
        network_full_path = self.get_network_path()
        network_basename = os.path.basename(network_full_path)
        network_dirname = os.path.dirname(network_full_path)
        network_prefixdir = os.path.basename(network_dirname)
        return os.path.join(network_prefixdir, network_basename)

    def create_netns_dir(
            self, network_dir=None, netns_network_dir=None, ignore=None):
        if not netns_network_dir:
            netns_network_dir = self.get_netns_network_dir()
        if not network_dir:
            network_dir = self.get_network_path()
        if not ignore:
            ignore = shutil.ignore_patterns('ifcfg-eth0*', 'ifcfg-lo*')
        super(RH, self).create_netns_dir(
            network_dir, netns_network_dir, ignore)

        # Copy /etc/sysconfig/network file
        src = '/etc/sysconfig/network'
        dst = '/etc/netns/{netns}/sysconfig'.format(
            netns=consts.AMPHORA_NAMESPACE)
        shutil.copy2(src, dst)

    def write_interfaces_file(self):
        # No interfaces file in RH based flavors
        return

    def write_vip_interface_file(self, interface_file_path,
                                 primary_interface, vip, ip, broadcast,
                                 netmask, gateway, mtu, vrrp_ip, vrrp_version,
                                 render_host_routes, template_vip=None):
        if not template_vip:
            template_vip = j2_env.get_template(self.ETH_X_VIP_CONF)
        super(RH, self).write_vip_interface_file(
            interface_file_path, primary_interface, vip, ip, broadcast,
            netmask, gateway, mtu, vrrp_ip, vrrp_version, render_host_routes,
            template_vip)

        # keepalived will handle the VIP if we are on active/standby
        if (ip.version == 4 and
            CONF.controller_worker.loadbalancer_topology ==
                consts.TOPOLOGY_SINGLE):
            # Create an IPv4 alias interface, needed in RH based flavors
            alias_interface_file_path = self.get_alias_network_interface_file(
                primary_interface)
            template_vip_alias = j2_env.get_template(self.ETH_X_ALIAS_VIP_CONF)
            super(RH, self).write_vip_interface_file(
                alias_interface_file_path, primary_interface, vip, ip,
                broadcast, netmask, gateway, mtu, vrrp_ip, vrrp_version,
                render_host_routes, template_vip_alias)

        routes_interface_file_path = (
            self.get_static_routes_interface_file(primary_interface))
        template_routes = j2_env.get_template(self.ROUTE_ETH_X_CONF)

        self.write_static_routes_interface_file(
            routes_interface_file_path, primary_interface,
            render_host_routes, template_routes, gateway, vip, netmask)

        # keepalived will handle the rule(s) if we are on actvie/standby
        if (CONF.controller_worker.loadbalancer_topology ==
                consts.TOPOLOGY_SINGLE):
            route_rules_interface_file_path = (
                self.get_route_rules_interface_file(primary_interface))
            template_rules = j2_env.get_template(self.RULE_ETH_X_CONF)

            self.write_static_routes_interface_file(
                route_rules_interface_file_path, primary_interface,
                render_host_routes, template_rules, gateway, vip, netmask)

        self._write_ifup_ifdown_local_scripts_if_possible()

    def write_static_routes_interface_file(self, interface_file_path,
                                           interface, host_routes,
                                           template_routes, gateway,
                                           vip, netmask):
        # write static routes interface file

        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH

        # TODO(johnsom): We need a way to clean out old interfaces records
        if CONF.amphora_agent.agent_server_network_file:
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        else:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC

        with os.fdopen(os.open(interface_file_path, flags, mode),
                       'w') as text_file:
            text = template_routes.render(
                consts=consts,
                interface=interface,
                host_routes=host_routes,
                gateway=gateway,
                network=utils.ip_netmask_to_cidr(vip, netmask),
                vip=vip,
                topology=CONF.controller_worker.loadbalancer_topology,
            )
            text_file.write(text)

    def write_port_interface_file(self, netns_interface, fixed_ips, mtu,
                                  interface_file_path=None,
                                  template_port=None):
        if not interface_file_path:
            interface_file_path = self.get_network_interface_file(
                netns_interface)
        if not template_port:
            template_port = j2_env.get_template(self.ETH_X_PORT_CONF)
        super(RH, self).write_port_interface_file(
            netns_interface, fixed_ips, mtu, interface_file_path,
            template_port)

        if fixed_ips:
            host_routes = []
            for fixed_ip in fixed_ips:
                host_routes.extend(self.get_host_routes(fixed_ip))

            routes_interface_file_path = (
                self.get_static_routes_interface_file(netns_interface))
            template_routes = j2_env.get_template(self.ROUTE_ETH_X_CONF)

            self.write_static_routes_interface_file(
                routes_interface_file_path, netns_interface,
                host_routes, template_routes, None, None, None)
            self._write_ifup_ifdown_local_scripts_if_possible()

    def bring_interfaces_up(self, ip, primary_interface, secondary_interface):
        if ip.version == 4:
            super(RH, self).bring_interfaces_up(
                ip, primary_interface, secondary_interface)
        else:
            # Secondary interface is not present in IPv6 configuration
            self._bring_if_down(primary_interface)
            self._bring_if_up(primary_interface, 'VIP')

    def has_ifup_all(self):
        return False

    def _write_ifup_ifdown_local_scripts_if_possible(self):
        if self._check_ifup_ifdown_local_scripts_exists():
            template_ifup_local = j2_env.get_template(
                self.ETH_IFUP_LOCAL_SCRIPT)
            self.write_port_interface_if_local_scripts(template_ifup_local)
            template_ifdown_local = j2_env.get_template(
                self.ETH_IFDOWN_LOCAL_SCRIPT)
            self.write_port_interface_if_local_scripts(template_ifdown_local,
                                                       ifup=False)

    def _check_ifup_ifdown_local_scripts_exists(self):
        file_names = ['ifup-local', 'ifdown-local']
        target_dir = '/sbin/'
        res = []
        for file_name in file_names:
            if os.path.exists(os.path.join(target_dir, file_name)):
                res.append(True)
            else:
                res.append(False)

        # This means we only add the scripts when both of them are non-exists
        return not any(res)

    def write_port_interface_if_local_scripts(
            self, template_script, ifup=True):
        file_name = 'ifup' + '-local'
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        if not ifup:
            file_name = 'ifdown' + '-local'
        with os.fdopen(
                os.open(os.path.join(
                    '/sbin/', file_name), flags, mode), 'w') as text_file:
            text = template_script.render()
            text_file.write(text)
        os.chmod(os.path.join('/sbin/', file_name), stat.S_IEXEC)


class CentOS(RH):

    PACKAGE_NAME_MAP = {'haproxy': 'haproxy18'}

    @classmethod
    def is_os_name(cls, os_name):
        return os_name in ['centos']
