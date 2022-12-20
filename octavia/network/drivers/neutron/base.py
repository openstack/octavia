#    Copyright 2015 Rackspace
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

from openstack.connection import Connection
import openstack.exceptions as os_exceptions
from openstack.network.v2._proxy import Proxy
from oslo_config import cfg
from oslo_log import log as logging

from octavia.common import clients
from octavia.common import data_models
from octavia.i18n import _
from octavia.network import base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import utils

LOG = logging.getLogger(__name__)
DNS_INT_EXT_ALIAS = 'dns-integration'
SEC_GRP_EXT_ALIAS = 'security-group'
QOS_EXT_ALIAS = 'qos'
CONF_GROUP = 'neutron'

CONF = cfg.CONF


class BaseNeutronDriver(base.AbstractNetworkDriver):
    def __init__(self):
        self.network_proxy: Proxy = self.os_connection.network
        self._check_extension_cache = {}
        self.sec_grp_enabled = self._check_extension_enabled(SEC_GRP_EXT_ALIAS)
        self.dns_integration_enabled = self._check_extension_enabled(
            DNS_INT_EXT_ALIAS)
        self._qos_enabled = self._check_extension_enabled(QOS_EXT_ALIAS)
        self.project_id = self.os_connection.current_project_id

    @property
    def os_connection(self) -> Connection:
        return clients.NeutronAuth.get_neutron_client()

    def _check_extension_enabled(self, extension_alias):
        if extension_alias in self._check_extension_cache:
            status = self._check_extension_cache[extension_alias]
            LOG.debug('Neutron extension %(ext)s cached as %(status)s',
                      {
                          'ext': extension_alias,
                          'status': 'enabled' if status else 'disabled'
                      })
        else:
            if self.network_proxy.find_extension(extension_alias):
                LOG.debug('Neutron extension %(ext)s found enabled',
                          {'ext': extension_alias})
                self._check_extension_cache[extension_alias] = True
            else:
                LOG.debug('Neutron extension %(ext)s is not enabled',
                          {'ext': extension_alias})
                self._check_extension_cache[extension_alias] = False
        return self._check_extension_cache[extension_alias]

    def _port_to_vip(self, port, load_balancer, octavia_owned=False):
        fixed_ip = None
        additional_ips = []
        for port_fixed_ip in port.fixed_ips:
            if (not fixed_ip and
                    port_fixed_ip.subnet_id == load_balancer.vip.subnet_id):
                fixed_ip = port_fixed_ip
            else:
                additional_ips.append(port_fixed_ip)
        if fixed_ip:
            primary_vip = data_models.Vip(ip_address=fixed_ip.ip_address,
                                          subnet_id=fixed_ip.subnet_id,
                                          network_id=port.network_id,
                                          port_id=port.id,
                                          load_balancer=load_balancer,
                                          load_balancer_id=load_balancer.id,
                                          octavia_owned=octavia_owned)
        else:
            primary_vip = data_models.Vip(ip_address=None, subnet_id=None,
                                          network_id=port.network_id,
                                          port_id=port.id,
                                          load_balancer=load_balancer,
                                          load_balancer_id=load_balancer.id,
                                          octavia_owned=octavia_owned)
        additional_vips = [
            data_models.AdditionalVip(
                ip_address=add_fixed_ip.ip_address,
                subnet_id=add_fixed_ip.subnet_id,
                network_id=port.network_id,
                port_id=port.id,
                load_balancer=load_balancer,
                load_balancer_id=load_balancer.id)
            for add_fixed_ip in additional_ips]
        return primary_vip, additional_vips

    def _nova_interface_to_octavia_interface(self, compute_id, nova_interface):
        fixed_ips = [utils.convert_fixed_ip_dict_to_model(fixed_ip)
                     for fixed_ip in nova_interface.fixed_ips]
        return network_models.Interface(compute_id=compute_id,
                                        network_id=nova_interface.net_id,
                                        port_id=nova_interface.port_id,
                                        fixed_ips=fixed_ips)

    def _port_to_octavia_interface(self, compute_id, port):
        fixed_ips = [utils.convert_fixed_ip_dict_to_model(fixed_ip)
                     for fixed_ip in port.get('fixed_ips', [])]
        return network_models.Interface(compute_id=compute_id,
                                        network_id=port['network_id'],
                                        port_id=port['id'],
                                        fixed_ips=fixed_ips)

    def _add_allowed_address_pairs_to_port(self, port_id, ip_address_list):
        aap = [{'ip_address': ip} for ip in ip_address_list]
        self.network_proxy.update_port(port_id,
                                       allowed_address_pairs=aap)

    def _add_security_group_to_port(self, sec_grp_id, port_id):
        # Note: Neutron accepts the SG even if it already exists
        try:
            self.network_proxy.update_port(
                port_id, security_groups=[sec_grp_id])
        except os_exceptions.NotFoundException as e:
            raise base.PortNotFound(str(e))
        except Exception as e:
            raise base.NetworkException(str(e))

    def _get_ports_by_security_group(self, sec_grp_id):
        all_ports = self.network_proxy.ports(project_id=self.project_id)
        filtered_ports = [
            p for p in all_ports if (p.security_group_ids and
                                     sec_grp_id in p.security_group_ids)]
        return filtered_ports

    def _create_security_group(self, name):
        sec_grp = self.network_proxy.create_security_group(name=name)
        return sec_grp

    def _create_security_group_rule(self, sec_grp_id, protocol,
                                    direction='ingress', port_min=None,
                                    port_max=None, ethertype='IPv6',
                                    cidr=None):
        rule = {
            'security_group_id': sec_grp_id,
            'direction': direction,
            'protocol': protocol,
            'port_range_min': port_min,
            'port_range_max': port_max,
            'ethertype': ethertype,
            'remote_ip_prefix': cidr,
        }

        self.network_proxy.create_security_group_rule(**rule)

    def apply_qos_on_port(self, qos_id, port_id):
        try:
            self.network_proxy.update_port(port_id, qos_policy_id=qos_id)
        except os_exceptions.ResourceNotFound as e:
            raise base.PortNotFound(str(e))
        except Exception as e:
            raise base.NetworkException(str(e))

    def get_plugged_networks(self, compute_id):
        # List neutron ports associated with the Amphora
        try:
            ports = self.network_proxy.ports(device_id=compute_id)
        except Exception:
            LOG.debug('Error retrieving plugged networks for compute '
                      'device %s.', compute_id)
            ports = tuple()
        return [self._port_to_octavia_interface(compute_id, port) for port in
                ports]

    def _get_resource(self, resource_type, resource_id, context=None):
        network = self.network_proxy
        if context and not CONF.networking.allow_invisible_resource_usage:
            network = clients.NeutronAuth.get_user_neutron_client(
                context)

        try:
            resource = getattr(
                network, f"get_{resource_type}")(resource_id)
            return getattr(utils, 'convert_%s_to_model' %
                           resource_type)(resource)
        except os_exceptions.ResourceNotFound as e:
            message = _('{resource_type} not found '
                        '({resource_type} id: {resource_id}).').format(
                resource_type=resource_type, resource_id=resource_id)
            raise getattr(base, '%sNotFound' % ''.join(
                [w.capitalize() for w in resource_type.split('_')]
            ))(message) from e
        except Exception as e:
            message = _('Error retrieving {resource_type} '
                        '({resource_type} id: {resource_id}.').format(
                resource_type=resource_type, resource_id=resource_id)
            LOG.exception(message)
            raise base.NetworkException(message) from e

    def _get_resources_by_filters(self, resource_type, unique_item=False,
                                  **filters):
        """Retrieves item(s) from filters. By default, a list is returned.

        If unique_item set to True, only the first resource is returned.
        """
        try:
            resources = getattr(
                self.network_proxy, f"{resource_type}s")(**filters)
            conversion_function = getattr(
                utils,
                'convert_%s_to_model' % resource_type)
            try:
                # get first item to see if there is at least one resource
                res_list = [conversion_function(next(resources))]
            except StopIteration:
                # pylint: disable=raise-missing-from
                raise os_exceptions.NotFoundException(
                    f'No resource of type {resource_type} found that matches '
                    f'given filter criteria: {filters}.')

            if unique_item:
                return res_list[0]
            return res_list + [conversion_function(r) for r in resources]

        except os_exceptions.NotFoundException as e:
            message = _('{resource_type} not found '
                        '({resource_type} Filters: {filters}.').format(
                resource_type=resource_type, filters=filters)
            raise getattr(base, '%sNotFound' % ''.join(
                [w.capitalize() for w in resource_type.split('_')]
            ))(message) from e
        except Exception as e:
            message = _('Error retrieving {resource_type} '
                        '({resource_type} Filters: {filters}.').format(
                resource_type=resource_type, filters=filters)
            LOG.exception(message)
            raise base.NetworkException(message) from e

    def get_network(self, network_id, context=None):
        return self._get_resource('network', network_id, context=context)

    def get_subnet(self, subnet_id, context=None):
        return self._get_resource('subnet', subnet_id, context=context)

    def get_port(self, port_id, context=None):
        return self._get_resource('port', port_id, context=context)

    def get_network_by_name(self, network_name):
        return self._get_resources_by_filters(
            'network', unique_item=True, name=network_name)

    def get_subnet_by_name(self, subnet_name):
        return self._get_resources_by_filters(
            'subnet', unique_item=True, name=subnet_name)

    def get_port_by_name(self, port_name):
        return self._get_resources_by_filters(
            'port', unique_item=True, name=port_name)

    def get_port_by_net_id_device_id(self, network_id, device_id):
        return self._get_resources_by_filters(
            'port', unique_item=True,
            network_id=network_id, device_id=device_id)

    def get_qos_policy(self, qos_policy_id):
        return self._get_resource('qos_policy', qos_policy_id)

    def qos_enabled(self):
        return self._qos_enabled

    def get_network_ip_availability(self, network):
        return self._get_resource('network_ip_availability', network.id)

    def plug_fixed_ip(self, port_id, subnet_id, ip_address=None):
        port = self.get_port(port_id).to_dict(recurse=True)
        fixed_ips = port['fixed_ips']

        new_fixed_ip_dict = {'subnet_id': subnet_id}
        if ip_address:
            new_fixed_ip_dict['ip_address'] = ip_address

        fixed_ips.append(new_fixed_ip_dict)

        try:
            updated_port = self.network_proxy.update_port(
                port_id, fixed_ips=fixed_ips)
            return utils.convert_port_to_model(updated_port)
        except Exception as e:
            raise base.NetworkException(str(e))

    def unplug_fixed_ip(self, port_id, subnet_id):
        port = self.get_port(port_id)
        fixed_ips = [
            fixed_ip.to_dict()
            for fixed_ip in port.fixed_ips
            if fixed_ip.subnet_id != subnet_id
        ]

        try:
            updated_port = self.network_proxy.update_port(
                port_id, fixed_ips=fixed_ips)
            return utils.convert_port_to_model(updated_port)
        except Exception as e:
            raise base.NetworkException(str(e))
