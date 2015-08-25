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

from neutronclient.common import exceptions as neutron_client_exceptions
from oslo_log import log as logging

from octavia.common import clients
from octavia.common import data_models
from octavia.i18n import _LE, _LI
from octavia.network import base
from octavia.network import data_models as network_models
from octavia.network.drivers.neutron import utils


LOG = logging.getLogger(__name__)
SEC_GRP_EXT_ALIAS = 'security-group'


class BaseNeutronDriver(base.AbstractNetworkDriver):

    def __init__(self, region=None):
        self.sec_grp_enabled = True
        self.neutron_client = clients.NeutronAuth.get_neutron_client(region)
        extensions = self.neutron_client.list_extensions()
        self._extensions = extensions.get('extensions')
        self._check_sec_grps()

    def _check_sec_grps(self):
        aliases = [ext.get('alias') for ext in self._extensions]
        if SEC_GRP_EXT_ALIAS not in aliases:
            LOG.info(_LI('Neutron security groups are disabled.  This driver'
                         'will not manage any security groups.'))
            self.sec_grp_enabled = False

    def _port_to_vip(self, port, load_balancer):
        fixed_ip = None
        for port_fixed_ip in port.fixed_ips:
            if port_fixed_ip.subnet_id == load_balancer.vip.subnet_id:
                fixed_ip = port_fixed_ip
                break
        return data_models.Vip(ip_address=fixed_ip.ip_address,
                               subnet_id=fixed_ip.subnet_id,
                               port_id=port.id,
                               load_balancer_id=load_balancer.id)

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

    def _add_allowed_address_pair_to_port(self, port_id, ip_address):
        aap = {
            'port': {
                'allowed_address_pairs': [
                    {'ip_address': ip_address}
                ]
            }
        }
        self.neutron_client.update_port(port_id, aap)

    def _add_security_group_to_port(self, sec_grp_id, port_id):
        port_update = {'port': {'security_groups': [sec_grp_id]}}
        try:
            self.neutron_client.update_port(port_id, port_update)
        except neutron_client_exceptions.PortNotFoundClient as e:
            raise base.PortNotFound(e.message)
        except Exception as e:
            raise base.NetworkException(str(e))

    def _create_security_group(self, name):
        new_sec_grp = {'security_group': {'name': name}}
        sec_grp = self.neutron_client.create_security_group(new_sec_grp)
        return sec_grp['security_group']

    def _create_security_group_rule(self, sec_grp_id, protocol,
                                    direction='ingress', port_min=None,
                                    port_max=None):
        rule = {
            'security_group_rule': {
                'security_group_id': sec_grp_id,
                'direction': direction,
                'protocol': protocol,
                'port_range_min': port_min,
                'port_range_max': port_max
            }
        }
        self.neutron_client.create_security_group_rule(rule)

    def get_plugged_networks(self, compute_id):
        # List neutron ports associated with the Amphora
        try:
            ports = self.neutron_client.list_ports(device_id=compute_id)
        except Exception:
            message = ('Error retrieving plugged networks for compute '
                       'device {compute_id}.').format(compute_id=compute_id)
            LOG.debug(message)
            ports = {'ports': []}
        return [self._port_to_octavia_interface(
                compute_id, port) for port in ports['ports']]

    def get_network(self, network_id):
        try:
            network = self.neutron_client.show_network(network_id)
            return utils.convert_network_dict_to_model(network)
        except neutron_client_exceptions.NotFound:
            message = _LE('Network not found '
                          '(network id: {network_id}.').format(
                network_id=network_id)
            LOG.exception(message)
            raise base.NetworkNotFound(message)
        except Exception:
            message = _LE('Error retrieving network '
                          '(network id: {network_id}.').format(
                network_id=network_id)
            LOG.exception(message)
            raise base.NetworkException(message)

    def get_subnet(self, subnet_id):
        try:
            subnet = self.neutron_client.show_subnet(subnet_id)
            return utils.convert_subnet_dict_to_model(subnet)
        except neutron_client_exceptions.NotFound:
            message = _LE('Subnet not found '
                          '(subnet id: {subnet_id}.').format(
                subnet_id=subnet_id)
            LOG.exception(message)
            raise base.SubnetNotFound(message)
        except Exception:
            message = _LE('Error retrieving subnet '
                          '(subnet id: {subnet_id}.').format(
                subnet_id=subnet_id)
            LOG.exception(message)
            raise base.NetworkException(message)

    def get_port(self, port_id):
        try:
            port = self.neutron_client.show_port(port_id)
            return utils.convert_port_dict_to_model(port)
        except neutron_client_exceptions.NotFound:
            message = _LE('Port not found '
                          '(port id: {port_id}.').format(
                port_id=port_id)
            LOG.exception(message)
            raise base.PortNotFound(message)
        except Exception:
            message = _LE('Error retrieving port '
                          '(port id: {port_id}.').format(
                port_id=port_id)
            LOG.exception(message)
            raise base.NetworkException(message)
